from bisect import bisect_right
from functools import lru_cache
from math import cos, pi, sin
from pathlib import Path
from random import Random

from PIL import GifImagePlugin, Image, ImageDraw, ImageFont, ImageSequence

from jungle import canopy

ART = Path(__file__).resolve().parent
STATIC = ART.parent / "priv/static"
GOLD = ["100f09","25220e","373316","50451c","6a5723","877135","aa9149","c8ac62","e1c985","f8e5ac","fff1cb"]
PALETTE = GOLD + ["4c1e13","83311c","af4823","df7130","738d22","a4c747","ccdf72","655c45","9f9e7a"]
RGB = [tuple(bytes.fromhex(c)) for c in PALETTE]
SWATCH = Image.new("P",(1,1))
SWATCH.putpalette(bytes.fromhex("".join(PALETTE)))
INK, PAPER = RGB[0], RGB[10]
CANOPY = canopy()
BOLD = str(STATIC / "barlow-condensed.ttf")


def tint(rgb, name):
    r,g,b = rgb
    value = (.30*r+.55*g+.15*b)/255
    level = min(10, int(value*11.4))
    if name == "santa" and r>1.55*g and r>1.55*b and value>.16:
        return RGB[min(14,11+int(value*5))]
    if name == "dr-beef" and r>1.8*g and r>1.5*b:
        return RGB[min(14,11+int(value*8))]
    if b>r*1.23 and b>100 and g>100: return RGB[18 if value<.60 else 19]
    return RGB[level]


@lru_cache(None)
def sprite(name):
    frames, ends, end = [], [], 0
    for im in ImageSequence.Iterator(Image.open(STATIC / (name+".gif"))):
        cut = im.convert("RGBA")
        colors = {c: (*tint(c[:3],name),c[3]) for _,c in cut.getcolors()}
        cut.putdata([colors[p] for p in cut.getdata()])
        end += im.info["duration"]
        frames.append(cut)
        ends.append(end)
    return frames, ends, end


@lru_cache(None)
def text_mask(words, size, width):
    font=ImageFont.truetype(BOLD,size*3)
    box=font.getbbox(words)
    im=Image.new("L",(box[2]-box[0],box[3]-box[1]))
    ImageDraw.Draw(im).text((-box[0],-box[1]),words,font=font,fill=255)
    return im.resize((width,max(1,round(im.height/3))),Image.Resampling.LANCZOS).point(lambda x:255 if x>98 else 0)


def label(im, words, size, x, y, width, color=PAPER):
    mask=text_mask(words,size,width)
    im.paste(INK,(x+1,y+1,x+1+mask.width,y+1+mask.height),mask)
    im.paste(color,(x,y,x+mask.width,y+mask.height),mask)


def actor(im, name, size, x, y, tick):
    frames,ends,duration=sprite(name)
    pic=frames[bisect_right(ends,tick*100%duration)].resize((size,size),Image.Resampling.NEAREST)
    mask=pic.getchannel("A")
    x,y=round(x),round(y)
    im.paste(INK,(x+1,y+1,x+size+1,y+size+1),mask)
    im.paste(pic,(x,y),mask)


def scenery(scene, t):
    x=(5,32,56,22)[scene]+int(t*.08)
    y=(4,12,7,14)[scene]-int(t*.04)
    grey=CANOPY.crop((x,y,x+128,y+96))
    tones=[RGB[min(7,max(0,int((v/255)**1.4*7.2)))] for v in range(256)]
    im=grey.convert("RGB")
    im.putdata([tones[v] for v in grey.getdata()])
    return im


def leaves(im,t,scene):
    pen=ImageDraw.Draw(im)
    for i in range(17):
        x=int((i*29+t*(.17+(i%3)*.05)+sin(t*.08+i)*3)%142)-7
        y=int((i*19+t*(.27+(i%4)*.08))%113)-8
        if y>74 and scene in (0,3): continue
        c=RGB[(6,8,9,7)[i%4]]
        w=2+i%3
        pen.polygon([(x-w,y+1),(x,y-1),(x+w,y-2),(x+1,y+1)],fill=c)


