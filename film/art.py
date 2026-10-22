"""Vector artwork and character controls. Coordinates use a 1920×1080 canvas.

All artwork is original and generated locally; no downloaded images or fonts.
"""
import math
from functools import lru_cache
import aggdraw
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
INK = '#151e28'
CREAM = '#e5dfc9'
TEAL = '#537e83'
RED = '#d57070'
GOLD = '#dabb7f'

def mix(a, b, p):
    return tuple(int(x+(y-x)*p) for x,y in zip(a,b))

def ease(x):
    x = max(0, min(1, x))
    return x*x*(3-2*x)

def lerp(a,b,t): return a+(b-a)*t

@lru_cache(maxsize=150)
def font(size, style='regular'):
    root='/usr/share/fonts/truetype/dejavu/'
    name={'regular':'DejaVuSans.ttf','bold':'DejaVuSans-Bold.ttf','serif':'DejaVuSerif.ttf','italic':'DejaVuSans-Oblique.ttf'}[style]
    return ImageFont.truetype(root+name, max(8,int(size)))

class Canvas:
    def __init__(self, image, zoom=1, cx=960, cy=540):
        self.im=image
        self.k=image.width/W
        self.zoom=zoom
        self.cx=cx; self.cy=cy
        self._context=None
    def draw(self):
        if self._context is None:self._context=aggdraw.Draw(self.im)
        return self._context
    def flush(self):
        if self._context is not None:
            self._context.flush()
            self._context=None
    def pt(self,x,y): return ((x-self.cx)*self.zoom*self.k+self.im.width/2,(y-self.cy)*self.zoom*self.k+self.im.height/2)
    def line(self, points, color, width=2):
        p=aggdraw.Path()
        for i,(x,y) in enumerate(points):
            x,y=self.pt(x,y)
            if i==0:p.moveto(x,y)
            else:p.lineto(x,y)
        self.draw().path(p,None,aggdraw.Pen(color,max(.5,width*self.k*self.zoom)))
    def path(self, commands, fill, stroke=None, width=2):
        p=aggdraw.Path()
        for cmd,coords in commands:
            if cmd=='Z':p.close();continue
            q=[]
            for i in range(0,len(coords),2):q.extend(self.pt(coords[i],coords[i+1]))
            if cmd=='M':p.moveto(*q)
            elif cmd=='L':p.lineto(*q)
            elif cmd=='C':p.curveto(*q)
        self.draw().path(p,aggdraw.Brush(fill) if fill else None,aggdraw.Pen(stroke,width*self.k*self.zoom) if stroke else None)
    def poly(self,points,fill,stroke=None,width=2):
        self.path([('M',points[0])]+[('L',x) for x in points[1:]]+[('Z',())],fill,stroke,width)
    def ellipse(self,box,fill,stroke=None,width=2):
        x0,y0=self.pt(box[0],box[1]);x1,y1=self.pt(box[2],box[3])
        self.draw().ellipse((min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1)),aggdraw.Brush(fill) if fill else None,aggdraw.Pen(stroke,width*self.k*self.zoom) if stroke else None)
    def rect(self,box,fill,stroke=None,width=2,r=0):
        x0,y0,x1,y1=box
        if not r:self.poly([(x0,y0),(x1,y0),(x1,y1),(x0,y1)],fill,stroke,width);return
        self.path([('M',(x0+r,y0)),('L',(x1-r,y0)),('C',(x1,y0,x1,y0,x1,y0+r)),('L',(x1,y1-r)),('C',(x1,y1,x1,y1,x1-r,y1)),('L',(x0+r,y1)),('C',(x0,y1,x0,y1,x0,y1-r)),('L',(x0,y0+r)),('C',(x0,y0,x0,y0,x0+r,y0)),('Z',())],fill,stroke,width)
    def text(self,xy,txt,size=28,color=CREAM,align='left',style='regular'):
        self.flush()
        x,y=self.pt(*xy); f=font(round(size*self.k*self.zoom),style)
        d=ImageDraw.Draw(self.im);d.text((x,y),txt,font=f,fill=color,anchor={'left':'lt','center':'mt','right':'rt'}[align],stroke_width=0)
    def glow(self,x,y,r,color,strength=.5):
        self.flush()
        radius=max(2,int(r*self.k*self.zoom)); sprite=radial(radius,color,round(strength,2))
        px,py=self.pt(x,y);self.im.paste(sprite,(round(px-radius),round(py-radius)),sprite)

