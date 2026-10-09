# Build Prompt: JSON-Driven Cartoon/Animation Video Generator (V1)

Build a production-quality Python project for generating cartoon-style videos entirely from JSON configuration.

## Goal

Create a JSON-driven animation/video generation tool.

The first version MUST focus on a lightweight 2D / 2.5D workflow suitable for long Khmer narration videos.

Do NOT start by building complex rigged 3D characters.

V1 pipeline:

```text
JSON project
→ validate schema
→ load scene assets
→ create layered 2D/2.5D scenes
→ camera pan / zoom / push / parallax
→ character/sprite placement
→ simple sprite animation
→ optional fog / particles / overlays
→ sync narration + music + SFX
→ render PNG image sequence (parallel, resumable)
→ FFmpeg encode
→ final MP4
```

The architecture MUST be designed so a Blender 3D renderer can be added later without rewriting the project format.

Use clean architecture, type hints, dataclasses/Pydantic models, logging, proper error handling, and tests.

Do not implement everything in one Python file.

---

# Technology

Use:

- Python 3.12+
- Pydantic v2 for configuration models and validation
- Pillow for image composition
- NumPy where useful
- FFmpeg through subprocess for final video/audio encoding
- pytest for tests
- pathlib for filesystem paths
- `multiprocessing` (standard library) for parallel frame rendering

Optional:
- OpenCV only when Pillow cannot reasonably handle an operation
- tkinter/customtkinter only for a very small GUI after the CLI/core engine works

Do NOT make GUI code the core engine. The engine must be usable entirely from CLI.

Do NOT render directly to MP4 during scene rendering. Always create recoverable image sequences first. Final encoding happens only after rendering succeeds.

---

# Important architecture rule

JSON contains human-friendly instructions. JSON MUST NOT expose implementation-specific animation details such as:

- bone rotation values
- raw transform matrices
- shader node values
- Blender-specific property paths

Good:

```json
{ "emotion": "scared", "action": "look_left", "camera": { "movement": "slow_push" } }
```

Bad:

```json
{ "bone_rotation_x": 0.72842 }
```

The engine is responsible for translating semantic commands into implementation details.

---

# Project Structure

Create approximately:

```text
cartoon_studio/
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
│
├── cartoon_studio/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── scene.py
│   │   ├── layer.py
│   │   ├── camera.py
│   │   ├── audio.py
│   │   ├── character.py
│   │   └── effects.py
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── director.py
│   │   ├── timeline.py
│   │   ├── scene_renderer.py
│   │   ├── compositor.py
│   │   ├── camera_engine.py
│   │   ├── parallax_engine.py
│   │   ├── character_engine.py
│   │   ├── effect_engine.py
│   │   ├── audio_engine.py
│   │   └── ffmpeg_engine.py
│   │
│   ├── renderers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── image_renderer.py
│   │
│   ├── presets/
│   │   ├── camera.py
│   │   ├── emotion.py
│   │   ├── movement.py
│   │   └── effects.py
│   │
│   └── utils/
│       ├── paths.py
│       ├── interpolation.py
│       ├── hashing.py
│       ├── subprocess.py
│       └── logging.py
│
├── schemas/
│   └── project.schema.json        # generated from Pydantic, not hand-written
│
├── assets/
│   ├── characters/
│   ├── backgrounds/
│   ├── foregrounds/
│   ├── props/
│   ├── overlays/
│   ├── effects/
│   ├── audio/
│   └── fonts/
│
├── projects/
│   └── example_forest_story.json
│
├── output/
│   ├── frames/
│   ├── scenes/
│   ├── audio/
│   └── final/
│
└── tests/
    ├── test_project_schema.py
    ├── test_timeline.py
    ├── test_camera.py
    ├── test_interpolation.py
    ├── test_parallax.py
    ├── test_determinism.py
    └── test_render_smoke.py
```

Small structural improvements are allowed if they improve maintainability.

---

# Core abstraction

Create a renderer interface.

```python
class BaseRenderer(ABC):
    @abstractmethod
    def prepare(self, project): ...

    @abstractmethod
    def render_scene(self, scene, context): ...

    @abstractmethod
    def finalize(self): ...
```

V1 implementation: `ImageRenderer`.

