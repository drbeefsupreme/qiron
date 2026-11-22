#include "display.h"
#include "protocol.h"
#include <cstdio>

void protocol::write(const void* bytes, size_t size) {
    fwrite(bytes, 1, size, stdout);
    fflush(stdout);
}

void display::text(uint8_t layer, const char* value, int32_t repeats) {
    fprintf(stderr, "start %u %d %s\n", layer, repeats, value);
}

void display::liveText(uint8_t layer, const char* value, int32_t repeats) {
    fprintf(stderr, "live %u %d %s\n", layer, repeats, value);
}

void display::speed(uint8_t layer, uint8_t value) {
    fprintf(stderr, "speed %u %u\n", layer, value);
}

void display::brightness(uint8_t value) {
    fprintf(stderr, "brightness %u\n", value);
}

void display::effect(uint8_t method) {
    fprintf(stderr, "effect %u\n", method);
}

void display::liveEffect(uint8_t method) {
    fprintf(stderr, "liveEffect %u\n", method);
}

int main() {
    for (int byte; (byte = getchar()) != EOF;) {
        protocol::receive(static_cast<uint8_t>(byte));
    }
}
