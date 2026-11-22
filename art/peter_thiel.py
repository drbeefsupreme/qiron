from pathlib import Path

from PIL import Image, ImageDraw

from pixel_gif import write_loop


COLORS = {
    "clear": "000000", "ink": "1a1925", "jacket": "263044", "lapel": "39485b",
    "edge": "526576", "shirt": "afbec7", "linen": "e8e5da", "fold": "8297a6",
    "hair": "392b30", "brown": "54403e", "strand": "785d54", "silver": "a38a79",
    "shade": "956a69", "skin": "cf9c88", "light": "e4b69a", "lit": "f3ccab",
    "warm": "bb877c", "crease": "80595a", "lip": "ae7371", "iris": "58676a",
}
PALETTE = bytes.fromhex("".join(COLORS.values()))
INDEX = {color: i for i, color in enumerate(COLORS)}


def frame(tick):
    image = Image.new("P", (96, 96))
    image.putpalette(PALETTE)
    pen = ImageDraw.Draw(image)
    lift = int(13 <= tick < 32 or 68 <= tick < 89)

    def area(color, *xy):
        pen.polygon(xy, fill=INDEX[color])

    def line(color, *xy):
        pen.line(xy, fill=INDEX[color])

    # Shoulders lift into the collar. The bottom stays anchored to the crop.
    area("ink", 0,96, 1,84-lift, 6,78-lift, 26,71-lift, 37,64, 61,65,
         71,70-lift, 87,76-lift, 92,80-lift, 96,92-lift, 96,96)
    area("jacket", 1,95, 3,84-lift, 7,79-lift, 30,71-lift, 39,68,
         64,68, 85,77-lift, 90,81-lift, 95,95)
    line("lapel", 3,86-lift, 7,80-lift, 24,74-lift)
    line("lapel", 9,95, 10,88-lift, 8,81-lift)
    area("lapel", 17,78-lift, 34,67, 38,66, 48,95, 34,95, 22,84-lift,
         27,81-lift)
    line("edge", 19,78-lift, 34,69)
    line("jacket", 25,85-lift, 34,92, 38,95)
    area("lapel", 57,95, 61,70, 64,68, 73,74-lift, 76,79-lift,
         69,80-lift, 72,83-lift, 62,95)
    line("edge", 62,92, 70,83-lift)
    line("edge", 75,91-lift, 84,89-lift)
    area("fold", 34,69, 39,63, 59,64, 65,69, 64,78, 59,95, 44,95)
    area("shirt", 35,70, 40,66, 58,69, 63,73, 58,95, 46,95)
    area("shade", 37,54, 55,54, 62,58, 60,71, 55,83, 48,77, 39,71)
    area("warm", 39,60, 53,64, 61,58, 58,72, 54,80, 48,74, 41,69)
    area("skin", 43,68, 52,70, 58,67, 56,73, 53,76, 48,72)
    area("linen", 34,68, 37,64, 43,70, 52,77, 45,85, 39,79)
    area("linen", 55,82, 60,71, 61,65, 64,69, 64,77, 61,85, 60,78)
    line("fold", 54,83, 52,89, 53,95)
    pen.point((55,90), fill=INDEX["linen"])

    # The near ear sits well behind the brow in three-quarter view.
    area("ink", 22,26, 25,17, 35,9, 47,6, 60,8, 67,13, 70,22,
         70,32, 71,39, 70,43, 73,48, 71,50, 69,50, 69,56, 67,62,
         60,68, 54,70, 45,69, 36,63, 30,56, 28,50, 24,50, 20,45, 19,38)
    area("shade", 23,28, 31,18, 46,10, 60,11, 67,17, 69,24, 69,33,
         70,39, 68,43, 71,48, 68,50, 68,56, 65,62, 59,67, 53,69,
         45,67, 36,61, 30,53, 28,48, 24,49, 21,44, 20,38)
    area("skin", 30,29, 38,16, 51,12, 62,15, 67,19, 69,29, 67,35,
         69,40, 66,44, 69,48, 66,50, 67,56, 64,62, 57,66, 48,65,
         39,61, 34,56, 31,48)
    area("light", 33,29, 40,19, 51,14, 61,16, 66,20, 68,29, 66,33,
         61,34, 57,37, 53,35, 46,33, 38,35, 34,36)
    line("skin", 44,24, 49,22, 55,22, 61,21)
    line("skin", 47,27, 52,26, 58,26)
    area("warm", 31,37, 38,34, 47,32, 53,34, 55,38, 50,39, 47,42,
         39,43, 35,46, 32,44)
    area("warm", 58,35, 63,32, 68,32, 69,37, 66,39, 61,39)
    area("light", 34,45, 39,42, 44,43, 51,41, 55,40, 53,45, 48,47,
         42,53, 37,53)
    area("skin", 22,37, 25,36, 29,39, 29,46, 26,48, 23,45)
    line("crease", 22,39, 25,38, 27,40, 26,42, 24,42, 26,45)
    area("hair", 21,37, 20,29, 21,20, 24,14, 29,11, 31,7, 38,5,
         44,3, 53,4, 61,6, 66,10, 68,15, 68,20, 64,18, 60,15, 52,14,
         46,16, 41,21, 35,21, 32,25, 31,32, 28,35, 28,40, 26,39, 25,35)
    area("brown", 23,27, 23,20, 27,14, 33,12, 41,8, 53,6, 60,8,
         50,8, 42,12, 36,17, 30,18, 25,24)
    area("brown", 34,8, 39,6, 46,4, 52,5, 45,6, 39,9, 31,12)
    line("strand", 23,24, 27,18, 30,16, 35,15, 40,11, 45,9)
    line("strand", 30,12, 37,10, 43,7, 49,6)
    line("brown", 25,31, 28,24, 33,20, 39,19, 46,14, 54,12)
    line("strand", 58,8, 61,10, 65,14, 66,17)
    line("brown", 56,10, 61,12, 65,16)
    line("silver", 28,31, 30,26, 32,24)
    line("strand", 25,33, 26,29, 28,26)

    area("brown", 37,35, 40,32, 46,31, 51,32, 53,35, 48,34, 43,33)
    area("brown", 59,34, 62,31, 66,30, 68,31, 68,32, 64,32, 61,34)
    line("strand", 39,33, 44,32, 48,32)
    line("warm", 39,41, 44,42, 49,41, 51,39)
    line("warm", 62,40, 66,39, 68,37)
    glance = int(48 <= tick < 63)
    for x, y, width in [(39,37,12), (61,36,7)]:
        line("crease", x,y, x+3,y-2, x+width-3,y-2, x+width,y)
        if tick in (31,32,81):
            line("crease", x,y, x+3,y+1, x+width-3,y+1, x+width,y)
        else:
            line("linen", x+1,y+1, x+width-2,y)
            pupil = x + width//2 + glance
            line("iris", pupil-1,y, pupil+1,y)
            pen.point((pupil,y+1), fill=INDEX["ink"])
            line("ink", x+1,y, x+3,y-1, x+width-3,y-1)
    area("warm", 54,37, 57,34, 59,35, 61,42, 65,46, 66,48,
         63,50, 58,49, 54,50, 52,48)
    area("light", 56,36, 58,35, 60,42, 64,45, 65,47, 60,47, 57,45)
    line("lit", 58,38, 59,42, 62,45)
    line("crease", 53,48, 55,47, 58,49, 61,49)
    line("shade", 62,49, 65,48)
    line("warm", 52,50, 49,52, 47,56)
    area("light", 50,54, 53,51, 56,51, 57,54, 60,51, 63,51, 66,54,
         62,56, 56,55)
    area("lip", 48,56, 53,55, 57,54, 60,55, 63,54, 66,54,
         63,57, 58,58, 53,58)
    line("crease", 48,56, 52,56, 56,55, 60,55, 64,54, 66,54)
    line("skin", 54,57, 59,57, 62,56)
    line("warm", 53,60, 57,59, 61,59)
    area("light", 48,61, 54,61, 59,60, 64,60, 61,63, 56,65, 52,65)
    return image


if __name__ == "__main__":
    write_loop(Path(__file__).resolve().parents[1] / "priv/static/peter-thiel.gif", frame)
