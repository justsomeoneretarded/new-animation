"""Write a Day One-style animated short from a title and a brief, with a local model (Ollama, no paid API).

python story/write.py --title "Lust vs Love" --brief "..." --out build/film.json

Stages (run in parallel on Actions):
  beats  — the concept: cast and wardrobe, the story device (a counter, day chapters or none), the demon's colour,
           narration, and 12-16 beats following the format's structure
  shots  — each beat becomes 2-4 shots in the engine's vocabulary (split across runners with --part/--parts)
  merge  — shots are joined, the ending cards added, and everything repaired by story/validate.py
A readable script (story.md) is written next to the film for review.
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

FORMULA = """THE FORMAT — a study of Day One Films shorts ("Loneliness", "Your Winter Arc Starts Now", "Lust vs Love"):
- A 1.5 to 3 minute animated short. A plain cream blob character (the hero) fights one relatable everyday struggle.
- THE DEMON: a black silhouette with glowing eyes is the hero's inner voice. Its glow colour fits the theme
  (red for fear or shame, pink for lust, green for envy, purple for anxiety, orange for anger). It appears beside the hero
  at weak moments and says SHORT, cruel, lowercase lines (2-6 words): "nobody wants to hear from you.", "stay quiet.",
  "just one more.", "she's nothing special.", "you'll quit." The demon shrinks, fades or is ignored by the end.
- A STORY DEVICE the viewer can track, chosen to fit the story — not always the same one:
  * a counter (one or two numbers) that measures the struggle, e.g. "WORDS SAID TODAY: 0", or two that contrast,
    e.g. "SEEN 1,003 / KNOWN 0", which moves through the film and turns red during relapses;
  * day chapters ("DAY 1", "DAY 4", "DAY 30") for a transformation over time, often with a calendar being marked;
  * or no device at all when the story doesn't need one.
- NARRATION: 3-5 times in the film, a calm narrator voice speaks a short line shown at the bottom. The best ones have a
  second line that twists the first: "The phone gave him a new face every second." / "She only had one."
  Narration is sparse; most of the film is wordless acting.
- DIALOGUE in white speech bubbles: rare, lowercase, short, human: "h-hi.", "...cool.", "coffee? saturday?",
  "finished it. your turn.", "you came!". Thoughts can appear in brackets.
- SPECIFIC, PHYSICAL details instead of abstract metaphors: a clock at 3:17am, a typed message that gets deleted,
  a message left on seen, an unknown caller, a cupcake with one candle, a fridge light at 2am, a note written in a notebook,
  a phone switched off, a charger, a calendar with days crossed off, a yellow umbrella shared in the rain.
- INSERT SHOTS: close-ups of objects that carry meaning (a handwritten note, a calendar, a photo, a phone being turned off).
- BIG WORDS in the scene mark a new chapter: "DAY 1.", "SATURDAY."
- COLOUR tells the emotion: grey or cold blue while the hero is stuck, the demon's colour during temptation,
  warm amber when connection happens, an orange sunset for the ending.
- Characters are distinct: the hero is cream with a hood or plain; others have hair, coats, scarves, hats, colours.
- STRUCTURE: (1) cold open — one line on black or one image that states the problem; (2) the demon wins small moments;
  (3) a trigger or invitation (a message, a person, an alarm); (4) a first awkward attempt; (5) a small win;
  (6) a RELAPSE where the demon wins again (counter red, colour drains); (7) the refusal — an extreme close-up of
  determined eyes, a phone switched off, a note written; (8) progress over days; (9) the demon smaller or ignored;
  (10) a quiet payoff with another person, often at sunset; (11) the opening line returns with a new ending;
  (12) a two-line quote card that twists ("Lust shows you everyone." / "Love shows you someone.");
  (13) a title card in the "X vs Y." style with a short tagline ("Look up." / "Or one more scroll."); (14) like and subscribe.
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


S = {'type': 'string'}
N = {'type': 'number'}
PERSON = {'type': 'object', 'required': ['id', 'kind'], 'properties': {
    'id': S, 'kind': S, 'hair': S, 'hair_color': S, 'top': S, 'top_style': S, 'pants': S, 'scarf': S, 'hat': S,
    'hood': {'type': 'boolean'}, 'glasses': {'type': 'boolean'}, 'skin': S}}
