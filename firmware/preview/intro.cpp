#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
#include "Layer_Background.h"
#include "scenes.h"

int main() {
    static rgb24 buffers[128 * 96 * 2];
    static color_chan_t lut[256];
    static scenes::Surface panel(buffers, 128, 96, lut);
    panel.setRotation(rotation0);
    panel.begin();
    for (unsigned elapsed = 0; elapsed < 24000; elapsed += 60) {
        scenes::intro(panel, elapsed);
        static_assert(sizeof(rgb24) == 3, "RGB24 expected");
        if (std::fwrite(panel.backBuffer(), sizeof(rgb24), 128 * 96, stdout) != 128 * 96) return 1;
    }
}
