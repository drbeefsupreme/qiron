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
    bool ready, hasFields, hasStack, hasChart, hasQuotes, hasMarket, stopped;
    char join[241], callin[121];
    display::Stack stack;
    uint32_t quotes[6];
    int brightness, preset, effect;
    int speeds[6];
    int32_t repeats[6];
    bool hasText[6];
    char path[241];
    display::Chart chart;
    display::Market market;
};
static Draft draft{};
DMAMEM static char stagedText[6][maxText + 1];

static void abortDraft() {
    draft.ready = false;
    display::cancelFile();
}
static bool valid, liveJoinConfigured, liveCallinConfigured, liveChart, liveMarket, liveQuotes;

void reset() {
    if (state != State::idle && (state == State::method || method == 40 || method == 41 || method == 42)) abortDraft();
    state = State::idle;
    offset = 0;
}

static uint32_t word(const uint8_t* p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}

static uint64_t wide(const uint8_t* p) {
    return uint64_t(word(p+4)) << 32 | word(p);
}

static bool fieldLength(uint8_t id, uint16_t size) {
    if (id < 6) return size >= 4 && size <= maxText + 4;
    if (id <= 12) return size == 1;
    if (id <= 36) return size == 0;
    if (id == 38) return size >= 28 && size <= 396 && (size - 12) % 16 == 0;
    if (id == 39) return size > 0 && size <= 240;
    if (id == 43) return size == 24;
    if (id == 44) return size >= 2 && size <= 2 + display::widgetCount;
    if (id == 48) return size > 0 && size <= 240;
    if (id == 49) return size == 20;
    if (id == 50) return size >= 1 && size <= 120;
    return false;
}

