---
name: jungle-pop
description: >-
  Project conventions for the `cartoon_studio` / Jungle Pop animation pipeline
  (Python + Pillow + FFmpeg for 2.5D, headless Blender for the 3D stage, Khmer
  narration + subtitles). Use this skill WHENEVER working in this repo — adding or
  editing a character (KIKO, TAVI, LUMA, BOKO, ZURI, VARGO, GRIB, MOMO, NANA, PIP,
  MIRA, RUKO, FIFI, TOTO, THE JUNGLE SPIRIT), building or rendering a story/episode,
  making a 2.5D puppet or rig.json, working with backgrounds/parallax, wiring
  narration/subtitles, or touching the Blender KIKO asset — even if the user does
  not name this skill. It encodes the character-package format, canon rules, the
  placeholder-vs-real-art honesty gate, and data-safety habits for this project.
---

# Jungle Pop — project skill

A family-adventure jungle animation universe. This skill is the rulebook for working
inside `cartoon_studio`. Read the two source-of-truth docs before non-trivial work:

- `docs/JUNGLE_POP_CHARACTER_HISTORY_KH.md` — the **Character Bible** (Khmer): canon
  role, personality, visual identity, backstory, relationships, production priority
  for all 15 characters. This is authoritative for *who a character is*.
- `PROJECT_STRUCTURE.md` — the folder/file map (where everything lives).

If either is missing, ask before guessing — do not invent canon or layout.

---

## Golden rules (never break)

1. **Honesty gate.** Code/structure can be built here; **real character + background
   art and real narration audio are human/tool steps.** Every art slot starts as a
   clearly-labeled **placeholder**. Never fake a finished look, never mark a package
   `production` unless it truly is, never claim a render "passes" just because it ran
   without errors — judge whether it actually does the thing.
2. **Originality.** These are the user's own original characters. Build only original
   or placeholder art. Never reproduce, trace, or fidelity-match any outside
   character or reference image.
3. **Canon consistency.** A character's role, personality, and visual identity must
   match the Character Bible. If a request contradicts the bible, flag it; change
   canon only when the user updates the bible.
4. **Silhouette first.** Every character must be recognizable by silhouette alone,
   not by color. Big expressive eyes, strong color identity, readable shapes.
5. **Data safety (this project was lost once).** NEVER `rm -rf`, delete files/dirs,
   or overwrite any `.blend` (especially `blender/KIKO_master_v001.blend`) without
   first copying it to a `*_backup`. `git commit` after every working change. If an
   action is destructive or irreversible and you are not certain, STOP and ask.

---

## The character package (the reusable unit)

Every character is one folder with the **same** shape. To add one, copy
`assets/characters/_TEMPLATE/`.

```
assets/characters/<id>/
├── character.json   # id, name, role, type, color_identity, priority, status
├── rig.json         # parts[]: {art, parent, pivot:[x,y], z, states:{…}}
├── layers/          # one transparent PNG per body part (placeholder or real)
├── states/          # expression / lip-sync viseme swaps (eyes_*, mouth_*)
├── thumbnail.png
└── README.md        # EXACT png paths real art replaces + pivot meaning
```

- `status`: `placeholder` → `wip` → `production` (be honest).
- **Swap-in rule:** replacing a PNG at its documented path must change the render with
  **zero code change**. That is where real art enters later.
- Validate every package against this shape (`assets_lib/character_package.py`); keep
  `assets/characters/registry.json` updated (id → path, role, priority, status).
- `rig.json` z-order back→front: tail → far arm → far leg → torso → near leg →
  near arm/hand → head → ears/crest → face → costume. Pivots sit at joints; nothing
  floats detached at rest. (This was the KIKO 2.5D bug — check it on every rig.)

### Adding / editing a character — checklist
1. `cp -r assets/characters/_TEMPLATE assets/characters/<id>`
2. Fill `character.json` from the bible: role, personality, visual identity,
   backstory, strengths/weaknesses, comedy style, relationships, story function,
   priority.
