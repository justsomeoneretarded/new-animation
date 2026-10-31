"""Check and repair a film (shot list) against engine/vocab.json so it always renders.

python story/validate.py film.json            -> prints problems, writes the repaired film back
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOCAB = json.loads((ROOT / 'engine' / 'vocab.json').read_text())
CARD_STYLES = {'title', 'quote', 'red', 'cta'}


def _num(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def repair(film: dict) -> tuple[dict, list[str]]:
    notes: list[str] = []
    film = dict(film)
    film.setdefault('title', 'Untitled')
    cast = {'hero': {'kind': 'hero'}, 'demon': {'kind': 'demon'}}
    for cid, c in (film.get('cast') or {}).items():
        c = dict(c or {})
        if c.get('kind') not in VOCAB['kinds']:
            c['kind'] = 'friend' if cid not in ('hero', 'demon') else cid
        if c.get('hat') and c['hat'] not in VOCAB['hats']:
            c['hat'] = 'beanie_orange'
        cast[str(cid)] = c
    film['cast'] = cast
    hud = film.get('hud')
    if isinstance(hud, str):
        film['hud'] = {'label': hud}
    elif not (isinstance(hud, dict) and hud.get('label')):
        film['hud'] = None
    shots = []
    for i, raw in enumerate(film.get('shots') or []):
        if not isinstance(raw, dict):
            continue
        s = dict(raw)
        s['dur'] = round(_num(s.get('dur'), 1.5, 9, 3.2), 2)
        if s.get('set') not in VOCAB['sets']:
            if s.get('set') and not s.get('card'):
                notes.append(f'shot {i}: unknown set {s.get("set")!r} -> void')
            s['set'] = 'void' if not s.get('card') else s.get('set', 'void')
            if s['set'] not in VOCAB['sets']:
                s['set'] = 'void'
        if s.get('time') not in VOCAB['times']:
            s.pop('time', None)
        if s.get('weather') not in VOCAB['weather']:
            s.pop('weather', None)
        cam = dict(s.get('camera') or {})
        if cam.get('frame') not in VOCAB['frames']:
            cam['frame'] = 'wide'
        if cam['frame'] == 'phone' and not isinstance(s.get('phone'), dict):
            cam['frame'] = 'close'
        if isinstance(s.get('phone'), dict) and cam['frame'] != 'phone' and not s.get('actors'):
            cam['frame'] = 'phone'
        s['camera'] = cam
        if cam['frame'] == 'phone':
            ph = s['phone']
            if ph.get('app') not in VOCAB['phone_apps']:
                ph['app'] = 'chat'
            for m in ph.get('messages') or []:
                m['from'] = 'me' if m.get('from') == 'me' else 'them'
                m['text'] = str(m.get('text', ''))[:60]
                m['at'] = _num(m.get('at'), 0, s['dur'], 0)
            ty = ph.get('typing')
            if isinstance(ty, dict):
                ty['text'] = str(ty.get('text', ''))[:48]
                if ty.get('action') not in ('delete', 'send', 'hold'):
                    ty['action'] = 'hold'
                need = _num(ty.get('at'), 0, 9, .4) + len(ty['text']) / 11 + (1.6 if ty['action'] == 'delete' else .9)
                if need > s['dur']:
                    s['dur'] = round(min(9, need), 2)
            elif ty is not None:
                ph.pop('typing')
            empty = {'chat': not ph.get('messages') and not ph.get('typing'), 'lock': not ph.get('notifications'),
                     'call': False, 'feed': False, 'alarm': False}.get(ph['app'], False)
            if empty:
                # a blank screen tells the viewer nothing: show a waiting notification instead
                ph['app'] = 'lock'
                ph['notifications'] = [{'app': 'Messages', 'text': f"{ph.get('contact') or 'new message'}", 'at': .4}]
                notes.append(f'shot {i}: empty phone screen -> lock screen notification')
        if isinstance(s.get('card'), dict):
            cd = s['card']
            if cd.get('style') not in CARD_STYLES:
                cd['style'] = 'title'
            cd['lines'] = [str(x)[:48] for x in (cd.get('lines') or [])][:3] or [film['title']]
        elif s.get('card') is not None:
            s.pop('card')
        actors = []
        for a in s.get('actors') or []:
            if not isinstance(a, dict):
                continue
            a = dict(a)
            aid = str(a.get('id', 'hero'))
            if aid not in cast:
                cast[aid] = {'kind': 'extra' if a.get('kind') == 'extra' else 'friend', 'hat': 'beanie_green'}
                notes.append(f'shot {i}: added unknown actor {aid!r} to the cast')
            a['id'] = aid
            if a.get('pose') not in VOCAB['poses']:
                if a.get('pose'):
                    notes.append(f'shot {i}: pose {a.get("pose")!r} -> stand')
                a['pose'] = 'stand'
            if a['pose'] in ('lean', 'grab') and cast.get(aid, {}).get('kind') != 'demon' and not a.get('target'):
                a['pose'] = 'stand'
            if a.get('mood') not in VOCAB['moods']:
                a.pop('mood', None)
            if a.get('hold') not in VOCAB['holds']:
                a.pop('hold', None)
            a['x'] = _num(a.get('x'), 2, 98, 50)
            if 'to' in a:
                a['to'] = _num(a.get('to'), -10, 110, a['x'])
            if a.get('facing') not in (-1, 0, 1):
                a.pop('facing', None)
            for key, lo, hi in (('scale', .3, 1.6), ('opacity', .1, 1), ('at', 0, s['dur'])):
                if key in a:
                    a[key] = _num(a[key], lo, hi, None)
                    if a[key] is None:
                        a.pop(key)
            actors.append(a)
        s['actors'] = actors[:5]
        lines = []
        ids = {a['id'] for a in actors}
        for ln in s.get('lines') or []:
            if not isinstance(ln, dict) or not str(ln.get('text', '')).strip():
                continue
            who = str(ln.get('who', 'caption'))
            if who not in ids and who not in ('caption', 'narrator'):
                who = 'demon' if who == 'demon' else 'caption'
            ln = {'who': who, 'text': str(ln['text']).strip()[:60], 'at': _num(ln.get('at'), 0, s['dur'] - .5, .4)}
            lines.append(ln)
        s['lines'] = lines[:3]
        if s.get('music') not in VOCAB['music_levels']:
            s.pop('music', None)
        if s.get('transition') not in VOCAB['transitions']:
            s.pop('transition', None)
        s['sfx'] = [x for x in (s.get('sfx') or []) if isinstance(x, dict) and x.get('name') in VOCAB['sfx']]
        s['items'] = [x for x in (s.get('items') or []) if isinstance(x, dict) and x.get('type') in VOCAB['items']]
        h = s.get('hud')
        if film['hud'] and isinstance(h, dict):
            v = h.get('value')
            if isinstance(v, list) and len(v) == 2 and all(isinstance(q, (int, float)) for q in v):
                pass
            elif not isinstance(v, (int, float)):
                h.pop('value', None)
        elif not isinstance(h, dict):
            s.pop('hud', None)
        if not s['actors'] and not s.get('card') and cam['frame'] != 'phone':
            notes.append(f'shot {i}: nothing to show, dropped')
            continue
        shots.append(s)
    if not shots:
        raise ValueError('the film has no usable shots')
    # carry the HUD forward so the counter never blinks off between shots
    last = None
    for s in shots:
        if film['hud'] and 'hud' not in s and last is not None and not s.get('card'):
            v = last.get('value'); s['hud'] = {'value': v[-1] if isinstance(v, list) else v, 'chapter': last.get('chapter')}
        if s.get('hud'):
            last = s['hud']
    if not any((s.get('card') or {}).get('style') == 'cta' for s in shots):
        shots.append({'dur': 4.2, 'set': 'void', 'music': 'mid', 'card': {'style': 'cta', 'lines': ['If this hit, like and subscribe.']},
                      'actors': [{'id': 'hero', 'x': 50, 'pose': 'wave', 'mood': 'happy', 'scale': .7}], 'lines': []})
        notes.append('added the closing like/subscribe card')
    shots[0].setdefault('transition', 'fade')
    film['shots'] = shots
    if not any(l['who'] == 'demon' for s in shots for l in s['lines']):
        notes.append('warning: the demon never speaks; the format relies on its red lines')
    film['duration'] = round(sum(s['dur'] for s in shots), 2)
    return film, notes


if __name__ == '__main__':
    p = Path(sys.argv[1])
    film, notes = repair(json.loads(p.read_text()))
    p.write_text(json.dumps(film, indent=1, ensure_ascii=False))
    print(f'{film["title"]}: {len(film["shots"])} shots, {film["duration"]} s')
    for n in notes:
        print(' -', n)
