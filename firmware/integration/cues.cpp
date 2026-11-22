#include <algorithm>
#include <array>
#include <cstdio>
#include <iostream>
#include <string>
#include <stdint.h>
#define PROGMEM
#include "cue_playback.h"

struct Pixel { uint8_t red, green, blue; };

int main() {
    CuePlayback cues;
    std::array<Pixel,128*96> panel{};
    std::string action;
    uint32_t now;
    unsigned background = 17;
    while (std::cin >> action >> now) {
        if (action == "burst") {
            unsigned type, seed;
            std::cin >> type >> seed;
            cues.trigger(type, seed, now);
        } else if (action == "splice") {
            unsigned interval;
            std::cin >> interval;
            cues.setInterval(interval, now);
        } else {
            bool present = cues.needsFrame(now);
            if (action == "take") {
                std::cin >> background;
                present = true;
            }
            fputc(present, stdout);
            if (present) {
                for (unsigned i=0; i<panel.size(); ++i)
                    panel[i] = Pixel{uint8_t(i % 128), uint8_t(background), uint8_t(i / 128)};
                cues.render(panel.data(), now);
                fwrite(panel.data(), sizeof(Pixel), panel.size(), stdout);
            }
        }
    }
}
