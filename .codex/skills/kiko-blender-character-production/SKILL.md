---
name: kiko-blender-character-production
description: Use for KIKO or Jungle Pop Blender character work: topology, modeling, UVs, shading, rigging, weight painting, pose libraries, locomotion, secondary animation, visual QA, and final rendering. Preserve existing KIKO engineering, follow stage gates, and never present procedural blockouts as final character art.
---

# KIKO Blender Character Production

Use this skill for KIKO/Jungle Pop character creation and animation inside the `cartoon-maker` repository.

## Core workflow

Topology → Head → Torso → Limbs → Clothes → Props → Cleanup/UVs → Texturing/Shading → Still Review → Rigging → Weights → Props Rigging → Pose Library → Walk/Run → Secondary Animation → Final Render

For KIKO, adapt this sequence to existing verified work. Do not restart completed stages without a demonstrated regression.

## Operating rules

1. Inspect before editing.
2. Read current implementation status and identify the active stage.
3. Back up known-good masters before destructive edits.
4. Never overwrite V1.1, V2, or another approved master directly.
5. Never claim success because a script ran, Blender opened, a GLB imported, or a file rendered.
6. A stage passes only when its explicit visual/technical gate passes.
7. Do not return to rejected primitive/procedural final-character sculpting.
8. Use procedural geometry only for temporary engineering tests, helpers, environments, or explicitly approved blockouts.
9. Keep final character art and engineering validation separate.
10. Stop on FAIL/BLOCKED rather than hiding the problem.

## Inspect first

When present, inspect:

- `KIKO_IMPLEMENTATION_STATUS.md`
- `KIKO_MASTER_IMPLEMENTATION_PLAN.md`
- `assets/hero/kiko.png`
- `assets/hero/kiko_4view_turnaround_v001.png`
- `KIKO_master_v1_1.blend`
- `KIKO_master_v2.blend`
- `projects/characters/kiko/`
- `assets/characters/kiko_final/`
- current verification reports
- current review renders

## Preserve existing engineering

Unless status says otherwise:

- preserve Animation Core V2
- preserve `KIKO_master_v1_1.blend`
- preserve `KIKO_master_v2.blend`
- preserve verified run and acting tests
- do not rebuild locomotion just because the visual mesh changes
- do not replace the existing expressive rig with Rigify automatically

Rigify is acceptable for new characters that do not already have a verified rig.

## Character-art gate

Before rigging, establish the final visual character.

Judge:

- face identity
- head volume
- cheek silhouette
- muzzle integration
- eyes and eyelids
- ears
- crest/hair
- torso
- limbs
- paws/hands/feet
- tail silhouette
- clothing layers
- props/accessories

Reject a final KIKO that reads as:

- mouse
- rabbit
- generic fox mascot
- teddy bear
- plastic/rubber toy
- smooth primitive mascot
- generic low-poly character

Do not hide weak form with lighting, fur, depth of field, bloom, or glossy materials.

## Head modeling priority

The face is the highest-priority identity region.

Require:

- broad cheek volume
- compact integrated muzzle
- large amber eyes seated in sockets
- meaningful upper/lower eyelids
- brow volume
- organic nose/mouth region
- natural head-to-ear transition
- layered, non-blade-like crest

A neutral expression should already feel alive before animation.

## Torso and limbs

Check:

- shoulder structure
- chest/waist/pelvis
- elbows/wrists
- hips/knees/ankles
- finger/toe separation

Reject tube limbs, capsule joints, mitten hands, or toy anatomy when they harm the production target.

## Clothes and props

Keep logically separated when useful:

- scarf
- vest/tunic
- harness
- belt
- pouches
- backpack
- wraps
- compass/flask/trinkets

Flexible clothing usually needs weights.
Rigid accessories can often be bone-parented.

## Cleanup and UVs

Audit:

