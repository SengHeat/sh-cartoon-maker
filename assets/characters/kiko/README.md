# KIKO 2.5D placeholder puppet

This is deliberately unfinished geometric placeholder art for exercising the existing cut-out pipeline. It is not final character artwork.

Package revision is `test-v002`, recorded in `rig_metadata.json`. Runtime `rig.json` retains `rig_version: 1`, the only value accepted by the strict current schema. The metadata records the changed v001 coordinates rather than discarding them.

## Replacement contract

`rig.json` is the source of truth. Real artwork can replace any PNG below at the same path without a code or JSON change. Preserve each image's pixel dimensions and keep its joint on the documented pivot; otherwise update that part's normalized `pivot` and its child's `attach` values.

The package locator is `kiko_2d_idle.png`. It is intentionally transparent: `ImageRenderer` finds the sibling `rig.json`, which loads the real layers.

Replaceable files under `layers/`:

- Body: `body.png`, `head.png`, `muzzle.png`, `nose.png`, `cheek_l.png`, `cheek_r.png`, `crest.png`.
- Tail: `tail_base.png`, `tail_mid.png`, `tail_tip.png`.
- Left/far limbs: `upper_arm_l.png`, `arm_l.png`, `hand_l.png`, `thigh_l.png`, `shin_l.png`, `foot_l.png`.
- Right/near limbs: `upper_arm_r.png`, `arm_r.png`, `hand_r.png`, `thigh_r.png`, `shin_r.png`, `foot_r.png`.
- Face states: `eyes_open.png`, `eyes_closed.png`, `mouth_neutral.png`, `mouth_open.png`.
- Costume: `scarf.png`, `vest.png`, `harness_straps.png`, `belt.png`, `backpack.png`, `charm.png`.

## Pivot meaning

All rig coordinates are normalized `[x, y]` values, with `(0,0)` at an image's upper-left. A part's `pivot` is its own rotation/origin joint. Its `attach` is the point inside its parent image where that pivot is placed. Examples: shin pivots are near their top edge and attach near the thigh's bottom; the head pivot is at the neck and attaches to the upper body.

The action presets recognize `body`, `head`, `arm_l`, and `arm_r`. Here `arm_l` and `arm_r` are forearms parented to `upper_arm_l/r`, so wave/walk rotations visibly articulate the elbow. The current renderer has no independent tail pose channel; the attached plume inherits gentle body sway without tearing, but cannot yet rotate independently of the hips.

## Expression states

The `eyes` rig part maps `open` and `closed`. `RigEngine` chooses `closed` during deterministic auto-blinks. The `mouth` part maps `closed`/`neutral` to `mouth_neutral.png` and `open`/`small`/`wide` to `mouth_open.png` so current emotion and lipsync state names resolve safely.

To add a state, create a same-alignment PNG and add a key/path to that part's `swap` object in `rig.json`. A state only activates automatically if `RigEngine` or an emotion preset requests the same key.

## Proof scene

`projects/kiko_2d_test.json` renders at 1280×720, 12 fps for 3.25 seconds. A short true-rest lead is followed by a head-turn action with low-intensity walk-in-place secondary motion, producing supported body/hip sway inherited by the plume while deterministic blinking exercises the eye swap. Run:

```sh
CARTOON_STUDIO_OUTPUT=review/kiko_2d/work python3 -m cartoon_studio.cli render projects/kiko_2d_test.json --workers 1 --no-dedupe
CARTOON_STUDIO_OUTPUT=review/kiko_2d/work python3 -m cartoon_studio.cli encode projects/kiko_2d_test.json
```
