#pragma once

#include <AnimatedGIF.h>

namespace films {
struct Frame { uint32_t offset, length, end; };
struct Film {
    const uint8_t* bytes;
    const Frame* frames;
    uint16_t count, width;
    uint32_t duration;
};

struct Cache {
    const Frame* frame;
    uint8_t* indices;
    uint8_t palette[256][3];
    int transparent;
};

inline const Frame& frameAt(const Film& film, uint32_t elapsed) {
    uint32_t phase = elapsed % film.duration;
    int lo = 0, hi = film.count - 1;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (phase < film.frames[mid].end) hi = mid;
        else lo = mid + 1;
    }
    return film.frames[lo];
}

class Player {
    AnimatedGIF decoder;

    static void draw(GIFDRAW* line) {
        auto& cache = *static_cast<Cache*>(line->pUser);
        if (line->y == 0) {
            memcpy(cache.palette, line->pPalette24, sizeof(cache.palette));
            cache.transparent = line->ucHasTransparency ? line->ucTransparent : -1;
        }
        memcpy(cache.indices + line->y * line->iWidth, line->pPixels, line->iWidth);
    }

public:
    template<class Pixel>
    void overlay(Pixel* pixels, const Film& film, Cache& cache, uint32_t elapsed) {
        const Frame& frame = frameAt(film, elapsed);
        if (cache.frame != &frame) {
            decoder.begin(GIF_PALETTE_RGB888);
            if (!decoder.open(const_cast<uint8_t*>(film.bytes + frame.offset), frame.length, draw)) return;
            if (decoder.playFrame(false, nullptr, &cache) < 0) return;
            cache.frame = &frame;
        }
        const uint8_t* pixel = cache.indices;
        int offset = (128 - film.width) / 2;
        for (int y = 0; y < 96; ++y) {
            Pixel* row = pixels + y*128 + offset;
            for (int x = 0; x < film.width; ++x) {
                int index = *pixel++;
                if (index == cache.transparent) continue;
                const auto* rgb = cache.palette[index];
                row[x] = Pixel{rgb[0], rgb[1], rgb[2]};
            }
        }
    }
};
}