CONCEPT_SCHEMA = {
    'type': 'object',
    'required': ['title', 'logline', 'demon_color', 'narrator', 'device', 'cast', 'music_prompt', 'opening_line', 'beats', 'quote', 'logo'],
    'properties': {
        'title': S, 'logline': S, 'demon_color': S, 'narrator': S, 'music_prompt': S, 'opening_line': S,
        'device': {'type': 'object', 'required': ['type'], 'properties': {
            'type': S, 'items': {'type': 'array', 'items': {'type': 'object', 'properties': {'label': S, 'color': S}}}}},
        'cast': {'type': 'array', 'items': PERSON},
        'quote': {'type': 'array', 'items': S}, 'logo': {'type': 'array', 'items': S}, 'red_card': {'type': 'array', 'items': S},
        'beats': {'type': 'array', 'items': {'type': 'object', 'required': ['name', 'seconds', 'where', 'what_happens', 'emotion'], 'properties': {
            'name': S, 'seconds': N, 'where': S, 'time': S, 'weather': S, 'grade': S, 'emotion': S, 'what_happens': S,
            'demon_line': S, 'dialogue': {'type': 'array', 'items': {'type': 'object', 'properties': {'who': S, 'text': S}}},
            'narration': S, 'narration_twist': S, 'phone': S, 'insert': S, 'big_text': S,
            'counter_values': {'type': 'array', 'items': N}, 'chapter': S, 'relapse': {'type': 'boolean'}}}}}}


def concept(title, brief):
    v = VOCAB
    system = FORMULA + f"""
You are the writer and director. From the title and brief, write the concept and the beat sheet as JSON:
- title; logline; demon_color (hex, fits the theme); narrator: male or female;
- device: {{"type": "counter" | "days" | "none", "items": [{{"label": "Seen", "color": "#ff4fa0"}}, ...]}} (items only for counter, 1-2 short labels of 1-3 plain words, e.g. "Words said today");
- cast: the hero (id "hero", kind "hero"), the demon (id "demon", kind "demon") and 1-3 other people with short lowercase ids
  (kind friend or extra) and distinct looks. Wardrobe options: hair {v['wardrobe']['hair']}; hair_color {v['wardrobe']['hair_color']};
  top/pants/scarf: colour names ({v['wardrobe']['top']}); top_style {v['wardrobe']['top_style']}; hat {v['hats']}; hood true/false; glasses true/false.
  The hero usually stays cream with a hood (hood true, no top).
- music_prompt: instrumental style for an AI composer (instruments, mood arc, bpm);
- opening_line: the cold-open line shown on black ("He had seen a thousand women.");
- beats: 12-15 beats, 4-12 seconds each, about 100-150 seconds in total. Each beat: where (one of the sets), time (night/dawn/day/dusk),
  weather (none/rain/snow), grade (one of {list(v['grades'])}), emotion (the hero's mood: one of {v['moods']}),
  what_happens (concrete visible action and acting), and when useful: demon_line, dialogue [{{"who": id, "text": ...}}],
  narration + narration_twist (ONLY 3-4 beats in the whole film have narration; plain, honest words, not poetic metaphors —
  "The phone gave him a new face every second." / "She only had one." — never "The screen is a window."), phone (what is on screen), insert (note/calendar/photo + what it shows),
  big_text ("DAY 1."), counter_values (numbers for the device items), chapter ("DAY 4"), relapse (true/false);
- quote: two lines, the second twists the first; logo: ["X vs Y.", "short tagline", "second tagline"]; red_card: optional ["LOOK UP.", "Right now."].
SETS: """ + '; '.join(f'{k} ({s["about"]})' for k, s in v['sets'].items())
    return chat(system, f'Title: {title}\nBrief: {brief}', .85, 5000, CONCEPT_SCHEMA)


