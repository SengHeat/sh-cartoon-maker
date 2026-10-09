# Stage 5 targeted correction — V4 review

**Visual result: FAIL.** Three corrective iterations were built and reviewed.
V4.03 is a useful face correction checkpoint, not an approved final character.
Stages 6–14 remain blocked. Existing Stage 1–4 engineering is preserved.

[Open the side-by-side review](../review/stage5_v4_03/review.html).

## Source, outputs and preserved work

Source: `assets/characters/kiko_final/source/KIKO_source_v3_1.glb`.
Targets: `assets/hero/kiko.png` and `assets/hero/kiko_4view_turnaround_v001.png`.
Candidate directory: `projects/characters/kiko/review/stage5_v4_03/`.
It contains `KIKO_candidate.blend`, `KIKO_candidate.glb`, eight neutral review
PNGs, `build_manifest.json`, the build-script snapshot and the comparison page.
The unchanged-source comparison is in `../review/stage5_v4_baseline/`.

The original source, V1.1 and V2 masters, run scene and acting scene were hash
checked during builds. No rig, animation engine or approved master was edited.
All previous backups remain. The status before this correction report is backed
up at `backups/kiko_stage5_v4/KIKO_IMPLEMENTATION_STATUS_0ae3a88ba2729318.md`.

Implementation: `scripts/kiko_stage5_targeted_correction.py` and
`scripts/kiko_stage5_verify_candidate.py`. No character primitives were added.

## Iterations and visual findings

| Candidate | Result | Evidence and disposition |
|---|---|---|
| V4.01 | FAIL | Lowering arms stretched the fused shoulder/head mesh. The enlarged separate muzzle still appeared attached. Archived at `../review/archive/stage5_v4_01/`. |
| V4.02 | FAIL | Reprojected face shell intersected the skull; tail-lock changes produced plates and distorted the silhouette. Archived at `../review/archive/stage5_v4_02/`. |
| V4.03 | FAIL overall | Restarted from the clean V3.1 source; preserved its limb pose and tail. Integrated muzzle volume into the continuous head and removed the detached cream shell and raised brow strips. Removed misplaced experimental cheek/tail pieces, adjusted eye seating and iris proportions, and defined cream/teal regions on the continuous head. Retained as an unapproved correction checkpoint. |

The third candidate avoids the first two regressions. It visibly improves the
cream face integration, but the eyes still protrude, lids remain separate strips,
cheek tufts are stubby pieces, crest locks read as blades, and the tail remains a
smooth banded tube. The paws and clothing still read as simplified toy forms.
The side/back/tail/outfit views make these weaknesses clear. A fur pass would
conceal problems rather than establish the missing form.

All eight required views were inspected. Face framing now includes eyes, nose,
mouth and cheeks; full-body views retain a margin; the silhouette is true black.
Five source/candidate comparisons use identical camera transforms and studio
settings. This review improvement is not a character-art PASS.

No new likeness percentages were invented. Historical thresholds (80 for face,
eyes, cheeks, ears, crest, tail and identity; 75 for body and outfit) are not
established by this work. The explicit no-toy criterion fails independently.

## Validation and limits

Built three candidates plus the unchanged-source baseline in Blender 5.2.2 LTS,
using Eevee at 768 × 768. Rendered 23 comparison/review stills before export QA.
V4.03 contains 133 mesh objects and 161,931 vertices before GLB reimport.
Source and output SHA-256 hashes are in the build manifests.

Export QA is recorded separately in `../review/stage5_v4_03/technical_verification.json`.
**Export preservation: PASS** — all 133 objects retained, maximum world-bounds
error 0.0 and exported face-color error 0.0. Both GLB roundtrip renders were
inspected and retain the corrected face. Total rendered stills: 25.
It checks object preservation, finite coordinates, world-space bounds and face
color data, and renders the imported GLB front and face. GLB stores float face
colors; Blender reimport uses byte colors, so import quantization is distinguished
from exact exported values. The initial overly strict import-color tolerance
failed; the verifier now checks the actual float payload and uses the documented
sRGB byte-step bound for imported storage, without changing the candidate.

This is not UV, manifold, intersection, skin-weight, deformation or animation
approval. No rig transfer or later-stage production work was attempted.

## What is needed for a pass

The next viable step is a stronger supplied sculpt or image-to-3D base matching
the two references, followed by this same neutral review. The existing source
retains the rejected procedural model's form limitations; three local correction
attempts did not resolve them. No callable image-to-3D service was available in
this session, and the inspected candidates do not supply a passing sculpt.

The replacement needs broad integrated cheek/head volume, compact muzzle,
eyes seated in sockets with continuous eyelids, organic ear transitions, a
layered crest, a tapered plume tail, separated paws and layered explorer clothing.
Keep head/torso/limb proportions faithful before adding fur or detailed shading.
Supply a `.blend`, `.glb` or `.fbx` with its materials; preserve flexible clothing
and rigid accessories as meaningful parts. Do not replace the verified V2 rig.

The [skill](../../../../.codex/skills/kiko-blender-character-production/SKILL.md)
requires: “Do not pile fixes onto a degraded mesh.” The
[master plan](../../../../docs/KIKO_MASTER_IMPLEMENTATION_PLAN.md) directs work
to stop after reasonable repairs when the method is clearly unsuitable.
The user authorized these corrections; the remaining blocker is visual source
quality and the available modeling method, not a pending permission request.
