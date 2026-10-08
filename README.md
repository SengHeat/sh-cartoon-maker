# Cartoon Studio

## KIKO V1.1 JSON animation engine

`kiko_engine.py` is the reusable Blender entry point. Edit scene JSON instead of
creating animation scripts. Run from this project (asset/output paths are always
relative to the engine's project root):

```bash
blender --background --python kiko_engine.py -- scenes/run_test_5s.json
# Only after the gate passes:
blender --background --python kiko_engine.py -- scenes/run_60s.json
blender --background --python kiko_engine.py -- scenes/run_with_gestures_demo.json
```

Requires Blender with EEVEE (developed on 5.2), FFmpeg with libx264, and
FFprobe on PATH. No extra Python packages. All fields below are required except
`gestures`; unknown fields, duplicate JSON keys, invalid types and unsupported
values are errors. The printed error names the field. A run's stride, speed and
cycle length are coupled: **root_speed = stride_length × fps / loop_frames**.
For example, 1.2 units over 28 frames at 24 fps requires 1.0285714286 units/sec.
Use that relationship when editing; arbitrary independent values cause sliding.

| JSON field | Control and accepted range |
| --- | --- |
| `scene.duration_sec` | 0.1–600 seconds; duration × fps must be an integer. |
| `scene.fps` | Integer 12–60; examples use 24. |
| `scene.resolution` | `[width,height]`, even integers 64–3840. Gate: `[854,480]`; long: `[1920,1080]`. |
| `scene.samples` | EEVEE render samples, integer 1–256; 32 preview, 48 final suggested. |
| `scene.engine` | `"EEVEE"` only. |
| `environment.ground` | Boolean; neutral ground plane at Z=0. Subtle fixed tiles reveal forward travel. |
| `environment.background` | `"neutral"` studio world only. |
| `camera.type` | `"tracking"` follows target's linear travel; `"static"` stays at its initial position. |
| `camera.target` | An existing character ID. |
| `camera.angle` | `"side"`, `"3-4"`, `"front"`, relative to target's facing. |
| `camera.distance` | Horizontal distance in Blender units, 4–500; 8.8 frames this model at 16:9. |
| `camera.height` | World height above ground, 0.2–50; suggested 1.7. Camera aims at target height 1.6. |
| `characters` | Array of 1–8 independent instances of the existing KIKO model. |
| `characters[].id` | Unique lowercase identifier, 1–32 letters/digits/underscores, starting with a letter. |
| `characters[].model` | `"KIKO_master_v1_1.blend"` only, loaded from project root. |
| `characters[].armature` | `"KIKO_RIG_armature"` only. |
| `characters[].position` | `[x,y,z]` in Blender units; X/Y −1000…1000; Z must be 0 for flat-ground locomotion. |
| `characters[].facing` | `"east"` +X, `"west"` −X, `"north"` +Y, `"south"` −Y. Source rig faces −Y. |
| `characters[].action.type` | `"run"`, `"walk"`, `"idle"`; distinct contact fractions/lift, or planted idle breathing. |
| `characters[].action.loop_frames` | Even integer 12–120, one full left/right cycle. Suggested run 28, walk 36–48. |
| `characters[].action.stride_length` | Distance per full cycle: run >0…1.6, walk >0…1.0, idle 0. Suggested run 1.2. |
| `characters[].action.root_speed` | Units/sec, 0–4, must satisfy stride equation; idle 0. |
| `characters[].action.pelvis_bounce` | Vertical excursion, 0–0.15 units; 0.04–0.08 suggested. Excess can exceed leg reach and fail verification. |
| `characters[].action.forward_lean_deg` | Forward spine lean, 0–18 degrees; suggested 8. |
| `characters[].action.squash_stretch` | Chest scale modulation, 0–0.1; suggested 0.03. Does not scale planted feet. |
| `characters[].secondary.ears.bones` | Exactly `["ear_01","ear_02","ear_03"]`; expands to both L/R chains. |
| `characters[].secondary.ears.delay_frames` | Ear root delay, 0…half the loop length; suggested 3. Each child adds one frame. |
| `characters[].secondary.ears.bounce` | Ear rotation amplitude in radians, 0–0.4; suggested 0.12. Zero disables it. |
| `characters[].secondary.tail.bones` | `["tail_01..tail_06"]` or the explicit ordered six bone names. |
| `characters[].secondary.tail.delay_frames` | Tail root delay, 0…half the loop length; suggested 5. Each child adds one frame. |
| `characters[].secondary.tail.follow_through` | Tail strength, 0–0.4; suggested 0.2. Applied per segment at 0.45× strength. Zero disables it. |
| `characters[].face.expression` | `"neutral"`, `"happy"`, `"surprised"`; existing smile shape and mouth-swap meshes, with source brow/eye expression values. |
| `characters[].face.blink` | Boolean; repeats the existing upper-lid arch motion every 3 seconds. This asset has no fully closing eyelid surface. |
| `characters[].gestures` | Optional array. Missing or `[]` gives base motion only. Overlapping gestures add together. |
| `characters[].gestures[].type` | `nod`, `head_turn`, `look_around`, `wave`, `point`, `crouch`, `body_turn`, `ear_flick`, `tail_flick`. |
| `characters[].gestures[].start_sec` | Start ≥0, within the scene; time 0 is frame 1. Fractional frame starts supported. |
| `characters[].gestures[].duration_sec` | At least 4 frames, and must end within scene duration. Suggested 0.6–2 seconds. |
| `characters[].gestures[].intensity` | 0–1; suggested 0.6. Zero is a no-op. |
| `characters[].gestures[].ease` | `"smooth"`: 25% fade at each end; `"sharp"`: 10% fade. Both use smoothstep, zero at endpoints. |
| `output.mp4_path` | Relative `output/<name>.mp4` path; no traversal/escaping symlinks. |
| `output.save_blend` | Boolean; save inspectable scene with repaired weights and all NLA layers. |

Gestures are additive NLA deltas, preserving the underlying run swing. Nod and
gaze use head/neck; wave and point use the right clavicle, arm and whole paw;
crouch lowers pelvis and lets the existing thigh/shin IK solve; body turn is a
temporary pelvis twist; flicks use the existing ear/tail chains. The asset's
CTRL_root/CTRL_COG/CTRL_head and eye_aim are disconnected, and its finger/eye
bones have no skin weights. Therefore independent finger pointing and eye aiming
are not exposed or claimed. A dormant jaw exists in the file but is never used.
There are no visemes, speech controls, or rig/model rebuilds.

The engine audits every loaded instance and repairs the source's inappropriate
shoulder, hip, neck and sole influences in the generated scene. It preserves the
source `.blend`, geometry, rest skeleton, and materials. Existing leg IK is
calibrated to bend forward; two orientation constraints keep the existing paw
soles parallel to the ground. A single sampled cycle repeats in NLA; root travel
has just two keys regardless of duration. No 1,440-frame hand-keyed animation.

For `output/kiko_run_test_5s.mp4`, artifacts go in `output/kiko_run_test_5s/`:
`rig_audit.json`, `scene.blend` (if enabled), `frames/frame_000001.png`,
`verification.json`, and `contact_sheet.jpg`. The gate encodes exactly 120 frames
at 24 fps, H.264/yuv420p, lasting 5 seconds. Contact-sheet requests are
0/0.5/1/2/3/4/5 seconds; since 5.0 is the exclusive endpoint, that last tile uses
frame 120 (4.958 seconds), explicitly labelled in the sheet and report.

Verification measures evaluated subdivided sole/toe vertices during stance,
ground clearance/contact, IK reach, forward knee bend, hip weight transfer,
arm/leg opposition, loop closure and secondary delays. It checks every half
frame for shots up to 240 frames; longer shots sample two cycles, all gesture
windows and the ending. It also probes the encoded file. Tolerances and measured
values appear in the report; visual review of the contact sheet is still needed
for artistic quality, intersections and silhouette. A critical failure produces
`FAIL` and a nonzero exit; do not proceed to long/demo rendering.

Other run renders require a matching `PASS` in the supplied gate's verification
file. Engine code, source model, FPS, base action or secondary changes invalidate
the gate; update and rerun the 5-second JSON first. Resolution, duration, camera,
face and gestures may change after the base gate. Accepted numeric ranges are
input limits, not a guarantee that every combined pose is physically reachable.

Frames are cleared idempotently only inside a marked engine-owned directory;
unrecognized files cause an error instead of being deleted. Missing FFmpeg prints
the exact encoding command and stops before expensive rendering. Saved frames
remain available if encoding fails. Diagnostic commands use the same engine:

```bash
blender --background --python kiko_engine.py -- scenes/run_test_5s.json --audit-only
blender --background --python kiko_engine.py -- scenes/run_test_5s.json --build-only
python3 -m unittest discover -s tests -p test_kiko_engine.py -v
blender --background --python tests/test_kiko_engine_blender.py
```

`--build-only` runs the audit and motion checks and saves the scene; it does not
render or qualify as a passed video gate.

The tests cover JSON rejection and output-directory protection, independent
character instances, additive gesture deltas/endpoints, visible wave height,
face selection, two-key root travel, walk/idle motion, and all gesture bone maps.

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
