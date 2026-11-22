#include "display.h"

#include <Arduino.h>
#include <MatrixHardware_Teensy4_ShieldV5.h>
#include <SmartMatrix.h>
#include <AnimatedGIF.h>
#include <SD.h>
#include <strings.h>

namespace {

constexpr uint16_t Width = 128, Height = 96;
SMARTMATRIX_ALLOCATE_BUFFERS(matrix, Width, Height, 36, 4, SM_PANELTYPE_HUB75_32ROW_MOD16SCAN, SM_HUB75_OPTIONS_C_SHAPE_STACKING);
SMARTMATRIX_ALLOCATE_BACKGROUND_LAYER(background, Width, Height, 24, SM_BACKGROUND_OPTIONS_NONE);
SMARTMATRIX_ALLOCATE_SCROLLING_LAYER(line1, Width, Height, 24, SM_SCROLLING_OPTIONS_NONE);
SMARTMATRIX_ALLOCATE_SCROLLING_LAYER(line2, Width, Height, 24, SM_SCROLLING_OPTIONS_NONE);
SMARTMATRIX_ALLOCATE_SCROLLING_LAYER(line3, Width, Height, 24, SM_SCROLLING_OPTIONS_NONE);
SMARTMATRIX_ALLOCATE_SCROLLING_LAYER(line4, Width, Height, 24, SM_SCROLLING_OPTIONS_NONE);
SMARTMATRIX_ALLOCATE_SCROLLING_LAYER(line5, Width, Height, 24, SM_SCROLLING_OPTIONS_NONE);
SMARTMATRIX_ALLOCATE_SCROLLING_LAYER(feature, Width, Height, 24, SM_SCROLLING_OPTIONS_NONE);

SMARTMATRIX_ALLOCATE_SCROLLING_LAYER(demo, Width, Height, 24, SM_SCROLLING_OPTIONS_SHORT_TEXT);
constexpr char demoTitle[] = "THE TOO LATE SHOW WITH DR. BEELZEBUB CROW";
bool demoVisible;

decltype(line1)* const lines[] = {&line1, &line2, &line3, &line4, &line5, &feature};

bool hasText[6];

struct LineStyle {
    ScrollMode mode;
    rgb24 color;
    uint8_t speed;
    fontChoices font;
    rotationDegrees rotation;
    uint8_t offset;
};

const LineStyle styles[] = {
    {wrapForward,   {255,255,255}, 10, gohufont11b, rotation0, 43},
    {bounceForward, {255,247,14},  20, gohufont11,  rotation0, 19},
    {bounceReverse, {192,35,54},   40, font8x13,    rotation0, 67},
    {wrapForward,   {0,0,255},     80, font6x10,  rotation270, 91},
    {bounceForward, {255,0,0},    120, font5x7,    rotation90, 91},
};

const rgb24 black = {0,0,0}, red = {64,0,0};
const char* const directories[] = {
    "/gifs/koyaanisqatsi", "/gifs/obama", "/gifs/flag", "/gifs/drugs", "/gifs/joker",
    "/gifs/spooky", "/gifs/subgenius", "/gifs/transparent", "/gifs/aj", "/gifs/blue", "/gifs/hank"
};

AnimatedGIF decoder;
File directory, currentFile;
uint8_t preset = 4;
bool sdReady, playing = true, cycling = true, decoding;
uint32_t lastSelection, lastFrame, frameDelay;

void fill(rgb24 color) {
    background.fillScreen(color);
    background.swapBuffers();
}

void closeGif() {
    if (decoding) decoder.close();
    decoding = false;
    currentFile.close();
    frameDelay = 0;
}

void stopGif() {
    closeGif();
    playing = false;
}

void* openFile(const char*, int32_t* size) {
    *size = currentFile.size();
    return &currentFile;
}

int32_t readFile(GIFFILE* file, uint8_t* data, int32_t requested) {
    int32_t bytes = currentFile.read(data, requested);
    file->iPos = currentFile.position();
    return bytes;
}

int32_t seekFile(GIFFILE* file, int32_t position) {
    if (!currentFile.seek(position)) return -1;
    return file->iPos = currentFile.position();
}

void drawGifLine(GIFDRAW* line) {
    int y = line->iY + line->y;
    if (y >= Height) return;
    for (int i = 0; i < line->iWidth && line->iX + i < Width; ++i) {
        uint8_t index = line->pPixels[i];
        if (line->ucHasTransparency && index == line->ucTransparent) {
            if (line->ucDisposalMethod != 2) continue;
            index = line->ucBackground;
        }
        const uint8_t* color = line->pPalette24 + index * 3;
        background.drawPixel(line->iX + i, y, {color[0], color[1], color[2]});
    }
}

bool openNextGif() {
    if (!directory) directory = SD.open(directories[preset]);
    if (!directory) return false;
    for (int pass = 0; pass < 2; ++pass) {
        while ((currentFile = directory.openNextFile())) {
            const char* name = currentFile.name();
            const char* extension = strrchr(name, '.');
            if (!currentFile.isDirectory() && !strchr("~_.", name[0]) &&
                extension && strcasecmp(extension, ".gif") == 0 &&
                decoder.open("", openFile, [](void*) {}, readFile, seekFile, drawGifLine)) {
                decoding = true;
                background.fillScreen(black);
                return true;
            }
            currentFile.close();
        }
        directory.rewindDirectory();
    }
    return false;
}

void animateGif(uint32_t now) {
    if (!sdReady || !playing) return;
    if (cycling && now - lastSelection >= 60000) closeGif();
    if (now - lastFrame < frameDelay) return;
    if (!decoding) {
        lastSelection = now;
        if (!openNextGif()) {
            lastFrame = now;
            frameDelay = 1000;
            return;
        }
    }
    int delayMs = 0;
    int status = decoder.playFrame(false, &delayMs);
    lastFrame = now;
    if (status < 0) {
        closeGif();
        frameDelay = 100;
        return;
    }
    background.swapBuffers();
    frameDelay = delayMs > 0 ? delayMs : 10;
    if (status == 0) decoder.reset();
}

uint16_t shapesLeft;
uint32_t lastShape, pixelsStarted, lastBlink;
bool shapesForeground, pixelsTimed, blinking, redNext = true;
uint16_t pixelBurstsLeft;

rgb24 randomColor() {
    return {(uint8_t)random(192), (uint8_t)random(192), (uint8_t)random(192)};
}

void drawShape() {
    int x = random(Width), y = random(Height);
    int x1 = random(Width), y1 = random(Height);
    int x2 = random(Width), y2 = random(Height);
    int r = random(Width);
    rgb24 edge = randomColor(), inside = randomColor();
    switch (random(15)) {
        case 0: background.drawPixel(x,y,edge); break;
        case 1: background.drawLine(x,y,x1,y1,edge); break;
        case 2: background.drawCircle(x,y,r,edge); break;
        case 3: background.drawTriangle(x,y,x1,y1,x2,y2,edge); break;
        case 4: background.drawRectangle(x,y,x1,y1,edge); break;
        case 5: background.drawRoundRectangle(x,y,x1,y1,r,edge); break;
        case 6: background.fillCircle(x,y,r,inside); break;
        case 7: background.fillTriangle(x,y,x1,y1,x2,y2,inside); break;
        case 8: background.fillRectangle(x,y,x1,y1,inside); break;
        case 9: background.fillRoundRectangle(x,y,x1,y1,r,inside); break;
        case 10: background.fillCircle(x,y,r,edge,inside); break;
        case 11: background.fillTriangle(x,y,x1,y1,x2,y2,edge,inside); break;
        case 12: background.fillRectangle(x,y,x1,y1,edge,inside); break;
        case 13: background.fillRoundRectangle(x,y,x1,y1,r,edge,inside); break;
        case 14: background.drawEllipse(x,y,r,random(Width),edge); break;
    }
    background.swapBuffers();
}

void drawPixels(uint32_t elapsed) {
    uint32_t offset = elapsed % 15000;
    uint8_t level = (offset % 7500) * 255 / 7500;
    rgb24 color = offset < 7500 ? rgb24(255-level, level, 0) : rgb24(0, 255-level/2, level);
    for (int i = 0; i < 20; ++i) background.drawPixel(random(Width), random(Height), color);
    background.swapBuffers();
}

}