def torn_band(im,y,seed):
    r=Random(seed)
    points=[(x,y+r.choice([-2,-1,0,0,1,2])) for x in range(-2,133,3)]
    ImageDraw.Draw(im).polygon(points+[(130,97),(-2,97)],fill=INK)


def delta(im,x,y):
    p=ImageDraw.Draw(im)
    p.polygon([(x,y+10),(x+5,y),(x+11,y+10)],fill=RGB[16])
    p.polygon([(x+3,y+8),(x+5,y+4),(x+8,y+8)],fill=INK)


def fronds(im):
    p=ImageDraw.Draw(im)
    rng=Random(31)
    for right in (False,True):
        def plant(x,y):
            return (127-x if right else x,y)
        for i in range(3):
            ox,oy=rng.randrange(-7,8),85+rng.randrange(9)
            w,h=rng.randrange(8,17),rng.randrange(17,38)
            tip=plant(ox+w,oy-h)
            p.line((plant(ox,oy),tip),fill=RGB[1])
            for j in range(2,9):
                q=j/10
                a,b=ox+w*q,oy-h*q
                p.polygon([plant(a,b),plant(a-5*q-2,b-6),plant(a+1,b-2)],fill=RGB[1])
                p.polygon([plant(a,b),plant(a+8*(1-q)+1,b-4),plant(a+1,b-3)],fill=RGB[2])


def frame(tick):
    scene,t=divmod(tick,60)
    im=scenery(scene,t)
    z=t/59
    if scene in (0,3):
        actor(im,"peter-thiel",45,83+z,-3-z,tick)
        actor(im,"dr-beef",49,3-z,19-2*z,tick)
        actor(im,"dr-crow",67,34+z,2-2*z,tick)
        actor(im,"santa",42,47-z,43-2*z,tick)
        fronds(im)
        leaves(im,tick,scene)
        torn_band(im,74,6)
        if scene==0:
            label(im,"TOO LATE SHOW",19,7,76,101)
            delta(im,113,77)
        else:
            label(im,"CHRISTMAS TELETHON",16,6,77,104)
            delta(im,113,77)
        p=ImageDraw.Draw(im)
        p.line((7,92,120,92),fill=RGB[4])
    elif scene==1:
        actor(im,"dr-crow",73,61-3*z,0-2*z,tick)
        actor(im,"dr-beef",80,-2+2*z,3-2*z,tick)
        fronds(im)
        leaves(im,tick,scene)
        torn_band(im,77,14)
        label(im,"CAW-IN",18,5,79,53)
        pen=ImageDraw.Draw(im)
        pen.line((65,87,124,87),fill=RGB[3])
        for j in range(48):
            amp=int((sin(j*.31-t*.55)**4)*4*(1+cos(j*.8+t*.6)))
            pen.line((70+j,87-amp,70+j,87+amp//2),fill=RGB[7 if j%3 else 5])
    else:
        p=ImageDraw.Draw(im)
        for y in (24,48,72): p.line((0,y,127,y),fill=RGB[3])
        for x in (24,48,72,96,120): p.line((x,0,x,95),fill=RGB[3])
        actor(im,"peter-thiel",64,70-3*z,-2+z,tick)
        actor(im,"santa",73,0+z,13-3*z,tick)
        p=ImageDraw.Draw(im)
        x=81+round(22*z)
        y=64-round(4*sin(z*pi))
        p.line((68,69,x,y),fill=RGB[7])
        p.ellipse((x-2,y-2,x+2,y+2),outline=RGB[14])
        fronds(im)
        leaves(im,tick,scene)
        torn_band(im,78,8)
        label(im,"SANTA TRACKER",17,6,80,96)
        delta(im,113,80)
    return im.quantize(palette=SWATCH,dither=Image.Dither.NONE)


def render():
    dest=STATIC / "telethon.gif"
    staged=dest.with_suffix(".gif.tmp")
    with staged.open("wb") as output:
        header,_=GifImagePlugin.getheader(frame(0),info={"loop":0})
        output.writelines(header)
        for i in range(240):
            output.writelines(GifImagePlugin.getdata(frame(i),duration=100,disposal=1))
        output.write(b";")
    staged.replace(dest)


if __name__=="__main__":
    render()
