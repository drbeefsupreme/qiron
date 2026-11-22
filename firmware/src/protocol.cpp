#include "protocol.h"
#include "display.h"
#include <string.h>
#include <strings.h>
#ifdef ARDUINO
#include <Arduino.h>
#else
#define DMAMEM
#endif

namespace protocol {
enum class State { idle, method, lengthLow, lengthHigh, payload };
static State state;
static uint8_t method;
static uint16_t length, offset;
static uint8_t payload[maxText + 6];
struct Draft {
    display::Mode mode;
    bool ready, hasChart, stopped;
    int brightness, preset, effect;
    int speeds[6];
    int32_t repeats[6];
    bool hasText[6];
    char path[241];
    display::Chart chart;
};
static Draft draft{};
DMAMEM static char stagedText[6][maxText + 1];

static void abortDraft() {
    draft.ready = false;
    display::cancelFile();
}
static bool valid;

void reset() {
    if (state != State::idle && (state == State::method || method == 40 || method == 41 || method == 42)) abortDraft();
    state = State::idle;
    offset = 0;
}

static uint32_t word(const uint8_t* p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}

static bool fieldLength(uint8_t id, uint16_t size) {
    if (id < 6) return size >= 4 && size <= maxText + 4;
    if (id <= 12) return size == 1;
    if (id <= 36) return size == 0;
    if (id == 38) return size >= 28 && size <= 396 && (size - 12) % 16 == 0;
    if (id == 39) return size > 0 && size <= 240;
    return false;
}

static bool validLength() {
    if (method == 37 || method == 40) return length == 1;
    if (method == 41) return length >= 1 && length <= maxText + 5;
    if (method == 42) return length == 0;
    return fieldLength(method, length);
}

static bool parseChart(const uint8_t* bytes, uint16_t size, display::Chart& chart) {
    chart.mark = word(bytes);
    chart.bullish = word(bytes+4);
    chart.bearish = word(bytes+8);
    chart.count = (size - 12) / 16;
    if (!chart.mark || chart.mark > 1000000) return false;
    for (unsigned i = 0; i < chart.count; ++i) {
        const uint8_t* p = bytes + 12 + i * 16;
        auto& c = chart.candles[i];
        c = {word(p), word(p+4), word(p+8), word(p+12)};
        if (!c.low || c.high > 1000000 || c.open < c.low || c.open > c.high ||
            c.close < c.low || c.close > c.high) return false;
    }
    return true;
}

static bool validPath(const char* path, uint16_t size) {
    if (strncmp(path, "/gifs/", 6) || strchr(path, '\\') || strstr(path, "/../") ||
        strstr(path, "/./") || memchr(path, 0, size)) return false;
    const char* filename = strchr(path+6, '/');
    return filename && filename != path+6 && !strchr(filename+1, '/') &&
        strlen(filename+1) > 4 && !strcasecmp(path+size-4, ".gif");
}

static bool field(uint8_t id, uint8_t* bytes, uint16_t size, bool staged) {
    if (!fieldLength(id, size)) return false;
    if (staged && id != 12 && ((id == 38 && draft.mode != display::Mode::blood) ||
        (id != 38 && draft.mode != display::Mode::gif))) return false;
    if (id < 6) {
        const char* value = reinterpret_cast<char*>(bytes+4);
        int32_t repeats = static_cast<int32_t>(word(bytes));
        if (memchr(value, 0, size-4)) return false;
        if (staged) {
            memcpy(stagedText[id], value, size-3);
            draft.hasText[id] = true;
            draft.repeats[id] = repeats;
        } else display::text(id, value, repeats);
    } else if (id < 12) {
        if (staged) draft.speeds[id-6] = bytes[0];
        else display::speed(id-6, bytes[0]);
    } else if (id == 12) {
        if (staged) draft.brightness = bytes[0];
        else display::brightness(bytes[0]);
    } else if (id <= 36) {
        if (!staged) display::effect(id);
        else if (id >= 25 && id <= 35) {
            draft.preset = id - 25;
            draft.path[0] = 0;
            if (!draft.stopped) display::preparePreset(draft.preset);
        }
        else if (id == 22) draft.stopped = true;
        else draft.effect = id;
    } else if (id == 38) {
        display::Chart chart{};
        if (!parseChart(bytes, size, chart)) return false;
        if (staged) {
            draft.chart = chart;
            draft.hasChart = true;
        } else display::setChart(chart);
    } else {
        const char* path = reinterpret_cast<char*>(bytes);
        if (!validPath(path, size)) return false;
        if (!staged) return display::selectFile(path);
        if (!display::prepareFile(path)) return false;
        strcpy(draft.path, path);
    }
    return true;
}

static bool take() {
    if (!draft.ready || (draft.mode == display::Mode::blood && !draft.hasChart)) return false;
    if (*draft.path && !display::prepareFile(draft.path)) return false;
    display::beginTake();
    display::setMode(draft.mode);
    if (draft.mode == display::Mode::gif) display::applySource(draft.preset, draft.path, draft.stopped);
    if (draft.hasChart) display::setChart(draft.chart);
    for (int i = 0; i < 6; ++i) {
        if (draft.speeds[i] >= 0) display::speed(i, draft.speeds[i]);
        if (draft.hasText[i]) display::text(i, stagedText[i], draft.repeats[i]);
    }
    if (draft.effect >= 0) display::effect(draft.effect);
    if (draft.brightness >= 0) display::brightness(draft.brightness);
    display::endTake();
    draft.ready = false;
    return true;
}

static bool dispatch() {
    payload[length] = 0;
    if (method == 41) return draft.ready && field(payload[0], payload+1, length-1, true);
    if (method == 42) return take();
    if (method == 37 || method == 40) {
        if (payload[0] > static_cast<uint8_t>(display::Mode::beef)) return false;
        auto mode = static_cast<display::Mode>(payload[0]);
        if (method == 37) display::setMode(mode);
        else {
            abortDraft();
            draft = {};
            draft.ready = true;
            draft.mode = mode;
            draft.brightness = draft.preset = draft.effect = -1;
            for (auto& speed : draft.speeds) speed = -1;
        }
        return true;
    }
    return field(method, payload, length, false);
}

static void finish() {
    bool ok = valid && dispatch();
    if (!ok && method >= 40 && method <= 42) abortDraft();
    const uint8_t reply[] = {0xfe, static_cast<uint8_t>(!ok)};
    write(reply, sizeof(reply));
    state = State::idle;
    offset = 0;
}

void receive(uint8_t byte) {
    switch (state) {
    case State::idle:
        if (byte == 0xfe) state = State::method;
        break;
    case State::method:
        method = byte;
        state = State::lengthLow;
        break;
    case State::lengthLow:
        length = byte;
        state = State::lengthHigh;
        break;
    case State::lengthHigh:
        length |= uint16_t(byte) << 8;
        valid = validLength();
        state = State::payload;
        if (!length) finish();
        break;
    case State::payload:
        if (valid) payload[offset] = byte;
        if (++offset == length) finish();
        break;
    }
}
}
