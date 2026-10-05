# Cartoon Studio

Cartoon Studio turns human-friendly JSON into a recoverable PNG sequence and then an MP4. V1 is a deterministic, multiprocessing 2D/2.5D renderer for narration-led stories: layered art, semantic camera moves, parallax, sprite motion, transitions, effects, and FFmpeg audio mixing. It deliberately does not implement skeletal 3D or Khmer phoneme lip sync.

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
```

The demo creates original placeholder forest, tree, character, ghost and fog PNGs plus synthetic WAV audio. Then run:

```bash
cartoon-studio validate projects/example_forest_story.json
cartoon-studio info projects/example_forest_story.json
cartoon-studio render-scene projects/example_forest_story.json scene_001 --preview
cartoon-studio render projects/example_forest_story.json --preview
cartoon-studio encode projects/example_forest_story.json --preview
```

Full-resolution rendering omits `--preview`. Use `--workers N` to control processes (default: `CARTOON_STUDIO_WORKERS`, then CPU count), `--from 30 --to 45` for a time range, `--resume` after interruption, and `--force` when global render settings change. `--no-dedupe` disables static-frame reuse for debugging. `clean` removes that project's output. `schema` emits the schema generated directly from Pydantic:

```bash
cartoon-studio schema > schemas/project.schema.json
```

## JSON reference

The runnable [example project](projects/example_forest_story.json) is the canonical starting point. A project defines format version, title/mode/resolution/FPS/seed/timing mode, defaults, project audio, and scenes. Each scene defines a positive duration, background, depth-sorted layers, semantic camera, characters, effects, audio clips and transition. Unknown keys and unsupported enum values fail validation.

JSON positions are normalized. `x` runs left to right (`0.0` = left, `1.0` = right); `y` runs top to bottom (`0.0` = top, `1.0` = bottom). This convention applies to positions and anchors everywhere. Opacity and depth are also in `[0, 1]`. Image scale modes are `contain`, `cover`, `stretch`, and `native`.

Camera movements are `static`, `slow_push`, `slow_pull`, pans, drifts, and `handheld_subtle`; easing supports `linear`, `ease_in`, `ease_out`, and `ease_in_out`. Character actions are semantic (`idle`, breathing, walking, looking, shake, float, fades). Effects include vignette, fog, grain, fade, flash, shake, darken and desaturate. Transitions are cut, crossfade and fade-to-black.

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
pytest
python -m cartoon_studio.cli schema > schemas/project.schema.json
```

Optional amplitude-based mouth assets are represented in the schema, but V1 does not perform phoneme/viseme analysis. Advanced rigs, physics, cloud rendering, GUI/web UI, accounts, and databases are out of scope.
# sh-cartoon-maker