Later we should be able to add `BlenderRenderer` without changing `Director`. Do NOT implement `BlenderRenderer` fully in V1 — a stub/interface is acceptable.

---

# JSON Format

Create a clean JSON configuration format approximately like this:

```json
{
  "format_version": 1,

  "project": {
    "title": "ព្រៃអាថ៌កំបាំង",
    "mode": "2.5d",
    "resolution": { "width": 1920, "height": 1080 },
    "fps": 24,
    "background_color": "#000000",
    "seed": 42,
    "timing_mode": "narration_driven"
  },

  "defaults": {
    "transition_duration": 1.0,
    "camera_easing": "ease_in_out",
    "music_volume": 0.15,
    "narration_volume": 1.0,
    "sfx_volume": 0.55
  },

  "audio": {
    "narration": "assets/audio/full_narration.wav",
    "background_music": "assets/audio/horror_ambient.wav"
  },

  "scenes": [
    {
      "id": "scene_001",
      "start": 0.0,
      "duration": 12.0,

      "background": { "source": "assets/backgrounds/forest_night.png", "scale": "cover" },

      "layers": [
        { "id": "far_fog", "source": "assets/overlays/fog.png", "depth": 0.15, "opacity": 0.4 },
        { "id": "trees", "source": "assets/foregrounds/trees.png", "depth": 0.45 },
        {
          "id": "rith",
          "type": "character",
          "source": "assets/characters/rith.png",
          "depth": 0.75,
          "position": { "x": 0.55, "y": 0.78 },
          "scale": 0.65
        }
      ],

      "camera": {
        "shot": "medium",
        "movement": "slow_push",
        "from": { "x": 0.5, "y": 0.5, "zoom": 1.0 },
        "to":   { "x": 0.53, "y": 0.48, "zoom": 1.12 },
        "easing": "ease_in_out"
      },

      "characters": [
        {
          "layer_id": "rith",
          "emotion": "worried",
          "action": "idle",
          "motion": { "type": "subtle_breathing", "intensity": 0.3 }
        }
      ],

      "effects": [
        { "type": "fog", "intensity": 0.35, "speed": 0.08 },
        { "type": "vignette", "intensity": 0.2 }
      ],

      "audio": [
        { "source": "assets/audio/forest_night.wav", "start": 0, "volume": 0.25, "loop": true }
      ],

      "transition_out": { "type": "crossfade", "duration": 1.0 }
    }
  ]
}
```

Use normalized coordinates from `0.0` to `1.0` for JSON-facing positions. Internally convert to pixels.

**Coordinate convention (state explicitly in code and README):** normalized `x` runs left→right (0.0 = left edge, 1.0 = right edge); normalized `y` runs **top→bottom** (0.0 = top edge, 1.0 = bottom edge). Document this in one place and apply it consistently everywhere.

---

# Timing model (resolve before rendering)

A project has one full `narration` track plus per-scene `duration` values. These two MUST be reconciled deterministically. Support a `project.timing_mode`:

- `"narration_driven"` (recommended default): the narration track defines total runtime. Scene `duration` values are treated as proportional/absolute hints and are scaled or validated so the sum of scene durations equals the narration length. If they cannot be reconciled, fail validation with a clear message showing the narration length, the summed scene length, and the delta.
- `"scenes_driven"`: scene durations define total runtime; narration is laid onto that timeline and may be shorter (silence pads the tail) or is flagged if longer.

Never silently truncate or stretch audio. Report the chosen total duration in `info` and `validate`.

---

# JSON validation

Use Pydantic. Unknown critical values should fail early with useful error messages:

- duplicate scene ID → validation error
- duration <= 0 → validation error
- fps <= 0 → validation error
- unsupported movement → validation error
- missing required asset → clear pre-render error
- invalid normalized position (outside 0.0–1.0) → validation error
- invalid opacity (outside 0.0–1.0) → validation error
- narration/scene-duration mismatch under the active `timing_mode` → validation error

Before rendering, perform complete project asset validation. Do NOT discover a missing background after rendering 40 minutes of frames.

**Generate `schemas/project.schema.json` from the Pydantic models** (via `model_json_schema()`) through a CLI command or build step — do not hand-maintain a second copy that can drift from the models.

