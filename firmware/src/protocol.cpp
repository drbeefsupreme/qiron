#include "protocol.h"
#include "discovery.h"
#include "display.h"
#include <string.h>

namespace protocol {
enum class State { idle, method, lengthLow, lengthHigh, frame, legacyText, legacyNumber };
static State state;
static uint8_t method;
static uint16_t length;
static uint16_t offset;
static uint32_t number;
static uint8_t shift;
static char text[maxText + 1];
static bool valid;

void reset() {
    state = State::idle;
    number = 0;
    shift = 0;
    offset = 0;
    valid = true;
}

static void finishFrame() {
    if (valid) {
        if (method < 6) {
            text[length - 4] = 0;
            display::liveText(method, text, static_cast<int32_t>(number));
        } else if (method < 12) {
            display::speed(method - 6, number);
        } else if (method == 12) {
            display::brightness(number);
        } else {
            display::liveEffect(method);
        }
    }
    const uint8_t reply[] = {0xfe, static_cast<uint8_t>(!valid)};
    write(reply, sizeof(reply));
    reset();
}

static void readCommand(uint8_t byte) {
    reset();
    method = byte;
    if (byte == 0xff) {
        write(discovery, sizeof(discovery));
    } else if (byte == 0xfe) {
        state = State::method;
    } else if (method < 6) {
        state = State::legacyText;
    } else if (method <= 12) {
        state = State::legacyNumber;
    } else if (method <= 36) {
        display::effect(method);
    }
}

void receive(uint8_t byte) {
    switch (state) {
    case State::idle:
        readCommand(byte);
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
        length |= static_cast<uint16_t>(byte) << 8;
        valid = method < 6 ? length >= 4 && length <= maxText + 4
              : method <= 12 ? length == 1 : method <= 36 && length == 0;
        state = State::frame;
        if (!length) finishFrame();
        break;
    case State::frame:
        if (valid) {
            if (offset < 4) number |= static_cast<uint32_t>(byte) << (offset * 8);
            else if (byte) text[offset - 4] = static_cast<char>(byte);
            else valid = false;
        }
        if (++offset == length) finishFrame();
        break;
    case State::legacyText:
        if (!byte) {
            text[offset] = 0;
            state = State::legacyNumber;
        } else if (offset < maxText) {
            text[offset++] = static_cast<char>(byte);
        }
        break;
    case State::legacyNumber:
        if (method >= 6 && method < 12) {
            display::speed(method - 6, byte);
            reset();
        } else {
            number |= static_cast<uint32_t>(byte) << shift;
            shift += 8;
            if (shift == 32) {
                if (method == 12) display::brightness(number);
                else display::text(method, text, static_cast<int32_t>(number));
                reset();
            }
        }
        break;
    }
}
}
