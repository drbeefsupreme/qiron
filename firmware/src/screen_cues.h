#pragma once

#include <stdint.h>

namespace screen_cues {
namespace detail {
constexpr int width = 128, height = 96;
constexpr int axisX[] = {1024, 887, 512, 0, -512, -887, -1024, -887, -512, 0, 512, 887};
constexpr int axisY[] = {0, 512, 887, 1024, 887, 512, 0, -512, -887, -1024, -887, -512};
constexpr int spectrum[] = {0xff487a, 0xff842e, 0xffdb54, 0x65f679, 0x35dbe6, 0x5d8bff, 0xaf70ff, 0xff69cf};

inline uint32_t mix(uint32_t n) {
    n ^= n >> 16;
    n *= 0x7feb352du;
    n ^= n >> 15;
    n *= 0x846ca68bu;
    return n ^ (n >> 16);
}

inline int magnitude(int n) { return n < 0 ? -n : n; }

struct Fracture {
    uint8_t cells[width * height];
    int hitX, hitY;
    uint32_t seed;
};

inline int triangle(int n) { return magnitude((n & 15) - 8) - 4; }

inline void split(Fracture& glass, uint32_t seed) {
    glass.seed = seed;
    glass.hitX = 38 + mix(seed) % 52;
    glass.hitY = 23 + mix(seed + 1) % 42;
    int cuts[12][3];
    for (int i = 0; i < 12; ++i) {
        uint32_t hash = mix(seed + i + 11);
        cuts[i][0] = 7 + (hash & 7);
        cuts[i][1] = 25 + ((hash >> 8) & 15);
        cuts[i][2] = 51 + ((hash >> 16) & 31);
    }
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            int dx = x - glass.hitX, dy = y - glass.hitY;
            int u = dx + triangle(dy + dx / 3) / 2;
            int v = dy + triangle(dx - dy / 2) / 2;
            int wedge = 0, projection = u * axisX[0];
            for (int i = 1; i < 12; ++i) {
                int p = u * axisX[i] + v * axisY[i];
                if (p > projection) { wedge = i; projection = p; }
            }
            int radial = projection / 1024 + (v * axisX[wedge] - u * axisY[wedge]) / 4096;
            int band = 0;
            while (band < 3 && radial > cuts[wedge][band]) ++band;
            glass.cells[y*width+x] = wedge * 4 + band;
        }
    }
    for (int i = 0; i < width * height; ++i) {
        int id = glass.cells[i];
        if ((i % width && (glass.cells[i-1] & 63) != id) ||
            (i >= width && (glass.cells[i-width] & 63) != id)) glass.cells[i] |= 128;
        else if ((i % width != width-1 && glass.cells[i+1] != id) ||
                 (i < width*(height-1) && glass.cells[i+width] != id)) glass.cells[i] |= 64;
    }
}

template<class Pixel>
inline Pixel tint(Pixel p, int rgb, int alpha) {
    int keep = 256-alpha;
    return Pixel{uint8_t((p.red*keep + (rgb>>16)*alpha)>>8),
                 uint8_t((p.green*keep + ((rgb>>8)&255)*alpha)>>8),
                 uint8_t((p.blue*keep + (rgb&255)*alpha)>>8)};
}

#if defined(__IMXRT1062__)
static DMAMEM Fracture glass;
#else
static Fracture glass;
#endif
static bool ready;

