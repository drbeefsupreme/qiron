#include <Arduino.h>
#include "protocol.h"
#include "display.h"

void protocol::write(const void* bytes, size_t size) {
    Serial.write(static_cast<const uint8_t*>(bytes), size);
}

void setup() {
    Serial.begin(9600);
    display::begin();
}

void loop() {
    static uint32_t lastByte;
    if (millis() - lastByte >= 1500) protocol::reset();
    for (unsigned i = 0; i < 1024 && Serial.available(); ++i) {
        protocol::receive(Serial.read());
        lastByte = millis();
    }
    display::tick();
}
