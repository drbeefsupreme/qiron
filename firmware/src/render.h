#pragma once

#include <algorithm>
#include "scenes.h"
#include "films.h"
#include "film_assets.h"
#include "compositor.h"

namespace compositor {
struct FilmCaches {
    films::Cache entries[sizeof(filmLibrary)/sizeof(filmLibrary[0])];
    uint8_t indices[filmPixelCount];

    void begin() {
        uint8_t* next = indices;
        for (size_t i=0; i<sizeof(entries)/sizeof(entries[0]); ++i) {
            entries[i].frame = nullptr;
            entries[i].indices = next;
            next += filmLibrary[i].width * 96;
        }
    }
};

template<class Scroll>
void render(scenes::Surface& background, const display::Stack& stack, Levels levels, const uint32_t* started,
            uint32_t now, const rgb24* sdPixels, const display::Chart& chart, const display::Market& market, const uint32_t* quotes, const char* joinText, const char* callinText,
            films::Player& filmPlayer, FilmCaches& filmCaches, Scroll scroll) {
    background.fillScreen({0,0,0});
    auto* pixels = background.backBuffer();
    compositor::layers(stack, [&](uint8_t id) {
        int slot = filmSlot(id);
        if (id == 0) std::copy_n(sdPixels, 128 * 96, pixels);
        else if (id == 1) scenes::blood(background, chart);
        else if (slot >= 0) filmPlayer.overlay(pixels, filmLibrary[slot], filmCaches.entries[slot], now-started[id]);
        else if (id == 7) scenes::ticker(background, quotes, now-started[id]);
        else if (id == 14) scenes::banner(background, joinText, now-started[id], 0, {8,13,28});
        else if (id == 15) scenes::price(background, market.mark);
        else if (id == 16) {
            scenes::interest(background, market);
            scenes::ticker(background, quotes, now-started[id]);
        } else if (id == 17) {
            scenes::banner(background, callinText, now-started[id], 87, {0,0,0});
        } else scroll(id-8, pixels);
    });
    compositor::effects(pixels, levels.melt, levels.hue, now);
}

template<class Line>
void drawLine(Line& line, rgb24* pixels, int first = 0, int end = 96) {
    for (int y = first; y < end; ++y) line.fillRefreshRow(y, pixels + y*128);
}
}