template<class Pixel>
void crack(Pixel* pixels, uint32_t ms, uint32_t seed) {
    if (!ready || glass.seed != seed) {
        split(glass, seed);
        ready = true;
    }
    int fall[48], slide[48], lag[48];
    for (int i = 0; i < 48; ++i) {
        uint32_t hash = mix(seed + i + 73);
        lag[i] = (hash & 63) * 4;
        int age = int(ms) - (2400 + (i%4)*790 + int((hash>>8)%3000));
        fall[i] = age <= 0 ? 0 : age*age / 38000;
        slide[i] = fall[i] ? (int((hash>>24)&31)-15)*age / 900 : 0;
    }
    for (int y = height-1; y >= 0; --y) {
        for (int x = 0; x < width; ++x) {
            int index = y*width+x, cell = glass.cells[index], id = cell & 63;
            Pixel pixel = pixels[index];
            if ((cell & 192) || ms < 230) {
                int dx = magnitude(x-glass.hitX), dy = magnitude(y-glass.hitY);
                int radius = dx > dy ? dx+dy/2 : dy+dx/2;
                int arrival = radius * 25 + lag[id];
                if ((cell & 192) && int(ms) >= arrival) {
                    if (cell & 128) pixel = tint(pixel, 0x050914, 220);
                    else pixel = tint(pixel, 0xc1e4f4, int(ms) < arrival+210 ? 218 : 117);
                }
                if (ms < 230 && radius <= 5 && int(ms) < 230-radius*30)
                    pixel = tint(pixel, 0xffe6c9, 216);
            }
            if (!fall[id]) { pixels[index] = pixel; continue; }
            pixels[index] = Pixel{2,3,8};
            int tx = x+slide[id], ty = y+fall[id];
            if (tx >= 0 && tx < width && ty < height) pixels[ty*width+tx] = pixel;
        }
    }
}

template<class Pixel>
inline void dot(Pixel* pixels, int x, int y, int color, int alpha) {
    if (x >= 0 && y >= 0 && x < width && y < height)
        pixels[y*width+x] = tint(pixels[y*width+x], color, alpha);
}

template<class Pixel>
void stars(Pixel* pixels, int ms, uint32_t seed) {
    ms += 510;
    int last = ms / 79;
    int first = last > 17 ? last-17 : 0;
    for (int shot = first; shot <= last; ++shot) {
        int age = ms-shot*79;
        uint32_t hash = mix(seed + shot);
        uint32_t path = mix(hash);
        int bx = 6 + (path & 127) * 115/127, by = 11 + ((path>>8)&127) * 74/127;
        int vx = 136 + ((hash>>12)&63), vy = 59 + ((hash>>20)&31);
        int flight = 325 + ((hash>>4)&511), color = hash & 7;
        int remain = flight-age;
        int hx = bx + remain*vx/1000, hy = by - remain*vy/1000;
        if (remain >= 0) {
            int length = 21 + ((path>>18)&15);
            for (int j = length; j >= 0; --j) {
                int x = hx+j, y = hy-j*vy/vx;
                int shade = spectrum[(color+j/6)&7];
                int alpha = 32 + (length-j)*208/length;
                dot(pixels, x, y, shade, alpha);
                if (j < 20) dot(pixels, x, y+1, shade, alpha*3/4);
                if (j < 7) dot(pixels, x, y-1, shade, alpha/3);
            }
            dot(pixels, hx, hy, 0xfff8f2, 256);
            dot(pixels, hx-1, hy, 0xfff8f2, 192);
            dot(pixels, hx, hy+2, spectrum[color], 146);
            dot(pixels, hx, hy-1, 0xfff8f2, 168);
        } else if (remain > -425) {
            int burst = -remain;
            for (int k = 0; k < 6; ++k) {
                int ray = (k*2 + (hash&1)) % 12;
                int reach = burst * (20 + int((path>>(3*k))&15)) / 1000;
                int x = bx + axisX[ray]*reach/1024;
                int y = by + axisY[ray]*reach/1024 + burst*burst/32000;
                dot(pixels, x, y, spectrum[(color+k)&7], 220-burst/2);
            }
        }
    }
}
}

template<class Pixel>
void draw(Pixel* pixels, uint8_t type, uint32_t elapsedMs, uint32_t seed) {
    if (elapsedMs >= 10000) return;
    if (type == 1) detail::crack(pixels, elapsedMs, seed);
    if (type == 2) detail::stars(pixels, elapsedMs, seed);
}
}
