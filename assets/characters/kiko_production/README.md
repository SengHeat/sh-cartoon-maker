# KIKO production runtime and canonical-layer intake

## Current milestone

**KIKO production layer scaffold + validation ready for new canonical artwork.**

The artwork currently in `layers/` and `source_layers/` failed production QA and
is invalid. It is retained only as quarantined historical input; it must not be
rendered, repaired, cropped, masked, or copied into the canonical intake.

New exports go in `canonical_layers/`. The delivery contract lives in
`canonical_layer_manifest.json`, and every file has a registration declaration
in `canonical_registration.json`. The approved neutral reference is deliberately
absent until art approval. Validate a delivery with:

```sh
python -m cartoon_studio.characters.kiko_layer_validator assets/characters/kiko_production
```

The command is read-only and fail-closed. A pass requires all named files,
identical 2048×2048 RGBA canvases, origin `(1024, 1843)`, true transparency,
clear borders, zero offsets, neutral registration, and a pixel-exact neutral
stack match. The runtime rig must not be repointed and the 30-second short must
not be rendered before it passes.

Artists must export each layer from the same uncropped neutral master. Include
hidden artwork overlap under every limb and tail joint. Only the named body part
may be visible in each file; semantic part isolation still requires art review
in addition to automated validation.

## Quarantined legacy notes

The notes below describe the rejected historical package and are not approval to use it.

## Drop-in compatibility
- `layers/` keeps the exact filenames and pixel dimensions used by the uploaded `rig.json`.
- `rig.json` remains `rig_version: 1` for compatibility with the existing strict renderer.
- `source_layers/` contains richer separated source parts (pupils, eyelids, brows, additional mouth states, front/back torso, and a four-part tail source).

## Important QA note
These are production-style illustrated assets rather than geometric placeholders, but they were generated and assembled by AI. Before publishing an episode, run the neutral-pose and motion tests in your actual `cartoon_studio` renderer and tune pivots/attach points if a joint needs a few pixels of correction.

## Recommended next test
Render: neutral idle -> blink -> head turn -> one arm raise -> two walk cycles -> tail sway. Check shoulder/elbow/wrist/knee/ankle overlap and tail continuity.
