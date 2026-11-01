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

FORMULA = """THE GENRE — minimalist animated shorts about one universal feeling (Day One Films style). These are TECHNIQUES,
not scenes to copy. Every film must be built from the brief's own world: the hero's job, hobby, family, city, habits, objects.
- Minimal characters: a plain cream blob hero; other people are distinguished by hair, clothes and colour.
- The inner world made visible. Usually an inner-voice figure: a dark silhouette with glowing eyes in a colour that fits the
  feeling. It speaks short, specific, cruel lowercase lines that come from THIS story (what this hero is afraid of). It is
  optional: some stories show the feeling another way (the room getting darker, colour draining, a shrinking frame).
- Show, don't tell. Most of the film is wordless acting: faces, posture, where people stand, what they hold, what they avoid.
- Specific physical details from the brief's world carry the meaning (a guitar left in its case, a paused game, a cold dinner,
  an unopened letter from a university, a running shoe with the tag still on). Invent details that belong to this hero only.
- Restraint with text: dialogue is rare, short and human, sometimes in speech bubbles; narration is optional (0-4 lines, plain
  words, a second line that turns the first); an on-screen device (a counter, day chapters) only if the story is about
  something measurable.
- Colour follows emotion: cold or grey when stuck, the inner voice's colour when tempted, warm when connection happens.
- Escalation, a turn, and an ending image that answers the opening image.

NEVER reuse these moments from the reference films unless the brief itself asks for them: a message left on "seen"; typing
a reply at 2am and deleting it; "h-hi."; a yellow umbrella or a bus stop meeting; a friend appearing at the door; a bench at
sunset as the ending; a calendar of ticked days; "just one more."; "nobody wants to hear from you."; "X vs Y." titles;
"Everyone falls. / Not everyone gets back up."; "LOCK IN."; a counter of words said, women seen or hours scrolled.
"""

SHAPES = """STORY SHAPES — choose the one that fits the brief best, or invent another; do not default to the first:
- spiral: the struggle repeats and gets worse, a low point, a choice, a different repeat at the end.
- two_paths: two versions of the same life or day shown side by side or alternating (what he does vs what he could do).
- countdown: something is coming (an exam, a flight, a goodbye, a deadline) and every scene is closer to it.
- twist: the viewer is led to misread something; the last scenes reveal what was really happening.
- loop: the same day repeats with one small change each time, until the change becomes the whole day.
- letter: narration is a letter or message to someone; the pictures show a different truth than the words.
- ripple: one small act passes from person to person and comes back to the hero.
- mirror: the first and last scenes are the same place and framing with one difference that holds the whole story.
- what_if: an impossible premise ("what if you could hear what people really think") played out with escalating consequences.
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
    'required': ['title', 'logline', 'shape', 'shape_why', 'inner_voice', 'demon_color', 'narrator', 'device', 'cast', 'music_prompt', 'opening', 'beats', 'ending_cards'],
    'properties': {
        'title': S, 'logline': S, 'shape': S, 'shape_why': S, 'inner_voice': {'type': 'boolean'}, 'demon_color': S, 'narrator': S, 'music_prompt': S,
        'opening': {'type': 'object', 'properties': {'type': S, 'text': S}},
        'ending_cards': {'type': 'array', 'items': {'type': 'object', 'properties': {'style': S, 'lines': {'type': 'array', 'items': S}}}},
        'device': {'type': 'object', 'required': ['type'], 'properties': {
            'type': S, 'items': {'type': 'array', 'items': {'type': 'object', 'properties': {'label': S, 'color': S}}}}},
        'cast': {'type': 'array', 'items': PERSON},
        'beats': {'type': 'array', 'items': {'type': 'object', 'required': ['name', 'seconds', 'where', 'what_happens', 'emotion'], 'properties': {
            'name': S, 'seconds': N, 'where': S, 'time': S, 'weather': S, 'grade': S, 'emotion': S, 'what_happens': S,
            'demon_line': S, 'dialogue': {'type': 'array', 'items': {'type': 'object', 'properties': {'who': S, 'text': S}}},
            'narration': S, 'narration_twist': S, 'phone': S, 'insert': S, 'big_text': S,
            'counter_values': {'type': 'array', 'items': N}, 'chapter': S, 'relapse': {'type': 'boolean'}}}}}}


def concept(title, brief):
    v = VOCAB
    system = FORMULA + '\n' + SHAPES + f"""
