from math import sin, tau
from pathlib import Path
from PIL import Image, ImageDraw
from pixel_gif import write_loop

COLORS = {
    "clear":"000000", "ink":"120e1b", "coal":"27202e", "seam":"51283c",
    "wine":"7b354a", "berry":"a64b5d", "shine":"d17e8b",
    "oxblood":"49192f", "red":"b4213f", "scarlet":"e84151", "thread":"ff7d76",
    "moss":"50572c", "olive":"85923c", "green":"b4c84e", "lime":"e0e867",
    "light":"f6f587", "navy":"14223f", "blue":"234e85", "azure":"227ab3",
    "water":"44b8d4", "ice":"bcf5f5", "steel":"69768a", "silver":"aeb7ca",
    "copper":"b78250", "gold":"e9ba70", "ivory":"f3e4cd", "mouth":"551c34",
}
INDEX = {k:i for i,k in enumerate(COLORS)}
PALETTE = bytes.fromhex("".join(COLORS.values()))


def frame(tick):
    image = Image.new("P",(96,96))
    image.putpalette(PALETTE)
    d = ImageDraw.Draw(image)

    def coords(s):
        v=list(map(int,s.split()))
        return list(zip(v[::2],v[1::2]))

    def area(c,s):
        d.polygon(coords(s),fill=INDEX[c])

    def line(c,s):
        d.line(coords(s),fill=INDEX[c])

    def dot(c,x,y):
        d.point((x,y),fill=INDEX[c])

    def oval(c,box):
        d.ellipse(box,fill=INDEX[c])

    area("ink","0 95 0 85 4 77 13 72 26 67 36 64 60 62 74 66 87 72 92 78 95 86 95 95")
    area("wine","1 95 1 84 5 78 12 74 25 69 29 70 23 82 15 95")
    area("berry","2 84 6 79 15 75 22 73 18 76 7 81 4 88 2 90")
    line("shine","3 84 5 80 10 77 15 75")
    area("seam","7 95 9 88 9 82 13 80 12 87 14 88 12 95")
    line("berry","10 94 11 89 12 87")
    area("coal","26 95 29 78 37 68 56 65 68 72 66 86 58 95")
    line("steel","38 95 41 92 46 91 47 88 44 88 46 85 51 85")
    line("silver","39 95 42 93 46 92")
    area("seam","15 78 23 71 33 65 41 64 35 74 31 95 19 95 24 85")
    area("wine","13 77 27 70 36 65 33 72 27 80 23 84")
    line("shine","15 77 23 73 31 69")
    area("berry","24 84 29 77 33 75 31 83 27 95 21 95")
    line("shine","23 88 28 81 31 78")
    dot("ivory",18,77)
    oval("ink",(24,85,27,88))
    dot("silver",25,86)
    area("wine","64 65 75 68 86 72 92 80 95 87 95 95 55 95 59 79")
    area("seam","58 82 64 69 65 66 73 68 85 73 77 77 84 80 71 93 65 95 72 82")
    area("berry","61 84 62 72 65 66 69 66 82 72 75 75 69 73 66 83 62 91")
    line("shine","61 86 63 74 65 69 71 69 78 72")
    dot("ivory",78,72)
    line("shine","71 88 81 80")
    line("steel","76 91 85 84")
    line("silver","77 91 85 84")
    dot("ivory",85,84)
    for offset,c in [(0,"copper"),(2,"silver"),(4,"gold")]:
        for j in range(28):
            x=34+j*.88 +offset*.3
            y=69+25*sin(j/27*3.14)+offset*.6
            dot(c,int(x),int(y))
            if j%3==1: dot("ivory",int(x)+1,int(y))
    oval("copper",(44,91,49,96))
    dot("gold",46,92)

    area("ink","25 26 32 21 54 16 66 17 70 26 72 36 70 49 66 61 61 65 60 72 53 76 44 77 35 72 33 65 28 59 25 49 22 37")
    area("olive","26 27 32 22 53 17 65 18 69 26 71 36 69 48 64 60 59 64 59 71 53 75 44 75 37 71 35 64 29 58 26 48 24 37")
    area("green","25 29 33 24 45 22 59 20 65 22 68 28 69 37 66 48 59 56 57 65 53 71 44 73 38 69 35 61 30 57 27 47 24 37")
    area("lime","25 33 33 24 46 22 59 21 60 28 56 35 57 43 53 47 49 46 46 44 41 44 36 49 31 53 27 46")
    area("lime","32 56 38 52 42 48 49 49 51 56 48 59 47 66 44 71 39 67")
    area("olive","41 63 48 61 53 54 55 58 49 65 44 68")
    mask=image.copy()
    for y in range(22,75):
        for x in range(25,71):
            n=mask.getpixel((x,y))
            if n not in (INDEX["lime"],INDEX["green"],INDEX["olive"]): continue
            course=int(1.5*sin(y/12)) + y//14
            if (x+course)%4==0 and (y+x//6)%4 in (0,1):
                dot({INDEX["lime"]:"green",INDEX["green"]:"olive",INDEX["olive"]:"moss"}[n],x,y)
            if n==INDEX["lime"] and (x+course)%4==2 and y%6 in (2,3):
                dot("light",x,y)
    area("olive","40 48 43 45 47 45 50 48 49 53 45 56 41 54")
    area("mouth","41 48 43 46 47 46 49 48 48 52 45 54 42 52")
    line("ink","42 48 44 47 47 47 48 49")
    line("shine","44 52 46 52")
    line("lime","42 54 45 56 49 53")

    area("ink","22 31 27 30 45 29 56 27 68 25 68 28 62 32 59 39 55 43 49 44 45 42 43 39 39 38 36 43 30 44 26 42 24 39")
    area("steel","23 31 45 29 57 27 68 25 67 28 62 31 59 37 57 39 53 41 47 42 44 37 39 36 35 41 31 42 26 40")
    area("blue","25 32 37 31 38 35 34 41 30 42 26 39")
    area("azure","26 33 30 32 30 39 28 40 26 38")
    line("water","26 33 27 38")
    area("navy","31 32 37 32 37 35 34 40 31 41")
    area("navy","40 31 46 30 60 28 58 37 55 40 48 42 45 40 43 36 41 36")
    area("blue","43 31 52 30 50 34 48 40 46 40 44 35")
    area("azure","44 31 49 30 48 32 45 35")
    line("water","43 31 44 34 46 37")
    line("azure","56 29 55 33 52 36")
    line("silver","24 31 39 30 42 30 57 28 65 26")
    line("ice","39 30 45 29")
    dot("ice",27,32)
    for sx,sy,length in [(28,40,11),(56,40,9),(65,28,14)]:
        for j in range(length):
            dot("steel" if j%3 else "silver",sx+(j//7),sy+j)
        dot("gold",sx+length//7,sy+length)
    line("seam","29 50 32 53 35 53 38 50")
    for x,y in [(31,52),(33,54),(36,53),(38,51)]: dot("gold",x,y)

    area("ink","10 29 16 27 25 24 27 15 33 9 48 4 61 4 67 6 71 12 74 22 73 26 66 25 54 25 40 28 25 31 14 33 8 33")
    area("red","26 24 28 15 34 10 47 6 59 5 65 7 70 12 73 21 70 23 59 21 44 23 35 25")
    area("scarlet","29 21 30 15 36 10 46 7 52 8 49 13 47 21 35 24")
    line("thread","31 17 34 12 42 9 46 8")
    line("oxblood","51 21 53 12 56 7 59 6")
    line("berry","52 20 54 13 56 9")
    area("ivory","32 15 43 11 43 17 33 21")
    line("red","34 16 36 15 36 17 37 15 39 14")
    dot("red",40,14)
    area("oxblood","9 31 18 27 36 23 58 20 69 20 74 23 71 26 63 24 53 24 41 27 24 31 13 33 8 33")
    area("red","8 31 16 27 30 23 45 22 36 25 21 30 10 32")
    line("scarlet","8 30 17 26 28 23 36 22")
    line("thread","15 27 24 24")
    for x,y in [(45,22),(50,21),(55,21),(61,20),(66,20),(71,22)]:
        area("steel",f"{x-1} {y} {x+1} {y-3} {x+2} {y}")
        line("ice",f"{x} {y-1} {x+1} {y-3}")
    area("ink","20 53 24 51 42 47 44 48 43 49 23 55 20 55")
    line("ivory","21 53 25 52 39 48 42 48")
    line("silver","22 54 26 53 36 50")
    line("copper","38 49 42 48")
    line("steel","21 53 23 53")
    glow = "gold" if 18 <= tick < 33 or 72 <= tick < 82 else "scarlet"
    line(glow,"20 53 20 54")
    if glow == "gold":
        dot("ivory",20,53)
    for offset in (0,50):
        phase=(tick+offset)%100
        step=phase//5
        x=19-step//4+round(2*sin(tau*phase/100))
        y=52-step
        shade="steel" if 2 <= step < 12 else "coal"
        if 1 <= step <= 18:
            line(shade,f"{x} {y} {x-1} {y-1} {x-1} {y-2} {x} {y-3}")
        if 5 <= step < 12:
            dot("silver",x-1,y-2)
    if tick in range(13,20):
        x=44+tick-13
        line("ice",f"{x} 31 {x+1} 33")
    if tick in (62,63,64):
        line("ice","70 20 73 20")
        line("ice","72 18 72 22")
    if tick in range(20,43) or tick in range(75,92):
        image=image.crop((0,1,96,96)).resize((96,96),Image.Resampling.NEAREST)
    return image


if __name__ == "__main__":
    write_loop(Path(__file__).resolve().parents[1] / "priv/static/dr-beef.gif", frame)
