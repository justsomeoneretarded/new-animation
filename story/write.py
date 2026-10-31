"""Write a Day One-style film from a short brief with a local model (Ollama, no paid API).

python story/write.py --title "Loneliness" --brief "..." --seconds 120 --out build/film.json [--counter "Words said today"]

Two passes: (1) a beat sheet that follows the format's proven structure, (2) shots for each
beat in the engine's vocabulary. The result is repaired by story/validate.py, and a readable
script (story.md) is written next to it for review.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'story'))
from validate import VOCAB, repair  # noqa: E402

OLLAMA = os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434')
MODEL = os.environ.get('SCRIPT_MODEL', 'gemma4:12b')

FORMULA = """THE FORMAT (study of Day One Films shorts such as "Loneliness" and "Your Winter Arc Starts Now"):
- A 2-3 minute, almost wordless animated short. A plain cream blob character (the hero) fights one relatable everyday struggle.
- A black shadow with red glowing eyes (the demon) is the hero's inner voice. It appears beside the hero at weak moments and says
  SHORT cruel lines in red, lowercase, 2-5 words: "nobody wants to hear from you.", "stay quiet.", "you'll quit.", "just one more.".
- A visible on-screen COUNTER that measures the struggle and that viewers can track, e.g. "WORDS SAID TODAY: 0" or a chapter label "DAY 1",
  "DAY 4", "DAY 60". It moves with the story and turns red (alert) during relapses.
- Specific, physical, everyday details instead of abstract metaphors: a 5:30 alarm, pizza boxes, an unread message, a phone call from
  an unknown number, a cupcake with one candle, a fridge light at 2am, a typed message that gets deleted.
- Structure: (1) cold open showing the problem in one image; (2) the demon wins small moments; (3) an invitation or trigger
  (a message, an alarm, a friend); (4) a first awkward attempt ("h-hi."); (5) a small win; (6) a RELAPSE where the demon wins again
  and the counter goes red; (7) the hero refuses the demon (an extreme close-up of determined eyes); (8) consistent progress
  montage with the counter/days moving; (9) the demon is smaller, weaker or ignored; (10) a quiet payoff with another person;
  (11) two-line quote card where the second line twists the first ("Everyone falls." / "Not everyone gets back up.");
  (12) a red imperative card ("LOCK IN." / "Right now."); (13) like and subscribe.
- Dialogue is rare, lowercase, short, human: "h-hi.", "...cool.", "you came!", "i said cool. i panicked.".
- Bottom captions are rare (at most 3 in the whole film), plain and honest: "Every word got a little easier."
"""


LOG = None


def chat(system: str, user: str, temperature=.7, num_predict=3000, schema=None) -> dict:
    body = json.dumps({'model': MODEL, 'stream': False, 'think': False, 'keep_alive': '30m', 'format': schema or 'json',
                       'options': {'temperature': temperature, 'num_ctx': 16384, 'num_predict': num_predict},
                       'messages': [{'role': 'system', 'content': system + '\nReturn only valid JSON. /no_think'},
                                    {'role': 'user', 'content': user}]}).encode()
    for attempt in range(3):
        text = ''
        try:
            req = urllib.request.Request(OLLAMA + '/api/chat', body, {'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=3600) as r:
                text = json.loads(r.read())['message']['content']
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.S)
            return json.loads(text[text.index('{'):text.rindex('}') + 1])
        except Exception as exc:  # noqa: BLE001
            print(f'  model call failed ({type(exc).__name__}: {str(exc)[:200]}); retry {attempt + 1}', flush=True)
            snippet = (text[:350] or '(empty reply)').replace('%', '%25').replace('\n', '%0A')
            print(f'::warning title=Model reply was not JSON ({type(exc).__name__})::{snippet}', flush=True)
            if LOG:
                with open(LOG, 'a') as f:
                    f.write(f'--- failed attempt {attempt + 1}: {type(exc).__name__}: {exc}\n{text[:4000]}\n')
            time.sleep(3)
    raise RuntimeError('the script model did not return usable JSON')


BEAT_SCHEMA = {
    'type': 'object', 'required': ['title', 'logline', 'hud_label', 'friend', 'music_prompt', 'beats', 'quote', 'red_card'],
    'properties': {
        'title': {'type': 'string'}, 'logline': {'type': 'string'}, 'hud_label': {'type': 'string'}, 'music_prompt': {'type': 'string'},
        'friend': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'hat': {'type': 'string'}}, 'required': ['name', 'hat']},
        'quote': {'type': 'array', 'items': {'type': 'string'}}, 'red_card': {'type': 'array', 'items': {'type': 'string'}},
        'beats': {'type': 'array', 'items': {'type': 'object', 'required': ['name', 'seconds', 'where', 'what_happens'], 'properties': {
            'name': {'type': 'string'}, 'seconds': {'type': 'number'}, 'where': {'type': 'string'}, 'time': {'type': 'string'},
            'weather': {'type': 'string'}, 'what_happens': {'type': 'string'}, 'counter': {'type': 'number'}, 'chapter': {'type': 'string'},
            'relapse': {'type': 'boolean'}, 'demon_line': {'type': 'string'}, 'dialogue': {'type': 'string'}, 'phone': {'type': 'string'}}}}}}


def beat_sheet(title, brief, seconds, counter):
    system = FORMULA + """
