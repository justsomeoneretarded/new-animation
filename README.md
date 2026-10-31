# new-animation

Day One-style animated shorts from a written brief: a cream blob hero, a black shadow with red eyes that says the cruel thing out loud, an on-screen counter the viewer can track, phone screens, a relapse, a payoff, a quote card and a red call to action.

Everything runs free on GitHub Actions: a local script model (Gemma through Ollama), a browser-canvas animation engine rendered by headless Chromium, ACE-Step for an original score, and synthesized sound effects.

## Make a film

**Actions → Make film → Run workflow**

| Input | What it does |
|---|---|
| Title | The video title. |
| Brief | The struggle, who the hero is, what the demon says, how it ends. Leave empty to render the example film. |
| Target length | 90–180 seconds. |
| Counter | Optional label such as `Words said today` or `Days clean`. The writer picks one if empty. |
| Film file | Render a shot list that is already in the repo instead of writing one, e.g. `examples/the-sketchbook.json`. |
| Script model | `gemma4:12b` writes better; `gemma4:e4b` is faster. |
| Score | Compose an original score with ACE-Step. Without it, a synthesized piano bed is used. |

Download the **film** artifact. It contains the MP4, `story.md` (the script, shot by shot), `film.json` (the shot list), `contact-sheet.jpg`, `thumbnail-frame.jpg` and the soundtrack WAV.

A brief that works well is specific and physical:

> A guy who hasn't talked to anyone in weeks. The demon tells him nobody wants to hear from him. A coworker invites him to a run club. He goes once, relapses, then keeps showing up. Counter: words said today.

## Editing a film by hand

The run summary shows the script. To change something, copy `film.json` from the artifact into the repo (for example `films/my-film.json`), edit it, and run the workflow with **Film file** set to that path. Writing is skipped, so the render only takes minutes.

A shot looks like this:

```json
{"dur": 3.8, "set": "street", "weather": "rain", "hud": {"value": 1, "chapter": "Thursday"},
 "camera": {"frame": "two", "on": "hero"},
 "actors": [{"id": "demon", "x": 50, "pose": "grab", "target": "hero"},
            {"id": "hero", "x": 60, "pose": "stand", "mood": "worried", "hold": "bag"}],
 "lines": [{"who": "demon", "text": "they'll laugh at you.", "at": 0.8}]}
```

Every option (sets, poses, moods, frames, phone apps, items and sound effects) is listed in [`engine/vocab.json`](engine/vocab.json). `story/validate.py` repairs anything the engine can't draw, so a film always renders.

## Preview locally

```bash
npm install && npx playwright install chromium
node render/render.mjs --film examples/the-sketchbook.json --stills build/stills --every 2 --width 1280   # review frames
node render/render.mjs --film examples/the-sketchbook.json --out build/picture.mp4                        # picture
node render/render.mjs --film examples/the-sketchbook.json --cues build/cues.json
python audio/sound.py --cues build/cues.json --out build/soundtrack.wav                                   # sound
```

You can also serve the repo (`python -m http.server`) and open `engine/index.html?film=../examples/the-sketchbook.json` to watch the film play live in a browser.

## How it works

| Part | File | Notes |
|---|---|---|
| Writer | `story/write.py` | Beat sheet first (the format's 13-step structure), then 2–4 shots per beat, written on four runners in parallel. |
| Validator | `story/validate.py` | Keeps every shot inside the engine's vocabulary. |
| Character rig | `engine/character.js` | One body and head blob, two-bone arm and leg IK, 12 moods, 21 poses, hats, held props. |
| Sets | `engine/sets.js` | 11 dark line-art sets with light pools, weather and time of day; desks and café tables sit in the foreground. |
| Phone, HUD, text | `engine/overlay.js` | Chat (typing that gets deleted or sent), calls, lock screen, feed, alarm; counter; red demon text; cards. |
| Camera | `engine/main.js` | Wide, medium, close, extreme, two-shot and phone framing; background blur on close shots; red glow on the demon; grain and vignette. |
| Sound | `audio/sound.py` | Effects and ambience come from the picture (footsteps, typing, notifications, demon drone, rain). Music follows each shot's level, ducks under the demon and is mastered to −14 LUFS. |
| Score | `audio/music.py` | ACE-Step 1.5 on CPU, with the film's own music prompt. |

Fonts: Patrick Hand and Share Tech Mono (SIL Open Font License) are downloaded during the run.
