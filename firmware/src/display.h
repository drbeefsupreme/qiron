#pragma once

#include <stdint.h>

namespace display {
enum class Mode : uint8_t { gif, blood, intro, crow, beef };
struct Stack { uint8_t count, ids[14], melt, hue; };
void setStack(const Stack& stack);
void setQuotes(const uint32_t* cents);
void setFx(uint8_t melt, uint8_t hue);
struct Candle { uint32_t open, high, low, close; };
struct Chart {
    uint32_t mark, bullish, bearish;
    Candle candles[24];
    uint8_t count;
};
void begin();
void tick();
void text(uint8_t layer, const char* value, int32_t repeats);
void speed(uint8_t layer, uint8_t value);
void brightness(uint8_t value);
void effect(uint8_t method);
void beginTake();
void endTake();
void setMode(Mode mode);
void setChart(const Chart& chart);
void cancelFile();
void preparePreset(uint8_t choice);
void applySource(int folder, const char* path, bool stopped);
bool prepareFile(const char* path);
bool selectFile(const char* path);
}
