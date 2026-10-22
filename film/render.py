"""CPU-only layered animation. Run: python -m film.render --width 1920."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .art import *
from .story import SHOTS, DURATION, FPS, POSE_FPS, TITLE, shot_at
from .toolchain import FFMPEG

def camera_image(im,zoom,cx=960,cy=540):
    k=im.width/1920
    return im.transform(im.size,Image.Transform.AFFINE,(1/zoom,0,(cx-960/zoom)*k,0,1/zoom,(cy-540/zoom)*k),resample=Image.Resampling.BICUBIC)

def mirror_actor(c,t,shadowed=False):
    if shadowed:shadow(c,1495,835,1.13,phase=t,hand=True)
    else:character(c,1488,841,.82,mood='tired',look=-1,phase=t)

def award(c,x,y,s=1):
    c.poly([(x-18*s,y-72*s),(x+3*s,y-41*s),(x+17*s,y-72*s)],TEAL,INK,2)
    c.ellipse((x-21*s,y-49*s,x+21*s,y-7*s),GOLD,INK,2)
    c.ellipse((x-13*s,y-41*s,x+13*s,y-15*s),None,'#9d804e',2)
    c.line([(x-6*s,y-28*s),(x,y-22*s),(x+8*s,y-34*s)],'#795f3f',2)

def tower(c,t,count=7,scatter=0):
    colors=['#506f7b','#aa8764','#58686d','#877866','#647b74','#92775d','#536576']
    rng=np.random.default_rng(319)
    for i in range(count):
        x=1218+math.sin(i*2.1)*18; y=870-i*48
        if scatter:
            x+=float(rng.uniform(-420,390))*scatter
            y+=i*48*scatter+math.sin(i)*18*scatter
        book(c,x-95,y,190+(i%2)*12,45,colors[i%len(colors)])
        if i in [1,4]:award(c,x+72,y-42,.6)

def phone(c,t,mode='feed',p=0):
    # Foreground device, hands, screen content, and screen-specific clipping.
    c.glow(970,515,480,'#51768b',.16)
    c.rect((714,158,1206,881),'#111a25','#727d86',4,r=45)
    c.rect((734,185,1186,850),'#202d3d',r=31)
    c.rect((878,194,1042,211),'#101722',r=9)
    c.text((767,229),'09:41' if mode=='feed' else '19:02',20,'#aebbc2')
    c.line([(1114,239),(1137,239),(1137,230)],'#aebbc2',3)
    if mode=='feed':
        c.text((771,283),'THE HIGHLIGHTS',20,'#b6c2c9',style='bold')
        c.line([(771,320),(1148,320)],'#3d4e5e',2)
        c.ellipse((772,347,815,390),'#67818e')
        c.text((833,349),'someone, somewhere',21,CREAM)
        c.text((833,379),'just now',16,'#8d9ca7')
        c.rect((771,425,1149,633),'#435c6c',r=12)
        for i in range(7):
            x=785+i*51;hh=35+(i*39)%140
            c.rect((x,626-hh,x+35,626),'#71858b')
        c.glow(1050,475,75,'#e4c897',.3)
        c.ellipse((1035,460,1069,494),GOLD)
        c.text((790,662),'Another milestone.',28,CREAM,style='bold')
        c.text((790,706),'So grateful. On to the next.',21,'#a6b4bb')
        c.text((790,776),'2,481 people celebrated this',18,'#8da0ae')
    else:
        c.ellipse((771,282,823,334),'#b87558')
        c.text((841,286),'Jules',27,CREAM,style='bold')
        c.text((841,324),'online earlier',16,'#8d9ca7')
        c.line([(770,367),(1150,367)],'#3c4b59',2)
        c.text((960,393),'TODAY',16,'#8b9ca9','center')
        for yy,txt in [(441,'Coffee this week?'),(510,'We saved you a seat.'),(579,'You coming?')]:
            c.rect((773,yy,1117,yy+53),'#3b4d5c',r=18)
            c.text((794,yy+15),txt,23,CREAM)
        if p<.37:
            msg='Sorry, I haven\'t really...';n=int(ease(p/.37)*len(msg));draft=msg[:n]
        elif p<.53:
            msg='Sorry, I haven\'t really...';draft=msg[:max(0,int((1-(p-.37)/.16)*len(msg)))]
        elif p<.83:
            msg='Yeah. Where are you?';draft=msg[:int(ease((p-.53)/.3)*len(msg))]
        else:draft=''
        if p>.83:
            c.rect((824,671,1145,728),'#4b7278',r=18)
            c.text((842,690),'Yeah. Where are you?',22,CREAM)
            c.text((1127,742),'delivered',16,'#829a9c','right')
        c.rect((766,785,1154,831),'#192431','#4b5c68',1,r=19)
        c.text((785,799),draft,20,CREAM)
    # Separate finger silhouettes, with small nail shapes.
    for i in range(4):
        yy=500+i*44;c.rect((680,yy,749,yy+32),CREAM,INK,2,r=16)
        c.ellipse((718,yy+8,736,yy+24),'#c5c5b6')
    c.path([('M',(1200,824)),('L',(1294,899)),('L',(1390,984)),('L',(1216,984)),('L',(1135,871)),('C',(1090,822,1070,787,1093,773)),('C',(1119,757,1156,807,1200,824)),('Z',())],CREAM,INK,3)
    c.poly([(1244,892),(1367,829),(1500,984),(1304,984)],'#465d6b',INK,3)
    c.line([(1270,909),(1390,850)],'#68808d',3)

def frame(t,width=1920):
    start,end,name,_,_=shot_at(t)
    u=t-start;p=u/(end-start)
    pt=math.floor(t*POSE_FPS)/POSE_FPS
    phase=pt*7.5
    blink=(int(pt*12)%61 in [0,1])
    kind={'opening':'room','reach':'room','feed':'room','raise':'room','work':'desk','run':'street','award':'room','late':'desk','measure':'room','build':'tower','climb':'tower','touch':'tower','fall':'tower','floor':'tower','message':'tower','leave':'room','cafe':'cafe','reflection':'cafe','connection':'cafe','ending':'cafe'}[name]
    zoom=1.015+.025*ease(p);cx=960;cy=540
    if name in ['reach','raise','measure','award']:cx=1150;zoom=1.16+.04*p
    if name=='floor':cx=1090;cy=650;zoom=1.14+.02*p
    if name=='reflection':cx=1100;zoom=1.12+.045*p
    if name=='connection':cx=1080;zoom=1.04+.06*p
    if name=='ending':zoom=1.02
    im=background(kind,width).copy()
    if name in ['feed','message']:im=im.filter(ImageFilter.GaussianBlur(width/130))
    im=camera_image(im,zoom,cx,cy);c=Canvas(im,zoom,cx,cy)
    if name in ['opening','reach']:
        rise=ease((u-.7)/3) if name=='reach' else 0
        character(c,1488,841-rise*12,.82,mood='hope' if rise>.6 else 'tired',look=-1,phase=pt,arm=((0,-230-85*rise),(-25,-180-250*rise)))
        yy=860-rise*15
        character(c,1235,yy,1,mood='hope' if rise>.6 else 'tired',arm=((83,-230-85*rise),(100,-180-250*rise)),phase=pt,blink=blink,look=1)
        enough(c,438)
        if name=='opening':
            c.text((190,587),'Am I',56,CREAM,style='serif')
            c.text((190,655),'enough?',77,CREAM,style='serif')
            c.text((193,756),'AN ORIGINAL ANIMATED SHORT',15,'#81929f')
        if name=='reach' and p>.65:c.text((1465,743),'Almost.',23,'#a8b5bb','center')
    elif name=='feed':
        c=Canvas(im);phone(c,t,'feed',p)
    elif name=='raise':
        mirror_actor(c,t,shadowed=True)
        character(c,1230,860,mood='sad',phase=pt,look=1,arm=((83,-270),(100,-418)))
        enough(c,lerp(438,337,ease(p)))
        if p>.45:c.text((1480,530),'A little more.',23,'#cd9294','center','italic')
    elif name in ['work','late']:
        arm=((83,-179+math.sin(phase*3)*3),(142,-185+math.sin(phase*4)*2))
        character(c,725,818,1.03,mood='tired',pose='sit',arm=arm,phase=pt,blink=blink,look=1,lean=14)
        cup(c,1450,594,t,.85)
        for i in range(3 if name=='work' else 8):
            x=867+(i%3)*81;y=650+(i//3)*56
            c.poly([(x,y),(x+57,y-5),(x+64,y+36),(x+7,y+41)],'#aeb3a8')
            for j in range(3):c.line([(x+10,y+10+j*6),(x+46,y+7+j*6)],'#66777b',1)
        if name=='late':
            for i in range(4):book(c,1680,862-i*27,135,25,['#667b84','#927c62'][i%2])
            shadow(c,480,850,1.22,phase=pt)
            c.text((1010,321),'ONE MORE THING.',20,'#8b9aa3','center')
        else:c.text((1010,321),'I can do more.',25,'#9eaeb5','center')
    elif name=='run':
        # Constant screen position plus moving city: lateral tracking shot.
        offset=(u*125)%1920;k=width/1920
        base=background('street',width)
        im=Image.new('RGB',base.size)
        shift=round(offset*k)
        im.paste(base,(-shift,0));im.paste(base,(width-shift,0));c=Canvas(im)
        character(c,885,812,1.05,mood='determined',pose='run',phase=phase,look=1)
        for i in range(3):
            xx=980+((u*.7+i*.3)%1)*80;yy=495-i*3
            c.ellipse((xx,yy,xx+16,yy+7),'#647885')
        weather(c,t)
        c.text((180,165),'05:12',26,'#9daeb7')
        c.text((180,204),'BEFORE THE WORLD WAKES',15,'#768c9c')
    elif name=='award':
        mirror_actor(c,t,shadowed=True)
        character(c,1240,860,mood='smile' if p<.5 else 'sad',phase=pt,arm=((66,-172),(9,-173)),look=1)
        award(c,1240,666,1.4)
        enough(c,lerp(337,280,ease((p-.4)/.45)))
        if p>.65:c.text((1490,512),'And now?',24,'#cd9294','center','italic')
    elif name=='measure':
        mirror_actor(c,t,shadowed=True)
        character(c,1230,860,mood='sad',phase=pt,blink=blink,look=1,lean=-12)
        enough(c,280)
        ruler_y=lerp(530,455,ease(p))
        c.rect((1280,ruler_y,1620,ruler_y+16),'#a97b78',INK,1,r=3)
        for i in range(17):c.line([(1288+i*19,ruler_y),(1288+i*19,ruler_y+9)],'#47343e',1)
        c.text((1450,590),'Still?',35,'#d79a9a','center','serif')
    elif name=='build':
        count=min(7,1+int(u*1.4));tower(c,t,count)
        character(c,815,870,mood='determined',phase=pt,arm=((95,-180),(170,-180)),look=1)
        if count<7:book(c,930,692,170,34,'#8f7b64')
        enough(c,235,1337,1750)
        c.text((202,677),'Something to show.',28,'#9aaab2')
    elif name=='climb':
        tower(c,t);rise=ease(p)*336
        character(c,1080+170*ease(p),870-rise,.94,mood='determined',pose='walk',phase=phase,arm=((75,-240),(85,-310)),look=1)
        shadow(c,1560,838,1.5,phase=pt,hand=True)
        enough(c,235,1337,1750)
    elif name=='touch':
        tower(c,t)
        character(c,1260,534,.94,mood='hope' if p<.5 else 'surprise',phase=pt,arm=((97,-250),(142,-320-30*ease(p))),look=1)
        shadow(c,1580,838,1.5,phase=pt,hand=True)
        enough(c,235-45*ease((p-.4)/.6),1337,1750)
        if .1<p<.46:c.glow(1395,235,110,'#ead0a2',.35*math.sin((p-.1)/.36*math.pi))
        if p>.55:c.text((1530,554),'Just a little more.',24,'#d3999b','center','italic')
    elif name=='fall':
        scatter=ease(min(1,p*1.8));tower(c,t,scatter=scatter)
        if p<.5:
            y=lerp(534,870,ease(p*2));x=lerp(1260,1045,ease(p*2))
            character(c,x,y,.94,mood='surprise',pose='crouch',arm=((100,-180),(140,-140)),phase=pt)
        else:character(c,1045,870,.94,mood='sad',pose='fall',phase=pt)
        enough(c,190,1337,1750)
        # Papers flutter at different speeds, then settle.
        for i in range(9):
            x=1040+math.sin(i*2.4)*300*p;y=600+((i*43+u*90)%220)
            c.poly([(x,y),(x+35,y-8),(x+46,y+13),(x+11,y+23)],'#8b999a')
    elif name=='floor':
        tower(c,t,scatter=1)
        character(c,1045,870,.94,mood='sad',pose='fall',phase=pt)
        enough(c,190,1337,1750)
        c.rect((1175,832,1263,852),'#334858','#7a929c',2,r=5)
        if p>.75:c.glow(1215,833,110,'#8dabb9',.18)
    elif name=='message':
        c=Canvas(im);phone(c,t,'message',p)
    elif name=='leave':
        mirror_actor(c,t,shadowed=True);enough(c,280)
        # Warm open doorway at left. Its light is a distinct change of direction.
        c.glow(235,630,390,'#cba46c',.22)
        c.rect((90,250,335,860),'#9c835f','#6f7064',4,r=6)
        c.poly([(335,250),(455,294),(455,859),(335,860)],'#35424b','#788082',2)
        xx=lerp(1110,210,ease(p))
        character(c,xx,860,mood='hope',pose='walk',phase=phase,look=-1)
    elif name in ['cafe','reflection','connection','ending']:
        # A separate, dim figure in the shop glass: reflection, not physical threat.
        if name=='reflection':
            shadow(c,1335,657,.86,phase=pt,hand=p<.65)
            ry=410+60*ease((p-.5)/.5)
            c.line([(1338,ry),(1450,ry)],'#8a6569',5)
            for xx in range(1340,1450,12):c.line([(xx,ry),(xx,ry+6)],'#b88a8d',1)
        friend_arm=((65,-180),(105,-177))
        friend_x=1180
        if name=='cafe':
            friend_x=lerp(1090,1180,ease(p/.4))
            # The bag is lifted away as a seat is made for the protagonist.
            bx=lerp(893,1340,ease(p/.45))
            by=740-70*math.sin(min(1,p/.45)*math.pi)
            c.rect((bx-34,by-57,bx+34,by),'#536c6d',INK,2,r=8)
            c.path([('M',(bx-15,by-57)),('C',(bx-19,by-85,bx+19,by-85,bx+15,by-57))],None,'#698183',4)
        character(c,friend_x,824,.83,mood='smile',pose='sit',friend=True,phase=pt,look=-1,arm=friend_arm,blink=blink)
        if name=='cafe':
            if p<.48:
                x=lerp(540,870,ease(p/.48))
                character(c,x,862,.9,mood='sad',pose='walk',phase=phase,look=1)
            else:
                character(c,895,824,.83,mood='sad' if p<.8 else 'hope',pose='sit',phase=pt,look=1,arm=((65,-171),(95,-175)))
            cup(c,lerp(1110,1000,ease((p-.45)/.4)),738,t,.8)
            cup(c,1275,738,t,.8)
            if p>.65:c.text((1190,438),'Hey. There you are.',26,'#e1d6bd','center')
        else:
            mood='sad' if name=='reflection' and p<.45 else 'relief'
            character(c,895,824,.83,mood=mood,pose='sit',phase=pt,look=1,arm=((65,-171),(95,-175)),blink=blink)
            cup(c,1000,738,t,.8);cup(c,1275,738,t,.8)
        if name=='connection':
            c.text((1030,424),'No explanation required.',25,'#d7c9ac','center','serif')
        if name=='ending':
            # The distant apartment retains the line; nobody remains beneath it.
            c.rect((37,252,161,471),'#273544','#5a6266',2,r=3)
            c.line([(51,309),(146,309)],'#a66a6b',2)
            c.text((150,289),'ENOUGH',10,'#c08a86','right')
            c.text((960,313),'Am I enough?',61,'#e4d9bf','center','serif')
            c.text((960,402),'You don’t have to earn your place here.',25,'#c3bba7','center')
        weather(c,t,True)
    dust(c,t,name in ['cafe','reflection','connection','ending'])
    # Screen-space typography and finishing never inherit camera movement.
    c.flush()
    c=Canvas(im)
    captions={
        'raise':'Every time I got close, it moved.',
        'late':'So I kept going.',
        'measure':'There was always something missing.',
        'build':'Maybe I just needed more proof.',
        'touch':'For a moment, I thought I had made it.',
        'floor':'I had so much to show. I’d forgotten to show up.',
    }
    if .16<p<.92:subtitle(c,captions.get(name,''))
    c.flush()
    bars(im)
    # Short dip transitions separate shots without hiding whole performances.
    fade=1
    if t<.6:fade=ease(t/.6)
    if t>89:fade=1-ease((t-89)/1)
    if name not in ['opening','feed','message']:
        fade*=.65+.35*min(ease(u/.16),ease((end-t)/.16))
    if fade<.999:im=Image.blend(Image.new('RGB',im.size,'#080d14'),im,fade)
    return im

def storyboard(out,width=640):
    thumb_h=round(width*1080/1920)
    sheet=Image.new('RGB',(width*4,(thumb_h+65)*5),'#101924')
    d=ImageDraw.Draw(sheet)
    for i,(start,end,name,purpose,_) in enumerate(SHOTS):
        im=frame(start+(end-start)*.65,width)
        x=i%4*width;y=i//4*(thumb_h+65)
        sheet.paste(im,(x,y));d.text((x+14,y+thumb_h+8),f'{start:02}–{end:02}s  {purpose}',font=font(18),fill=CREAM)
    sheet.save(out/'storyboard.jpg',quality=92)

def render(args):
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    if args.stills:
        storyboard(out)
        for t in [2.4,7.5,15.5,21,25,29,34,39,44,49,53,57.5,62,67.5,71,76.5,81,85,88]:
            frame(t,args.width).save(out/f'frame-{t:05.1f}.jpg',quality=93)
        return
    begin=args.start;end=min(args.end,DURATION);fps=args.fps
    target=out/f'picture-{begin:g}-{end:g}.mp4'
    cmd=[FFMPEG,'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{args.width}x{round(args.width*1080/1920)}','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(target)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    n=round((end-begin)*fps);started=time.monotonic()
    try:
        for i in range(n):
            proc.stdin.write(frame(begin+i/fps,args.width).tobytes())
            if i%max(1,int(fps*5))==0:print(f'picture {begin+i/fps:.1f}s / {end:.1f}s | {i+1}/{n} frames | {time.monotonic()-started:.1f}s elapsed',flush=True)
    finally:proc.stdin.close()
    if proc.wait()!=0:raise RuntimeError('FFmpeg picture encode failed')
    print(target,flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--width',type=int,default=1920);p.add_argument('--fps',type=int,default=FPS);p.add_argument('--start',type=float,default=0);p.add_argument('--end',type=float,default=DURATION);p.add_argument('--out',default='build');p.add_argument('--stills',action='store_true')
    a=p.parse_args()
    if a.width<320 or a.width%32: p.error('width must be a multiple of 32, at least 320')
    if not 0<=a.start<a.end<=DURATION:p.error('time range must lie inside the film')
    render(a)

if __name__=='__main__':main()
