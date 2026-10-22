"""Original deterministic synthesis: score, room/city ambience and timed foley.

No stock recordings, APIs, model weights, or copyrighted source soundtracks.
"""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
from scipy import signal
from scipy.io import wavfile
from .story import DURATION
from .toolchain import FFMPEG

SR=48000
RNG=np.random.default_rng(1947)

def frequency(note):return 440*2**((note-69)/12)

def add(dst,src,start,gain=1,pan=0):
    i=round(start*SR);a=max(0,-i);i=max(0,i);n=min(len(src)-a,len(dst)-i)
    if n<=0:return
    g=np.array([np.cos((pan+1)*np.pi/4),np.sin((pan+1)*np.pi/4)],np.float32)
    dst[i:i+n]+=src[a:a+n,None]*g[None,:]*gain

def piano(note,duration=3,velocity=.5):
    t=np.arange(round(duration*SR),dtype=np.float32)/SR;f=frequency(note)
    out=np.zeros(len(t),np.float32)
    for h in range(1,8):
        amp=np.exp(-h*.52)/h**.45
        # Slight inharmonicity and detuning create a soft struck-string color.
        out+=amp*np.sin(2*np.pi*f*h*(1+.00012*h*h)*t+.02*h)*np.exp(-t*(.75+h*.18))
        out+=amp*.17*np.sin(2*np.pi*f*h*1.0017*t)*np.exp(-t*(1+h*.2))
    out*=np.minimum(1,t/.008)*np.minimum(1,(duration-t)/.12)
    return out*velocity*.4

def bowed(note,duration=6):
    t=np.arange(round(duration*SR),dtype=np.float32)/SR;f=frequency(note)
    phase=2*np.pi*f*t+.018*np.sin(2*np.pi*4.8*t)
    a=sum(np.sin(h*phase)/(h*h) for h in range(1,6))
    env=np.minimum(1,t/1.1)*np.minimum(1,(duration-t)/1.6)
    return (a*env*.11).astype(np.float32)

def noise(duration,low=100,high=5000,decay=6):
    t=np.arange(round(duration*SR),dtype=np.float32)/SR
    n=RNG.normal(0,1,len(t)).astype(np.float32)
    sos=signal.butter(2,[low,high],btype='bandpass',fs=SR,output='sos')
    n=signal.sosfilt(sos,n).astype(np.float32)
    return n*np.exp(-t*decay)*np.minimum(1,t/.002)

def tone(f,duration=.4,decay=8):
    t=np.arange(round(duration*SR),dtype=np.float32)/SR
    return (np.sin(2*np.pi*f*t)*np.exp(-decay*t)*np.minimum(1,t/.004)).astype(np.float32)

def envelope(t,a,b,fade=.5):
    return np.minimum(1,np.maximum(0,(t-a)/fade))*np.minimum(1,np.maximum(0,(b-t)/fade))