You write the beat sheet. Reply with JSON only:
{"title": str, "logline": str,
 "hud_label": str  (the counter label, e.g. "Words said today"; 2-4 words),
 "friend": {"name": str, "hat": one of beanie_orange|beanie_green|beanie_blue|beanie_red|cap_grey|cap_red},
 "music_prompt": str (instrumental style for an AI composer: instruments, mood arc, bpm),
 "beats": [ {"name": str, "seconds": number, "where": one of SETS, "time": night|dawn|day|dusk, "weather": none|rain|snow,
             "what_happens": str (concrete visible action, 1-2 sentences), "counter": number, "chapter": str or "",
             "relapse": bool, "demon_line": str or "", "dialogue": str or "", "phone": str or "" (what is on the phone screen, if any)} ],
 "quote": [str, str], "red_card": [str, str]}
Write 11-14 beats whose seconds add up to the target length minus 12 seconds for the cards.
SETS: """ + ', '.join(f'{k} ({v["about"]})' for k, v in VOCAB['sets'].items())
    user = f'Title: {title}\nBrief: {brief}\nTarget length: {seconds} seconds\n' + (f'Counter label to use: {counter}\n' if counter else '')
    return chat(system, user, .85, 4000, BEAT_SCHEMA)


def shot_schema():
    v = VOCAB
    return f"""SHOT JSON (one object per shot):
{{"dur": seconds 1.8-5.5,
 "set": one of {list(v['sets'])}, "time": one of {v['times']}, "weather": one of {v['weather']},
 "clock": "02:47" (bedroom clock text, optional),
 "camera": {{"frame": one of {list(v['frames'])}, "on": actor id to frame, "push": 0.03-0.1 slow zoom}},
 "actors": [{{"id": cast id, "x": 0-100 position, "to": 0-100 (walk/run target), "pose": one of {list(v['poses'])},
             "mood": one of {v['moods']}, "hold": one of {v['holds']}, "facing": -1|0|1, "seated": true (phone while sitting),
             "target": id (for lean/grab), "at": seconds delay, "depth": "back" (background person), "scale": 0.5-1.2, "opacity": 0.3-1}}],
 "lines": [{{"who": actor id or "caption", "text": short text, "at": seconds}}],
 "hud": {{"value": number or [from, to], "alert": true when relapsing, "chapter": "DAY 4"}},
 "phone": {{"app": one of {list(v['phone_apps'])}, "contact": name, "time": "18:02",
           "messages": [{{"from": "them"|"me", "text": str, "at": seconds}}],
           "typing": {{"text": str, "at": seconds, "action": "delete"|"send"}},
           "notifications": [{{"app": str, "text": str, "at": seconds}}], "call": {{"decline_at": seconds}}, "label": alarm label}},
 "items": [{{"type": one of {v['items']}, "x": 0-100, "on": "nightstand"|"desk"|"table"|"bed"}}],
 "door": [0, 1] (door opens; bedroom/hallway), "door_at": seconds, "fridge": [0, 1] (kitchen),
 "music": one of {v['music_levels']}, "transition": one of {v['transitions']},
 "sfx": [{{"name": one of {v['sfx']}, "at": seconds}}]}}
