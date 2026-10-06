# Autonomous production-pipeline checklist

[ ] P0 baseline and recovery audit — acceptance: the full Python test suite passes and protected Blender files are present, non-empty, and checksummed
[ ] P1 story schema and asset system — acceptance: schema/validation tests pass; CLI validates the canonical sample and rejects a missing referenced asset before rendering
[ ] P2 2.5D render and parallax — acceptance: a preview scene renders numbered PNG frames and a measured foreground/background displacement differs across frames
[ ] P3 audio integration — acceptance: audio model/timing tests pass and a preview encode contains an audio stream when project audio is supplied
[ ] P4 lip-sync and Khmer subtitles — acceptance: deterministic amplitude mouth cues and UTF-8 Khmer subtitle export are covered by tests; phoneme-accurate alignment remains explicitly labeled external
[ ] P5 composite and export — acceptance: effects/compositing tests pass and FFmpeg produces a playable H.264 MP4 from rendered frames
[ ] P6 CLI, samples, resume, determinism, and docs — acceptance: documented CLI workflow runs; resume/dedupe/worker-count determinism tests pass; README matches verified behavior
[ ] P7 full pipeline acceptance — acceptance: full test suite passes from a clean work directory and the canonical sample validate/render/encode workflow succeeds
[ ] KIKO-Z verify fixed tail/arm z-order — acceptance: automated inspection of KIKO_master_v001.blend confirms the expected fixed relative tail/arm ordering, not an older snapshot
[ ] KIKO-MAT confirm MAT_freckle — acceptance: automated Blender inspection confirms MAT_freckle exists and is assigned to freckle geometry
[ ] KIKO-TURN smoke-test .blend turntable — acceptance: a low-resolution turntable frame rendered from a protected copy is non-empty and visually inspectable

External broadcast-quality gates (not actionable without supplied production inputs): approved final character/background art, final narration/TTS, and a phoneme-accurate Khmer aligner.
