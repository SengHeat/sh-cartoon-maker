
# KIKO MASTER IMPLEMENTATION PLAN
## Autonomous Codex Execution — Step-by-Step

**Project root**

`/Users/macbook/Automation-Workplace/cartoon-maker`

**Primary goal**

Build a production-ready KIKO pipeline for polished stylized 3D YouTube animation, while preserving proven engineering work and replacing only weak visual assets where necessary.

This file is both:
1. the project roadmap; and
2. the execution instruction for Codex.

---

# 0. AUTONOMOUS EXECUTION RULES

Codex must execute this plan **step by step in order**.

For normal work inside the project, Codex is authorized to:
- inspect files
- read code
- edit code
- create files
- create Blender `.blend` files
- create Python scripts
- run Blender headless
- render previews
- run tests
- create reports
- create backups
- create directories
- modify project-local configuration
- use FFmpeg
- replace generated outputs
- fix discovered project-local issues
- retry failed builds
- refactor project-local code when required for the current step

**Do not ask the user yes/no questions before each step.**

Do not stop merely because a task is large.

Do not stop after only writing code. Run it, inspect the result, verify it, and continue to the next gate when it passes.

Only stop and report when one of these is true:
- a required source asset is genuinely missing
- an external account/login/license is required
- an operation would destroy unrelated user data outside this project
- a technical limitation makes the requested result unreliable
- a quality gate fails after reasonable repair iterations
- a tool/runtime is unavailable

When a gate fails:
1. diagnose the cause
2. fix the largest problem
3. rerun
4. inspect again
5. repeat for a reasonable number of iterations
6. stop only if the method itself is clearly unsuitable

Never hide a failed gate.
Never claim completion just because code executed.

---

# 1. GLOBAL SAFETY / BACKUP RULES

Before modifying an important working `.blend` file:
- make a backup
- never overwrite the last known-good master
- use versioned outputs

Protected assets include:
- `KIKO_master_v1_1.blend`
- existing successful animation/test scenes
- rejected-clay archive
- current working animation engine

Recommended version naming:
- `KIKO_master_v2.blend`
- `KIKO_master_v3_visual.blend`
- `KIKO_run_test_5s.blend`
- `KIKO_acting_test_8s.blend`

Do not delete rejected work unless the user explicitly requests cleanup.

---

# 2. AUTHORITATIVE KIKO VISUAL TARGET

The authoritative KIKO concept is the existing project reference, expected at:

`assets/hero/kiko.png`

Target visual direction:
- high-quality stylized 3D
- cute premium adventure character
- fennec-cat / gremlin hybrid
- large expressive amber eyes
- broad organic ears
- warm orange/pink inner ears
- fluffy cream cheeks/muzzle
- dramatic messy mohawk/crest
- teal/gray body fur
- cream chest/muzzle
- orange/red scarf accents
- compact small adventurer body
- furry paws
- large fluffy striped plume tail
- layered weathered explorer clothing
- backpack / straps / pouches / charms
- cinematic but stylized, not photoreal

Do not interpret the target as smooth plastic or low-poly toy styling.

---

# 3. CURRENT COMPLETED WORK

## 3.1 Blender / Project Foundation — COMPLETED

Existing project already has:
- Blender 5.2 LTS workflow
- Python/headless workflow
- render pipeline
- FFmpeg/video workflow
- scene/camera/light automation
- animation architecture

Do not rebuild these unless a current step exposes a real defect.

## 3.2 Animation Core V2 — COMPLETED

Existing engineering includes:
- locomotion phases: CONTACT, DOWN, PASSING, UP, AIRBORNE
- root/body/head channels
- eye control
- arm channels
- tail channels
- run/walk foundation
- camera support

Preserve working APIs and naming where practical.

## 3.3 KIKO V1.1 Technical Character — COMPLETED

Existing technical KIKO includes a working rig suitable for engineering tests.

Known rig concepts include:
- `KIKO_RIG_armature`
- pelvis
- spine
- chest
- neck
- head
- arm chains
- finger chains
- leg chains
- IK feet
- knee poles
- eye aim
- ear chains
- tail chain

A previous 10-second motion test succeeded.

**Important:** this technical character is acceptable for locomotion engineering, but not the final visual-quality KIKO.

## 3.4 Runaway Fruit Technical Scene — COMPLETED

