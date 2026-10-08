# KIKO engineering gates

These commands implement Stages 1–4 of `KIKO_MASTER_IMPLEMENTATION_PLAN.md`.
The master plan and `KIKO_IMPLEMENTATION_STATUS.md` remain authoritative for
which gates passed. These are engineering tests using the technical character;
they do not constitute final visual production approval.

Run from the project root with Blender, FFmpeg, FFprobe and the project's Python
dependencies available. On this Mac Blender needs execution outside the restricted
sandbox to start its graphics runtime.

```sh
blender --background --python-exit-code 1 --python cartoon_studio/blender/kiko_master_plan.py -- audit
blender --background --python-exit-code 1 --python cartoon_studio/blender/kiko_master_plan.py -- run
# Inspect the run evidence and record its visual gate before proceeding.
blender --background --python-exit-code 1 --python cartoon_studio/blender/kiko_expressive_rig.py
# Inspect the rig evidence and record its visual gate before proceeding.
blender --background --python-exit-code 1 --python cartoon_studio/blender/kiko_acting_gate.py
```

The renderers write `AWAITING_VISUAL_REVIEW` with `pass: false` after numerical
and encoding checks. A successful render is not a visual approval. After inspecting
the current renders, the reviewer records a `visual_review` object with `status`,
`method`, `observations` and `scope`, then sets top-level `status: "PASS"` and
`pass: true` only if both numerical and visual gates pass. Failed reviews retain
`pass: false`, identify the defect, and require a repair and rerender. Never copy
a prior approval onto changed evidence. Downstream stages check source signatures.

The five-second master plan configuration is `scenes/kiko_master_run_gate.json`.
It preserves the older example configurations and the engine's existing APIs.
The corrected run compresses during stance and rises during flight, with sufficient
pelvis drop to prevent the knees locking at maximum extension.

Outputs:

| Gate | Master | Evidence |
|---|---|---|
| Audit | Source is `KIKO_master_v1_1.blend` | `reports/kiko_project_audit.md` and `.json` |
| Run | `KIKO_run_test_5s.blend` | `output/kiko_run_test_5s/` |
| V2 rig | `KIKO_master_v2.blend` | `review/kiko_v2_rig/`, `output/kiko_v2_rig_test/verification.json` |
| Acting | `KIKO_acting_test_8s.blend` | `output/kiko_acting_test_8s/` |

Existing masters/reports/previews are backed up by content hash under
`backups/kiko_master_plan/`. V1.1 is never overwritten. Pose assets use fake users
so Blender retains them without an active timeline assignment.

V2 animator controls:

- `CTRL_jaw["open"]`: drives jaw rotation, lower-muzzle weights and mouth opening.
- `CTRL_face`: smile, frown, wide smile, blink, squint, brows and `VIS_*` sliders.
- `mouth_corner_L/R`, `lip_upper/lower`: signed `offset` sliders.
- `CTRL_eye_aim`: head-relative binocular target; moving it aims iris/pupil bones.
- `CTRL_chest`, `CTRL_pelvis`, `CTRL_shoulder_L/R`, `CTRL_hand_L/R`,
  `CTRL_ear_L/R`, `CTRL_tail_base/tip`: additive rotation controls.
- `POSE_*`, `FACE_*`, `HAND_*`, `EAR_*`, `TAIL_*`: reusable action assets.

Only the previously unused finger chains were refitted to the digit meshes. Body
chains retain their rest positions and the run/walk contract. Eyelid surfaces cover
the actual eyes; the old moving lid arches are hidden in V2. The attached mouth
surface is suitable for this technical acting gate, but final mouth cavity,
teeth/tongue anatomy and speech shapes must be built on the final visual asset.
`VIS_FV` and `VIS_L` currently provide approximate base openings, not anatomically
accurate phonemes. No Khmer lip-sync claim is made.

Validation:

```sh
python3 -m pytest tests/test_kiko_engine.py -q
blender --background --python-exit-code 1 --python tests/test_kiko_engine_blender.py
```

The integration suite covers instance independence, additive gestures, walk/idle,
and the corrected run's flight height, knee bend and planted soles. The gate
builders additionally measure evaluated geometry, control-driven deformation,
eye aim through head turns, source integrity and encoded duration/FPS/frame count.
Visual inspection is sampled; these checks are not an exhaustive collision proof.
