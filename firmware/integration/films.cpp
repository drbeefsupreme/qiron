#include <array>
#include <chrono>
#include <vector>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "Layer_Background.h"
#include "Layer_Scrolling.h"
#include "render.h"

int main(int argc, char** argv) {
    if (argc < 5) return 1;
    static rgb24 buffers[128*96*2], sd[128*96];
    static color_chan_t lut[256];
    scenes::Surface panel(buffers,128,96,lut);
    panel.setRotation(rotation0);
    panel.begin();
    std::fill_n(sd, 128*96, rgb24{14,22,38});
    uint8_t bitmap[128*96/8]{};
    SMLayerScrolling<rgb24, SM_SCROLLING_OPTIONS_NONE> line(bitmap,128,96);
    line.setRotation(rotation0);
    line.enableColorCorrection(false);
    line.setColor({12,220,47});
    line.setFont(font8x13);
    line.setOffsetFromTop(44);
    line.setSpeed(0);
    line.start("CROW LIVE", -1);
    static films::Cache caches[5];
    films::Player player;
    uint32_t started[display::widgetCount]{}, quotes[]{12345,6543,300,999,9000,12200};
    display::Chart chart{11000,13,7,{{9000,11000,6700,10500}},1};
    display::Market market{13050,5000000,250000000};
    if (const char* cents = getenv("RENDER_LONG_CENTS")) market.longCents = strtoull(cents,nullptr,10);
    if (const char* cents = getenv("RENDER_SHORT_CENTS")) market.shortCents = strtoull(cents,nullptr,10);
    const char* callin = getenv("RENDER_CALLIN");
    if (!callin) callin = "TELETHON CALL-IN";
    display::Stack stack{};
    for (char* word = strtok(argv[1], ","); word; word = strtok(nullptr, ",")) {
        if (stack.count >= display::widgetCount) return 1;
        stack.ids[stack.count++] = atoi(word);
    }
    compositor::Levels levels{strtof(argv[2],nullptr),strtof(argv[3],nullptr)};
    auto render = [&](uint32_t ms) {
        compositor::render(panel, stack, levels, started, ms, sd, chart, market, quotes, "SAMPLE BANNER", callin, player, caches,
            [&](uint8_t, rgb24* pixels) { compositor::drawLine(line,pixels); });
    };
    if (!strcmp(argv[4], "fade")) {
        compositor::EffectFades fades;
        unsigned now, melt, hue;
        char cmd;
        while (scanf(" %c %u", &cmd, &now) == 2) {
            if (cmd == 's') {
                if (scanf("%u %u", &melt, &hue) != 2) return 1;
                fades.set(melt,hue,now);
            } else if (cmd == 'r') {
                bool needed = fades.needsFrame();
                fputc(needed,stdout);
                if (needed) {
                    levels = fades.sample(now);
                    render(now);
                    fwrite(panel.backBuffer(),sizeof(rgb24),128*96,stdout);
                }
            } else return 1;
        }
        return 0;
    }
    if (!strcmp(argv[4], "caption") && argc == 6) {
        panel.fillScreen({0,0,0});
        panel.setFont(font5x7);
        panel.drawString(0,88,{255,240,168},argv[5]);
        fwrite(panel.backBuffer(),sizeof(rgb24),128*96,stdout);
        return 0;
    }
    if (!strcmp(argv[4], "reference") && argc == 7) {
        panel.fillScreen({0,0,0});
        panel.setFont(font5x7);
        panel.drawString(3,78,scenes::mint,argv[5]);
        panel.drawString(66,78,scenes::scarlet,argv[6]);
        fwrite(panel.backBuffer(),sizeof(rgb24),128*88,stdout);
        return 0;
    }
    if (!strcmp(argv[4], "bench")) {
        std::vector<double> times;
        unsigned checksum = 0;
        for (unsigned ms = 0; ms < 24000; ms += 33) {
            auto before = std::chrono::steady_clock::now();
            render(ms);
            times.push_back(std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-before).count());
            checksum += panel.backBuffer()[ms%(128*96)].red;
        }
        std::sort(times.begin(),times.end());
        printf("p50 %.0f us, p95 %.0f us, max %.0f us, checksum %u\n",times[times.size()/2],times[times.size()*95/100],times.back(),checksum);
        return 0;
    }
    for (int i = 4; i < argc; ++i) {
        render(strtoul(argv[i], nullptr, 10));
        fwrite(panel.backBuffer(), sizeof(rgb24), 128*96, stdout);
    }
}