Existing work includes:
- approximately 30-second story structure
- fruit action
- cameras
- jungle environment
- lighting
- 1080p rendering
- technical scene proof

Do not treat the current visual quality as final production quality.

## 3.5 Procedural Visual Rebuild Experiment — CLOSED / REJECTED

The procedural sculpt/blockout method failed the likeness gate.

Rejected archive exists under:

`backups/rejected_kiko_clay_v001`

Do not use those meshes as the production visual base.
Do not resume procedural primitive-based sculpting and pretend it is final character art.

---

# 4. EXECUTION ORDER

Codex must work through the following stages in sequence.

---

# STAGE 1 — PROJECT AUDIT

## Goal

Confirm actual current files and working assets before modifying anything.

## Tasks

1. Inspect project root.
2. Locate:
   - `KIKO_master_v1_1.blend`
   - working KIKO rig
   - current animation scripts
   - Animation Core V2 code
   - existing test outputs
   - `assets/hero/kiko.png`
   - rejected archive
3. Inspect `.blend` metadata where practical.
4. Identify:
   - exact armature name
   - existing bone names
   - existing controls
   - existing shape keys
   - existing actions
   - existing weight/deformation issues
5. Create:

`reports/kiko_project_audit.md`

## Gate

PASS only if the actual source files required for Stage 2 are located.

If file names differ from this plan, use the real project paths and document them.

---

# STAGE 2 — 5-SECOND RUN LOCOMOTION GATE

## Goal

Prove the existing KIKO rig and procedural locomotion can produce a believable run.

## Do Not

- rebuild KIKO visually
- rebuild the armature
- create a 30s/60s video
- spend time on final materials
- build a detailed environment

## Target

- 5 seconds
- 24 FPS
- 120 frames
- 854 × 480 preview

## Required run behavior

- clear contact
- down
- passing
- up
- airborne
- opposite contact
- alternating legs
- opposing arm swing
- pelvis vertical movement
- pelvis rotation
- chest counter-rotation
- slight forward lean
- stable readable head
- no obvious foot sliding
- no foot penetration
- correct knee bending
- ear secondary bounce
- delayed tail follow-through

## Environment

Only:
- neutral background
- ground plane
- simple lighting
- side or 3/4 tracking camera

## Output

Create:
- `KIKO_run_test_5s.blend`
- `output/kiko_run_test_5s/preview.mp4`
- `output/kiko_run_test_5s/contact_sheet.jpg`
- `output/kiko_run_test_5s/verification.json`

## Verification JSON must include

- duration
- FPS
- frame count
- cycle length
- approximate stride length
- approximate root speed
- contact frames
- tail delay
- ear delay
- known deformation issues
- preview path
- contact sheet path
- pass/fail

## Gate

PASS only if:
- loop is visually readable
- feet do not visibly slide during stance
- no major leg deformation collapse
- body weight transfer exists
- arms oppose legs
- ears and tail have delayed motion

If deformation problems appear, fix the relevant weights/constraints first and rerender.

Do not continue to Stage 3 until this passes.

---

# STAGE 3 — KIKO V2 EXPRESSIVE RIG

## Goal

Extend the existing V1.1 rig into a production-capable acting rig.

This is an **additive upgrade**.

## Source

Use the real located V1.1 master from Stage 1.

Expected source:

`KIKO_master_v1_1.blend`

## Output

`KIKO_master_v2.blend`

Never overwrite V1.1.

## Preserve

Keep the existing body rig, weights, and animation compatibility.

Do not rebuild working body chains.

## Add body animator controls only if missing

Possible helpers:
- `CTRL_chest`
- `CTRL_pelvis`
- `CTRL_shoulder_L`
- `CTRL_shoulder_R`
- `CTRL_hand_L`
- `CTRL_hand_R`
- `CTRL_tail_base`
- `CTRL_tail_tip`
- `CTRL_ear_L`
- `CTRL_ear_R`

Use constraints to drive existing deform bones where practical.

## Add facial rig

Required:
- jaw
- `CTRL_jaw`
- `mouth_corner_L`
- `mouth_corner_R`
- `lip_upper`
- `lip_lower`

Useful if practical:
- `cheek_L`
- `cheek_R`
- `brow_L`
- `brow_R`
- upper/lower eyelid controls

## Mouth requirements

Support:
- mouth closed
- mouth open
- smile
- frown
- wide smile
- surprise
- scared
- angry
- sad