def shot_schema():
    v = VOCAB
    return f"""SHOT JSON (one object per shot):
{{"dur": seconds 1.8-6,
 "set": one of {list(v['sets'])}, "time": one of {v['times']}, "weather": one of {v['weather']}, "grade": one of {list(v['grades'])},
 "clock": "03:17" (bedroom clock), "camera": {{"frame": one of {list(v['frames'])}, "on": actor id, "push": 0.03-0.12}},
 "actors": [{{"id": cast id, "x": 0-100, "to": 0-100 (walk/run/umbrella target), "pose": one of {list(v['poses'])},
             "mood": one of {v['moods']}, "hold": one of {v['holds']}, "facing": -1|0|1, "seated": true,
             "target": id (lean/grab/hug/reachout), "at": seconds delay, "depth": "back", "scale": 0.4-1.2, "opacity": 0.3-1}}],
 "lines": [{{"who": actor id | "narrator" | "caption", "text": str, "twist": str (narrator only), "at": seconds, "style": "bubble"|"float"|"thought"|"whisper"}}],
 "hud": {{"values": [numbers or [from, to]], "chapter": "DAY 4", "alert": true}},
 "big": {{"text": "DAY 1.", "at": 0.3}},
 "phone": {{"app": one of {list(v['phone_apps'])}, "contact": name, "time": "18:02", "messages": [{{"from": "them"|"me", "text": str, "at": s}}],
           "typing": {{"text": str, "at": s, "action": "delete"|"send"}}, "notifications": [{{"app": str, "text": str, "at": s}}],
           "call": {{"decline_at": s}}, "off_at": s, "label": alarm label}},
 "insert": {json.dumps(v['inserts'])},
 "items": [{{"type": one of {v['items']}, "x": 0-100, "on": "nightstand"|"desk"|"table"|"bed"}}],
 "door": [0, 1], "door_at": s, "music": one of {v['music_levels']}, "transition": one of {v['transitions']}}}
SPOTS per set: {json.dumps({k: s['spots'] for k, s in v['sets'].items()})}
SEATS: {json.dumps({k: s.get('seat') for k, s in v['sets'].items() if s.get('seat')})}
RULES:
- frame "phone" shows only the phone (no actors) and must show something specific; frame "insert" needs "insert" and no actors.
- Vary framing like an editor: never more than two "wide" shots in a row; "close" for reactions (the face is detailed there),
  "extreme" for the decision, "two" when two characters share a moment, "medium" for actions, "phone"/"insert" for objects.
- The demon stands right next to the hero (x within 10-14) when it speaks, pose lean or grab with target "hero".
- Two people at a table or bench sit facing each other: facing 1 for the one on the left, -1 for the one on the right.
- Put each person's mood on every actor. Use the beat's grade on every shot of the beat.
- Narration lines use who "narrator" with a "twist" second line; leave the shot long enough to hear it. Only add narration if the beat has it.
- The demon is in at most half the shots, its lines never repeat, and it never encourages the right choice.
- An "insert" note must contain the exact words written. No stage directions like "[sigh]" in lines; show them with mood and pose.
- A phone shot shows a message once: either as a sent bubble or as typing, not both."""


def shots_for_beat(beat, i, n, sheet, example):
    # The system prompt is identical for every beat so Ollama can reuse its prompt cache.
    ids = ', '.join(p.get('id') for p in sheet.get('cast', []) if p.get('id'))
    dev = sheet.get('device') or {}
    system = FORMULA + '\n' + shot_schema() + f"""
You are the storyboard artist. Turn ONE beat into 2-4 shots. Reply with JSON only: {{"shots": [ ...shot objects... ]}}.
Cast ids: {ids}. Story device: {json.dumps(dev)} — put the beat's counter values in hud.values (same order as the items) and its chapter in hud.chapter.
Shot durations in a beat add up to about the beat's seconds.
Example shots from another film in this format (follow the style and JSON shape, not the story):
{example}"""
    user = f"Beat {i + 1} of {n}:\n{json.dumps(beat, ensure_ascii=False)}"
    shots = chat(system, user, .55, 3200).get('shots') or []
    for s in shots:
        if not s.get('card') and (s.get('camera') or {}).get('frame') not in ('insert',):
            s.setdefault('set', beat.get('where'))
        for key in ('time', 'grade'):
            if beat.get(key):
                s.setdefault(key, beat[key])
        if beat.get('weather') and beat['weather'] != 'none':
            s.setdefault('weather', beat['weather'])
        if beat.get('relapse') and isinstance(s.get('hud'), dict):
            s['hud'].setdefault('alert', True)
    return shots


