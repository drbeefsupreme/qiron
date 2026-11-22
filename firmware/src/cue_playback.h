#pragma once

#include <stdint.h>
#include "screen_cues.h"
#include "splice_assets.h"

class CuePlayback {
    uint32_t burstStart = 0, seed = 0, lastSplice = 0;
    uint8_t burst = 0, seconds = 0, nextPhoto = 0;
    bool showingPhoto = false;

    bool due(uint32_t now) const {
        return seconds && now - lastSplice >= uint32_t(seconds) * 1000;
    }

public:
    void trigger(uint8_t kind, uint32_t newSeed, uint32_t now) {
        burst = kind;
        seed = newSeed;
        burstStart = now;
    }

    void setInterval(uint8_t interval, uint32_t now) {
        if (interval == seconds) return;
        nextPhoto = 0;
        seconds = interval;
        lastSplice = now;
    }

    bool needsFrame(uint32_t now) const {
        return burst || showingPhoto || due(now);
    }

    template<class Pixel>
    void render(Pixel* pixels, uint32_t now) {
        if (burst && now - burstStart >= 10000) burst = 0;
        bool restore = showingPhoto;
        showingPhoto = false;
        if (due(now)) {
            uint32_t interval = uint32_t(seconds) * 1000;
            uint32_t slots = (now - lastSplice) / interval;
            lastSplice += slots * interval;
            nextPhoto ^= slots & 1;
            if (!restore) {
                const uint16_t* source = splicePhotos + (nextPhoto ^ 1) * 128 * 96;
                for (unsigned i = 0; i < 128 * 96; ++i) {
                    unsigned packed = source[i];
                    unsigned r = packed >> 11, g = (packed >> 5) & 63, b = packed & 31;
                    pixels[i] = Pixel{uint8_t((r << 3) | (r >> 2)), uint8_t((g << 2) | (g >> 4)),
                                      uint8_t((b << 3) | (b >> 2))};
                }
                showingPhoto = true;
                return;
            }
        }
        if (burst) screen_cues::draw(pixels, burst, now - burstStart, seed);
    }
};