- non-manifold geometry
- flipped normals
- duplicates
- intersecting shells
- internal hidden geometry
- deformation-critical edge flow
- UVs
- material slots
- transforms/orientation/scale

Do not retopologize a visually failed model just to make it easier to rig.

## Texturing and shading

After visual form approval:

- matte stylized fur
- soft cloth
- worn leather
- controlled metal accents
- layered eye materials
- subtle roughness/color variation

Avoid uniform glossy/plastic response.

Keep grooms lightweight for M2 Pro / 16 GB.

## Still review

Before rigging/animation, render:

- front
- three-quarter
- side
- back
- face close-up
- tail profile
- outfit detail
- black silhouette

Use neutral studio lighting.

## Rigging

### Existing KIKO

Prefer fitting the verified expressive rig to the approved final mesh.

Preserve:

- body controls
- face/viseme controls
- ear controls
- tail controls
- locomotion compatibility

### New character

If no production rig exists:

- create/align armature
- Rigify may be used
- auto weights are only a starting point
- manually validate/correct weights

## Skin-weight QA

Test:

- shoulders
- elbows
- wrists
- hips
- knees
- ankles
- neck/head
- jaw/mouth
- eyelids
- tail base
- ear extremes

Look for:

- collapsing volume
- twisting
- pinching
- clothing penetration
- floating accessories
- broken facial deformation

## Props rigging

Classify into:

- deform with body
- flexible clothing needing weights
- secondary-motion object
- rigid bone-parented accessory
- static/remove/review

## Pose library

Useful KIKO poses:

- neutral
- curious
- alert
- worried
- excited
- pointing
- thinking
- listening
- crouch
- ready-to-run
- surprise
- happy
- determined

Coordinate body, face, ears, and tail.

## Locomotion

Reuse the verified animation system.

Inspect:

- contact
- down
- passing
- up
- airborne when applicable
- foot sliding
- pelvis motion
- chest counterrotation
- arm opposition
- head stability
- ear follow-through
- tail delay/follow-through

Do not invent unsupported JSON scene fields. If a new capability is needed, extend the existing schema/engine/tests once; scenes remain JSON-driven.

## Secondary animation

May include:

- ears
- tail
- scarf
- backpack
- pouches
- cloth
- crest/hair

Secondary motion follows the primary action and should not compete with it.

## Rendering

Engineering previews:

- Eevee
- moderate samples
- test resolution such as 854×480 when specified

Production:

- 1080p unless explicitly changed
- validate materials/lighting before expensive render
- prefer frame sequence for important renders
- encode with FFmpeg afterward

## Quality-gate discipline

Use exact thresholds from the active stage/report.

For KIKO Stage 5, typically judge:

- face likeness
- eyes/expression
- cheek identity
- ears
- crest
- tail
- body proportions
- outfit identity
- overall KIKO identity
- plastic/rubber appearance

If a required gate fails, report `FAIL` and stop unless explicitly asked for a targeted correction.

Never inflate scores.

## Iteration policy

If a candidate is close:

- make localized changes
- protect already-passing areas
- compare before/after using identical lighting/camera
- archive degraded attempts
- revert to the last cleaner checkpoint when a pass gets worse

Do not pile fixes onto a degraded mesh.

## Hardware constraints

Target: Apple Silicon M2 Pro, 16 GB RAM.

Prefer:

- Eevee for validation
- moderate texture resolution during tests
- lightweight fur
- reusable environments/animations
- rigid-parenting when appropriate
- optimization only after visual approval

## Definition of done

End every task with:

1. source used
2. files created/modified
3. backups preserved
4. tests/renders executed
5. exact output paths
6. visual/technical gate result
7. remaining weaknesses
8. next safe stage

Use explicit status:

- `PASS`
- `FAIL`
- `BLOCKED`

Read `references/course-map.md` for the character-creation learning sequence.
Read `references/kiko-stage-map.md` for the KIKO 14-stage production map.