SPOTS per set: {json.dumps({k: s['spots'] for k, s in v['sets'].items()})}
RULES: frame "phone" needs "phone" and shows only the phone (no actors). Seats: {json.dumps({k: s.get('seat') for k, s in v['sets'].items() if s.get('seat')})}.
Vary framing like a film editor: never more than two "wide" shots in a row; use "close" for reactions, "extreme" for the decision,
"two" when the demon or a friend is next to the hero, "phone" whenever a message, call, alarm or feed matters.
The demon stands right next to the hero (x within 10-14) when it speaks, using pose lean or grab with target "hero"."""


def shots_for_beat(beat, i, n, sheet, fid, example):
    # The system prompt is identical for every beat so Ollama can reuse its prompt cache;
    # everything that changes goes in the user message.
    system = FORMULA + '\n' + shot_schema() + f"""
You are the storyboard artist. Turn ONE beat into 2-4 shots. Reply with JSON only: {{"shots": [ ...shot objects... ]}}.
Cast ids: hero, demon, {fid}, and background extras extra1, extra2.
Counter label: "{sheet.get('hud_label', '')}". Shot durations in a beat add up to about the beat's seconds.
Example shots from another film in this format (follow the style and the JSON shape, not the story):
{example}"""
    user = (f"Beat {i + 1} of {n}. Counter value in this beat: {beat.get('counter', '')}; chapter: \"{beat.get('chapter', '')}\"; "
            f"relapse (counter shown red): {bool(beat.get('relapse'))}.\n{json.dumps(beat, ensure_ascii=False)}")
    out = chat(system, user, .55, 3000)
    shots = out.get('shots') or []
    for s in shots:
        s.setdefault('set', beat.get('where'))
        if beat.get('time'):
            s.setdefault('time', beat['time'])
        if beat.get('weather') and beat['weather'] != 'none':
            s.setdefault('weather', beat['weather'])
    return shots


def friend_id(sheet):
    friend = sheet.get('friend') or {}
    fid = ''.join(ch for ch in str(friend.get('name') or 'sam').lower() if ch.isalpha())[:10] or 'sam'
    return 'sam' if fid in ('hero', 'demon', 'extra') else fid


def example_shots():
    film = json.loads((ROOT / 'examples' / 'the-sketchbook.json').read_text())
    return json.dumps([film['shots'][k] for k in (2, 6, 11, 15, 17, 18, 26, 27)], ensure_ascii=False)


def stage_beats(title, brief, seconds, counter, out_dir):
    global LOG
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True); LOG = out_dir / 'model-log.txt'
    t0 = time.time()
    print(f'Writing the beat sheet with {MODEL}', flush=True)
    sheet = beat_sheet(title, brief, seconds, counter)
    beats = sheet.get('beats') or []
    if len(beats) < 6:
        raise RuntimeError(f'beat sheet too short ({len(beats)} beats)')
    sheet['_title'], sheet['_counter'] = title, counter
    (out_dir / 'beats.json').write_text(json.dumps(sheet, indent=1, ensure_ascii=False))
    print(f'{len(beats)} beats in {(time.time() - t0) / 60:.1f} min', flush=True)
    print('::notice title=Beat sheet::' + ' | '.join(f"{b.get('name')}: {b.get('what_happens')}" for b in beats)[:4000].replace('\n', ' '))
    return sheet


def stage_shots(out_dir, part, parts):
    global LOG
    out_dir = Path(out_dir); LOG = out_dir / f'model-log-{part}.txt'
    sheet = json.loads((out_dir / 'beats.json').read_text())
    beats = sheet['beats']; fid = friend_id(sheet); ex = example_shots()
    result = {}
    for i, beat in enumerate(beats):
        if i % parts != part:
            continue
        t0 = time.time()
        try:
            result[i] = shots_for_beat(beat, i, len(beats), sheet, fid, ex)
        except RuntimeError as exc:
            print(f'  beat {i + 1} skipped: {exc}', flush=True); result[i] = []
        print(f'  beat {i + 1}/{len(beats)}: {len(result[i])} shots in {(time.time() - t0) / 60:.1f} min', flush=True)
    (out_dir / f'shots-{part}.json').write_text(json.dumps(result, ensure_ascii=False))


def stage_merge(out_dir, out_path):
    out_dir = Path(out_dir)
    sheet = json.loads((out_dir / 'beats.json').read_text())
    per_beat = {}
    for f in sorted(out_dir.glob('shots-*.json')):
        per_beat.update({int(k): v for k, v in json.loads(f.read_text()).items()})
    shots = [s for i in sorted(per_beat) for s in per_beat[i]]
    missing = [i + 1 for i in range(len(sheet['beats'])) if not per_beat.get(i)]
    if missing:
        print(f'::warning title=Beats without shots::{missing}')
    if len(shots) < 8:
        raise RuntimeError(f'only {len(shots)} shots were written')
    return assemble(sheet, shots, out_path)


def assemble(sheet, shots, out_path):
    title, counter = sheet.get('_title', ''), sheet.get('_counter', '')
    fid = friend_id(sheet); friend = sheet.get('friend') or {}
    q = sheet.get('quote') or []
    r = sheet.get('red_card') or []
    if len(q) >= 2:
        shots.append({'dur': 4.4, 'music': 'high', 'card': {'style': 'quote', 'lines': q[:2]}})
    if r:
        shots.append({'dur': 3.0, 'music': 'high', 'card': {'style': 'red', 'lines': r[:2]}})
    shots.append({'dur': 4.2, 'music': 'mid', 'card': {'style': 'cta', 'lines': ['If this hit, like and subscribe.']},
                  'actors': [{'id': 'hero', 'x': 50, 'pose': 'wave', 'mood': 'happy', 'scale': .7}]})
    film = {
        'title': sheet.get('title') or title, 'logline': sheet.get('logline', ''),
        'hud': {'label': counter or sheet.get('hud_label') or ''} if (counter or sheet.get('hud_label')) else None,
        'music': {'prompt': sheet.get('music_prompt') or ''},
        'cast': {'hero': {'kind': 'hero'}, 'demon': {'kind': 'demon'},
                 fid: {'kind': 'friend', 'hat': friend.get('hat') or 'beanie_orange', 'skin': '#d9c6a6'},
                 'extra1': {'kind': 'extra', 'hat': 'beanie_green'}, 'extra2': {'kind': 'extra', 'hat': 'cap_grey'}},
        'shots': shots, 'beats': sheet.get('beats'),
    }
    film, notes = repair(film)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(film, indent=1, ensure_ascii=False))
    script_md(film, Path(out_path).with_name('story.md'))
    print(f'{film["title"]}: {len(film["shots"])} shots, {film["duration"]} s')
    for n in notes:
        print(' -', n)
    return film


def write(title, brief, seconds, counter, out_path):
    """Everything in one process (local use)."""
    d = Path(out_path).parent
    stage_beats(title, brief, seconds, counter, d)
    stage_shots(d, 0, 1)
    return stage_merge(d, out_path)


def script_md(film, path):
    lines = [f'# {film["title"]}', '', f'_{film.get("logline", "")}_', '']
    if film.get('hud'):
        lines += [f'Counter: **{film["hud"]["label"]}**', '']
    t = 0.0
    for i, s in enumerate(film['shots']):
        cam = s.get('camera', {}).get('frame', 'wide')
        who = ', '.join(f'{a["id"]} {a["pose"]}' + (f' ({a["mood"]})' if a.get('mood') else '') for a in s.get('actors', []))
        desc = f'**{i + 1:02d}** `{int(t // 60)}:{t % 60:04.1f}` {s.get("set")} · {cam} · {who}'
        if s.get('card'):
            desc = f'**{i + 1:02d}** `{int(t // 60)}:{t % 60:04.1f}` CARD ({s["card"]["style"]}): ' + ' / '.join(s['card']['lines'])
        lines.append(desc)
        for ln in s.get('lines', []):
            lines.append(f'  - {ln["who"]}: "{ln["text"]}"')
        ph = s.get('phone')
        if ph and cam == 'phone':
            for m in ph.get('messages', []):
                lines.append(f'  - 📱 {m["from"]}: {m["text"]}')
            if ph.get('typing'):
                lines.append(f'  - 📱 types "{ph["typing"]["text"]}" → {ph["typing"]["action"]}')
        t += s['dur']
    path.write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', choices=['all', 'beats', 'shots', 'merge'], default='all')
    ap.add_argument('--title', default=''); ap.add_argument('--brief', default='')
    ap.add_argument('--seconds', type=float, default=120); ap.add_argument('--counter', default='')
    ap.add_argument('--dir', default='build/writing'); ap.add_argument('--part', type=int, default=0); ap.add_argument('--parts', type=int, default=1)
    ap.add_argument('--out', default='build/film.json')
    a = ap.parse_args()
    if a.stage == 'all':
        write(a.title, a.brief, a.seconds, a.counter.strip(), a.out)
    elif a.stage == 'beats':
        stage_beats(a.title, a.brief, a.seconds, a.counter.strip(), a.dir)
    elif a.stage == 'shots':
        stage_shots(a.dir, a.part, a.parts)
    else:
        stage_merge(a.dir, a.out)