Avoid:
- floating lips
- jaw detachment
- teeth clipping
- cheek collapse
- mouth mesh tearing

## Viseme shape keys

Create a usable base set:
- `Basis`
- `VIS_REST`
- `VIS_AA`
- `VIS_EE`
- `VIS_IH`
- `VIS_OH`
- `VIS_OO`
- `VIS_MBP`
- `VIS_FV`
- `VIS_L`

Optional useful shapes:
- `VIS_TH`
- `VIS_CH`
- `VIS_SS`

Do not build Khmer lip-sync animation yet.

## Eye acting

Verify:
- both eyes aim correctly
- blink
- squint
- no cross-eye bug
- head rotation does not break aim

## Ear acting

Support:
- neutral
- alert
- relaxed
- frightened/back
- asymmetric expression
- bounce

## Tail acting

Support:
- relaxed
- happy wag
- scared tuck
- alert raise
- angry/stiff
- run follow-through

## Hand acting

Verify:
- relaxed
- open
- fist
- point
- grip
- wave

## Pose library

Create reusable validation poses/actions.

### Body
- `POSE_neutral`
- `POSE_confident`
- `POSE_scared`
- `POSE_angry`
- `POSE_curious`
- `POSE_surprised`
- `POSE_happy`
- `POSE_sad`
- `POSE_crouch`
- `POSE_point`
- `POSE_wave`

### Face
- `FACE_neutral`
- `FACE_happy`
- `FACE_surprised`
- `FACE_angry`
- `FACE_sad`
- `FACE_curious`
- `FACE_scared`

## Validation output

Create:
- `review/kiko_v2_rig/neutral.png`
- `review/kiko_v2_rig/smile.png`
- `review/kiko_v2_rig/mouth_open.png`
- `review/kiko_v2_rig/surprised.png`
- `review/kiko_v2_rig/angry.png`
- `review/kiko_v2_rig/sad.png`
- `review/kiko_v2_rig/curious.png`
- `review/kiko_v2_rig/scared.png`
- `review/kiko_v2_rig/wave_full_body.png`
- `review/kiko_v2_rig/crouch_full_body.png`
- `review/kiko_v2_rig/validation_contact_sheet.jpg`
- `output/kiko_v2_rig_test/verification.json`

## Gate

PASS only if:
- previous body rig still works
- no major shoulder collapse
- no major hip collapse
- no neck collapse
- jaw works
- mouth controls work
- blink works
- expressions are readable
- viseme shape keys exist
- run/walk compatibility remains intact

---

# STAGE 4 — 8-SECOND ACTING TEST

## Goal

Prove that KIKO can act, not only locomote.

## Target

- 8 seconds
- 24 FPS
- 192 frames
- 854 × 480 preview

## Sequence

- 0–1s: neutral idle
- 1–2s: curious head tilt + ears
- 2–3s: wave + smile
- 3–4s: point with torso gesture
- 4–5s: surprised face + open jaw + ears up
- 5–6s: scared crouch + ears back + tail tuck
- 6–7s: determined/confident pose
- 7–8s: happy celebration + tail movement

## Output

- `KIKO_acting_test_8s.blend`
- `output/kiko_acting_test_8s/preview.mp4`
- `output/kiko_acting_test_8s/contact_sheet.jpg`
- `output/kiko_acting_test_8s/verification.json`

## Gate

PASS only if body, head, eyes, face, ears, hands, and tail combine without major deformation failure.

---

# STAGE 5 — FINAL BEAUTIFUL KIKO VISUAL ASSET

## Goal

Replace the plastic/toy-looking visual shell with a production-worthy stylized visual asset.

## Critical Rule

Do **not** return to procedural primitive-based character sculpting as the main production method.

The previous procedural likeness approach failed.

## Preferred acquisition path

Use the strongest practical visual-base path available in the project.

### Option A — AI / image-to-3D base

`assets/hero/kiko.png`

→ image-to-3D base asset

→ import into Blender

→ cleanup

→ retopology

→ material/fur pass

→ fit existing rig

### Option B — manually supplied sculpt/model

If a good external KIKO model exists in the project, use it.

### If neither exists

Stop this stage and report exactly what source asset is missing.

Do not generate another obviously low-likeness primitive KIKO and call the stage complete.

## Visual target

Aim for approximately 75–85% design likeness to the KIKO concept.

