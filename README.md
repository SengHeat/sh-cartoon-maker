# Cartoon Studio

## Modular Blender characters

The existing 2D/2.5D renderer remains unchanged. A separate Blender pipeline builds
TEST_DUMMY from individual smooth-shaded mesh objects attached to a conventional armature,
then applies semantic JSON actions (never raw bone rotations).

Validate and render the 15-second example with:

```bash
cartoon-studio render-blender stories/test_dummy.json
```

For a faster 854x480 render, add `--preview`. To generate only the inspectable
`scene.blend`, add `--blend-only`. Blender 4.0 or newer is expected. Set
`CARTOON_STUDIO_BLENDER=/path/to/blender` when `blender` is not on `PATH`.

Outputs are written to `output/test_dummy/scene.blend` and
`output/test_dummy/final.mp4`.

Cartoon Studio turns human-friendly JSON into rendered animation. The original pipeline remains a deterministic, multiprocessing 2D/2.5D renderer; the Blender pipeline adds modular skeletal 3D characters and semantic actions. Khmer phoneme lip sync is not implemented.

```text
JSON → Pydantic validation → Director → BaseRenderer
                                      └─ ImageRenderer (Pillow)
                 PNG sequence → FFmpegEngine → H.264/AAC MP4
```

## Install

Python 3.12+ and FFmpeg are required. On macOS, install FFmpeg with `brew install ffmpeg`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cartoon-studio create-demo
cartoon-studio create-demo --full
```

The basic demo creates a forest story and synthetic WAV audio. `create-demo --full` additionally creates the documented 20-character placeholder catalog, environments, props, overlays, effects, audio, per-character manifests, and a root asset manifest without replacing existing real artwork. Then run:

```bash
cartoon-studio validate projects/example_forest_story.json
cartoon-studio info projects/example_forest_story.json
cartoon-studio contact-sheet projects/example_forest_story.json
cartoon-studio render-scene projects/example_forest_story.json scene_001 --preview
cartoon-studio render projects/example_forest_story.json --preview
cartoon-studio encode projects/example_forest_story.json --preview
cartoon-studio render projects/example_puppet_talk.json --preview
cartoon-studio encode projects/example_puppet_talk.json
```

Full-resolution rendering omits `--preview`. Use `--workers N` to control processes (default: `CARTOON_STUDIO_WORKERS`, then CPU count), `--from 30 --to 45` for a time range, `--resume` after interruption, and `--force` when global render settings change. `--no-dedupe` disables static-frame reuse for debugging. `clean` removes that project's output. `schema` emits the schema generated directly from Pydantic:

```bash
cartoon-studio schema > schemas/project.schema.json
```

## JSON reference

The intact [KIKO 2.5D project](projects/kiko_2d_test.json) is the currently verified starting point. The forest example is retained for recovery work, but several of its referenced image files are presently zero-byte lost artifacts and it intentionally fails render preflight until those real assets are restored. A project defines format version, title/mode/resolution/FPS/seed/timing mode, defaults, project audio, and scenes. Each scene defines a positive duration, background, depth-sorted layers, semantic camera, characters, effects, audio clips and transition. Unknown keys and unsupported enum values fail validation.

JSON positions are normalized. `x` runs left to right (`0.0` = left, `1.0` = right); `y` runs top to bottom (`0.0` = top, `1.0` = bottom). This convention applies to positions and anchors everywhere. Character positions default to a bottom-center feet pivot; other layers default to their center. Opacity and depth are also in `[0, 1]`. Image scale modes are `contain`, `cover`, `stretch`, and `native`.

Camera movements are `static`, `slow_push`, `slow_pull`, pans, drifts, and `handheld_subtle`; easing supports `linear`, `ease_in`, `ease_out`, and `ease_in_out`. Character actions remain semantic (`idle`, breathing, walk/run, look/turn/nod, point/wave, sit/stand/fall/take, shake, float, fades). A character folder may opt into `rig.json` cut-out animation or `anim/<action>/` numbered frames (packed PNG plus frame-index JSON is also supported). `dialogue_audio` drives deterministic closed/small/wide mouth swaps, while `auto_blink` controls seeded blink and idle sway. Plain V1 sprites remain supported. Effects include vignette, fog, grain, fade, flash, shake, darken and desaturate. Transitions are cut, crossfade and fade-to-black.

`narration_driven` uses WAV narration length as total runtime and proportionally reconciles scene duration hints. `scenes_driven` uses the scene sum; shorter narration leaves silence, while longer narration fails rather than being truncated. WAV duration is read without FFmpeg during validation.

## Recovery, performance, and determinism

Frames are `frame_000001.png`, etc. A render manifest records settings, hashes each scene plus referenced asset contents/metadata, and tracks completion. Resume validates PNGs and rerenders only changed scene ranges; FPS, resolution, seed, format or frame-count changes require `--force`. Frames render independently in a process pool, each process owns a bounded image cache, and no full sequence is held in memory. Consecutive equal render signatures use hardlinks (or copies). Random grain is a pure function of seed and frame number, so resumed and differently parallelized renders match.

## Extending

Add camera semantics in `presets/camera.py` and translate them in `CameraEngine`. Add an effect enum/model, then its pixel implementation in `EffectEngine`. Keep low-level transforms out of story JSON.

A future renderer should implement `BaseRenderer` and preserve the flow:

```text
JSON → Director → BlenderRenderer → .blend scene
→ Blender background render → PNG sequence → FFmpeg → MP4
```

Even with Blender, image sequences remain the recovery boundary; Blender-specific paths, bones, shaders, or matrices do not enter the core project format.

## Development

```bash
python3 -m pytest
python -m cartoon_studio.cli schema > schemas/project.schema.json
```

Optional amplitude-based mouth assets are represented in the schema, but V1 does not perform phoneme/viseme analysis. Advanced rigs, physics, cloud rendering, GUI/web UI, accounts, and databases are out of scope.
# sh-cartoon-maker