You are the writer and director. Read the brief closely and build an original film from it. Reply with JSON:
- title; logline; shape (one of the shapes above, or your own) and shape_why (one sentence: why this shape fits this brief);
- inner_voice: true/false; demon_color (hex, fits the feeling); narrator: male or female;
- device: {{"type": "counter" | "days" | "none", "items": [{{"label": "...", "color": "#..."}}]}} — items only for a counter,
  1-2 labels of 1-3 plain words that belong to THIS story;
- cast: the hero (id "hero", kind "hero"), the inner voice (id "demon", kind "demon") if used, and 1-3 other people with short
  lowercase ids (kind friend or extra) and distinct looks. Wardrobe: hair {v['wardrobe']['hair']}; hair_color {v['wardrobe']['hair_color']};
  top/pants/scarf: colour names ({v['wardrobe']['top']}); top_style {v['wardrobe']['top_style']}; hat {v['hats']}; hood true/false; glasses true/false;
- music_prompt: instrumental style for an AI composer (instruments, mood arc, bpm);
- opening: {{"type": "line" | "image", "text": "..."}} — "line" shows one sentence on black; "image" starts straight in a scene;
- beats: 10-15 beats, 4-12 seconds each, 90-150 seconds in total, following YOUR chosen shape. Each beat: where (one of the
  sets), time (night/dawn/day/dusk), weather (none/rain/snow), grade (one of {list(v['grades'])}), emotion (the hero's mood:
  one of {v['moods']}), what_happens (concrete visible action and acting, specific to this story), and only when the beat
  needs it: demon_line, dialogue [{{"who": id, "text": ...}}], narration + narration_twist, phone (what is on the screen),
  insert (note/calendar/photo/letter + exactly what it shows), big_text, counter_values, chapter, relapse (true/false);