```bash
python -m cartoon_studio.cli validate projects/story.json
```

Output should clearly state:

```text
Project valid
17 scenes
23 assets
Timing mode: narration_driven
Duration: 00:42:18
Resolution: 1920x1080
FPS: 24
```

---

# Timeline

Implement a proper timeline engine. Each scene should know: `start_time`, `end_time`, `duration`, `start_frame`, `end_frame`.

Functions:

```python
seconds_to_frame()
frame_to_seconds()
scene_at_time()
scene_at_frame()
local_scene_time()
```

Avoid floating-point drift: derive frame boundaries from integer frame indices, not by accumulating float durations.

---

# Frame rendering

For every output frame:

1. Determine scene.
2. Calculate local scene progress `0.0 → 1.0`.
3. Calculate camera position.
4. Calculate zoom.
5. Transform each layer.
6. Apply depth-based parallax.
7. Apply character motion.
8. Apply effects (grain seeded per-frame — see Determinism).
9. Composite RGBA layers.
10. Save numbered PNG.

Frame naming: `frame_000001.png`, `frame_000002.png`, …

Do not overwrite an existing complete frame unless requested (enables resume).

---

# Parallel rendering (required, not optional)

Frame rendering is embarrassingly parallel — each frame is computed independently from the project model and its frame index. The frame loop MUST use a process pool (`multiprocessing.Pool` or `concurrent.futures.ProcessPoolExecutor`).

Requirements:

- Worker count defaults to CPU count, overridable via `--workers N` and an env/config value.
- Each worker reconstructs or receives the (read-only) project model and renders assigned frame indices; workers must not share mutable state.
- The asset cache is per-process (see Asset cache). Do not attempt to share Pillow image objects across processes.
- Progress reporting aggregates across workers (frames completed / total), without interleaving garbled log lines.
- `--workers 1` must run a simple single-process path, used by tests for determinism and easier debugging.

This is the single most important performance decision for hour-long videos; a single-threaded frame loop is not acceptable for V1.

---

# Static-frame optimization

In long narration, many consecutive frames are visually identical (static camera, no character motion, no animated effect that frame). Avoid recomputing and rewriting identical PNGs.

