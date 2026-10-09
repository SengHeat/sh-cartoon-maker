# KIKO skill gate audit — 2026-10-09

**Visual gate: FAIL. Active stage: 5. Stages 6–14: BLOCKED.**

## Source and scope

Applied the [production skill](../../../../.codex/skills/kiko-blender-character-production/SKILL.md),
both of its reference maps, and the [master plan](../../../../docs/KIKO_MASTER_IMPLEMENTATION_PLAN.md).
Compared `assets/hero/kiko.png` and `assets/hero/kiko_4view_turnaround_v001.png`
with the existing V3 contact sheet and all six standalone V3.1 review views.
Latest candidate: `assets/characters/kiko_final/source/KIKO_source_v3_1.glb`;
associated blend: `projects/characters/kiko/blends/master/KIKO_visual_stage5_v3_1.blend`.

This is an audit of existing evidence, not a new render or model correction.
The generator script names these paths, but the old renders have no source-hash
manifest proving they correspond to the current GLB bytes. No numeric likeness
scores were invented. Historical thresholds remain 80 for face, eyes, cheeks,
ears, crest, tail and overall identity; 75 for body and outfit. The explicit
no-toy requirement already fails, so a new numerical average cannot justify PASS.

## Visual findings

| Region | Existing evidence | Finding |
|---|---|---|
| Face and cheeks | V3.1 front, three-quarter, side | Oval muzzle appears attached to a rounded head; broad integrated cheek structure is missing. |
| Eyes and lids | V3.1 front, three-quarter, side | Eyes protrude from the face; lid strips do not establish the reference's seated sockets. |
| Ears and crest | V3.1 front and silhouette | Ears read as smooth oval shells; crest remains rigid, blade-like pieces. |
| Tail | V3.1 tail profile and silhouette | Smooth curved tube with color bands and attached pieces, rather than a layered plume. |
| Body and outfit | V3.1 front and side | Mitten-like paws, capsule-like joints and smooth clothing retain the toy appearance. |
| Surface | V3 sheet and V3.1 views | Matte color alone does not correct the smooth primitive form. |

V3.1 `face_closeup.png` shows the crest/forehead and only parts of the eyes,
excluding the muzzle. Required back and outfit-detail views are absent from
that review directory. Its silhouette remains shaded rather than flat black,
and one ear reaches the image edge. The older V3 contact sheet also includes
misframed face/eye views and cropped comparisons. These are insufficient approval
evidence even apart from the visible form failures.

## Technical findings and preservation

- Parsed six GLB headers and JSON chunks: all have valid GLB 2 container headers
  and matching declared byte lengths. This does not validate topology, UVs,
  materials in Blender, rig readiness or visual quality.
- Current V3 has 210 mesh definitions, whereas its assessment reports 192 meshes
  and the roundtrip report reports 174. V3.1 contains 145 mesh definitions.
- Current `KIKO_source_v3.glb` is byte-identical to
  `assets/characters/kiko_final/archive/KIKO_source_v3_iter2_REJECTED.glb`.
- The historical roundtrip report sets `material_export_pass` to false while
  the assessment claims PASS. It lists one intentionally white catchlight;
  this conflict alone does not establish actual material loss.
- SHA-256 hashes of protected assets, sources, scripts and review evidence are
  recorded in the [JSON audit](KIKO_SKILL_GATE_AUDIT_2026-10-09.json).
- V1.1 and V2 masters have byte-identical existing backups under
  `backups/kiko_master_plan/`; exact matches are recorded in the JSON.
  Existing run/acting scenes and all backups were preserved without edits.
- No Blender invocation, new render, deformation test or animation regression
  test was performed. No application code or character geometry changed.

## Files changed

- Updated `KIKO_IMPLEMENTATION_STATUS.md` to expose the current FAIL and label
  the historical PASS as superseded, preserving the historical record.
- Created this report and `KIKO_SKILL_GATE_AUDIT_2026-10-09.json`.
- Preserved the pre-edit status at
  `backups/kiko_skill_audit/KIKO_IMPLEMENTATION_STATUS_08643f74184692f3.md`.

## Next safe stage

Remain at Stage 5. Use a suitable supplied sculpt/image-to-3D base or an
explicitly requested localized correction, prioritizing integrated cheeks,
muzzle and eye sockets. Do not repeat the primitive-assembly method or start
fur/rig transfer on this failed visual base. After correction, render all eight
required neutral views with proper framing and source-hash provenance; assess
them against both references before advancing.

The skill explicitly requires: “If a required gate fails, report `FAIL` and
stop unless explicitly asked for a targeted correction.” This is the reason
production work stops at the audit; no approval request is pending.
