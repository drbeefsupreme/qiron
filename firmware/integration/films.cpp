#include "films.h"
#include "film_assets.h"
#include <array>

struct Pixel { uint8_t red, green, blue; };

struct Panel {
    std::array<Pixel, 128 * 96> pixels;
    void fillScreen(Pixel color) { pixels.fill(color); }
    void drawPixel(int x, int y, Pixel color) { pixels.at(y * 128 + x) = color; }
};

int main(int argc, char** argv) {
    if (argc < 3) return 1;
    Panel panel;
    films::Player<Panel> player;
    if (!strcmp(argv[1], "crow")) player.start(crowFilm);
    else if (!strcmp(argv[1], "beef")) player.start(beefFilm);
    else player.start(introFilm);
    for (int i = 2; i < argc; ++i) {
        player.render(panel, strtoul(argv[i], nullptr, 10));
        fwrite(panel.pixels.data(), sizeof(Pixel), panel.pixels.size(), stdout);
    }
}
