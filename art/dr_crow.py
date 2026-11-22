from math import sin, tau
from pathlib import Path
from random import Random
from PIL import Image, ImageDraw
from pixel_gif import write_loop

SIZE = 96
COLORS = {
    "clear": "000000", "ink": "100d19", "coal": "211b2b", "curl": "372c40", "plum": "524055",
    "rim": "817385", "night": "302548", "shadow": "64495f", "rose": "986a82",
    "skin": "c397ac", "lit": "ead0d5", "steel": "595b78", "chrome": "a7b9c9",
    "ice": "e0f3ef", "white": "fff6dc", "pin": "bb3f49", "gold": "dfab62",
}
INDEX = {name: i for i, name in enumerate(COLORS)}
PALETTE = bytes.fromhex("".join(COLORS.values()))


def frame(tick):
    image = Image.new("P", (SIZE, SIZE))
    image.putpalette(PALETTE)
    pen = ImageDraw.Draw(image)
    lift = int(18 <= tick < 38 or 74 <= tick < 90)

    def points(s):
        v = list(map(int, s.split()))
        return list(zip(v[::2], v[1::2]))

    def area(color, s):
        pen.polygon(points(s), fill=INDEX[color])

    def line(color, s):
        pen.line(points(s), fill=INDEX[color], width=1)

    def dot(color, x, y):
        pen.point((x, y), fill=INDEX[color])

    def oval(color, x, y, w, h):
        pen.ellipse((x, y, x+w, y+h), fill=INDEX[color])

    area("ink", "0 96 3 82 12 77 17 70 30 67 41 62 58 61 71 65 86 69 91 77 95 82 95 96")
    area("night", "0 95 5 83 18 77 24 71 36 69 32 95")
    area("coal", "42 68 60 64 78 68 90 76 95 88 95 95 40 95")
    area("chrome", "56 70 78 68 88 72 84 74 57 75")
    area("steel", "55 74 84 72 82 75 56 78")
    area("chrome", "53 83 86 81 88 85 53 88")
    area("steel", "53 87 88 84 88 86 53 90")
    area("chrome", "17 77 31 72 29 78 15 83")
    line("ice", "55 72 61 71 77 69")
    line("ink", "74 69 74 75 75 79 72 82 69 79 68 71")
    area("pin", "69 70 73 70 74 78 72 80 70 78")
    line("lit", "71 70 72 78")
    oval("ink", 69,80,6,7)
    oval("gold", 70,81,4,5)
    dot("white",71,82)
    line("steel","53 72 50 80 49 88 47 95")
    line("ice","55 72 52 80 50 91")
    area("ink","30 67 38 62 58 60 65 66 60 73 47 77 38 74")
    line("plum","38 69 46 72 58 70")

    area("ink","14 69 9 61 9 45 13 34 17 26 27 21 30 12 35 6 45 3 57 5 65 10 67 20 74 18 83 21 89 31 90 50 86 63 86 72 81 77 76 78 70 68 60 60 43 60 29 65 23 72")
    rng = Random(937)
    curls = []
    for cx, cy, sx, sy in [(19,46,12,23),(74,47,13,25),(46,14,17,10)]:
        for j in range(110):
            x = rng.uniform(-1,1)
            y = rng.uniform(-1,1)
            if x*x + y*y > 1: continue
            sway = round(.7*sin(tau*tick/100 + cy*.06)) if abs(y)>.65 else 0
            curls.append((round(cx+x*sx)+sway, round(cy+y*sy), rng.randrange(3,7), rng.randrange(3,7), rng.randrange(8)))
    for x,y,w,h,k in curls:
        oval("ink",x-w//2,y-h//2,w,h)
    for x,y,w,h,k in curls:
        x -= w//2
        y -= h//2
        if k>2:
            pen.arc((x,y,x+w,y+h),170+k*7,320+k*3,fill=INDEX["curl" if k>4 else "coal"])
        if k==6:
            line("plum",f"{x+1} {y+1} {x+2} {y}")
    for x,y in [(12,34),(18,27),(21,38),(14,49),(19,58),(11,55),(23,64),
                (72,25),(82,31),(75,42),(83,49),(78,59),(73,65),(79,70)]:
        pen.arc((x-2,y-2,x+3,y+3),130,365,fill=INDEX["plum"])
        line("curl",f"{x+3} {y+1} {x+2} {y+3} {x} {y+3} {x-1} {y+2}")
        dot("ink",x+1,y+1)
    line("steel","11 41 10 43 11 45")
    line("plum","7 53 8 55 11 55 12 53")
    line("rim","80 19 82 20 83 22")
    line("plum","80 70 81 72 80 75 78 76")
    area("shadow","29 24 33 16 40 12 48 10 55 11 61 15 64 21 65 35 64 48 61 57 55 62 46 64 38 60 32 52 30 40")
    area("rose","30 24 34 17 41 13 50 11 57 13 61 17 63 24 64 38 61 49 56 55 47 59 39 55 33 47 30 36")
    area("skin","32 23 35 18 43 14 49 13 55 14 60 18 60 27 56 28 52 27 48 32 45 32 42 29 36 28 31 30")
    area("lit","34 24 38 18 46 15 52 15 55 16 48 17 44 19 40 19 36 25")
    area("skin","31 35 35 37 39 37 43 34 44 40 41 45 36 47 33 46")
    area("skin","49 34 54 35 61 31 62 40 60 44 55 46 51 44")
    area("rose","33 30 37 28 41 29 44 31 41 32 36 32")
    area("coal","32 30 35 27 39 27 42 29 41 30 38 29 35 29")
    area("coal","49 29 51 26 56 25 60 27 55 27 52 29")
    line("plum","34 28 38 27")
    line("plum","52 27 55 26 57 26")

    def eye(x,y,closed):
        if closed:
            line("ink",f"{x-2} {y-1} {x+1} {y+1} {x+5} {y+1} {x+8} {y-1}")
            return
        area("ink",f"{x-2} {y-1} {x+1} {y} {x+2} {y-1} {x+6} {y-1} {x+8} {y} {x+6} {y+2} {x+2} {y+2}")
        line("lit",f"{x+1} {y+1} {x+6} {y}")
        dot("ink",x+4,y+1)
        dot("ink",x+4,y)
        dot("white",x+5,y)
    eye(33,33,tick in (29,30,31,83,84))
    eye(50,32,tick in (29,30,31,83,84))
    line("shadow","34 35 33 37 34 38")
    line("shadow","36 35 37 37 36 39")
    line("shadow","51 34 52 36 51 37")

    area("ink","29 35 33 38 40 39 42 37 43 34 45 33 47 34 49 37 51 37 57 34 61 30 64 30 62 34 59 36 61 36 60 38 55 39 62 39 64 41 64 43 62 42 51 41 49 43 47 40 45 39 43 40 43 43 40 42 33 46 32 45 35 42 32 43 31 42 33 40 30 39")
    area("chrome","30 36 34 38 40 40 42 39 42 41 37 42 33 44 36 41 33 41 34 40 31 39")
    line("ice","31 37 34 39 39 40")
    line("white","37 41 40 40")
    area("steel","42 40 43 35 45 34 47 35 49 38 49 41 47 39 45 38 43 39 43 42")
    line("ice","42 40 43 35 44 34")
    line("chrome","47 35 48 38 49 40")
    area("chrome","50 38 56 36 61 31 63 31 60 34 58 36 61 35 60 37 55 39 61 39 63 40 63 41 58 40 51 40")
    line("ice","51 38 56 37 61 32")
    line("white","55 39 60 39")
    area("skin","44 40 46 39 48 41 47 43 45 44 43 43")
    line("shadow","43 43 45 44 48 43")
    area("plum","32 48 35 51 38 54 41 56 46 56 50 55 55 54 61 48 63 45 62 54 59 59 54 63 48 64 42 62 36 58 33 53")
    area("coal","34 52 37 57 43 61 47 62 52 61 57 57 61 53 61 56 57 61 52 64 46 65 40 62 36 58")
    area("coal","37 49 39 46 43 44 46 45 48 44 52 45 56 49 52 48 49 47 45 47 41 48")
    for x,y in [(35,52),(37,54),(38,56),(40,57),(42,59),(44,59),(52,60),(54,58),(57,55),(59,53)]:
        line("shadow",f"{x} {y} {x+1} {y-1}")
    line("shadow","40 47 43 45")
    area("ink","39 51 44 48 50 48 54 50 50 51 46 52 42 52")
    line("chrome","43 50 46 49 51 49")
    line("rose","44 52 48 52 51 51")
    area("shadow","42 55 46 54 50 54 52 56 49 57 46 57")
    line("rim","31 46 31 52 30 57 30 59")
    line("steel","63 45 64 47 64 57 65 60")
    dot("ice",65,61)
    area("ink","42 64 47 65 53 63 56 64 54 69 50 72 45 71 42 68")
    line("chrome","46 65 44 66 45 68 47 68 48 66 47 65")
    line("chrome","49 65 51 64 52 65 52 67 50 68 48 66")
    line("chrome","47 68 46 70 48 71 50 70 50 68")

    area("ink","3 95 6 85 12 77 18 72 24 68 28 61 32 56 38 52 43 49 41 54 36 58 32 64 36 66 40 65 41 67 38 70 41 72 40 75 37 76 39 78 37 82 34 84 32 88 24 90 21 95")
    area("rose","5 95 8 85 17 76 25 70 29 62 34 57 40 52 39 55 34 60 31 65 35 67 39 66 39 68 35 71 40 72 39 75 35 76 38 78 36 81 33 82 30 87 23 88 20 95")
    area("skin","7 93 10 85 19 77 26 71 29 64 33 60 35 59 31 65 30 69 34 69 32 73 35 74 31 77 34 78 29 83 23 84 18 91 17 95 6 95")
    area("lit","28 64 31 60 33 59 31 62 30 64")
    area("steel","25 64 27 59 34 55 39 52 43 49 40 54 35 57 33 61 30 63 27 64")
    line("ice","26 63 28 60 35 55 37 55")
    line("chrome","32 59 35 58 39 54")
    dot("white",32,57)
    line("ink","32 57 33 58 34 58")
    dot("ice",34,56)
    line("steel","29 61 31 60")
    line("ink","28 62 28 61 31 59")
    area("steel","33 68 35 66 40 65 38 68 35 70")
    line("ice","34 68 37 67 39 66")
    line("steel","34 71 37 70 40 72 40 74 37 75")
    line("ice","35 71 38 71 39 72")
    oval("gold",34,77,3,3)
    dot("white",35,77)

    for start,x,y in [(8,60,33),(52,32,58)]:
        age = tick-start
        if 0 <= age <= 5:
            size = (1,2,3,3,2,1)[age]
            pen.line((x-size,y,x+size,y),fill=INDEX["ice"])
            pen.line((x,y-size,x,y+size),fill=INDEX["ice"])
            dot("white",x,y)
    if lift:
        image = image.crop((0,1,SIZE,SIZE)).resize((SIZE,SIZE),Image.Resampling.NEAREST)
    return image


if __name__ == "__main__":
    write_loop(Path(__file__).resolve().parents[1] / "priv/static/dr-crow.gif", frame)