3. Generate placeholder `layers/` + a correct `rig.json` (pivots, z-order, states).
4. Add to `registry.json`.
5. Smoke-test in a `projects/` scene through ImageRenderer.
6. Commit. Later: drop real art at the documented paths.

---

## Canon quick map (details in the bible)

- **Core team — build reusable/production-ready first, in this order:**
  KIKO (1) · LUMA (2) · TAVI (3) · BOKO (4) · ZURI (5). Do NOT build all 15 to
  production at once.
- **Returning cast:** VARGO (villain), GRIB, MOMO, NANA, PIP, MIRA, RUKO, FIFI,
  TOTO, THE JUNGLE SPIRIT.
- **Episode-type casts** (don't force all 15 into one episode):
  comedy → KIKO, BOKO, MOMO, GRIB, TOTO, PIP ·
  adventure → KIKO, TAVI, LUMA, ZURI, BOKO ·
  mystery → KIKO, TAVI, NANA, JUNGLE_SPIRIT, VARGO ·
  emotional → KIKO, FIFI, TAVI, BOKO, MIRA ·
  rival → KIKO, ZURI, LUMA ·
  villain → VARGO, GRIB, KIKO, TAVI, ZURI.

Always confirm a character's specific look/voice against the bible before building —
this map is only a cast list, not the canon.

---

## Stories / episodes

- Entry point: `stories/epNNN_<slug>/story.json` → `cartoon_studio/cli.py` → final
  mp4 + `.srt` + run manifest. Templates per type in `stories/templates/`.
- Story schema (`cartoon_studio/models/story.py`): project meta (title, resolution,
  fps, orientation) → ordered scenes; each scene = background, character placements
  (id, position, scale, z, pose/expression), an action timeline, camera directives,
  dialogue lines (text + speaker + optional audio), duration.
- Output both 16:9 (1920×1080) and 9:16 (1080×1920).

## Rendering

- Default renderer is **2.5D** (`renderers/image_renderer.py`): per-part transforms
  from `rig.json`, z-order, expression/viseme swaps, keyframe interpolation, and
  multi-plane **parallax** from background depth tags.
- A scene may set `"renderer": "blender"` → `renderers/hybrid_renderer.py` routes to
  `renderers/blender_kiko.py`, which shells out to `blender/kiko_render.py`
  (headless). KIKO's Blender rig is **unskinned** → rest-pose / turntable / camera
  moves only until skinning.
- One FFmpeg route only (`compositor/ffmpeg_engine.py`): stitch + mux narration/
  music/sfx + optional burned subtitles. Even dimensions, yuv420p, H.264.

## Audio & Khmer subtitles

- **Integrate** the existing TTS (VoxCPM2 / voice_studio) — do not rebuild it. A
  dialogue line names text + speaker; the pipeline supplies the clip + duration,
  which drives that beat's timing. If no TTS is wired, accept pre-rendered audio
  paths and flag TTS as an external step.
- Subtitles are **Khmer Unicode**: use a Khmer-capable font from `assets/fonts/` and
  verify glyphs render (no tofu boxes). Export `.srt`; burn-in is a toggle.
- Lip-sync baseline = amplitude-driven mouth open/close; leave a viseme hook for a
  phoneme aligner later.

---

## Backgrounds

Jungle regions are layered for parallax: `assets/backgrounds/<region>/background.json`
with `layers[]: {art, depth}` (0 = far … 1 = near). Starter regions: deep_jungle,
waterfall, ancient_temple, caves, canopy_high, hidden_path. Placeholder art until real.

## Visual consistency (gate before any art is "production")

Stylized 3D look · big expressive eyes · readable silhouette · soft organic materials ·
believable fur/feathers/skin per species · handmade-adventure accessories · strong
per-character color identity. ❌ smooth plastic · ❌ generic low-poly · ❌ photoreal.
Full guide: `docs/visual_style_guide.md`.

---

## When finishing any task

Report honestly: what changed, what passed (and how verified), and what still needs
**real art / real audio / skinning / a phoneme aligner** before broadcast quality.
Then `git add -A && git commit`.
