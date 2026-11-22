#pragma once

#include <stdint.h>

namespace display {
void begin();
void tick();
void text(uint8_t layer, const char* value, int32_t repeats);
void speed(uint8_t layer, uint8_t value);
void brightness(uint8_t value);
void effect(uint8_t method);
}