@lru_cache(maxsize=200)
def radial(r,color,strength):
    from PIL import ImageColor
    rgb=ImageColor.getrgb(color)
    y,x=np.ogrid[-1:1:complex(2*r),-1:1:complex(2*r)]
    a=(np.exp(-4*(x*x+y*y))*strength*255).astype('uint8')
    out=Image.new('RGBA',(2*r,2*r),rgb+(0,));out.putalpha(Image.fromarray(a));return out

def tube(c,points,color=CREAM,width=28):
    c.line(points,INK,width+5)
    c.line(points,color,width)
    r=width/2
    for x,y in (points[0],points[-1]):c.ellipse((x-r,y-r,x+r,y+r),color,INK,2)

def character(c,x,y,s=1,mood='tired',pose='stand',phase=0,arm=None,look=1,friend=False,blink=False,lean=0):
    """Articulated limbs, overlapping silhouette, replacement facial performance."""
    def P(a,b):return (x+(a+lean*(-b/300))*s,y+b*s)
    def E(box,fill,stroke=None,w=2):
        a,b=P(box[0],box[1]);d,e=P(box[2],box[3]);c.ellipse((a,b,d,e),fill,stroke,w*s)
    def T(points,col=CREAM,w=27):tube(c,[P(a,b) for a,b in points],col,w*s)
    body='#b7c5c5' if friend else CREAM
    shadow='#9da9a6' if friend else '#c4c2b3'
    sit=pose=='sit'; run=pose=='run';walk=pose=='walk'; crouch=pose=='crouch';fall=pose=='fall'
    bob=(math.sin(phase*2)*4 if walk or run else math.sin(phase)*1.2)
    y+=bob*s
    if fall:
        # Exhausted kneeling silhouette, with a low head and planted palms.
        T([(-45,-55),(-75,-30),(-110,-22)],body,30)
        T([(30,-65),(20,-25),(65,-20)],body,30)
        E((-65,-125,65,-44),body,INK)
        E((28,-158,135,-59),body,INK)
        T([(25,-85),(72,-24),(122,-21)],body,23)
        for ex in [80,110]:c.line([P(ex-7,-113),P(ex+5,-110)],INK,3*s)
        c.line([P(88,-83),P(109,-83)],INK,3*s)
        return
    if sit:
        T([(-24,-104),(-38,-47),(-8,-24)],shadow,31)
        T([(25,-104),(48,-45),(24,-22)],body,31)
    elif crouch:
        T([(-23,-90),(-53,-46),(-32,-7)],shadow,31)
        T([(23,-90),(55,-46),(38,-7)],body,31)
    elif walk or run:
        swing=math.sin(phase)
        reach=62 if run else 44
        T([(-20,-104),(-20+reach*swing*.6,-56),(-20+reach*swing,-10-max(0,-swing)*24)],shadow,30)
        T([(20,-104),(20-reach*swing*.6,-56),(20-reach*swing,-10-max(0,swing)*24)],body,30)
    else:
        T([(-22,-110),(-25,-52),(-30,-9)],shadow,31)
        T([(23,-110),(27,-53),(33,-9)],body,31)
    # Far arm behind the torso.
    if walk or run:
        sw=math.sin(phase)*(45 if run else 25)
        T([(-39,-205),(-60-sw,-152),(-41-sw*1.5,-134)],shadow,23)
    else:T([(-39,-207),(-59,-161),(-51,-126)],shadow,24)
    # One continuous shoulder / torso outline, with subtle shaded side.
    cmds=[('M',P(-38,-224)),('C',P(-72,-191)+P(-62,-115)+P(-38,-99)),('C',P(-12,-78)+P(39,-87)+P(51,-117)),('C',P(68,-153)+P(62,-208)+P(35,-226)),('Z',())]
    c.path(cmds,body,INK,2.5*s)
    c.path([('M',P(-40,-208)),('C',P(-58,-170)+P(-52,-112)+P(-27,-103)),('L',P(-13,-105)),('C',P(-39,-144)+P(-32,-185)+P(-29,-210)),('Z',())],shadow)
    # Head silhouette with softer cheeks and a slightly asymmetric crown.
    c.path([('M',P(-55,-279)),('C',P(-58,-324)+P(-17,-344)+P(19,-335)),('C',P(58,-329)+P(70,-294)+P(60,-262)),('C',P(54,-231)+P(21,-216)+P(-10,-225)),('C',P(-43,-228)+P(-64,-248)+P(-55,-279)),('Z',())],body,INK,2.5*s)
    # Scarf gives the original protagonist a stable color identity.
    scarf=GOLD if friend else TEAL
    c.path([('M',P(-49,-231)),('C',P(-15,-214)+P(24,-214)+P(53,-235)),('L',P(51,-216)),('C',P(13,-195)+P(-22,-202)+P(-49,-216)),('Z',())],scarf,INK,2*s)
    c.poly([P(35,-216),P(55,-209),P(48,-164),P(29,-171)],scarf)
    if friend:
        E((-62,-345,62,-305),'#b87558',INK)
        c.rect((*P(-68,-319),*P(67,-303)),'#bb7e5d',INK,r=7*s)
        E((-12,-362,14,-338),'#b87558',INK)
    # Eyes and brows.
    dx=look*5; eyeY=-276
    if blink or mood in ['closed','relief']:
        for ex in [-20,23]:
            c.path([('M',P(ex-9,eyeY)),('C',P(ex-5,eyeY+6)+P(ex+5,eyeY+6)+P(ex+10,eyeY-1))],None,INK,3*s)
    elif mood=='tired':
        for ex in [-20,23]:
            E((ex-7+dx,eyeY-3,ex+7+dx,eyeY+8),INK)
            c.line([P(ex-12,eyeY-4),P(ex+12,eyeY-4)],body,5*s)
            c.path([('M',P(ex-10,eyeY+15)),('C',P(ex-3,eyeY+20)+P(ex+5,eyeY+20)+P(ex+10,eyeY+14))],None,'#8c928a',2*s)
    else:
        rr=9 if mood in ['surprise','sad'] else 7
        for ex in [-20,23]:E((ex-rr+dx,eyeY-rr,ex+rr+dx,eyeY+rr),INK)
    for i,ex in enumerate([-20,23]):
        tilt={'sad':(5,-5),'hope':(1,-2),'determined':(-5,5),'tired':(0,0),'surprise':(-2,2)}.get(mood,(0,0))
        a,b=tilt if i==0 else tilt[::-1]
        c.line([P(ex-12,-301+a),P(ex+12,-301+b)],INK,4*s)
    if mood in ['smile','relief','hope']:
        c.path([('M',P(-9,-250)),('C',P(0,-240)+P(12,-240)+P(21,-250))],None,INK,3.5*s)
    elif mood=='surprise':E((-3,-253,12,-236),INK)
    elif mood=='sad':
        c.path([('M',P(-9,-243)),('C',P(0,-251)+P(11,-251)+P(20,-243))],None,INK,3*s)
    elif mood=='determined':
        c.rect((*P(-13,-252),*P(22,-240)),CREAM,INK,2*s,r=3*s)
        for q in [-3,7,16]:c.line([P(q,-250),P(q,-241)],INK,1*s)
    else:c.line([P(-8,-246),P(17,-246)],INK,3*s)
    # Front arm, individually controllable for reaching / holding / gestures.
    if arm:
        elbow,hand=arm;T([(43,-205),elbow,hand],body,25)
    elif sit:T([(43,-205),(65,-160),(18,-138)],body,25)
    elif walk or run:
        sw=math.sin(phase)*(50 if run else 29)
        T([(42,-205),(62+sw,-160),(41+sw*1.4,-143)],body,25)
    else:T([(42,-205),(59,-156),(48,-121)],body,25)

