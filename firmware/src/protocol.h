#pragma once

#include <stddef.h>
#include <stdint.h>

namespace protocol {
constexpr size_t maxText = 32767;
void receive(uint8_t byte);
void reset();
void write(const void* bytes, size_t size);
}