def make(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    n=round(SR*DURATION)
    music=np.zeros((n,2),np.float32);amb=np.zeros_like(music);fx=np.zeros_like(music)
    # D minor / B-flat / F / C, shifting to F major / C / Dm / B-flat at the invitation.
    chords=[[50,57,62,65],[46,53,58,62],[41,53,57,60],[48,55,60,64]]
    melody=[74,69,65,67,69,65,62,64,65,69,72,69,67,65,64,62]
    beat=.89
    for i,start in enumerate(np.arange(.8,55,beat)):
        chord=chords[(i//8)%4]
        note=chord[(i*3)%4]+(12 if i%4==2 else 0)
        velocity=.34 if start<18 else .43
        add(music,piano(note,3.5,velocity),start,pan=(-.18 if i%2 else .18))
        if i%2==0:add(music,piano(melody[(i//2)%len(melody)],4,.24),start+.07,pan=.1)
        if i%8==0:
            add(music,bowed(chord[0]-12,8),start,gain=.45,pan=-.12)
            add(music,bowed(chord[2],7),start+.15,gain=.22,pan=.2)
    # Gentle heartbeat-like pulse accumulates without becoming a loud trailer bed.
    for st in np.arange(18.2,55,.89):
        add(music,tone(58,.35,13),st,gain=.035)
        add(music,noise(.12,200,1600,32),st+.445,gain=.012,pan=.15)
    # Collapse leaves a genuinely sparse passage, then the theme opens in major.
    for st,note in [(59.8,62),(62.2,65),(65,69)]:add(music,piano(note,4.5,.25),st)
    warm=[[53,60,65,69],[48,55,60,64],[50,57,62,65],[46,53,58,62]]
    for i,st in enumerate(np.arange(68.8,87.5,.94)):
        chord=warm[(i//5)%4]
        add(music,piano(chord[i%4],4,.42),st,pan=-.2 if i%2 else .2)
        if i%5==0:
            for j,note in enumerate(chord):add(music,bowed(note,6),st+j*.03,gain=.24,pan=(j-1.5)*.15)
        if i%3==0:add(music,piano([72,74,77,76,72,69,65][(i//3)%7],4,.3),st+.12,pan=.1)
    for j,note in enumerate([41,53,57,60,65,69]):add(music,piano(note,5,.32),86.7+j*.035,pan=(j-2.5)*.1)
    # A quiet reverb field; separate channel delays avoid a dry mono result.
    for delay,gain in [(.071,.14),(.127,.11),(.233,.075),(.391,.045)]:
        shift=round(delay*SR)
        music[shift:,0]+=music[:-shift,1]*gain
        music[shift:,1]+=music[:-shift,0]*gain*.9
    # Persistent room air; filtered stereo air becomes exterior ambience.
    for ch in [0,1]:
        air=RNG.normal(0,1,n).astype(np.float32)
        air=signal.sosfilt(signal.butter(2,[150,2200],btype='bandpass',fs=SR,output='sos'),air).astype(np.float32)
        amb[:,ch]=air*.0022
    ts=np.arange(n,dtype=np.float32)/SR
    exterior=envelope(ts,23,27,.3)+envelope(ts,73,90,1)
    for ch in [0,1]:
        wind=RNG.normal(0,1,n).astype(np.float32)
        wind=signal.sosfilt(signal.butter(2,[90,650],btype='bandpass',fs=SR,output='sos'),wind).astype(np.float32)
        amb[:,ch]+=wind*.013*exterior*(.65+.35*np.sin(ts*.7+ch)**2)
    events=[]
    def hit(st,snd,gain,label,pan=0):
        add(fx,snd,st,gain,pan);events.append({'time':round(float(st),3),'event':label})
    # Glass-line motif: restrained high partials and a low uneasy swell.
    for st in [13.4,28.6,36.3,52.6,79.0]:
        hit(st,tone(1280,1.4,3)+tone(1920,1.4,4)*.3,.055,'glass / measuring-line motif',.2)
        if st<60:hit(st,bowed(38,3),.5,'low reflection swell',.25)
    # Notifications: related sound, gentler on the personal invitation.
    for st,gain in [(9.3,.17),(64.2,.11)]:
        hit(st,tone(784,.55,7),gain,'notification first note')
        hit(st+.12,tone(1046,.65,6),gain*.75,'notification second note',.08)
    for st in [9.15,64.05]:hit(st,tone(115,.25,12),.08,'phone vibration')
    # Keyboard and pencil timings match desk poses.
    for a,b in [(18.2,22.7),(31.2,35.5)]:
        for st in np.arange(a,b,.16):
            if RNG.random()<.82:hit(st,noise(.045,900,7000,80),.035,'keyboard',float(RNG.uniform(-.15,.15)))
    for st in np.arange(23.15,26.95,.42):
        hit(st,noise(.16,80,1800,22),.12,'running foot contact',-.05)
        hit(st+.1,noise(.13,500,3800,18),.03,'shoe scuff',.08)
    for st in [24,25.25,26.4]:hit(st,noise(.55,250,2600,5),.025,'exhalation')
    for st in [27.4,41.7,43.1,44.5]:
        hit(st,tone(1580,.7,8)+tone(2310,.7,11)*.4,.07,'medal / metal detail',.1)
    for st in np.arange(41.35,45.9,.7):hit(st,noise(.15,100,1900,28),.12,'book placed',float(RNG.uniform(-.15,.2)))
    for st in np.arange(46.25,50.8,.65):
        hit(st,noise(.14,80,1500,24),.11,'climbing contact',.12)
        hit(st+.05,tone(330,.25,17),.025,'stack creak',.18)
    hit(51.4,tone(1568,1.2,4),.09,'fingertip touches line',.2)
    for st,gain in [(55.55,.32),(55.83,.2),(56.12,.15),(56.5,.1),(57.1,.06)]:
        hit(st,noise(.5,50,2800,12),gain,'tower / body impact',-.02)
        hit(st+.035,noise(.7,1400,8000,5),gain*.21,'paper scatter',.18)
    for st in np.arange(65.0,68.3,.18):hit(st,noise(.028,1200,5500,100),.018,'phone typing')
    hit(68.35,tone(660,.18,20),.035,'message sent')
    for st in np.arange(69.4,72.7,.5):hit(st,noise(.17,100,2200,23),.085,'walking away',-.2)
    hit(72.65,noise(.16,250,3100,20),.075,'door latch',-.45)
    hit(75.4,noise(.18,250,2800,25),.055,'bag moved on bench',.25)
    hit(76.05,tone(910,.32,14)+noise(.32,200,1800,35)*.6,.065,'cup set down',.05)
    hit(76.23,noise(.22,900,4200,10),.025,'cup slide',-.1)
    # Shape dramatic level envelopes, including the pause after the collapse.
    music_gain=np.ones(n,np.float32)
    music_gain*=1-.88*envelope(ts,55.25,59.3,.18)
    # The phone insert gets breathing room for readable text.
    music_gain*=1-.32*envelope(ts,64,68.8,.4)
    music*=music_gain[:,None]
    for stem in [music,amb,fx]:
        stem*=np.minimum(1,ts/.3)[:,None]
        stem*=np.minimum(1,np.maximum(0,(90-ts)/1.8))[:,None]
    # Keep unmastered stems, then master the sum with FFmpeg's two-pass loudnorm.
    for name,stem in [('music',music),('ambience',amb),('foley',fx)]:
        wavfile.write(out/f'{name}.wav',SR,stem)
    master=music+amb+fx
    wavfile.write(out/'premaster.wav',SR,master)
    command=[FFMPEG,'-hide_banner','-nostats','-i',str(out/'premaster.wav'),'-af','loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json','-f','null','-']
    r=subprocess.run(command,capture_output=True,text=True,check=True)
    import re
    stats=json.loads(re.search(r'\{\s*"input_i".*?\}',r.stderr,re.S).group())
    fil=('loudnorm=I=-16:TP=-1.5:LRA=9:measured_I='+stats['input_i']+':measured_TP='+stats['input_tp']+':measured_LRA='+stats['input_lra']+':measured_thresh='+stats['input_thresh']+':offset='+stats['target_offset']+':linear=true:print_format=json')
    subprocess.run([FFMPEG,'-y','-v','error','-i',str(out/'premaster.wav'),'-af',fil,'-ar',str(SR),'-c:a','pcm_s24le',str(out/'soundtrack.wav')],check=True)
    (out/'sound-events.json').write_text(json.dumps(events,indent=2)+'\n')
    (out/'audio-analysis.json').write_text(json.dumps(stats,indent=2)+'\n')
    print(f'Original soundtrack and {len(events)} sound events written to {out}',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='build/audio');a=p.parse_args();make(a.out)