def shadow(c,x,y,s=1,phase=0,hand=False,small=False):
    c.glow(x,y-210*s,215*s,'#c95d69',.24)
    color='#12141e'
    p=lambda a,b:(x+a*s,y+b*s)
    c.path([('M',p(-42,-104)),('C',p(-72,-182)+p(-60,-240)+p(-56,-290)),('C',p(-65,-364)+p(61,-366)+p(60,-293)),('C',p(55,-243)+p(78,-174)+p(47,-106)),('L',p(32,-11)),('L',p(10,-9)),('L',p(-4,-103)),('L',p(-22,-9)),('L',p(-47,-10)),('Z',())],color,'#8a4d59',2*s)
    if hand:
        tube(c,[p(48,-239),p(82,-270),p(142,-279+math.sin(phase)*8)],color,22*s)
    else:
        c.line([p(-48,-235),p(-73,-138)],color,23*s)
        c.line([p(48,-235),p(73,-138)],color,23*s)
    for ex,tilt in [(-20,3),(20,-3)]:c.line([p(ex-10,-303),p(ex+10,-303+tilt)],'#df8889',4*s)

def enough(c,y=440,x0=1120,x1=1675,alpha=1):
    c.glow((x0+x1)/2,y,210,'#c56268',.11*alpha)
    c.line([(x0,y),(x1,y)],'#d8797e',3)
    for x in range(int(x0),int(x1),24):c.line([(x,y),(x,y+9)],'#985663',1)
    c.text((x1,y-39),'ENOUGH',22,'#e49b9c','right','bold')

