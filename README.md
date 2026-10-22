# Am I enough?

An original 90-second animated short about trying to reach a standard that keeps moving. An ivory character with a teal scarf works, runs and builds a literal tower of achievements beneath a line marked **ENOUGH**. A quiet invitation offers another way to spend the evening.

## Watch the finished film

**[Download the first complete cut](https://github.com/justsomeoneretarded/new-animation/actions/runs/39749049154/artifacts/12412153526)** — unzip and open `Am-I-enough.mp4`. [Verified workflow run](https://github.com/justsomeoneretarded/new-animation/actions/runs/39749049154) completed in approximately 3 minutes, including parallel rendering, original sound synthesis, assembly, validation and upload. This is one measured run, not a guarantee of future queue or execution time.

Open this repository’s **Actions** tab, select the latest successful **Render Am I enough** run, and download **Am-I-enough-complete-film** under Artifacts. Unzip it and open `Am-I-enough.mp4`.

The artifact also contains a storyboard, poster, production script, stereo soundtrack, timing log and validation results. Editable audio stems are available in a separate artifact. Artifacts expire after the retention period; download a copy you want to keep.

## Render on GitHub Actions

The first push containing the workflow starts a full-HD render. To render again:

1. Open **Actions → Render Am I enough → Run workflow**.
2. Select `1920` for 1080p, or `1280` for a faster 720p review.
3. Wait for the three picture jobs and finishing job to succeed.
4. Download the finished-film artifact.

No secrets, paid APIs, GPU, external model or asset downloads are required. The workflow uses Ubuntu’s CPU runners. GitHub’s account limits, runner availability and artifact storage policies still apply; software being free does not remove those limits.

## Run locally

Requirements: Python 3.12 and DejaVu fonts. FFmpeg is supplied by a pinned Python wheel, avoiding slow system-package mirror updates in GitHub Actions. On Ubuntu:

```bash
sudo apt-get install fonts-dejavu-core
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m film.build --width 1920 --out build/final
```

For a quick storyboard:

```bash
python -m film.render --stills --width 1280 --out build/review
```

For a specific section:

```bash
python -m film.render --start 46 --end 55 --width 1280 --out build/review
```

## Production design

- **90 seconds, 1920×1080, 24 fps**. Character poses principally update at 12 fps; cameras, weather, text and effects can move at the delivery rate.
- Articulated original vector characters; separate expressions and hand targets; reusable rooms, street and café; camera reframing; glass reflections; moving text; atmosphere; original typography treatment.
- A silent story with text, music and effects, **no narrator**.
- An original procedural score and independently synthesized foley. No audio from the reference videos is reused. The music uses struck-string and sustained bowed-like synthesis, not recordings of acoustic performers.
- Separate music, ambience and foley stems. Two-pass loudness normalization targets −16 LUFS and −1.5 dBTP before AAC delivery.
- Complete FFmpeg decode plus frame count, duration, stereo audio and loudness checks.

The renderer uses **Python, Pillow, aggdraw, NumPy, SciPy and FFmpeg**, rather than a 3D engine. This is deliberately layered 2D artwork, allowing CPU-only reproducible builds. It does not create a Blender `.blend` project.

## Edit and make further films

`film/story.py` owns shot timing and story purpose. `film/art.py` owns the drawing primitives, environments, palette and character controls. `film/render.py` stages each shot and camera. `film/audio.py` owns the score, sound synthesis and cue timing. `film/build.py` assembles and validates the delivery.

This is a reusable production codebase, not an automatic “type any concept and receive a finished movie” generator. A different story needs deliberate shot design, acting and sound cues.

## Rights and credits

Story, generated drawings, animation code and synthesized composition were created for this project. Reference films informed a general production target; their characters, images, music and recordings are not bundled. DejaVu fonts remain under their own license (installed by the OS, not copied into this repository). See `THIRD_PARTY.md` for tool licenses. This repository does not grant a separate public license to the original film or its artwork.
