#pragma once

#include <algorithm>
#include "scenes.h"
#include "films.h"
#include "film_assets.h"
#include "compositor.h"

namespace compositor {
template<class Scroll>
void render(scenes::Surface& background, const display::Stack& stack, const uint32_t* started,
            uint32_t now, const rgb24* sdPixels, const display::Chart& chart, const uint32_t* quotes,
            films::Player& filmPlayer, films::Cache* filmCaches, Scroll scroll) {
    background.fillScreen({0,0,0});
    auto* pixels = background.backBuffer();
    compositor::layers(stack, [&](uint8_t id) {
        if (id == 0) std::copy_n(sdPixels, 128 * 96, pixels);
        else if (id == 1) scenes::blood(background, chart);
        else if (id <= 6) filmPlayer.overlay(pixels, filmsByLayer[id-2], filmCaches[id-2], now-started[id]);
        else if (id == 7) scenes::ticker(background, quotes, now-started[id]);
        else scroll(id-8, pixels);
    });
    compositor::effects(pixels, stack.melt, stack.hue, now);
}

template<class Line>
void drawLine(Line& line, rgb24* pixels, int first = 0, int end = 96) {
    for (int y = first; y < end; ++y) line.fillRefreshRow(y, pixels + y*128);
}
}
