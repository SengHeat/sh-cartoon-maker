# KIKO 3D rig audit — 2026-10-07

## Recovery status

The tracked `KIKO_master_v001.blend`, `KIKO_master_v001.blend1`, and
`KIKO_blockout_v001.blend` are zero-byte files. Git history contains no non-empty
version of them. All modular Blender files except `kiko_blockout.py` are also
zero-byte placeholders. Consequently there are no recoverable vertex groups,
constraints, or actions in a source `.blend`.

## Authoritative source rig contract

`blender/kiko_blockout.py` defines the recoverable skeleton:

- Armature object: `KIKO_RIG_armature` (`KIKO_RIG_data`)
- Spine/deform chain: `root`, `COG`, `pelvis`, `spine_01`, `spine_02`,
  `chest`, `neck`, `head`, `jaw`
- Ears: `ear_01_L` through `ear_03_L`, mirrored `_R`
- Eyes: `eye_L`, `eye_R`; non-deforming target: `eye_aim`
- Arms: `clavicle`, `upperarm`, `lowerarm`, `hand`, and four two-bone finger
  chains per side
- Legs: `thigh`, `shin`, `foot`, `toe` per side
- Tail: `tail_01` through `tail_06`, parented from `pelvis`
- Controls: `CTRL_root`, `CTRL_COG`, `CTRL_head`, `IK_foot_L/R`, and
  `POLE_knee_L/R`
- Source count: 49 deform bones and 8 non-deforming controls

## Missing from the lost artifact

- No existing vertex groups can be inspected.
- The source blockout parents rigid proxy objects to the armature and explicitly
  creates no skin weights.
- The source declares IK controls and knee poles but no constraints.
- No action data survives in Git.

## Rebuild compatibility policy

The production rebuild retains every published bone name above, creates
normalized vertex groups with the same deform names, installs leg IK constraints,
and supplies semantic actions without changing the story/renderer API. The
primitive blockout remains excluded from production renders.
