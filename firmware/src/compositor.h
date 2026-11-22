#pragma once

#include <math.h>
#include <stdint.h>
#include "display.h"

namespace compositor {
template<class Draw>
void layers(const display::Stack& stack, Draw draw) {
    int first = 0;
    for (int i = 1; i < stack.count; ++i)
        if (stack.ids[i] <= 2) first = i;
    for (int i = first; i < stack.count; ++i) draw(stack.ids[i]);
}

inline uint8_t channel(int value) {
    return value < 0 ? 0 : value > 255 ? 255 : value;
}

template<class Pixel>
void effects(Pixel* pixels, uint8_t melt, uint8_t hue, uint32_t now) {
    if (!melt && !hue) return;
    float t = float(now % 60000) * (6.2831853f / 60000);
    for (int x = 0; x < 128; ++x) {
        float wave = .5f + .32f * sinf(x * .11f + t * 9) + .18f * sinf(x * .27f - t * 5);
        int drop = int(wave * wave * melt * .48f);
        float angle = hue * .030f * sinf(x * .044f + t * 11);
        int a = 0, b = 0, c = 0;
        if (hue) {
            float cosine = cosf(angle);
            a = lroundf((1 + 2 * cosine) * (256.f / 3));
            b = lroundf(((1 - cosine)/3 - sinf(angle) * .57735027f) * 256);
            c = 256 - a - b;
        }
        for (int y = 95; y >= 0; --y) {
            Pixel value = y >= drop ? pixels[(y-drop)*128+x] : Pixel{0,0,0};
            if (hue) {
                int r = value.red, g = value.green, bl = value.blue;
                value = Pixel{channel((a*r+b*g+c*bl+128)>>8), channel((c*r+a*g+b*bl+128)>>8),
                         channel((b*r+c*g+a*bl+128)>>8)};
            }
            pixels[y*128+x] = value;
        }
    }
}
}
