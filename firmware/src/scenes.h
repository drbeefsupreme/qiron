#pragma once

#include "display.h"
#include <stdio.h>

namespace scenes {
using Surface = SMLayerBackground<rgb24, SM_BACKGROUND_OPTIONS_NONE>;
const rgb24 ink(5, 8, 17), paper(248, 239, 201), mint(76, 241, 156), scarlet(254, 68, 85);
const rgb24 grid(37, 59, 65);

inline void blood(Surface& s, const display::Chart& chart) {
    s.fillScreen(ink);
    s.setFont(font5x7);
    s.drawString(3, 1, scarlet, "CROW BLOOD");
    if (!chart.count) {
        s.drawString(3, 17, paper, "AWAITING MARK");
        return;
    }
    char label[32];
    snprintf(label, sizeof(label), "%lu.%02lu", (unsigned long)(chart.mark / 100), (unsigned long)(chart.mark % 100));
    s.setFont(font8x13);
    s.drawString(3, 10, paper, label);
    uint32_t low = chart.candles[0].low, high = chart.candles[0].high;
    for (int i = 1; i < chart.count; ++i) {
        if (chart.candles[i].low < low) low = chart.candles[i].low;
        if (chart.candles[i].high > high) high = chart.candles[i].high;
    }
    auto y = [=](uint32_t price) { return high == low ? 51 : int(73 - (price - low) * 44 / (high - low)); };
    for (int y = 29; y <= 73; y += 11) s.drawLine(3, y, 124, y, grid);
    for (int i = 0; i < chart.count; ++i) {
        int x = 122 - 5 * (chart.count - 1 - i);
        const auto& c = chart.candles[i];
        bool up = c.close >= c.open;
        rgb24 color = up ? mint : scarlet;
        s.drawLine(x, y(c.high), x, y(c.low), color);
        s.fillRectangle(x-1, y(up ? c.close : c.open), x+1, y(up ? c.open : c.close), color);
    }
    s.setFont(font5x7);
    snprintf(label, sizeof(label), "BULL %lu", (unsigned long)chart.bullish);
    s.drawString(3, 78, mint, label);
    snprintf(label, sizeof(label), "BEAR %lu", (unsigned long)chart.bearish);
    s.drawString(3, 87, scarlet, label);
}
}
