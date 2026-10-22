"""Build and validate the final film, locally or from GitHub Actions chunks."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from . import audio
from .render import frame, storyboard
from .story import SHOTS, DURATION, FPS, TITLE

def run(cmd):
    print(' '.join(map(str,cmd)),flush=True)
    subprocess.run(list(map(str,cmd)),check=True)

def production_script():
    intro='''# Am I enough?\n\nAn original 90-second wordless animated short about measuring your worth against a moving target. Story dialogue and inner thoughts appear as text; there is no synthesized narrator.\n\n## Creative direction\n\nIvory protagonist, teal scarf, expressive eyelids and eyebrows. The reflected measuring figure uses muted coral against navy. A friend wears a terracotta hat and warm scarf. Dark, softly textured interiors open into a warmer café exterior. 1080p, 24 fps picture, principally 12 fps character pose timing, independently moving camera and atmosphere.\n\nThe ENOUGH line moves upward after each apparent success. The final action is turning attention toward a friend, rather than defeating an emotion forever. A distant line remains visible in the final shot, with nobody beneath it.\n\n## Shot and sound plan\n\n| Time | Shot | Purpose | Sound direction |\n|---|---|---|---|\n'''
    for a,b,name,purpose,cue in SHOTS:intro+=f'| {a:02}–{b:02}s | {name} | {purpose} | {cue} |\n'
    return intro+'''\n## Sound production\n\nAn original procedurally composed score: soft struck-string synthesis, a sustained bowed-like layer, sparse low pulses, then warmer resolving harmony. Independently synthesized room/city air and timed foley include notifications, keyboard, shoes, books, metallic details, the collapse, paper, latch and cup. These are sound-design intentions for this film, not claims about the reference videos.\n\nMusic, ambience and foley remain available as separate stems. The final mix targets -16 LUFS integrated / -1.5 dBTP using two-pass EBU R128 normalization. No borrowed soundtrack, stock recording, paid API, voice clone or external model is used.\n\n## Production limits\n\nThis is an original first production with reusable articulated vector characters and procedural sound. It is not a claim that subjective quality matches the reference films. No audio-by-ear approval is represented by automated checks.\n'''

def verify(path):
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]))
    video=next(s for s in info['streams'] if s['codec_type']=='video')
    sound=next(s for s in info['streams'] if s['codec_type']=='audio')
    assert abs(float(info['format']['duration'])-DURATION)<.15,info['format']['duration']
    assert int(video['nb_frames'])==round(DURATION*FPS),video.get('nb_frames')
    assert video['r_frame_rate']=='24/1',video['r_frame_rate']
    assert sound['channels']==2
    assert int(sound['sample_rate'])==48000
    # A complete decode catches truncated or corrupt packets, not merely headers.
    run(['ffmpeg','-v','error','-xerror','-i',path,'-f','null','-'])
    report={'title':TITLE,'duration_seconds':float(info['format']['duration']),'width':video['width'],'height':video['height'],'fps':24,'frames':int(video['nb_frames']),'audio_sample_rate':48000,'audio_channels':2,'full_decode':'passed'}
    path.with_name('validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)

def assemble(out,chunks,width):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    chunks=[Path(p).resolve() for p in chunks]
    manifest=out/'concat.txt'
    manifest.write_text(''.join("file '"+str(p).replace("'","'\\''")+"'\n" for p in chunks))
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',manifest,'-c','copy',out/'picture.mp4'])
    audio.make(out/'audio')
    final=out/'Am-I-enough.mp4'
    run(['ffmpeg','-y','-v','error','-i',out/'picture.mp4','-i',out/'audio/soundtrack.wav','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','256k','-ar','48000','-t','90','-metadata','title=Am I enough?','-metadata','comment=Original artwork, animation and synthesized score. Reproducible without paid services.','-movflags','+faststart',final])
    storyboard(out)
    frame(88,width).save(out/'poster.jpg',quality=95)
    frame(7.5,width).save(out/'mirror-still.jpg',quality=95)
    (out/'PRODUCTION.md').write_text(production_script())
    verify(final)
    # Validate the delivered AAC mix, not only the premaster WAV.
    r=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(final),'-af','loudnorm=print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
    import re
    stats=json.loads(re.search(r'\{\s*"input_i".*?\}',r.stderr,re.S).group())
    (out/'final-loudness.json').write_text(json.dumps(stats,indent=2)+'\n')
    assert -18<float(stats['input_i'])<-14,stats
    assert float(stats['input_tp'])<0,stats
    print(f'Finished: {final}',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='build/final');p.add_argument('--width',type=int,default=1920);p.add_argument('--chunks',nargs='*');p.add_argument('--verify',type=Path)
    a=p.parse_args()
    if a.verify:verify(a.verify);return
    if a.chunks:assemble(a.out,a.chunks,a.width);return
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    chunks=[]
    for start,end in [(0,30),(30,60),(60,90)]:
        run([sys.executable,'-m','film.render','--start',start,'--end',end,'--width',a.width,'--out',out/'chunks'])
        chunks.append(out/'chunks'/f'picture-{start}-{end}.mp4')
    assemble(out,chunks,a.width)

if __name__=='__main__':main()