def book(c,x,y,w=145,h=25,color='#647d86',angle=0):
    c.rect((x,y-h,x+w,y),color,INK,2,r=3)
    c.rect((x+9,y-h+6,x+w-7,y-5),'#c9c6b1',r=2)
    c.line([(x+17,y-h+11),(x+w-14,y-h+11)],'#91998d',1)

def cup(c,x,y,t=0,scale=1,color=CREAM):
    c.ellipse((x+19*scale,y-36*scale,x+42*scale,y-12*scale),None,color,4*scale)
    c.path([('M',(x-24*scale,y-46*scale)),('L',(x+24*scale,y-46*scale)),('L',(x+18*scale,y-5*scale)),('C',(x+10*scale,y+5*scale,x-16*scale,y+5*scale,x-19*scale,y-8*scale)),('Z',())],color,INK,2*scale)
    c.ellipse((x-23*scale,y-49*scale,x+23*scale,y-41*scale),'#513e35',INK,2*scale)
    for i in range(2):
        xx=x+(-9+i*18)*scale;yy=y-58*scale
        c.path([('M',(xx,yy)),('C',(xx+12*scale*math.sin(t+i),yy-20*scale,xx-10*scale,yy-35*scale,xx+5*scale,yy-54*scale))],None,'#8d9a98',1.5*scale)

def clock(c,x,y,txt='02:17'):
    c.rect((x,y,x+138,y+65),'#19202b','#485160',2,r=9)
    c.text((x+69,y+13),txt,31,'#c97e77','center')

def plant(c,x,y,s=1):
    c.poly([(x-32*s,y-65*s),(x+32*s,y-65*s),(x+23*s,y),(x-23*s,y)],'#675143',INK)
    for i in range(5):
        angle=(i-2)*.4;dx=math.sin(angle)*72*s
        c.path([('M',(x,y-63*s)),('C',(x+dx-35*s,y-115*s,x+dx-20*s,y-172*s,x+dx,y-183*s)),('C',(x+dx+23*s,y-130*s,x+dx+10*s,y-91*s,x,y-63*s)),('Z',())],'#394f4d')

def window(c,x,y,w,h,warm=False):
    c.rect((x-12,y-12,x+w+12,y+h+12),'#222e3c','#4a535f',2,r=6)
    c.rect((x,y,x+w,y+h),'#192a3a' if not warm else '#796351')
    rng=np.random.default_rng(81)
    for i in range(13):
        bx=x+float(rng.uniform(0,w-20));bh=float(rng.uniform(40,h*.7))
        c.rect((bx,y+h-bh,bx+26,y+h),'#202b37')
        if i%2:c.rect((bx+8,y+h-bh+15,bx+13,y+h-bh+24),'#91846b')
    c.ellipse((x+w*.73,y+27,x+w*.73+28,y+55),'#a2aeb5')
    c.line([(x+w/2,y),(x+w/2,y+h)],'#4a535f',5)
    c.line([(x,y+h/2),(x+w,y+h/2)],'#4a535f',5)
    c.rect((x-25,y+h,x+w+25,y+h+16),'#49525b',r=4)

