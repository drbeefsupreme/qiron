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

void display::setJoin(const char* glyphs) { fprintf(stderr, "join %zu\n", std::string(glyphs).size()); }
void display::setQuotes(const uint32_t* cents) {
    fprintf(stderr, "quotes");
    for (unsigned i = 0; i < 6; ++i) fprintf(stderr, " %u", cents[i]);
    fputc('\n', stderr);
}
void display::setStack(const Stack& stack) {
    fprintf(stderr, "stack %u %u", stack.melt, stack.hue);
    for (unsigned i = 0; i < stack.count; ++i) fprintf(stderr, " %u", stack.ids[i]);
    fputc('\n', stderr);
}
void display::triggerBurst(uint8_t kind, uint32_t seed) { fprintf(stderr, "burst %u %u\n", kind, seed); }
void display::setSpliceInterval(uint8_t seconds) { fprintf(stderr, "splice %u\n", seconds); }
void display::setFx(uint8_t melt, uint8_t hue) {
    fprintf(stderr, "fx %u %u\n", melt, hue);
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