Key identity features:
- large organic ears
- expressive amber eyes
- cream integrated muzzle
- fluffy cheeks
- strong messy crest
- compact torso
- short sturdy limbs
- furry paws/toes
- huge fluffy plume tail
- layered explorer outfit
- scarf
- backpack
- straps/pouches/trinkets

## Gate

Before rig transfer, create:
- `review/kiko_visual/front.png`
- `review/kiko_visual/three_quarter.png`
- `review/kiko_visual/side.png`
- `review/kiko_visual/back.png`
- `review/kiko_visual/face_closeup.png`
- `review/kiko_visual/contact_sheet.jpg`

PASS only when the character is clearly recognizable as the intended KIKO direction and no longer reads as a smooth plastic toy.

---

# STAGE 6 — FUR + MATERIALS

## Goal

Remove the rubber/plastic look.

## Fur strategy

Use a practical hybrid solution:

1. sculpt/model major fur silhouette into the mesh
2. add lightweight Hair Curves where useful

Priority areas:
- crest
- cheeks
- ears
- chest
- forearms
- calves
- tail

Do not use an unnecessarily dense groom that destabilizes the M2 Pro / 16 GB workflow.

## Materials

Create/upgrade:
- teal-gray fur
- cream fur
- orange accent fur
- ear interior
- eye white
- iris
- pupil
- nose
- teeth
- tongue
- scarf fabric
- worn leather
- backpack
- metal/charm details

## Shading goals

- appropriate fur roughness
- subtle roughness variation
- soft specular
- eye gloss only where appropriate
- cloth/leather separation
- subtle color breakup
- no toy-plastic sheen

## Gate

Rerender visual review sheet.

PASS only when plastic appearance is substantially removed.

---

# STAGE 7 — FIT EXISTING RIG TO FINAL VISUAL KIKO

## Goal

Reuse engineering work on the final visual asset.

## Rules

- visual proportions come first
- rig must adapt to the final mesh
- do not force the final mesh back into bad old proportions
- preserve control/action API where practical

## Tasks

1. duplicate/refit existing armature
2. adjust rest bone positions if required
3. transfer/rebuild weights only on the final mesh
4. restore IK
5. restore tail
6. restore ears
7. restore eye controls
8. restore facial rig
9. restore visemes
10. add corrective shape keys where needed

## Gate

Run static deformation QA before animation.

---

# STAGE 8 — DEFORMATION QA

## Required poses

Render/test:
- T-pose
- neutral
- crouch
- deep squat
- run contact
- run airborne
- jump prep
- landing
- wave
- point
- arms raised
- head turn
- scared
- happy
- angry
- mouth open
- smile

## Inspect carefully

- shoulders
- elbows
- wrists
- neck
- jaw
- cheeks
- hips
- knees
- ankles
- paws
- tail base
- ear roots

## Gate

Fix visible collapse/pinching before continuing.

---

# STAGE 9 — RE-RUN LOCOMOTION + ACTING TESTS ON FINAL KIKO

Repeat:
- 5-second run gate
- 8-second acting gate

using the final visual KIKO.

Create separate final-quality test outputs.

Do not assume old animation quality automatically transfers.

---

# STAGE 10 — KHMER LIP-SYNC FOUNDATION

## Goal

Make future Khmer dialogue possible.

## Pipeline

Khmer voice audio

→ phoneme/timing analysis

→ mapping to available visemes

→ viseme curves

→ jaw motion

→ lip motion

→ expression overlay

## Important

The initial system may use approximate viseme mapping.

Do not promise phoneme-perfect speech if the available analysis cannot reliably distinguish Khmer phonemes.

## Test

Create a short 5–10 second dialogue test only.

Verify:
- jaw timing
- closed consonants
- open vowels
- lip closure
- no mesh tearing
- expression remains usable while speaking

---

# STAGE 11 — FINAL CINEMATIC LOOK

## Goal

Upgrade the scene after the character itself is production-ready.

## Tasks

Improve:
- jungle composition
- foreground/background depth
- vegetation layering
- atmospheric fog
- contact shadows
- light softness
- warm/cool separation
- rim lighting
- environment scale
- color grading
- camera framing
- depth of field only where useful

Avoid:
- toy diorama look
- flat gray test lighting
- overbright plastic highlights
- clutter that hides KIKO

---

