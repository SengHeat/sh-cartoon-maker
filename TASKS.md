# Autonomous production-pipeline checklist

[!] P0 baseline and recovery audit — blocked: Python suite passes (16 tests), but KIKO_master_v001.blend, KIKO_blockout_v001.blend, and KIKO_master_v001.blend1 are zero-byte lost artifacts (SHA-256 e3b0c442…); human recovery/source artifact required
[x] P1 story schema and asset system — acceptance: schema/validation tests pass; CLI validates the canonical sample and rejects a missing referenced asset before rendering
[x] P2 2.5D render and parallax — acceptance: a preview scene renders numbered PNG frames and a measured foreground/background displacement differs across frames
[x] P3 audio integration — acceptance: audio model/timing tests pass and a preview encode contains an audio stream when project audio is supplied
[x] P4 lip-sync and Khmer subtitles — acceptance: deterministic amplitude mouth cues and UTF-8 Khmer subtitle export are covered by tests; phoneme-accurate alignment remains explicitly labeled external
[ ] P5 composite and export — acceptance: effects/compositing tests pass and FFmpeg produces a playable H.264 MP4 from rendered frames
[ ] P6 CLI, samples, resume, determinism, and docs — acceptance: documented CLI workflow runs; resume/dedupe/worker-count determinism tests pass; README matches verified behavior
[ ] P7 full pipeline acceptance — acceptance: full test suite passes from a clean work directory and the canonical sample validate/render/encode workflow succeeds
[ ] KIKO-Z verify fixed tail/arm z-order — acceptance: automated inspection of KIKO_master_v001.blend confirms the expected fixed relative tail/arm ordering, not an older snapshot
[ ] KIKO-MAT confirm MAT_freckle — acceptance: automated Blender inspection confirms MAT_freckle exists and is assigned to freckle geometry
[ ] KIKO-TURN smoke-test .blend turntable — acceptance: a low-resolution turntable frame rendered from a protected copy is non-empty and visually inspectable

External broadcast-quality gates (not actionable without supplied production inputs): approved final character/background art, final narration/TTS, and a phoneme-accurate Khmer aligner.
