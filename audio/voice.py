"""Voiceover for narrator lines with Kokoro (Apache-2.0, runs on CPU).

python audio/voice.py build/film.json build/voice

For every line with who == "narrator" this speaks the text (and its twist line after a short
pause), stretches the shot if the voice needs more time, sets the on-screen typing speed to match
the voice, and records the file in the line ("voice_file", "voice_dur"). The film JSON is
rewritten in place. If anything fails, the film is left unchanged: captions still appear, silently.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

VOICES = {'male': ('a', 'am_michael'), 'female': ('a', 'af_heart'), 'british_male': ('b', 'bm_george'), 'british_female': ('b', 'bf_emma')}


def notice(title, message, level='notice'):
    print(f"::{level} title={title}::{message.replace(chr(10), '%0A')}", flush=True)


def main() -> int:
    film_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    film = json.loads(film_path.read_text())
    jobs = [(i, k, ln) for i, s in enumerate(film['shots']) for k, ln in enumerate(s.get('lines') or []) if ln.get('who') == 'narrator']
    if not jobs:
        notice('Voiceover', 'no narrator lines in this film')
        return 0
    try:
        import numpy as np
        import soundfile as sf
        from kokoro import KPipeline
        lang, voice = VOICES.get(film.get('narrator', 'male'), VOICES['male'])
        pipe = KPipeline(lang_code=lang, repo_id='hexgrad/Kokoro-82M')
        out_dir.mkdir(parents=True, exist_ok=True)
        started = time.time()
        sr = 24000

        def speak(text):
            chunks = [np.asarray(audio, dtype=np.float32) for _, _, audio in pipe(text, voice=voice, speed=0.94)]
            return np.concatenate(chunks) if chunks else np.zeros(1, np.float32)

        for i, k, ln in jobs:
            first = speak(ln['text'])
            parts = [first]
            if ln.get('twist'):
                parts += [np.zeros(int(.38 * sr), np.float32), speak(ln['twist'])]
            audio = np.concatenate(parts)
            name = f'vo-{i:03d}-{k}.wav'
            sf.write(out_dir / name, audio, sr)
            dur = len(audio) / sr
            ln['voice_file'] = name
            ln['voice_dur'] = round(dur, 3)
            # captions reveal in step with the voice
            ln['cps'] = round(max(10.0, len(ln['text']) / max(.4, len(first) / sr * .9)), 2)
            if ln.get('twist'):
                ln['twist_at'] = round(len(first) / sr + .38, 3)
            shot = film['shots'][i]
            need = (ln.get('at') or 0) + dur + .7
            if shot['dur'] < need:
                shot['dur'] = round(need, 2)
        film['duration'] = round(sum(s['dur'] for s in film['shots']), 2)
        film_path.write_text(json.dumps(film, indent=1, ensure_ascii=False))
        notice('Voiceover', f'{len(jobs)} narrator lines with {voice} in {time.time() - started:.0f}s; film is now {film["duration"]}s')
    except Exception as exc:  # noqa: BLE001 -- captions remain, silently
        notice('Voiceover unavailable', f'{type(exc).__name__}: {str(exc)[:400]}; narration stays as on-screen text.', 'warning')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