def example_shots():
    film = json.loads((ROOT / 'examples' / 'envy-vs-enough.json').read_text())
    return json.dumps([film['shots'][k] for k in (1, 3, 5, 9, 11, 13, 16, 18)], ensure_ascii=False)


def stage_beats(title, brief, out_dir):
    global LOG
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True); LOG = out_dir / 'model-log.txt'
    t0 = time.time()
    print(f'Writing the concept with {MODEL}', flush=True)
    sheet = concept(title, brief)
    beats = sheet.get('beats') or []
    if len(beats) < 6:
        raise RuntimeError(f'beat sheet too short ({len(beats)} beats)')
    sheet['_title'] = title
    # normalise ids so every later stage and the validator agree on them
    idmap = {}
    for p in sheet.get('cast') or []:
        raw = str(p.get('id', '')); clean = re.sub(r'[^a-z0-9_]', '', raw.lower())[:12] or 'friend'
        idmap[raw] = clean; p['id'] = clean
    for b in beats:
        for d in b.get('dialogue') or []:
            d['who'] = idmap.get(str(d.get('who')), re.sub(r'[^a-z0-9_]', '', str(d.get('who', '')).lower())[:12])
    (out_dir / 'beats.json').write_text(json.dumps(sheet, indent=1, ensure_ascii=False))
    with open(LOG, 'a') as f:
        f.write('--- concept\n' + json.dumps(sheet, indent=1, ensure_ascii=False) + '\n')
    print(f'{len(beats)} beats in {(time.time() - t0) / 60:.1f} min', flush=True)
    summary = f"{sheet.get('logline', '')} | device: {json.dumps(sheet.get('device'))} | " + ' | '.join(f"{b.get('name')}: {b.get('what_happens')}" for b in beats)
    print('::notice title=Concept::' + summary[:6000].replace('\n', ' ').replace('%', '%25'))
    return sheet


def stage_shots(out_dir, part, parts):
    global LOG
    out_dir = Path(out_dir); LOG = out_dir / f'model-log-{part}.txt'
    sheet = json.loads((out_dir / 'beats.json').read_text())
    beats = sheet['beats']; ex = example_shots()
    result = {}
    for i, beat in enumerate(beats):
        if i % parts != part:
            continue
        t0 = time.time()
        try:
            result[i] = shots_for_beat(beat, i, len(beats), sheet, ex)
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
    title = sheet.get('title') or sheet.get('_title') or 'Untitled'
    cast = {'hero': {'kind': 'hero', 'hood': True}, 'demon': {'kind': 'demon'}}
    for p in sheet.get('cast') or []:
        pid = re.sub(r'[^a-z0-9_]', '', str(p.get('id', '')).lower())[:12]
        if not pid:
            continue
        entry = {k: v for k, v in p.items() if k not in ('id',) and v not in (None, '', 'none')}
        if pid == 'hero':
            entry['kind'] = 'hero'
        if pid == 'demon':
            entry = {'kind': 'demon'}
        cast[pid] = {**cast.get(pid, {}), **entry}
        if p.get('hat') == 'none':
            cast[pid].pop('hat', None)
    dev = sheet.get('device') or {}
    hud = {'items': dev.get('items')[:2]} if dev.get('type') == 'counter' and dev.get('items') else None
    opening = (sheet.get('opening_line') or '').strip()
    head = []
    if opening:
        head.append({'dur': 3.6, 'music': 'low', 'card': {'style': 'line', 'lines': [opening]},
                     'lines': [{'who': 'narrator', 'text': opening, 'at': .2, 'hidden': True}]})
    tail = []
    q = sheet.get('quote') or []
    if len(q) >= 2:
        tail.append({'dur': 4.6, 'music': 'high', 'card': {'style': 'quote', 'lines': q[:2]}})
    logo = sheet.get('logo') or []
    if logo:
        tail.append({'dur': 4.6, 'music': 'high', 'card': {'style': 'logo', 'lines': logo[:3]}})
    r = sheet.get('red_card') or []
    if r and not logo:
        tail.append({'dur': 3.0, 'music': 'high', 'card': {'style': 'red', 'lines': r[:2]}})
    tail.append({'dur': 4.2, 'music': 'mid', 'card': {'style': 'cta', 'lines': ['If this hit, like and subscribe.']},
                 'actors': [{'id': 'hero', 'x': 50, 'pose': 'wave', 'mood': 'happy', 'scale': .7}]})
    film = {
        'title': title, 'logline': sheet.get('logline', ''), 'demon_color': sheet.get('demon_color'), 'narrator': sheet.get('narrator'),
        'hud': hud, 'music': {'prompt': sheet.get('music_prompt') or ''}, 'cast': cast,
        'shots': head + shots + tail, 'beats': sheet.get('beats'),
    }
    film, notes = repair(film)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(film, indent=1, ensure_ascii=False))
    script_md(film, Path(out_path).with_name('story.md'))
    print(f'{film["title"]}: {len(film["shots"])} shots, {film["duration"]} s')
    for n in notes:
        print(' -', n)
    return film


