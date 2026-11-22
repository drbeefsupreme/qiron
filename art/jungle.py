from math import cos, hypot, pi, sin
from random import Random
from PIL import Image, ImageDraw


def canopy():
    rng = Random(92527)
    w,h = 192,116
    image = Image.new("L",(w,h))
    brush = ImageDraw.Draw(image)
    for y in range(h):
        for x in range(w):
            shaft = (x-y*.61)%72
            light = max(0,1-abs(shaft-29)/22)
            haze = sin(.024*x+.029*y)+sin(.09*x-.05*y)
            image.putpixel((x,y),int(111+light*65+haze*10-27*y/h+rng.randrange(-6,7)))

    def stem(points,width,value,highlight):
        brush.line(points,fill=value,width=width)
        brush.line([(x-1,y) for x,y in points],fill=highlight,width=max(1,width//4))

    def leaf(x,y,length,angle,width,pigment):
        dx,dy=cos(angle),sin(angle)
        end=(x+length*dx,y+length*dy)
        mx,my=x+length*dx*.52,y+length*dy*.52
        upper=(mx-dy*width,my+dx*width)
        lower=(mx+dy*width*.7,my-dx*width*.7)
        brush.polygon([(x,y),upper,end,lower],fill=pigment)
        brush.polygon([(x,y),upper,end],fill=min(250,pigment+25))

    for _ in range(86):
        x=rng.randrange(-2,w+5)
        y=rng.randrange(0,50)
        dx=rng.randrange(-10,11)
        v=rng.randrange(65,118)
        brush.line((x+dx,-2,x+dx//2,y,x,y+24),fill=v,width=rng.randrange(1,3))
        for j in range(6):
            leaf(x+rng.randrange(-5,6),y+rng.randrange(-8,15),rng.randrange(4,11),
                 rng.uniform(-pi,pi),rng.uniform(1,2.2),v-10)
    for x0,tilt,wave,thickness in [(4,24,8,9),(60,-47,15,5),(148,41,17,13),(177,-16,7,5)]:
        route=[(round(x0+tilt*y/h+wave*sin(y*.038+x0*.1)),y) for y in range(-4,h+5)]
        stem(route,thickness,32,68)
        for y in range(2,h,4):
            x=route[y+4][0]
            brush.line((x+1,y,x+thickness//3,y+3),fill=53)
        stem([(x+round(4*sin(y*.17)),y) for x,y in route],2,76,117)

    for x0,anchor,span,drop in [(-12,-10,72,30),(24,-12,78,42),(110,-13,81,39),
                                (155,-10,67,61),(-23,38,56,36),(115,2,93,32)]:
        route=[]
        for n in range(span+1):
            y=anchor+drop*sin(n*pi/span)+2*sin(n*.15)
            route.append((x0+n,round(y)))
        stem(route,3,47,96)
        for n in range(5,span-4,rng.randrange(5,9)):
            x,y=route[n]
            angle=rng.uniform(.3,1.3) if n%3 else rng.uniform(1.7,2.7)
            leaf(x,y,rng.randrange(6,12),angle,rng.uniform(1,2.6),rng.randrange(23,74))

    def frond(x,y,spread,rise,shade):
        pts=[(x+spread*i/15,y-rise*(i/15)**.74) for i in range(16)]
        brush.line(pts,fill=shade+20,width=1)
        for n in range(2,15):
            px,py=pts[n]
            length=(sin(n*pi/17)*13+1)
            dx,dy=pts[n+1][0]-px,pts[n+1][1]-py
            k=hypot(dx,dy)
            dx,dy=dx/k,dy/k
            for side in (-1,1):
                tip=(px+(dx*.6-dy*side)*length,py+(dy*.6+dx*side)*length)
                mid=(px-dy*side*length*.5,py+dx*side*length*.5)
                brush.polygon([(px,py),mid,tip,(px+dx*2,py+dy*2)],fill=shade+9*(side==1))
    for i in range(22):
        frond(rng.randint(-18,w+14),rng.randint(102,134),rng.choice((-1,1))*rng.randint(14,39),
              rng.randint(22,58),rng.randint(14,76))
    for x,y in [(-9,100),(173,76),(8,135),(138,124),(188,130)]:
        for j in range(8):
            frond(x,y,rng.randrange(-34,35),rng.randrange(24,48),rng.randrange(11,47))
    return image