static bool validLength() {
    if (method == 37 || method == 40) return length == 1;
    if (method == 41) return length >= 1 && length <= maxText + 5;
    if (method == 42) return length == 0;
    if (method == 45) return length == 2;
    if (method == 46) return length == 5;
    if (method == 47) return length == 1;
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

static bool includes(uint8_t widget) {
    if (draft.hasStack) return memchr(draft.stack.ids, widget, draft.stack.count) != nullptr;
    if (draft.mode == display::Mode::gif) return widget == 0 || (widget >= 8 && widget < 14);
    return draft.mode == display::Mode::blood && (widget == 1 || widget == 15 || widget == 16);
}

static bool acceptsField(uint8_t id) {
    if (id == 44) return !draft.hasFields;
    if (id == 12) return true;
    if (id < 12) return includes(8 + id % 6);
    if (id == 38) return includes(1);
    if (id == 43) return includes(7) || includes(16);
    if (id == 49) return includes(15) || includes(16);
    if (id == 48) return includes(14);
    if (id == 50) return includes(17);
    return includes(0);
}

static bool joinGlyphs(const uint8_t* bytes, uint16_t size, char* output) {
    for (unsigned i = 0; i < size;) {
        uint32_t cp = bytes[i++];
        if (!cp) return false;
        if (cp >= 128) {
            if (cp < 0xc2 || cp > 0xf4) return false;
            unsigned extra = cp < 0xe0 ? 1 : cp < 0xf0 ? 2 : 3;
            if (i + extra > size) return false;
            cp &= 0x7f >> (extra+1);
            for (unsigned n = 0; n < extra; ++n) {
                if ((bytes[i] & 0xc0) != 0x80) return false;
                cp = (cp << 6) | (bytes[i++] & 63);
            }
            if ((extra == 2 && cp < 0x800) || (extra == 3 && cp < 0x10000) ||
                (cp >= 0xd800 && cp <= 0xdfff) || cp > 0x10ffff) return false;
        }
        *output++ = (cp >= 32 && cp <= 126) || (cp >= 160 && cp <= 255) ? char(cp) : '?';
    }
    *output = 0;
    return true;
}

static bool field(uint8_t id, uint8_t* bytes, uint16_t size, bool staged) {
    if (!fieldLength(id, size)) return false;
    if (staged) {
        if (!acceptsField(id)) return false;
        draft.hasFields = true;
    }
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
        } else {
            display::setChart(chart);
            liveChart = true;
        }
    } else if (id == 43) {
        uint32_t quotes[6];
        for (unsigned i = 0; i < 6; ++i) quotes[i] = word(bytes + 4*i);
        if (staged) {
            memcpy(draft.quotes, quotes, sizeof(quotes));
            draft.hasQuotes = true;
        } else {
            display::setQuotes(quotes);
            liveQuotes = true;
        }
    } else if (id == 49) {
        display::Market market{word(bytes),wide(bytes+4),wide(bytes+12)};
        if (!market.mark || market.mark > 1000000) return false;
        if (staged) {
            draft.hasMarket = true;
            draft.market = market;
        } else {
            display::setMarket(market);
            liveMarket = true;
        }
    } else if (id == 50) {
        for (unsigned i = 0; i < size; ++i)
            if (bytes[i] < 32 || bytes[i] > 126) return false;
        const char* text = reinterpret_cast<const char*>(bytes);
        if (staged) strcpy(draft.callin, text);
        else {
            display::setCallin(text);
            liveCallinConfigured = true;
        }
    } else if (id == 48) {
        char glyphs[241];
        if (!joinGlyphs(bytes, size, glyphs)) return false;
        if (staged) strcpy(draft.join, glyphs);
        else {
            display::setJoin(glyphs);
            liveJoinConfigured = true;
        }
    } else if (id == 44) {
        if (bytes[0] > 100 || bytes[1] > 100) return false;
        display::Stack stack{};
        stack.melt = bytes[0];
        stack.hue = bytes[1];
        for (unsigned i = 2; i < size; ++i) {
            uint8_t widget = bytes[i];
            if (widget >= sizeof(stack.ids) || memchr(stack.ids, widget, stack.count)) return false;
            stack.ids[stack.count++] = widget;
        }
        if (staged) {
            draft.stack = stack;
            draft.hasStack = true;
        } else {
            for (unsigned i = 0; i < stack.count; ++i) {
                uint8_t widget = stack.ids[i];
                if ((widget == 1 && !liveChart) || (widget == 14 && !liveJoinConfigured) ||
                    (widget == 17 && !liveCallinConfigured) ||
                    ((widget == 7 || widget == 16) && !liveQuotes) ||
                    ((widget == 15 || widget == 16) && !liveMarket)) return false;
            }
            display::setStack(stack);
        }
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
    if (!draft.ready || (includes(1) && !draft.hasChart)) return false;
    if ((includes(7) || includes(16)) && !draft.hasQuotes) return false;
    if ((includes(15) || includes(16)) && !draft.hasMarket) return false;
    if (includes(14) && !draft.join[0]) return false;
    if (includes(17) && !draft.callin[0]) return false;
    if (*draft.path && !display::prepareFile(draft.path)) return false;
    display::beginTake();
    display::setMode(draft.mode);
    if (draft.hasStack) display::setStack(draft.stack);
    if (includes(0)) display::applySource(draft.preset, draft.path, draft.stopped);
    if (draft.hasChart) {
        liveChart = true;
        display::setChart(draft.chart);
    }
    if (draft.hasQuotes) {
        liveQuotes = true;
        display::setQuotes(draft.quotes);
    }
    if (draft.hasMarket) {
        liveMarket = true;
        display::setMarket(draft.market);
    }
    if (draft.callin[0]) {
        display::setCallin(draft.callin);
        liveCallinConfigured = true;
    }
    if (draft.join[0]) {
        display::setJoin(draft.join);
        liveJoinConfigured = true;
    }
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
    if (method == 45) {
        if (payload[0] > 100 || payload[1] > 100) return false;
        display::setFx(payload[0], payload[1]);
        return true;
    }
    if (method == 46) {
        if (payload[0] != 1 && payload[0] != 2) return false;
        display::triggerBurst(payload[0], word(payload+1));
        return true;
    }
    if (method == 47) {
        if (payload[0] != 0 && payload[0] != 5 && payload[0] != 60) return false;
        display::setSpliceInterval(payload[0]);
        return true;
    }
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
