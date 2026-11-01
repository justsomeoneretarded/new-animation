# new-animation

Day One-style animated shorts from a title and a brief. A cream blob hero; a shadow demon whose glow matches the theme and who says the cruel thing out loud; narration with a twist line; speech bubbles; phone screens, handwritten notes and calendars; colour that follows the emotion; a quote card, an "X vs Y." title card, and like-and-subscribe.

Everything runs free on GitHub Actions:
- a local script model (Gemma 4 12B through Ollama) writes the story;
- a browser-canvas animation engine, rendered by headless Chromium, draws it;
- Kokoro speaks the narration;
- ACE-Step composes the score;
- the sound effects are synthesized from what happens on screen.

## Make a film

**Actions → Make film → Run workflow.** There are two inputs:

| Input | What to write |
|---|---|
| Title | The video title, e.g. `Lust vs Love`. |
| Brief | The story: who the hero is, what they struggle with, what the demon tells them, who helps, how it ends. Specific moments make the best films. Leave empty to render the example film. |

The writer decides the rest:
- the length (about 1.5–3 minutes);
- whether a counter fits (like `SEEN / KNOWN`), day chapters (`DAY 1 … DAY 30`), or neither;
- the demon's colour;
- where narration goes;
- the colour of each scene;
- the cast's looks.

Download the **film** artifact when the run finishes. It contains the MP4, `story.md` (the script shot by shot), `film.json` (the shot list), a contact sheet, a thumbnail frame and the soundtrack. The **Concept** and **Story** notes on the run page show what was written before the film renders.

A run takes about an hour: about 35 minutes of writing, then narration, score and picture in parallel.

### Example brief

> A guy who scrolls through thousands of faces a night but has never really known anyone. The demon (pink) says "she's nothing special" and "just one more." A girl with a yellow umbrella at his bus stop asks "coffee? saturday?". He goes, but relapses into scrolling. He writes "look up sometimes" in a notebook, switches his phone off, and counts the days. On day 30 he finally talks to her properly at sunset.

## Editing a film by hand

Copy `film.json` from the artifact into the repo, for example `films/my-film.json`, and edit it. Then run the workflow with that path as the **brief**, such as `films/my-film.json`. Writing is skipped and only the picture and sound are made again.

Every option (sets, poses, moods, wardrobe, frames, object close-ups, phone apps, colour grades, cards and sound effects) is listed in [`engine/vocab.json`](engine/vocab.json). `story/validate.py` repairs anything the engine can't draw, so a film always renders. [`examples/envy-vs-enough.json`](examples/envy-vs-enough.json) shows every feature.

## Preview locally

```bash
npm install && npx playwright install chromium
node render/render.mjs --film examples/envy-vs-enough.json --stills build/stills --every 2 --width 1280   # review frames
node render/render.mjs --film examples/envy-vs-enough.json --out build/picture.mp4                        # picture
node render/render.mjs --film examples/envy-vs-enough.json --cues build/cues.json
python audio/sound.py --cues build/cues.json --out build/soundtrack.wav                                   # sound
```

Serve the repo (`python -m http.server`) and open `engine/index.html?film=../examples/envy-vs-enough.json` to watch it play live.

## How it works

| Part | File | Notes |
|---|---|---|
| Concept and beats | `story/write.py` | Cast and wardrobe, story device, demon colour, narration, 12–16 beats in the format's structure. |
| Storyboard | `story/write.py` | 2–4 shots per beat, written on four runners in parallel. |
| Checker | `story/validate.py` | Keeps every shot inside the engine's vocabulary. |
| Characters | `engine/character.js` | Body and arm/leg rig, 23 moods with full eyes in close-ups (irises, lids, tears, blush), side-on sitting and walking, characters looking at each other, hair, hoods, coats, scarves, hats, glasses, umbrellas. |
| Sets | `engine/sets.js` | 13 sets (bedroom, desk, office, kitchen, café, street, bus stop, park, gym, hill, rooftop, hallway, void) with light pools, rain with splashes and reflections, snow, out-of-focus city lights, and time of day. |
| Screens and text | `engine/overlay.js`, `engine/inserts.js` | Chat (typing that gets deleted or sent), calls, feed, alarm, power-off; notes, calendars, photos; counters and chapters; speech bubbles, narration with twist lines, big chapter words, demon text in the demon's colour; cards. |
| Camera and colour | `engine/main.js` | Wide, medium, close, extreme, two-shot, phone and insert framing; background blur; a colour grade per shot; grain and vignette. |
| Narration | `audio/voice.py` | Kokoro speaks the narrator lines; each shot is stretched to fit, and the captions type in time with the voice. |
| Sound | `audio/sound.py` | Effects and ambience come from the picture: footsteps, typing, bubbles, notifications, pen scratches, the demon's drone, rain, the café. Music ducks under the voice and the demon, and the mix is mastered to −14 LUFS. |
| Score | `audio/music.py` | ACE-Step 1.5 on CPU, with the film's own music prompt. |

Fonts are downloaded during the run: Patrick Hand, Nunito and Share Tech Mono, all under the SIL Open Font License.
