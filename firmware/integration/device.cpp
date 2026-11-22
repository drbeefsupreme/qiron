#include "display.h"
#include "protocol.h"
#include <cstdio>
#include <string>

void protocol::write(const void* bytes, size_t size) {
    fwrite(bytes, 1, size, stdout);
    fflush(stdout);
}

void display::text(uint8_t layer, const char* value, int32_t repeats) {
    fprintf(stderr, "start %u %d %s\n", layer, repeats, value);
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

int main() {
    for (int byte; (byte = getchar()) != EOF;) {
        protocol::receive(static_cast<uint8_t>(byte));
    }
}

void display::setMode(Mode mode) { fprintf(stderr, "mode %u\n", unsigned(mode)); }
void display::setChart(const Chart& c) {
    fprintf(stderr, "chart %u %u %u %u %u\n", c.mark, c.bullish, c.bearish, c.count, c.candles[c.count-1].close);
}

void display::beginTake() { fprintf(stderr, "beginTake\n"); }
void display::endTake() { fprintf(stderr, "endTake\n"); }
void display::cancelFile() {}
bool display::prepareFile(const char* path) { return std::string(path) == "/gifs/joker/caw.gif"; }
bool display::selectFile(const char* path) {
    if (!prepareFile(path)) return false;
    fprintf(stderr, "file %s\n", path);
    return true;
}

void display::preparePreset(uint8_t folder) { fprintf(stderr, "prepare preset %u\n", unsigned(folder)); }
void display::applySource(int folder, const char* path, bool stopped) {
    fprintf(stderr, "source %d %s %u\n", folder, path, unsigned(stopped));
}
