from pathlib import Path

from PIL import Image, ImageDraw

from pixel_gif import write_loop


COLORS = {
    "clear": "000000", "ink": "2b1e2b", "wine": "702638", "red": "b93b39",
    "scarlet": "e65743", "vermilion": "fc8961", "ochre": "bd874c",
    "gold": "f2c880", "umber": "985041", "rose": "d87258",
    "skin": "f0a777", "peach": "ffd1a1", "slate": "606575",
    "sage": "97a5a0", "linen": "dacfb4", "cream": "fff0cd", "eye": "4d7369",
}
INDEX = {name: i for i, name in enumerate(COLORS)}
PALETTE = bytes.fromhex("".join(COLORS.values()))


def frame(tick):
    image = Image.new("P", (96, 96))
    image.putpalette(PALETTE)
    d = ImageDraw.Draw(image)
    lift = 0

    def points(s):
        values = [int(n) for n in s.split()]
        return [(x, y - lift) for x, y in zip(values[::2], values[1::2])]

    def area(c, s):
        d.polygon(points(s), fill=INDEX[c])

    def line(c, s):
        d.line(points(s), fill=INDEX[c])

    def oval(c, x, y, w, h):
        d.ellipse((x, y-lift, x+w, y+h-lift), fill=INDEX[c])

    area("ink", "1 95 4 83 11 77 27 71 33 65 65 65 72 71 85 75 92 81 95 90 95 95")
    area("red", "3 95 6 84 13 78 31 72 64 67 84 76 90 81 94 90 94 95")
    area("wine", "10 95 16 84 30 76 54 75 77 78 66 88 64 95")
    area("scarlet", "5 89 8 83 18 78 24 77 19 81 11 84")
    area("scarlet", "75 75 85 78 90 83 83 80 79 80 70 87")
    for x, y in [(11, 88), (78, 86)]:
        oval("ochre", x-3, y-2, 6, 4)
        line("gold", f"{x-4} {y} {x} {y-2} {x+4} {y}")
        line("gold", f"{x} {y-4} {x} {y+3}")
    lift = int(16 <= tick % 50 < 35)

    # The outer beard locks overlap around a single mass of shadow.
    locks = [(22, 53, 9), (22, 63, 7), (26, 69, 9), (32, 75, 9),
             (39, 80, 8), (47, 83, 8), (54, 80, 9), (62, 75, 9),
             (69, 69, 9), (73, 60, 8), (72, 51, 8)]
    for c, inset in [("ink", 0), ("sage", 2)]:
        for x, y, r in locks:
            oval(c, x-r+inset, y-r+inset, 2*(r-inset), 2*(r-inset)+1)
    area("linen", "20 49 71 45 76 56 73 65 68 72 62 74 58 80 51 81 47 87 41 83 37 77 31 78 27 72 27 67 21 65 23 60 18 57")

    oval("umber", 21, 25, 53, 39)
    oval("skin", 23, 25, 48, 36)
    area("peach", "26 37 34 31 54 28 63 31 62 35 54 35 49 40 44 43 39 40 32 43 26 42")
    oval("rose", 22, 46, 17, 12)
    oval("scarlet", 24, 48, 11, 6)
    oval("skin", 25, 48, 5, 2)
    oval("rose", 53, 43, 17, 13)
    oval("scarlet", 56, 46, 12, 6)
    oval("skin", 58, 46, 6, 2)

    # A folded crown hangs clear of the temple on the right.
    area("ink", "16 36 18 25 28 12 39 6 53 3 65 4 74 9 80 18 85 31 82 37 75 35 69 23 64 33 51 35 24 44")
    area("red", "18 35 21 25 29 14 40 8 54 5 65 6 73 11 79 20 83 31 80 33 74 27 69 19 64 30 48 33 24 41")
    area("scarlet", "21 29 30 16 41 10 55 6 62 7 55 10 46 11 37 17 31 24")
    line("vermilion", "28 22 32 17 42 11 49 9")
    area("wine", "39 25 53 18 61 16 66 11 70 11 67 17 68 22 64 30 55 31 60 24 60 21 52 21")
    line("scarlet", "71 14 76 21 79 29")
    area("ink", "14 36 19 30 30 25 46 22 58 21 65 22 69 26 70 32 65 35 54 33 37 35 23 41 17 44 13 41")
    area("linen", "15 36 21 31 32 26 48 23 62 23 67 26 68 31 63 33 54 31 38 33 25 38 18 42 15 40")
    area("cream", "16 36 23 31 32 28 47 24 59 24 63 26 58 27 51 26 48 29 43 28 38 30 33 30 29 33 25 33 21 37 17 39")
    for x, y in [(24, 35), (34, 31), (47, 29), (60, 28)]:
        line("sage", f"{x} {y+2} {x+2} {y+2} {x+4} {y}")
    bob = int(22 <= tick % 50 < 40)
    oval("ink", 75, 29+bob, 16, 16)
    oval("sage", 76, 30+bob, 14, 14)
    oval("linen", 76, 30+bob, 13, 12)
    area("cream", f"76 {35+bob} 79 {31+bob} 82 {32+bob} 85 {30+bob} 88 {34+bob} 85 {35+bob} 84 {38+bob} 81 {37+bob} 79 {39+bob} 77 {38+bob}")

    area("umber", "26 41 29 37 36 36 42 40 40 42 34 40 28 42")
    area("cream", "25 41 28 37 34 35 38 36 42 40 36 38 32 38 28 41")
    area("umber", "48 38 52 33 58 32 65 36 60 36 55 35 51 39")
    area("cream", "48 37 51 33 55 31 59 31 64 34 57 33 53 35 49 39")
    for x, y, shut in [(29, 43, 63 <= tick <= 65), (51, 40, 63 <= tick <= 67)]:
        line("ink", f"{x} {y+1} {x+3} {y-1} {x+7} {y-1} {x+10} {y+1}")
        if not shut:
            oval("cream", x+1, y, 8, 3)
            oval("eye", x+2, y-1, 4, 4)
            line("ink", f"{x+3} {y} {x+3} {y+2}")
            oval("cream", x+2, y, 0, 0)
        line("umber", f"{x+3} {y+5} {x+6} {y+5} {x+8} {y+4}")
    line("umber", "63 42 66 40 68 40")
    line("rose", "65 43 68 42")
    oval("ink", 34, 56, 27, 13)
    area("rose", "39 64 45 65 52 63 55 62 53 65 48 67 44 67")

    area("cream", "20 54 22 58 25 59 23 56 29 58 32 62 38 64 35 69 29 69 32 66 27 66 23 63")
    area("cream", "58 62 64 58 71 52 74 50 73 55 78 53 75 59 70 61 71 64 65 67 60 67 63 64")
    for x, y, r in [(26,63,4), (32,70,5), (40,76,5), (49,81,5),
                     (59,74,5), (69,67,5), (48,71,4)]:
        box = (x-r, y-r-lift, x+r, y+r-lift)
        d.arc(box, 15, 222, fill=INDEX["sage"], width=2)
        d.arc((box[0], box[1]-1, box[2]-1, box[3]-2), 22, 216, fill=INDEX["cream"], width=2)
        line("linen", f"{x+1} {y-2} {x+3} {y-1} {x+2} {y+1} {x} {y+1}")
    twitch = int(42 <= tick < 46)
    area("slate", "20 53 26 55 34 51 42 50 47 53 45 59 37 63 29 63 23 60")
    area("cream", "21 53 26 56 34 52 42 51 46 54 42 58 34 61 28 61 24 58 30 58 34 56 28 57")
    lift += twitch
    area("slate", "45 53 52 49 59 49 65 51 72 49 76 44 76 51 72 56 64 59 55 59 47 56")
    area("cream", "46 53 52 50 58 50 65 53 72 50 75 46 74 51 70 55 63 57 57 57 52 54 57 55 61 55 55 52")
    lift -= twitch
    oval("umber", 37, 45, 16, 11)
    oval("rose", 37, 45, 15, 9)
    oval("skin", 38, 45, 12, 6)
    oval("peach", 39, 46, 6, 2)
    line("umber", "49 51 51 50 52 51")
    return image


if __name__ == "__main__":
    write_loop(Path(__file__).resolve().parents[1] / "priv/static/santa.gif", frame)