# STAGE 12 — 30-SECOND PRODUCTION TEST

## Goal

Use the final KIKO in a real short sequence.

Prefer reusing the Runaway Fruit structure where practical.

## Target

- 1920 × 1080
- 24 FPS
- 30 seconds
- H.264 review render

## Include

- run
- acting
- reactions
- ears
- tail
- facial expressions
- clear camera storytelling
- environment
- lighting
- sound-ready timing

## Output

- `output/kiko_production_30s/final.mp4`
- `output/kiko_production_30s/contact_sheet.jpg`
- `output/kiko_production_30s/verification.json`

## Gate

Review:
- character consistency
- deformation
- locomotion
- acting readability
- camera clarity
- visual quality
- render stability

---

# STAGE 13 — 60-SECOND EPISODE

Only start after the 30-second production gate passes.

Do not create a 60-second video by simply looping one run cycle with no storytelling.

Use a shot structure such as:

1. establish
2. discover
3. react
4. run/action
5. obstacle
6. close-up
7. emotional beat
8. payoff

Reuse cycles intelligently but vary:
- camera
- speed
- expressions
- pose
- environment
- timing
- story beat

## Target

- 1920 × 1080
- 24 FPS
- 60 seconds
- stable final MP4

---

# STAGE 14 — YOUTUBE PRODUCTION PIPELINE

After a successful 60-second episode, package reusable production tooling.

Create repeatable workflows for:
- story JSON
- scene generation
- animation assignment
- voice
- lip-sync
- camera
- render
- sound
- final MP4
- thumbnail/reference frame export

Document the final pipeline in:

`docs/KIKO_PRODUCTION_PIPELINE.md`

---

# 5. CODING / BLENDER QUALITY RULES

For generated Python/Blender code:
- make scripts idempotent where appropriate
- preserve versioned source assets
- avoid hardcoded paths when a project-relative path is practical
- log meaningful progress
- fail loudly on missing required assets
- do not silently substitute unrelated assets
- create verification/report files
- keep render tests lightweight before full-quality rendering
- do not render 1080p long sequences before short gates pass

---

# 6. RENDER STRATEGY

For engineering tests:
- 854 × 480
- Eevee
- lightweight samples
- simple environment

For production approval:
- 1920 × 1080
- Eevee or another stable project-approved renderer
- optimized samples
- final materials
- final lighting

Do not waste full-resolution render time on broken animation or broken deformation.

---

# 7. HARD FAILURE CONDITIONS

A stage must FAIL instead of being falsely marked complete when:
- output file is missing
- Blender crashes
- required source asset is missing
- KIKO mesh visibly collapses
- feet slide badly
- face rig tears
- jaw detaches
- tail penetrates body severely
- visual rebuild still looks like rejected primitive KIKO
- rendered video duration/FPS is wrong
- output is not inspectable
- verification was not actually run

---

# 8. FINAL EXECUTION CHECKLIST

Codex should maintain progress in:

`KIKO_IMPLEMENTATION_STATUS.md`

Use this format:

```md
# KIKO Implementation Status

- [x] Stage 1 — Project Audit
- [ ] Stage 2 — 5s Run Gate
- [ ] Stage 3 — V2 Expressive Rig
- [ ] Stage 4 — 8s Acting Test
- [ ] Stage 5 — Final Visual KIKO
- [ ] Stage 6 — Fur + Materials
- [ ] Stage 7 — Rig Fit
- [ ] Stage 8 — Deformation QA
- [ ] Stage 9 — Final Run + Acting Retest
- [ ] Stage 10 — Khmer Lip-sync
- [ ] Stage 11 — Cinematic Scene
- [ ] Stage 12 — 30s Production Test
- [ ] Stage 13 — 60s Episode
- [ ] Stage 14 — YouTube Pipeline
```

After every completed stage:
1. update status
2. record output paths
3. record failures/fixes
4. record gate result
5. continue automatically to the next stage if the gate passes

---

# 9. START COMMAND TO CODEX

**Execute this plan now from Stage 1.**

Do not ask for routine confirmation.

Do not ask “Do you want me to continue?” after each step.

Do not stop after writing code.

Inspect, implement, run, render, verify, fix, and continue.

Preserve backups.

Respect all gates.

If a gate cannot be passed with the current method, stop at that gate and report the exact technical limitation, evidence, generated files, and recommended next input needed.
