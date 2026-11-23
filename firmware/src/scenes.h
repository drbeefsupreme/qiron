#pragma once

#include "display.h"
#include <stdio.h>
#include <algorithm>

namespace scenes {
using Surface = SMLayerBackground<rgb24, SM_BACKGROUND_OPTIONS_NONE>;
const rgb24 ink(5, 8, 17), paper(248, 239, 201), mint(76, 241, 156), scarlet(254, 68, 85);
const rgb24 grid(37, 59, 65);

inline void blood(Surface& s, const display::Chart& chart) {
    for (int y = 29; y <= 73; y += 11) s.drawLine(3, y, 124, y, grid);
    if (!chart.count) return;
    uint32_t low = chart.candles[0].low, high = chart.candles[0].high;
    for (int i = 1; i < chart.count; ++i) {
        if (chart.candles[i].low < low) low = chart.candles[i].low;
        if (chart.candles[i].high > high) high = chart.candles[i].high;
    }
    auto y = [=](uint32_t price) { return high == low ? 51 : int(73 - (price - low) * 44 / (high - low)); };
    for (int i = 0; i < chart.count; ++i) {
        int x = 122 - 5 * (chart.count - 1 - i);
        const auto& c = chart.candles[i];
        bool up = c.close >= c.open;
        rgb24 color = up ? mint : scarlet;
        s.drawLine(x, y(c.high), x, y(c.low), color);
        s.fillRectangle(x-1, y(up ? c.close : c.open), x+1, y(up ? c.open : c.close), color);
    }
}

inline void price(Surface& s, uint32_t cents) {
    char label[20];
    snprintf(label, sizeof(label), "%lu.%02lu", (unsigned long)(cents/100), (unsigned long)(cents%100));
    s.setFont(font5x7);
    s.drawString(3, 1, scarlet, "BABY BLOOD");
    s.setFont(font8x13);
    s.drawString(3, 10, paper, label);
}

inline void positionValue(char* label, size_t size, const char* side, uint64_t cents) {
    const char suffix[] = " KMBTQ";
    uint64_t scale = 100;
    unsigned power = 0;
    while (power < sizeof(suffix)-2 && cents/scale >= 1000) {
        scale *= 1000;
        ++power;
    }
    unsigned whole = cents/scale;
    unsigned fraction = (cents % scale) * 100 / scale;
    char value[12];
    if (!power && fraction % 10) snprintf(value, sizeof(value), "%u.%02u", whole, fraction);
    else if (fraction >= 10) snprintf(value, sizeof(value), "%u.%u", whole, fraction/10);
    else snprintf(value, sizeof(value), "%u", whole);
    if (power) snprintf(label, size, "%s %s%c", side, value, suffix[power]);
    else snprintf(label, size, "%s %s", side, value);
}

inline void interest(Surface& s, const display::Market& market) {
    char label[32];
    s.setFont(font5x7);
    positionValue(label, sizeof(label), "LONG", market.longCents);
    s.drawString(3, 78, mint, label);
    positionValue(label, sizeof(label), "SHORT", market.shortCents);
    s.drawString(66, 78, scarlet, label);
}

inline void banner(Surface& s, const char* text, uint32_t elapsed, int top, rgb24 ground) {
    const rgb24 yellow(255,240,168);
    s.fillRectangle(0,top,127,top+8,ground);
    const int length = strlen(text);
    const int period = length * 5 + 18;
    const int phase = (elapsed / 50) % period;
    for (int origin = -phase; origin < 128; origin += period) {
        for (int i = std::max(0, -origin / 5); i < length && origin + i*5 < 128; ++i) {
            auto glyph = std::lower_bound(apple5x7.Index, apple5x7.Index + apple5x7.Chars, uint8_t(text[i]));
            if (glyph == apple5x7.Index + apple5x7.Chars || *glyph != uint8_t(text[i])) continue;
            const uint8_t* rows = apple5x7.Bitmap + (glyph - apple5x7.Index) * 7;
            for (int y = 0; y < 7; ++y)
                for (int x = 0; x < 5; ++x)
                    if (rows[y] & (0x80 >> x)) s.drawPixel(origin + i*5 + x, top+y+1, yellow);
        }
    }
}

inline void ticker(Surface& background, const uint32_t* quotes, uint32_t elapsed) {
    static const char* const names[] = {"PISSCOIN","PRICECOIN","BONER","FARTCOIN","ROGUE","CROW"};
    static const rgb24 colors[] = {{255,216,74},{84,207,255},{255,119,183},{169,236,92},{193,142,255},{255,146,89}};
    char label[6][32];
    int widths[6], period = 0;
    for (int i=0; i<6; ++i) {
        snprintf(label[i], sizeof(label[i]), "%s %lu.%02lu", names[i], (unsigned long)(quotes[i]/100), (unsigned long)(quotes[i]%100));
        widths[i] = strlen(label[i])*5 + 12;
        period += widths[i];
    }
    background.fillRectangle(0,87,127,95,{0,0,0});
    background.setFont(font5x7);
    int x = int((elapsed / 40) % period) - period;
    while (x < 128) {
        for (int i=0; i<6; ++i) {
            if (x < 128 && x + widths[i] > 0) background.drawString(x,88,colors[i],label[i]);
            x += widths[i];
        }
    }
}

}