def write(title, brief, out_path):
    """Everything in one process (local use)."""
    d = Path(out_path).parent
    stage_beats(title, brief, d)
    stage_shots(d, 0, 1)
    return stage_merge(d, out_path)


def script_md(film, path):
    lines = [f'# {film["title"]}', '', f'_{film.get("logline", "")}_', '']
    if film.get('hud'):
        lines += ['Counter: **' + ' / '.join(i['label'] for i in film['hud']['items']) + '**', '']
    t = 0.0
    for i, s in enumerate(film['shots']):
        cam = s.get('camera', {}).get('frame', 'wide')
        who = ', '.join(f'{a["id"]} {a["pose"]}' + (f' ({a["mood"]})' if a.get('mood') else '') for a in s.get('actors', []))
        stamp = f'**{i + 1:02d}** `{int(t // 60)}:{t % 60:04.1f}`'
        if s.get('card'):
            desc = f'{stamp} CARD ({s["card"]["style"]}): ' + ' / '.join(s['card']['lines'])
        elif cam == 'insert':
            desc = f'{stamp} INSERT {s["insert"]["type"]}: {s["insert"].get("text", "")}'
        else:
            desc = f'{stamp} {s.get("set")} · {cam}' + (f' · {s["grade"]}' if s.get('grade') else '') + f' · {who}'
        if s.get('big'):
            desc += f'  [{s["big"]["text"]}]'
        lines.append(desc)
        for ln in s.get('lines', []):
            lines.append(f'  - {ln["who"]}: "{ln["text"]}"' + (f' / "{ln["twist"]}"' if ln.get('twist') else ''))
        ph = s.get('phone')
        if ph and cam == 'phone':
            for m in ph.get('messages', []):
                lines.append(f'  - 📱 {m["from"]}: {m["text"]}')
            if ph.get('typing'):
                lines.append(f'  - 📱 types "{ph["typing"]["text"]}" → {ph["typing"]["action"]}')
            for nn in ph.get('notifications', []):
                lines.append(f'  - 📱 {nn.get("app", "")}: {nn.get("text", "")}')
        t += s['dur']
    path.write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', choices=['all', 'beats', 'shots', 'merge'], default='all')
    ap.add_argument('--title', default=''); ap.add_argument('--brief', default='')
    ap.add_argument('--dir', default='build/writing'); ap.add_argument('--part', type=int, default=0); ap.add_argument('--parts', type=int, default=1)
    ap.add_argument('--out', default='build/film.json')
    a = ap.parse_args()
    if a.stage == 'all':
        write(a.title, a.brief, a.out)
    elif a.stage == 'beats':
        stage_beats(a.title, a.brief, a.dir)
    elif a.stage == 'shots':
        stage_shots(a.dir, a.part, a.parts)
    else:
        stage_merge(a.dir, a.out)