def gradient(top,bottom,width,height):
    a=np.linspace(0,1,height)[:,None,None]; rgb=np.array(top)[None,None,:]*(1-a)+np.array(bottom)[None,None,:]*a
    rgb=np.repeat(rgb,width,axis=1)
    xx=np.linspace(-1,1,width)[None,:]; yy=np.linspace(-1,1,height)[:,None]
    vignette=1-.23*np.minimum(1,xx*xx*.6+yy*yy*.5)
    rgb*=vignette[:,:,None]
    rng=np.random.default_rng(702);rgb+=rng.normal(0,.55,(height,width,1))
    return Image.fromarray(np.uint8(np.clip(rgb,0,255)))

@lru_cache(maxsize=16)
def background(kind,width):
    height=round(width*H/W)
    if kind in ['cafe','streetwarm']:
        im=gradient((31,39,45),(53,47,43),width,height)
    else:im=gradient((18,27,41),(26,34,44),width,height)
    c=Canvas(im)
    if kind=='room':
        c.glow(435,430,560,'#527b95',.16)
        c.glow(1330,570,370,'#495b72',.1)
        for x in range(70,1900,310):c.line([(x,96),(x,857)],'#263341',1)
        c.rect((0,862,1920,988),'#1a222c')
        c.line([(0,858),(1920,858)],'#59616a',2)
        for x in range(-500,2300,240):c.line([(x,988),(960+(x-960)*.6,863)],'#26303a',1)
        window(c,190,220,330,290)
        # Bed / desk left; mirror on the right.
        c.rect((80,775,760,839),'#252e3b','#4a5360',2,r=12)
        c.rect((80,708,126,862),'#343e4c','#59616d',2,r=8)
        c.path([('M',(128,768)),('C',(280,730,620,730,747,780)),('L',(747,815)),('L',(128,815)),('Z',())],'#3c4e62','#566878',2)
        c.ellipse((145,751,292,790),'#697785')
        c.rect((160,833,174,862),'#535a63');c.rect((704,833,718,862),'#535a63')
        c.rect((775,710,950,852),'#242e38','#46535e',2,r=8)
        clock(c,793,646)
        c.rect((1122,207,1684,861),'#4b5360','#767a7a',3,r=34)
        c.rect((1134,220,1672,847),'#1c2938','#313e50',2,r=27)
        c.poly([(1142,232),(1288,232),(1550,840),(1457,840)],'#253345')
        c.poly([(1323,232),(1347,232),(1610,840),(1584,840)],'#29384a')
        plant(c,1798,859,.8)
    elif kind=='desk':
        c.glow(1170,520,570,'#b7a071',.22)
        window(c,180,165,400,350)
        c.rect((0,862,1920,990),'#19232c');c.line([(0,861),(1920,861)],'#535e68',2)
        c.rect((780,600,1660,631),'#665846',INK,3,r=9)
        for x in [815,1598]:c.rect((x,630,x+20,861),'#4a4640',INK)
        c.rect((1133,427,1382,578),'#202d3c','#707b81',4,r=8)
        c.rect((1148,442,1367,560),'#355469')
        for i in range(6):c.rect((1167,459+i*14,1310+(i%3)*12,463+i*14),'#7a9395')
        c.line([(1257,579),(1257,596)],'#737d83',8)
        c.rect((1121,594,1390,604),'#616e75',r=4)
        c.line([(1512,596),(1512,434),(1454,390)],'#83908e',8)
        c.poly([(1423,373),(1491,398),(1450,430),(1405,410)],'#b1ad99',INK)
        c.poly([(1434,424),(1270,595),(1605,595)],'#625c46')
        c.glow(1450,468,210,'#d3b77d',.16)
        clock(c,1500,252,'03:46')
        book(c,865,596,150,29)
        c.rect((568,730,770,752),'#384451',INK,r=7)
        c.rect((575,470,605,747),'#384451',INK,r=9)
        c.line([(600,751),(600,860)],'#384451',12)
        c.line([(750,751),(750,860)],'#384451',12)
    elif kind in ['street','streetwarm']:
        warm=kind=='streetwarm'
        c.glow(1510,480,650,'#b88753' if warm else '#51677d',.2)
        rng=np.random.default_rng(36)
        for i in range(16):
            x=i*145-120;bh=float(rng.uniform(280,490))
            c.rect((x,780-bh,x+130,790),'#25303c' if i%2 else '#202a36','#36424f',1)
            for row in range(3):
                for col in range(3):
                    xx=x+20+col*35;yy=800-bh+row*95
                    c.rect((xx,yy,xx+16,yy+33),'#9d8861' if rng.random()<.3 else '#2f3b48')
        c.rect((0,810,1920,980),'#1b2530')
        c.line([(0,811),(1920,811)],'#657079',2)
        c.line([(0,919),(1920,919)],'#505a63',2)
        for x in range(50,1920,210):c.line([(x,948),(x+85,948)],'#4a5159',3)
        for x in [340,1230,1840]:
            c.line([(x,810),(x,330),(x+80,330)],'#505a61',6)
            c.poly([(x+62,340),(x-100,810),(x+270,810)],'#383b36')
            c.glow(x+79,355,195,'#c3aa79',.22)
            c.ellipse((x+52,322,x+103,342),'#c3b38f')
    elif kind=='tower':
        c.glow(1000,600,620,'#516778',.17)
        c.rect((0,871,1920,988),'#1a222c');c.line([(0,870),(1920,870)],'#5a6269',2)
        window(c,166,270,270,300)
        c.rect((1325,140,1770,870),'#404b59','#626a74',2,r=25)
        c.rect((1337,154,1757,857),'#1b2939',r=20)
        plant(c,1850,870,.65)
    elif kind=='cafe':
        c.glow(1080,440,650,'#bb8f58',.3)
        # Shopfront, warm interior, window and rainy-city reflections.
        c.rect((200,175,1630,865),'#4c4941','#6b6355',3)
        c.rect((254,230,1576,669),'#283844','#8d7a60',5)
        for x in [270,610,950,1290]:
            c.rect((x,260,x+210,660),'#2f3f48')
            for j in range(4):c.rect((x+20+j*40,320+(j%2)*75,x+32+j*40,350+(j%2)*75),'#7e806b')
        for x in [690,1120]:c.line([(x,236),(x,665)],'#6b675a',8)
        c.poly([(850,239),(965,239),(1190,663),(1075,663)],'#34434b')
        c.text((920,186),'O P E N   L A T E',24,'#d1bc94','center')
        c.rect((200,667,1630,865),'#51493e')
        for x in range(220,1630,90):c.line([(x,670),(x,860)],'#423e38',2)
        c.rect((0,865,1920,990),'#262d31');c.line([(0,865),(1920,865)],'#777269',2)
        # Bench: slats behind characters, seat at 748.
        for y in [590,630,670]:c.rect((610,y,1390,y+26),'#79634a',INK,2,r=7)
        c.rect((590,740,1410,770),'#8b7153',INK,3,r=7)
        for x in [660,1320]:c.rect((x,768,x+20,864),'#3a4041',INK)
        c.line([(1590,865),(1590,222),(1490,222)],'#626259',7)
        c.ellipse((1460,210,1525,234),'#d7bf8a')
        c.glow(1490,262,310,'#d7ae70',.3)
        plant(c,332,864,1.1)
    # Built-in letterboxing; all compositions respect the 96–984 picture area.
    c.flush()
    d=ImageDraw.Draw(im); hh=round(96*width/W)
    d.rectangle((0,0,width,hh),fill='#080d14');d.rectangle((0,height-hh,width,height),fill='#080d14')
    return im

def weather(c,t,warm=False):
    for i in range(55):
        x=(i*193.17+t*(10+i%4*4))%2000-40
        y=(i*91.31+t*(62+i%5*13))%900+90
        if y<980:c.line([(x,y),(x-3,y+13)],'#697b85' if not warm else '#69716d',.8)

def dust(c,t,warm=False):
    for i in range(22):
        x=(i*173.7+math.sin(t*.21+i)*16)%1900
        y=160+(i*83.2+t*(1+i%3))%720
        c.ellipse((x,y,x+1.8,y+1.8),'#6b6c63' if warm else '#4a5b68')

def bars(im):
    d=ImageDraw.Draw(im);h=round(im.height*96/1080)
    d.rectangle((0,0,im.width,h),fill='#080d14');d.rectangle((0,im.height-h,im.width,im.height),fill='#080d14')

def subtitle(c,text,opacity=1):
    if not text:return
    c.text((960,924),text,28,'#dcd8ca','center')