namespace display {

void begin() {
    matrix.addLayer(&background);
    for (auto line : lines) matrix.addLayer(line);
    matrix.addLayer(&demo);
    matrix.begin();
    demo.setMode(wrapForward);
    demo.setFont(font6x10);
    demo.setSpeed(40);
    demo.setColor({255,255,255});
    demo.setVisible(false);
    for (unsigned i = 0; i < sizeof(styles)/sizeof(styles[0]); ++i) {
        auto& line = *lines[i];
        const auto& style = styles[i];
        line.setMode(style.mode);
        line.setColor(style.color);
        line.setSpeed(style.speed);
        line.setFont(style.font);
        line.setRotation(style.rotation);
        line.setOffsetFromTop(style.offset);
    }
    matrix.setBrightness(255);
    background.enableColorCorrection(true);
    decoder.begin(GIF_PALETTE_RGB888);
    sdReady = SD.begin(BUILTIN_SDCARD);
    if (!sdReady) text(0, "No SD card", -1);
}

void text(uint8_t layer, const char* value, int32_t repeats) {
    __disable_irq();
    lines[layer]->start(value, repeats);
    if (!*value) memset(lines[layer]->scrollingBitmap, 0, Width * Height / 8);
    __enable_irq();
    hasText[layer] = *value != 0;
}

void liveText(uint8_t layer, const char* value, int32_t repeats) {
    if (hasText[layer] && *value && repeats == -1 && lines[layer]->getStatus() == -1) {
        __disable_irq();
        lines[layer]->update(value);
        __enable_irq();
    } else {
        text(layer, value, repeats);
    }
}

void speed(uint8_t layer, uint8_t value) {
    __disable_irq();
    lines[layer]->setSpeed(value);
    __enable_irq();
}
void brightness(uint8_t value) { matrix.setBrightness(value); }

void effect(uint8_t method) {
    uint32_t now = millis();
    switch (method) {
        case 13:
            demoVisible = false;
            demo.setVisible(false);
            feature.setVisible(true);
            fill(red);
            feature.setColor({255,255,255});
            feature.setMode(wrapForward);
            feature.setSpeed(40);
            feature.setFont(font6x10);
            text(5, demoTitle, 1);
            break;
        case 14:
        case 16:
            shapesForeground = method == 14;
            shapesLeft = shapesForeground ? 40 : 10000;
            lastShape = now - 250;
            break;
        case 15:
        case 17:
            pixelsTimed = method == 15;
            pixelBurstsLeft = pixelsTimed ? 0 : 10000;
            pixelsStarted = now;
            if (pixelsTimed) fill(black);
            break;
        case 18: fill(black); break;
        case 19: fill(red); break;
        case 20:
            blinking = !blinking;
            lastBlink = now - 200;
            break;
        case 21:
            closeGif();
            playing = true;
            break;
        case 22: stopGif(); break;
        case 23:
            cycling = playing = true;
            lastSelection = now;
            break;
        case 24:
            cycling = false;
            stopGif();
            break;
        case 36:
            shapesLeft = pixelBurstsLeft = 0;
            pixelsTimed = cycling = false;
            stopGif();
            break;
        default:
            if (method >= 25 && method <= 35) {
                closeGif();
                directory.close();
                preset = method - 25;
                if (!sdReady) sdReady = SD.begin(BUILTIN_SDCARD);
                playing = cycling = true;
            }
    }
}

void liveEffect(uint8_t method) {
    if (method != 13) {
        effect(method);
        return;
    }
    fill(red);
    __disable_irq();
    feature.setVisible(false);
    demo.start(demoTitle, 1);
    demo.setVisible(true);
    __enable_irq();
    demoVisible = true;
}

void tick() {
    if (demoVisible && !demo.getStatus()) {
        demo.setVisible(false);
        feature.setVisible(true);
        demoVisible = false;
    }
    uint32_t now = millis();
    uint32_t elapsed = now - pixelsStarted;
    if (pixelsTimed && elapsed >= 15000) pixelsTimed = false;
    if (!pixelsTimed && !(shapesForeground && shapesLeft)) animateGif(now);
    if (shapesLeft && now - lastShape >= 250) {
        drawShape();
        --shapesLeft;
        lastShape = now;
    }
    if (pixelsTimed || pixelBurstsLeft) {
        drawPixels(elapsed);
        if (pixelBurstsLeft) --pixelBurstsLeft;
    }
    if (blinking && now - lastBlink >= 200) {
        fill(redNext ? red : black);
        redNext = !redNext;
        lastBlink = now;
    }
}

}
