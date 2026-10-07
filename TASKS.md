# Autonomous production-pipeline checklist

[!] P0 baseline and recovery audit — blocked: Python suite passes (16 tests), but KIKO_master_v001.blend, KIKO_blockout_v001.blend, and KIKO_master_v001.blend1 are zero-byte lost artifacts (SHA-256 e3b0c442…); human recovery/source artifact required
[x] P1 story schema and asset system — acceptance: schema/validation tests pass; CLI validates the canonical sample and rejects a missing referenced asset before rendering
[x] P2 2.5D render and parallax — acceptance: a preview scene renders numbered PNG frames and a measured foreground/background displacement differs across frames
[x] P3 audio integration — acceptance: audio model/timing tests pass and a preview encode contains an audio stream when project audio is supplied
[x] P4 lip-sync and Khmer subtitles — acceptance: deterministic amplitude mouth cues and UTF-8 Khmer subtitle export are covered by tests; phoneme-accurate alignment remains explicitly labeled external
[x] P5 composite and export — acceptance: effects/compositing tests pass and FFmpeg produces a playable H.264 MP4 from rendered frames
[x] P6 CLI, samples, resume, determinism, and docs — acceptance: documented CLI workflow runs; resume/dedupe/worker-count determinism tests pass; README matches verified behavior
[x] P7 full pipeline acceptance — acceptance: full test suite passes from a clean work directory and the canonical sample validate/render/encode workflow succeeds
[!] KIKO-Z verify fixed tail/arm z-order — blocked: KIKO_master_v001.blend is zero bytes, so no scene graph exists to inspect; restore the real .blend without overwriting this recovery checkpoint
[!] KIKO-MAT confirm MAT_freckle — blocked: source builder declares MAT_freckle, but KIKO_master_v001.blend is zero bytes so material presence/assignment in the recovered artifact cannot be verified
[!] KIKO-TURN smoke-test .blend turntable — blocked: all tracked .blend files are zero bytes; a real recovered Blender artifact is required before a non-fabricated turntable smoke render

External broadcast-quality gates (not actionable without supplied production inputs): approved final character/background art, final narration/TTS, and a phoneme-accurate Khmer aligner.
