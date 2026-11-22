#pragma once

#include <AnimatedGIF.h>

namespace films {
struct Film {
    const uint8_t* bytes;
    size_t length;
    uint32_t duration;
    int offset;
};

template<class Surface>
class Player {
    struct Target {
        Surface& surface;
        int offset;
    };

    AnimatedGIF decoder;
    const Film* film;
    uint32_t cycle;
    uint32_t nextFrame;

    static void draw(GIFDRAW* line) {
        auto& target = *static_cast<Target*>(line->pUser);
        const auto y = line->iY + line->y;
        for (int i = 0; i < line->iWidth; ++i) {
            auto index = line->pPixels[i];
            if (line->ucHasTransparency && index == line->ucTransparent) {
                if (line->ucDisposalMethod == 2) target.surface.drawPixel(target.offset + line->iX + i, y, {0, 0, 0});
                continue;
            }
            const auto* rgb = line->pPalette24 + index * 3;
            target.surface.drawPixel(target.offset + line->iX + i, y, {rgb[0], rgb[1], rgb[2]});
        }
    }

public:
    void start(const Film& selected) {
        film = &selected;
        decoder.begin(GIF_PALETTE_RGB888);
        decoder.open(const_cast<uint8_t*>(film->bytes), film->length, draw);
        cycle = UINT32_MAX;
    }

    bool render(Surface& surface, uint32_t elapsed) {
        auto current = elapsed / film->duration;
        if (cycle != current) {
            cycle = current;
            decoder.reset();
            surface.fillScreen({0, 0, 0});
            nextFrame = 0;
        }
        const auto phase = elapsed % film->duration;
        if (phase < nextFrame) return false;
        Target target{surface, film->offset};
        do {
            int delayMs = 0;
            int more = decoder.playFrame(false, &delayMs, &target);
            nextFrame = more > 0 && delayMs > 0 ? nextFrame + delayMs : film->duration;
        } while (phase >= nextFrame);
        return true;
    }
};
}
