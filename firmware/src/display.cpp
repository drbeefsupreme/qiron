#include "display.h"

#include <Arduino.h>
#include <algorithm>
#include <MatrixHardware_Teensy4_ShieldV5.h>
#include <SmartMatrix.h>
#include <AnimatedGIF.h>
#include <SD.h>
#include <strings.h>
#include "render.h"
#include "cue_playback.h"

namespace {

constexpr uint16_t Width = 128, Height = 96;
SMARTMATRIX_ALLOCATE_BUFFERS(matrix, Width, Height, 36, 4, SM_PANELTYPE_HUB75_32ROW_MOD16SCAN, SM_HUB75_OPTIONS_C_SHAPE_STACKING);
SMARTMATRIX_ALLOCATE_BACKGROUND_LAYER(background, Width, Height, 24, SM_BACKGROUND_OPTIONS_NONE);
DMAMEM rgb24 sdPixels[2 * Width * Height];
color_chan_t sdLut[256];
decltype(background) sdSurface(sdPixels, Width, Height, sdLut);
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

struct Gif {
    AnimatedGIF decoder;
    File file;
};
DMAMEM films::Player filmPlayer;
DMAMEM compositor::FilmCaches filmCaches;
display::Stack stack{7, {0,8,9,10,11,12,13}, 0, 0};
uint32_t mask = 0x3f01;
char joinText[241], callinText[121];
uint32_t started[display::widgetCount], lastComposition, lastScroll;
uint32_t quotes[6];
bool dirty = true;
CuePlayback cues;
compositor::EffectFades fades;
Gif first;
DMAMEM Gif second;
Gif *live = &first, *spare = &second;
File directory, preparedDirectory;
int preparedPreset = -1;
File* opening;
rgb24* const firstFrame = sdPixels + Width * Height;
int firstDelay;
bool taking;
char exactFile[241], preparedFile[241];

display::Chart chart{};
display::Market market{};
bool hasMarket;


uint8_t preset = 4;
bool sdReady, playing = true, cycling = true, decoding;
uint32_t lastSelection, lastFrame, frameDelay;

bool includes(uint8_t id) {
    for (unsigned i = 0; i < stack.count; ++i)
        if (stack.ids[i] == id) return true;
    return false;
}

void fill(rgb24 color) {
    sdSurface.fillScreen(color);
    dirty = true;
}

void closeGif() {
    if (decoding) live->decoder.close();
    decoding = false;
    live->file.close();
    frameDelay = 0;
}

void stopGif() {
    closeGif();
    playing = false;
}

void* openFile(const char*, int32_t* size) {
    *size = opening->size();
    return opening;
}

int32_t readFile(GIFFILE* file, uint8_t* data, int32_t requested) {
    File& source = *static_cast<File*>(file->fHandle);
    int32_t bytes = source.read(data, requested);
    file->iPos = source.position();
    return bytes;
}

int32_t seekFile(GIFFILE* file, int32_t position) {
    File& source = *static_cast<File*>(file->fHandle);
    if (!source.seek(position)) return -1;
    return file->iPos = source.position();
}

void drawGifLine(GIFDRAW* line) {
    int y = line->iY + line->y;
    if (y < 0 || y >= Height) return;
    for (int i = 0; i < line->iWidth && line->iX + i < Width; ++i) {
        int x = line->iX + i;
        if (x < 0) continue;
        uint8_t index = line->pPixels[i];
        if (line->ucHasTransparency && index == line->ucTransparent) {
            if (line->ucDisposalMethod != 2) continue;
            index = line->ucBackground;
        }
        const uint8_t* color = line->pPalette24 + index * 3;
        rgb24 pixel(color[0], color[1], color[2]);
        if (line->pUser) firstFrame[y * Width + x] = pixel;
        else sdSurface.drawPixel(x, y, pixel);
    }
}

bool openDecoder(Gif& slot) {
    opening = &slot.file;
    return slot.file && !slot.file.isDirectory() &&
        slot.decoder.open("", openFile, [](void*) {}, readFile, seekFile, drawGifLine);
}

bool gifFile(File& file) {
    const char* name = file.name();
    const char* extension = strrchr(name, '.');
    return !file.isDirectory() && !strchr("~_.", name[0]) && extension &&
        strcasecmp(extension, ".gif") == 0;
}

bool openNextGif() {
    if (*exactFile) {
        live->file = SD.open(exactFile);
        decoding = openDecoder(*live);
        if (!decoding) live->file.close();
        return decoding;
    }
    if (!directory) directory = SD.open(directories[preset]);
    if (!directory) return false;
    for (int pass = 0; pass < 2; ++pass) {
        while ((live->file = directory.openNextFile())) {
            if (gifFile(live->file) && openDecoder(*live)) {
                decoding = true;
                sdSurface.fillScreen(black);
                return true;
            }
            live->file.close();
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
    int status = live->decoder.playFrame(false, &delayMs);
    lastFrame = now;
    if (status < 0) {
        closeGif();
        frameDelay = 100;
        return;
    }
    dirty = true;
    frameDelay = delayMs > 0 ? delayMs : 10;
    if (status == 0) live->decoder.reset();
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
        case 0: sdSurface.drawPixel(x,y,edge); break;
        case 1: sdSurface.drawLine(x,y,x1,y1,edge); break;
        case 2: sdSurface.drawCircle(x,y,r,edge); break;
        case 3: sdSurface.drawTriangle(x,y,x1,y1,x2,y2,edge); break;
        case 4: sdSurface.drawRectangle(x,y,x1,y1,edge); break;
        case 5: sdSurface.drawRoundRectangle(x,y,x1,y1,r,edge); break;
        case 6: sdSurface.fillCircle(x,y,r,inside); break;
        case 7: sdSurface.fillTriangle(x,y,x1,y1,x2,y2,inside); break;
        case 8: sdSurface.fillRectangle(x,y,x1,y1,inside); break;
        case 9: sdSurface.fillRoundRectangle(x,y,x1,y1,r,inside); break;
        case 10: sdSurface.fillCircle(x,y,r,edge,inside); break;
        case 11: sdSurface.fillTriangle(x,y,x1,y1,x2,y2,edge,inside); break;
        case 12: sdSurface.fillRectangle(x,y,x1,y1,edge,inside); break;
        case 13: sdSurface.fillRoundRectangle(x,y,x1,y1,r,edge,inside); break;
        case 14: sdSurface.drawEllipse(x,y,r,random(Width),edge); break;
    }
    dirty = true;
}

void drawPixels(uint32_t elapsed) {
    uint32_t offset = elapsed % 15000;
    uint8_t level = (offset % 7500) * 255 / 7500;
    rgb24 color = offset < 7500 ? rgb24(255-level, level, 0) : rgb24(0, 255-level/2, level);
    for (int i = 0; i < 20; ++i) sdSurface.drawPixel(random(Width), random(Height), color);
    dirty = true;
}

}

namespace display {

void begin() {
    filmCaches.begin();
    matrix.addLayer(&background);
    sdSurface.begin();
    sdSurface.setRotation(rotation0);
    for (auto line : lines) {
        line->begin();
        line->setRotation(rotation0);
        line->setRefreshRate(120);
        line->enableColorCorrection(false);
    }
    demo.begin();
    demo.setRotation(rotation0);
    demo.setRefreshRate(120);
    demo.enableColorCorrection(false);
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
    first.decoder.begin(GIF_PALETTE_RGB888);
    second.decoder.begin(GIF_PALETTE_RGB888);
    sdReady = SD.begin(BUILTIN_SDCARD);
    if (!sdReady) text(0, "No SD card", -1);
}

void text(uint8_t layer, const char* value, int32_t repeats) {
    if (hasText[layer] && *value && repeats == -1 && lines[layer]->getStatus() == -1) {
        lines[layer]->update(value);
    } else {
        lines[layer]->start(value, repeats);
        if (!*value) memset(lines[layer]->scrollingBitmap, 0, Width * Height / 8);
    }
    hasText[layer] = *value != 0;
    dirty = true;
}

void speed(uint8_t layer, uint8_t value) {
    lines[layer]->setSpeed(value);
}
void brightness(uint8_t value) { matrix.setBrightness(value); }

static void activate() {
    uint32_t next = 0;
    auto now = millis();
    constexpr uint32_t tickerMask = (1u << 7) | (1u << 16);
    uint32_t tickerStart = mask & tickerMask ? started[mask & (1u << 7) ? 7 : 16] : now;
    for (unsigned i=0; i<stack.count; ++i) {
        auto id = stack.ids[i];
        next |= 1u << id;
        if (!(mask & (1u << id))) started[id] = now;
    }
    if (next & tickerMask) started[7] = started[16] = tickerStart;
    if ((mask & 1) && !(next & 1)) {
        closeGif();
        demoVisible = false;
        feature.setVisible(true);
        demo.setVisible(false);
        shapesLeft = pixelBurstsLeft = 0;
        pixelsTimed = blinking = false;
    }
    mask = next;
    fades.set(stack.melt, stack.hue, now);
    dirty = true;
}

void setStack(const Stack& selected) {
    stack = selected;
    if (!taking) activate();
}

void setMode(Mode next) {
    Stack preset{};
    if (next == Mode::gif) preset = {7, {0,8,9,10,11,12,13}, 0, 0};
    else if (next == Mode::blood) preset = {3, {1,15,16}, 0, 0};
    else preset = {1, {static_cast<uint8_t>(next)}, 0, 0};
    setStack(preset);
}

void triggerBurst(uint8_t kind, uint32_t seed) { cues.trigger(kind, seed, millis()); }
void setSpliceInterval(uint8_t seconds) { cues.setInterval(seconds, millis()); }

void setFx(uint8_t melt, uint8_t hue) {
    stack.melt = melt;
    stack.hue = hue;
    fades.set(melt,hue,millis());
    dirty = true;
}

void setCallin(const char* text) {
    strcpy(callinText,text);
    dirty = true;
}

void setJoin(const char* glyphs) {
    strcpy(joinText, glyphs);
    dirty = true;
}

void setQuotes(const uint32_t* prices) {
    memcpy(quotes, prices, sizeof(quotes));
    dirty = true;
}

void setMarket(const Market& value) {
    market = value;
    hasMarket = true;
    dirty = true;
}

void setChart(const Chart& value) {
    if (!hasMarket) market.mark = value.mark;
    chart = value;
    dirty = true;
}

void cancelFile() {
    if (*preparedFile || preparedPreset >= 0) spare->decoder.close();
    preparedDirectory.close();
    preparedPreset = -1;
    spare->file.close();
    *preparedFile = 0;
}

bool decodeFirstFrame() {
    if (!openDecoder(*spare)) {
        spare->file.close();
        return false;
    }
    std::fill_n(firstFrame, Width * Height, black);
    firstDelay = 0;
    int status = spare->decoder.playFrame(false, &firstDelay, firstFrame);
    if (status < 0 || (status == 0 && spare->decoder.getLastError() != GIF_SUCCESS)) {
        spare->decoder.close();
        spare->file.close();
        return false;
    }
    if (!status) spare->decoder.reset();
    return true;
}

bool prepareFile(const char* path) {
    if (!strcmp(preparedFile, path)) return true;
    cancelFile();
    if (!sdReady) sdReady = SD.begin(BUILTIN_SDCARD);
    if (!sdReady) return false;
    spare->file = SD.open(path);
    if (!decodeFirstFrame()) return false;
    strcpy(preparedFile, path);
    return true;
}

void preparePreset(uint8_t choice) {
    cancelFile();
    if (includes(0) && preset == choice && !*exactFile && playing && decoding) return;
    if (!sdReady) sdReady = SD.begin(BUILTIN_SDCARD);
    if (!sdReady) return;
    preparedDirectory = SD.open(directories[choice]);
    if (preparedDirectory) {
        while ((spare->file = preparedDirectory.openNextFile())) {
            if (gifFile(spare->file) && decodeFirstFrame()) {
                preparedPreset = choice;
                return;
            }
            spare->file.close();
        }
    }
    preparedDirectory.close();
}

void usePrepared() {
    closeGif();
    Gif* previous = live;
    live = spare;
    spare = previous;
    strcpy(exactFile, preparedFile);
    *preparedFile = 0;
    cycling = preparedPreset >= 0;
    if (cycling) {
        directory = preparedDirectory;
        preparedDirectory = File();
    }
    preparedPreset = -1;
    playing = decoding = true;
    if (includes(0)) {
        auto* pixels = sdSurface.backBuffer();
        std::copy_n(firstFrame, Width * Height, pixels);
        dirty = true;
    }
    lastFrame = millis();
    lastSelection = lastFrame;
    frameDelay = firstDelay > 0 ? firstDelay : 10;
}

bool selectFile(const char* path) {
    if (!prepareFile(path)) return false;
    usePrepared();
    return true;
}

void applySource(int folder, const char* path, bool stopped) {
    if (folder < 0 && !*path) {
        if (stopped) stopGif();
        return;
    }
    bool same = (folder < 0 || folder == preset) && !strcmp(exactFile, path);
    if (folder >= 0 && folder != preset) {
        directory.close();
        preset = folder;
    }
    if (stopped && !*path) {
        cancelFile();
        stopGif();
        if (!same) {
            directory.close();
            *exactFile = 0;
            fill(black);
        }
        return;
    }
    if (same && (stopped || (decoding && playing))) {
        cancelFile();
    } else if (*path || preparedPreset == preset) {
        usePrepared();
    } else {
        closeGif();
        *exactFile = 0;
        directory.close();
        playing = cycling = true;
        fill(black);
    }
    if (stopped) stopGif();
}

void effect(uint8_t method) {
    if (!includes(0)) return;
    uint32_t now = millis();
    switch (method) {
        case 13:
            fill(red);
            feature.setVisible(false);
            demo.start(demoTitle, 1);
            demo.setVisible(true);
            demoVisible = true;
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
            *exactFile = 0;
            closeGif();
            playing = true;
            break;
        case 22: stopGif(); break;
        case 23:
            if (*exactFile) closeGif();
            *exactFile = 0;
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
                *exactFile = 0;
                directory.close();
                preset = method - 25;
                if (!sdReady) sdReady = SD.begin(BUILTIN_SDCARD);
                playing = cycling = true;
            }
    }
}

static void compose(uint32_t now) {
    while (background.isSwapPending()) {}
    compositor::render(background, stack, fades.sample(now), started, now, sdSurface.backBuffer(), chart, market, quotes, joinText, callinText,
                       filmPlayer, filmCaches, [](uint8_t id, rgb24* pixels) {
        if (id == 5 && demoVisible) compositor::drawLine(demo, pixels, 1, 11);
        else if (!hasText[id]) return;
        else if (id < 3) {
            auto& style = styles[id];
            compositor::drawLine(*lines[id], pixels, style.offset, style.offset + fontLookup(style.font)->Height);
        }
        else compositor::drawLine(*lines[id], pixels);
    });
    cues.render(background.backBuffer(), now);
    background.swapBuffers(false);
    lastComposition = now;
    dirty = false;
}

void beginTake() { taking = true; }

void endTake() {
    activate();
    taking = false;
    compose(millis());
    while (background.isSwapPending()) {}
}

void tick() {
    auto now = millis();
    if (now - lastScroll >= 8) {
        unsigned steps = min(15u, (now-lastScroll)/8);
        lastScroll = now - (now-lastScroll)%8;
        while (steps--) {
            for (auto line : lines) line->frameRefreshCallback();
            demo.frameRefreshCallback();
        }
    }
    if (now - lastComposition >= 33) {
        bool changed = dirty || fades.needsFrame() || cues.needsFrame(now);
        compositor::layers(stack, [&](uint8_t id) {
            int slot = filmSlot(id);
            if (slot >= 0)
                changed |= filmCaches.entries[slot].frame != &films::frameAt(filmLibrary[slot], now-started[id]);
            if (id == 7 || id == 14 || id == 16 || id == 17 || (id >= 8 && id < 14 && (hasText[id-8] || (id == 13 && demoVisible)))) changed = true;
        });
        if (changed) compose(now);
        else lastComposition = now;
    }
    if (!(mask & 1)) return;
    if (demoVisible && !demo.getStatus()) {
        demo.setVisible(false);
        feature.setVisible(true);
        demoVisible = false;
        dirty = true;
    }
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
