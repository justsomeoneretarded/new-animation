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


def chat(system: str, user: str, temperature=.7, num_predict=3000) -> dict:
    body = json.dumps({'model': MODEL, 'stream': False, 'format': 'json',
                       'options': {'temperature': temperature, 'num_ctx': 16384, 'num_predict': num_predict},
                       'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(OLLAMA + '/api/chat', body, {'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=3600) as r:
                text = json.loads(r.read())['message']['content']
            return json.loads(text[text.index('{'):text.rindex('}') + 1])
        except Exception as exc:  # noqa: BLE001
            print(f'  model call failed ({type(exc).__name__}: {exc}); retry {attempt + 1}', flush=True)
            time.sleep(3)
    raise RuntimeError('the script model did not return usable JSON')


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
    return chat(system, user, .85, 2500)


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


def shots_for_beat(beat, i, n, state, sheet, example):
    system = FORMULA + '\n' + shot_schema() + f"""
You are the storyboard artist. Turn ONE beat into 2-4 shots. Reply with JSON only: {{"shots": [ ...shot objects... ]}}.
Cast ids: hero, demon, {state['friend_id']}{', and background extras with ids extra1, extra2 (kind extra)' if True else ''}.
Counter label: "{sheet.get('hud_label', '')}". The counter is currently {state['counter']} and the chapter is "{state['chapter']}".
Shot durations in this beat should add up to about {beat.get('seconds', 8)} seconds.
Example shots from another film in this format (follow the style and the JSON shape, not the story):
{example}"""
    user = f"Beat {i + 1} of {n}: {json.dumps(beat, ensure_ascii=False)}"
    out = chat(system, user, .55, 2600)
    return out.get('shots') or []


def write(title, brief, seconds, counter, out_path):
    t0 = time.time()
    print(f'Writing with {MODEL}: beat sheet', flush=True)
    sheet = beat_sheet(title, brief, seconds, counter)
    beats = sheet.get('beats') or []
    if len(beats) < 6:
        raise RuntimeError(f'beat sheet too short ({len(beats)} beats)')
    friend = sheet.get('friend') or {}
    fid = ''.join(ch for ch in str(friend.get('name') or 'sam').lower() if ch.isalpha())[:10] or 'sam'
    if fid in ('hero', 'demon'):
        fid = 'sam'
    example_film = json.loads((ROOT / 'examples' / 'the-sketchbook.json').read_text())
    example = json.dumps([example_film['shots'][k] for k in (2, 6, 11, 15, 17, 18, 26, 27)], ensure_ascii=False)
    state = {'counter': 0, 'chapter': '', 'friend_id': fid}
    shots = []
    for i, beat in enumerate(beats):
        print(f'  beat {i + 1}/{len(beats)}: {beat.get("name", "")}  ({(time.time() - t0) / 60:.1f} min)', flush=True)
        try:
            new = shots_for_beat(beat, i, len(beats), state, sheet, example)
        except RuntimeError as exc:
            print(f'  skipped beat: {exc}', flush=True); continue
        for s in new:
            s.setdefault('set', beat.get('where'))
            if beat.get('time'):
                s.setdefault('time', beat['time'])
            if beat.get('weather') and beat['weather'] != 'none':
                s.setdefault('weather', beat['weather'])
        shots.extend(new)
        if isinstance(beat.get('counter'), (int, float)):
            state['counter'] = beat['counter']
        if beat.get('chapter'):
            state['chapter'] = beat['chapter']
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
        'shots': shots, 'beats': beats,
    }
    film, notes = repair(film)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(film, indent=1, ensure_ascii=False))
    script_md(film, Path(out_path).with_name('story.md'))
    print(f'{film["title"]}: {len(film["shots"])} shots, {film["duration"]} s, written in {(time.time() - t0) / 60:.1f} min')
    for n in notes:
        print(' -', n)
    return film


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
    ap.add_argument('--title', required=True); ap.add_argument('--brief', required=True)
    ap.add_argument('--seconds', type=float, default=120); ap.add_argument('--counter', default='')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    write(a.title, a.brief, a.seconds, a.counter.strip(), a.out)
