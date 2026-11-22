#pragma once

#include "display.h"
#include <stdio.h>

namespace scenes {
using Surface = SMLayerBackground<rgb24, SM_BACKGROUND_OPTIONS_NONE>;
const rgb24 ink(5, 8, 17), paper(248, 239, 201), mint(76, 241, 156), scarlet(254, 68, 85);
const rgb24 gold(255, 205, 51), grid(37, 59, 65);

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

inline void telephone(Surface& s, int t) {
    const rgb24 violet(36,9,50), pink(250,106,171);
    s.fillScreen(violet);
    int shake = t % 32 < 12 ? t % 3 - 1 : 0;
    int x = 64 + shake;
    s.fillRoundRectangle(x-30, 44, x+30, 66, 5, scarlet);
    s.fillRoundRectangle(x-20, 40, x+20, 56, 5, scarlet);
    s.fillRoundRectangle(x-27, 28, x+27, 35, 3, pink);
    for (int offset : {-21, 21}) s.fillRoundRectangle(x+offset-7, 30, x+offset+7, 40, 3, pink);
    s.fillCircle(x, 53, 11, paper);
    s.fillCircle(x, 53, 5, scarlet);
    const int dx[] = {0,6,8,6,0,-6,-8,-6}, dy[] = {-8,-6,0,6,8,6,0,-6};
    for (int i = 0; i < 8; ++i) s.drawPixel(x+dx[i], 53+dy[i], ink);
    for (int i = 0; i < 3; ++i) {
        int distance = (t+i*5)%17;
        s.drawLine(31-distance,33,27-distance,38, pink);
        s.drawLine(97+distance,33,101+distance,38, pink);
    }
    s.setFont(font5x7);
    s.drawString(26, 7, paper, "CROW SWITCHBOARD");
    s.setFont(font8x13);
    s.drawString(40, 74, pink, "CAW-IN");
}

inline void coinMint(Surface& s, int t) {
    const rgb24 green(7, 35, 20), bronze(167, 90, 22);
    s.fillScreen(green);
    s.setFont(font5x7);
    s.drawString(26, 6, mint, "TELETHON TREASURY");
    int phase = t % 32;
    int radius = phase < 16 ? 2+phase : 33-phase;
    for (int i = 0; i < 3; ++i) {
        int x = 19 + 43*i, y = 46 + ((t+9*i)%15)/3;
        for (int dx = -radius; dx <= radius; ++dx) {
            int dy = 0;
            while ((dx*dx*361 + (dy+1)*(dy+1)*radius*radius) <= 361*radius*radius) ++dy;
            s.drawLine(x+dx, y-dy, x+dx, y+dy, dx < -radius/2 ? bronze : gold);
        }
        if (radius > 9) {
            s.setFont(font8x13);
            s.drawString(x-3,y-6,bronze,"P");
        }
    }
    s.drawLine(4,70,123,70,bronze);
    s.setFont(font8x13);
    s.drawString(28, 75, gold, "PISS COIN");
}

inline void tracker(Surface& s, int t) {
    const rgb24 navy(3, 17, 25), dim(19, 76, 70);
    s.fillScreen(navy);
    for (int x = 8; x < 128; x+=12) s.drawLine(x,16,x,74,dim);
    for (int y = 20; y < 75; y+=12) s.drawLine(5,y,122,y,dim);
    s.drawCircle(64,45,18,dim);
    s.drawCircle(64,45,27,dim);
    int sweep = 5 + t%117;
    s.drawLine(sweep,16,sweep,74,mint);
    int x = 10 + (t*2)%106, y = 44 + abs(19-t%38)/2;
    s.fillRectangle(x-3,y,x+3,y+2,scarlet);
    s.drawLine(x+2,y,x+5,y-4,paper);
    s.drawLine(x+5,y-4,x+4,y-8,gold);
    s.drawLine(x+5,y-4,x+7,y-8,gold);
    s.drawPixel(x+6,y-3,scarlet);
    s.setFont(font5x7);
    s.drawString(4,4,mint,"NORTH POLE TELEMETRY");
    s.drawString(9,82,paper,"REINDEER OFF ROUTE");
}

inline void feed(Surface& s, int t) {
    s.fillScreen(ink);
    for (int i = 0; i < 23; ++i) {
        int x = (i*47 + (t/17)%5)%128;
        int head = (i*33 + t*(1+i%3))%112;
        for (int trail = 0; trail < 6; ++trail) {
            int y = head-trail*3;
            if (y >= 0 && y < 96) s.drawLine(x,y,x+1+(i+trail)%3,y,trail < 2 ? mint : grid);
        }
    }
    for (int i = 0; i < t; ++i) {
        int y = (i*31+t*2)%96;
        s.drawPixel((i*53+t/4+y/16)%128,y,paper);
    }
    s.fillRectangle(6,32,121,61,ink);
    s.setFont(font8x13);
    if (t < 45) s.drawString(12+t%3,37,mint,"CROW DATA FEED");
    else s.drawString(31,37,paper,"TLS XMAS");
    s.setFont(font5x7);
    s.drawString(t < 45 ? 37 : 26,53,scarlet,t < 45 ? "OVERLOAD" : "END TRANSMISSION");
}

inline void intro(Surface& s, uint32_t elapsed) {
    int t = (elapsed % 6000) / 60;
    switch ((elapsed / 6000) % 4) {
        case 0: telephone(s,t); break;
        case 1: coinMint(s,t); break;
        case 2: tracker(s,t); break;
        case 3: feed(s,t); break;
    }
}
}