- ending_cards: 0-2 closing cards that fit THIS film, each {{"style": "quote" | "logo" | "red" | "title", "lines": [...]}}
  (quote = two lines where the second turns the first; logo = the film's title with a short tagline; red = a short imperative).
Vary the sets: use the places this story would really happen, not the same bedroom-cafe-desk every time.
SETS: """ + '; '.join(f'{k} ({s["about"]})' for k, s in v['sets'].items())
    return chat(system, f'Title: {title}\nBrief: {brief}', .9, 5000, CONCEPT_SCHEMA)


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
JSON shape examples (placeholders in <> are filled from THIS story; invent the content, never copy it):
{example}"""
    user = f"Beat {i + 1} of {n}:\n{json.dumps(beat, ensure_ascii=False)}"
    shots = chat(system, user, .6, 3200).get('shots') or []

    def scrub(o):
        # drop any placeholder the model copied literally from the shape examples
        if isinstance(o, dict):
            return {k: scrub(v) for k, v in o.items() if not (isinstance(v, str) and re.fullmatch(r'\s*<[^>]*>\s*', v))}
        if isinstance(o, list):
            return [scrub(x) for x in o]
        return o
    shots = [scrub(x) for x in shots if isinstance(x, dict)]
    for s in shots:
        for a_ in s.get('actors') or []:
            a_.setdefault('mood', beat.get('emotion')) if a_.get('id') == 'hero' else None
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
    """JSON shape only. Placeholders in <angle brackets> stand for content from THIS story; nothing here is a scene to reuse."""
    return json.dumps([
        {"dur": 3.4, "set": "<set>", "time": "<time>", "grade": "<grade>", "camera": {"frame": "wide", "push": 0.05},
         "actors": [{"id": "hero", "x": 48, "pose": "<pose>", "mood": "<mood>", "hold": "<item or none>"}],
         "items": [{"type": "<item>", "x": 30}]},
        {"dur": 3.0, "set": "<set>", "grade": "<grade>", "camera": {"frame": "close", "on": "hero"},
         "actors": [{"id": "hero", "x": 50, "pose": "<pose>", "mood": "<mood>"}, {"id": "demon", "x": 38, "pose": "lean", "target": "hero"}],
         "lines": [{"who": "demon", "text": "<short cruel line from this story>", "at": 0.8}]},
        {"dur": 4.2, "set": "<set>", "camera": {"frame": "two", "on": "hero"},
         "actors": [{"id": "<friend id>", "x": 20, "pose": "sit", "mood": "<mood>", "facing": 1}, {"id": "hero", "x": 31, "pose": "sit", "mood": "<mood>", "facing": -1}],
         "lines": [{"who": "<friend id>", "text": "<short line>", "at": 0.4, "dur": 1.8}, {"who": "hero", "text": "<reply>", "at": 2.4}]},
        {"dur": 5.0, "set": "<set>", "grade": "<grade>", "camera": {"frame": "medium"},
         "actors": [{"id": "hero", "x": 50, "pose": "<pose>", "mood": "<mood>"}],
         "lines": [{"who": "narrator", "text": "<plain sentence>", "twist": "<second sentence that turns it>", "at": 0.3}]},
        {"dur": 4.5, "set": "<set>", "camera": {"frame": "phone"}, "phone": {"app": "chat", "contact": "<name>", "messages": [{"from": "them", "text": "<message>", "at": 0.3}], "typing": {"text": "<reply>", "at": 1.5, "action": "send"}}},
        {"dur": 4.0, "camera": {"frame": "insert"}, "insert": {"type": "note", "text": "<exact words written>"}},
        {"dur": 2.4, "set": "<set>", "camera": {"frame": "extreme", "on": "hero", "push": 0.1}, "actors": [{"id": "hero", "x": 50, "pose": "<pose>", "mood": "<mood>"}]},
        {"dur": 4.0, "set": "<set>", "camera": {"frame": "wide"}, "big": {"text": "<CHAPTER WORD.>", "at": 0.3},
         "actors": [{"id": "hero", "x": 15, "to": 70, "pose": "walk", "mood": "<mood>"}]}
    ], ensure_ascii=False)


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
    summary = f"shape: {sheet.get('shape')} ({sheet.get('shape_why', '')}) | {sheet.get('logline', '')} | device: {json.dumps(sheet.get('device'))} | " + ' | '.join(f"{b.get('name')}: {b.get('what_happens')}" for b in beats)
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
    op = sheet.get('opening') or {}
    head = []
    if op.get('type') == 'line' and str(op.get('text') or '').strip():
        line = str(op['text']).strip()
        head.append({'dur': 3.6, 'music': 'low', 'card': {'style': 'line', 'lines': [line]},
                     'lines': [{'who': 'narrator', 'text': line, 'at': .2, 'hidden': True}]})
    tail = []
    for card in (sheet.get('ending_cards') or [])[:2]:
        lines = [str(x) for x in (card.get('lines') or []) if str(x).strip()]
        if lines and card.get('style') in ('quote', 'logo', 'red', 'title'):
            tail.append({'dur': 4.6 if card['style'] != 'red' else 3.2, 'music': 'high', 'card': {'style': card['style'], 'lines': lines[:3]}})
    tail.append({'dur': 4.2, 'music': 'mid', 'card': {'style': 'cta', 'lines': ['If this hit, like and subscribe.']},
                 'actors': [{'id': 'hero', 'x': 50, 'pose': 'wave', 'mood': 'happy', 'scale': .7}]})
    if sheet.get('inner_voice') is False:
        for s_ in shots:
            s_['actors'] = [a_ for a_ in s_.get('actors') or [] if a_.get('id') != 'demon']
            s_['lines'] = [l_ for l_ in s_.get('lines') or [] if l_.get('who') != 'demon']
    film = {
        'title': title, 'logline': sheet.get('logline', ''), 'shape': sheet.get('shape'), 'demon_color': sheet.get('demon_color'), 'narrator': sheet.get('narrator'),
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