Implement a per-frame "render signature": a cheap hash of everything that affects the pixels of that frame (camera state, each layer's transform/opacity, active character motion values, active effect parameters, grain seed contribution). If a frame's signature equals the previous frame's, reuse the previous frame via copy or hardlink instead of recompositing.

- Must remain correct with resume and with parallel workers (signature is a pure function of frame index + project, so any worker computes the same result).
- Must be disableable via `--no-dedupe` for debugging.
- Animated effects (fog drift, grain, breathing, shake) naturally change the signature every frame, so they are never wrongly deduped.

---

# Determinism (grain, noise, resume must agree)

Same project + same `seed` must produce visually repeatable output, including across a resumed render and across parallel workers.

Therefore all randomness MUST be a pure function of `(project.seed, frame_index[, element_id])` — e.g. seed a fresh `numpy.random.default_rng(project.seed + frame_index)` per frame. Never advance a shared/running RNG whose state depends on how many frames were rendered in this process. This guarantees frame 14,523 rendered today matches frames 1–14,522 rendered yesterday.

Add a determinism test: render a given frame index twice (separately) and assert the PNG bytes are identical.

---

# Resume capability

Implement:

```bash
cartoon-studio render story.json --resume
```

If `frame_000001.png … frame_014522.png` already exist and are valid, continue from `frame_014523.png`. Do not rerender completed frames unnecessarily.

Also support `--force` to rerender everything.

Resume safety is governed by the render manifest and per-scene hashing (below).

---

# Render manifest + per-scene hashing

Create `output/<project>/render_manifest.json`, storing at least:

```json
{
  "format_version": 1,
  "project_hash": "...",
  "scene_hashes": { "scene_001": "...", "scene_002": "..." },
  "seed": 42,
  "fps": 24,
  "resolution": [1920, 1080],
  "total_frames": 60000,
  "completed_frames": 14522,
  "started_at": "...",
  "updated_at": "...",
  "status": "rendering"
}
```

**Hash each scene separately** (scene config + the content/mtime of the assets it references), in addition to a whole-project hash. On `--resume`:

- Compare each scene's current hash to the manifest.
- Only invalidate and re-render the frame ranges of scenes whose hash changed. Editing scene 17 must NOT force re-rendering scenes 1–16.
- If `format_version`, `fps`, `resolution`, or `seed` changed, warn and require `--force` (these affect every frame).

---

# Scene-only + range rendering

```bash
cartoon-studio render-scene story.json scene_005
cartoon-studio render-scene story.json scene_005 --preview
cartoon-studio render story.json --from 30 --to 45 --preview
```

`--preview` uses cheaper settings (e.g. 960x540, 12fps). `--from/--to` are in seconds.

---

# Camera Engine

Reusable semantic movements (behind `CameraEngine`/presets, not hard-coded in renderer code):

```text
static  slow_push  slow_pull  pan_left  pan_right
pan_up  pan_down   drift_left drift_right  handheld_subtle
```

Easing: `linear`, `ease_in`, `ease_out`, `ease_in_out` (implement in `utils/interpolation.py`).

Interpolation must start exactly at `from` and end exactly at `to`.

---

# Parallax

Each layer has `depth` 0.0–1.0. Example meaning: `0.1` distant background, `0.4` environment, `0.7` character, `0.9` foreground. When the camera moves, closer objects shift more than distant ones. Keep the math simple and predictable — stylized 2.5D parallax, not physically correct projection.

Test: foreground moves more than background; depth 0 and 1 handled correctly.

---

# Character Engine V1

V1 characters are sprites/layers — no skeleton rigs. Semantic values:

```json
{ "emotion": "scared", "action": "idle" }
```

Actions required: `idle`, `subtle_breathing`, `walk_in_place`, `look_left`, `look_right`, `shake`, `float`, `fade_in`, `fade_out`.

Actions may animate position/rotation/scale/opacity. No sprite sheets required for V1, but structure `CharacterEngine` so sprite-sheet animation can be added later.

---

# Lip Sync V1

Do NOT attempt Khmer phoneme/viseme lip sync. Implement only optional amplitude-based mouth animation:

```json
{ "mouth": { "closed": "rith_mouth_closed.png", "open": "rith_mouth_open.png" } }
```

Audio amplitude MAY select/blend between closed/open. Keep optional; never fail a project because lipsync assets don't exist. Design the interface so viseme-based lipsync can be added later.

---

# Emotion Presets

Preset system controlling subtle visual transforms/effects (not skeletal facial animation in V1): `neutral`, `calm`, `worried`, `scared`, `angry`, `sad`, `shocked`, `ghostly`.

```python
"scared": { "breathing_speed": 1.25, "shake": 0.015, "scale_pulse": 0.005 }
```

Do not expose these low-level values in normal project JSON.

---

# Effects

Required V1 effects: `vignette`, `fog`, `film_grain`, `fade`, `flash`, `shake`, `darken`, `desaturate`.

Fog via one or more transparent moving textures. Film grain and all noise are deterministic per the Determinism section (seeded by `project.seed + frame_index`).

---

# Audio

Audio is NOT rendered frame-by-frame — mixed via FFmpeg during final composition. Support narration, background music, scene ambience, SFX.

Each clip:

```json
{ "source": "audio.wav", "start": 12.5, "volume": 0.45, "loop": false, "fade_in": 0.5, "fade_out": 1.0 }
```

Narration must remain dominant. Do not destructively normalize narration.

---

# FFmpeg Engine

Create a single `FFmpegEngine` class (do not scatter subprocess calls). Responsibilities: detect/validate FFmpeg, encode PNG sequence, mix audio, output final MP4, expose progress, report useful errors.

Defaults: H.264, yuv420p, AAC, MP4, YouTube-friendly CRF/preset. Do not hardcode absolute FFmpeg paths; allow config/env override. Output e.g. `output/final/forest_story.mp4`.

The system MUST use `frames → FFmpeg → video`, never generating the final MP4 directly from Pillow/Blender (enables crash recovery, resume, frame inspection, selective re-render, easier debugging).

---

# Image quality

Preserve alpha channels correctly. Use high-quality resizing. Handle images larger and smaller than output. Scale modes: `contain`, `cover`, `stretch`, `native`.

---

# Transitions

Required: `cut`, `crossfade`, `fade_black`. Timeline-aware. Render transition frames directly into the main image sequence — do NOT encode per-scene MP4s and stitch them.

---

# Asset cache

Do not reopen the same PNG from disk for every frame. Implement an in-memory cache (`AssetManager.get_image(path)`), **per worker process** (caches are not shared across processes). Reuse loaded assets; avoid unbounded memory growth on large projects (bounded cache / eviction where needed).

---

# Performance summary

Long narration videos can contain tens of thousands of frames. Do not: reload images every frame, parse JSON every frame, build unnecessary giant arrays, or keep every rendered frame in memory. Generate and save frames sequentially within each worker, in parallel across workers, with static-frame dedupe. Make code safe for hour-long projects.

---

# Progress reporting

```text
Project: ព្រៃអាថ៌កំបាំង
Scene 5/17
Frame 12540 / 60520  (20.72%)
Workers: 8
Rendering frame_012540.png
```

Do not spam logs. Use Python logging. Support `--verbose`.

---

# Future Blender compatibility

Design interfaces now; do not build the 3D engine. Future flow:

```text
Director → BaseRenderer ├─ ImageRenderer
                        └─ BlenderRenderer
```

`BlenderRenderer` will later translate semantic JSON (`action`, `emotion`, `camera.movement`) into Blender operations. Keep Blender-specific keys out of the core schema.

---

# Future modes

Schema allows `mode`: `2d`, `2.5d`, `3d`. Only `2d` and `2.5d` implemented now. If `3d` is requested in V1:

```text
3D rendering is not implemented yet.
Use mode=2.5d or install/enable BlenderRenderer.
```

---

# Example Khmer horror project

Realistic example, ~3 short scenes, no copyrighted assets:

1. Dark forest, slow camera push, narrator audio, light fog.
2. Character near a tree, subtle breathing, camera drift right, night ambience.
3. Pale ghost sprite appears in background, opacity fade-in, mild camera shake, fade to black.

If real assets are unavailable, generate simple placeholder PNGs programmatically so the example runs immediately.

---

# Placeholder asset generator

```bash
cartoon-studio create-demo
```

Creates basic forest background, tree foreground, character silhouette, ghost silhouette, fog texture. Not beautiful — just enough for the full pipeline to run after install.

---

# CLI

```bash
cartoon-studio validate project.json
cartoon-studio info project.json
cartoon-studio schema > schemas/project.schema.json   # emit schema from Pydantic
cartoon-studio create-demo
cartoon-studio render project.json
cartoon-studio render project.json --resume
cartoon-studio render project.json --force
cartoon-studio render project.json --workers 8
cartoon-studio render project.json --from 30 --to 45 --preview
cartoon-studio render-scene project.json scene_003
cartoon-studio render-scene project.json scene_003 --preview
cartoon-studio encode project.json
cartoon-studio clean project.json
```

`info` shows: Title, Scenes, FPS, Resolution, Timing mode, Total duration, Estimated total frames, Assets, Narration, Output directory.

---

# Tests

Deterministic tests. At minimum:

**Validation:** valid project succeeds; duplicate scene ID fails; negative duration fails; invalid FPS fails; missing asset detected; invalid normalized coordinates fail; narration/scene timing mismatch fails.

**Timeline:** seconds/frame conversion; scene start/end; correct scene at frame; local progress correct.

**Camera:** interpolation starts at `from`, ends at `to`; easing bounded; static camera stays static.

**Parallax:** foreground moves more than background; depth 0/1 handled.

**Determinism:** same frame index rendered twice yields byte-identical PNG; render signature stable across a `--workers 1` and `--workers 4` run for the same frames.

**Render smoke:** tiny 320x180, 5fps, 1-second project produces exactly 5 PNG frames. If FFmpeg exists, optionally verify final MP4. Do not fail the whole suite when FFmpeg is absent (except FFmpeg-specific tests).

---

# README

Cover: what it does; architecture diagram; installation; FFmpeg requirement; `create-demo`; validate; render preview; full render; resume; encode; `--workers` and performance notes; static-frame dedupe and determinism/seed behaviour; coordinate convention; timing modes; JSON reference; adding camera movements; adding effects; future Blender renderer architecture. Include macOS commands where useful (development may run on macOS).

---

# Dependency philosophy

Keep dependencies minimal. Before adding a package ask: can stdlib, Pillow, NumPy, or Pydantic already do this cleanly? Avoid large frameworks.

---

# Code quality

Type hints; no giant functions; clear class responsibilities; no circular imports; pathlib over string concatenation; useful exceptions; reusable interpolation utilities; deterministic tests; docstrings where useful; no dead code; no fake implementations silently pretending to work. Do not catch `Exception` everywhere — handle errors at sensible boundaries.

Error messages must be specific:

```text
AssetNotFoundError:
Scene 'scene_004' references missing character asset:
assets/characters/rith_scared.png
```

---

# Scope limitations (do NOT implement in V1)

Advanced skeleton rigging; AI-generated 3D meshes; real Khmer phoneme recognition; full viseme lipsync; motion capture; Cycles rendering; complex physics; cloud/multiplayer rendering; web frontend; database; auth; user accounts.

Focus on making the local JSON-to-video pipeline excellent.

---

# Implementation order

**Phase 1** — skeleton; Pydantic models; JSON loader; schema emit; asset validator; timing-mode reconciliation; CLI `validate`/`info`; tests. Make Phase 1 fully working first.

**Phase 2** — timeline; compositor; static layer rendering; numbered PNG frames; single-process smoke render.

**Phase 3** — camera movement; easing; parallax; transitions.

**Phase 4** — character semantic motion; fog; vignette; grain (seeded); other effects.

**Phase 5** — audio model; FFmpeg encoding; narration/music/ambience/SFX.

**Phase 6** — render manifest + per-scene hashing; resume; range rendering; preview; scene-only rendering; **parallel rendering + static-frame dedupe + determinism tests**.

**Phase 7** — demo asset generator; example project; README; final tests/refactoring.

Do not jump to later phases while fundamental architecture is broken.

---

# First deliverable (must work)

```bash
python -m cartoon_studio.cli create-demo
python -m cartoon_studio.cli validate projects/example_forest_story.json
python -m cartoon_studio.cli render-scene projects/example_forest_story.json scene_001 --preview
python -m cartoon_studio.cli render projects/example_forest_story.json --preview
python -m cartoon_studio.cli encode projects/example_forest_story.json
```

Result: `output/example_forest_story/final.mp4` containing animated 2.5D scenes, camera motion, parallax, effects, and narration/audio when provided.

---

# Acceptance criteria (V1 complete only when)

1. JSON fully controls the video.
2. No Python source edit is required to create another story.
3. A new story = new JSON + assets only.
4. Missing assets fail before rendering.
5. Scene preview works.
6. Full render creates numbered PNG frames.
7. Interrupted rendering resumes correctly (per-scene invalidation).
8. FFmpeg creates MP4 from the frame sequence.
9. Camera motion is smooth.
10. Parallax is visibly working.
11. Long projects do not keep all frames in RAM.
12. Frame rendering runs in parallel across CPU cores.
13. Identical consecutive frames are not needlessly recomputed.
14. Output is deterministic for a fixed seed, including across resume and worker count.
15. Narration and scene durations are reconciled per the timing mode.
16. Example project works from a clean install.
17. Tests pass.
18. Core architecture can accept a future `BlenderRenderer` with human-friendly JSON kept independent of Blender internals.

---

# Development behavior

Before writing code: inspect the existing repository; do not delete/rewrite unrelated files; identify existing conventions; reuse suitable utilities; briefly explain the files you intend to add/change; then implement.

Do not stop after an architecture proposal — actually implement the working V1. Run tests after each meaningful phase and fix failures instead of merely reporting them.

After implementation, report:

```text
Implemented
Changed files
Commands to run
Tests performed
Known V1 limitations
Recommended V2
```

For V2, recommend adding Blender as:

```text
JSON → Director → BlenderRenderer → .blend scene
→ Blender background render → PNG sequence → FFmpeg → MP4
```

Even in V2, continue using image-sequence rendering rather than directly rendering the final MP4.
