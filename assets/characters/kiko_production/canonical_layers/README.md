# Canonical layer intake

Place the **new** KIKO production PNG exports here only after exporting them
from one registered neutral-pose master. The old `../layers/` and
`../source_layers/` artwork is rejected source material and must not be copied,
cropped, masked, repaired, or reused here.

Every file must be an uncropped 2048×2048 RGBA PNG with character origin
`(1024, 1843)`. Only the named part may be visible; every other pixel must have
alpha 0. Preserve hidden overlap beneath joints. Do not bake checkerboards,
labels, borders, cards, or contact sheets into the export.

Populate `../canonical_registration.json` for every required filename and add
the separately approved neutral composite at
`../canonical_reference/neutral_approved.png`. Validation must pass before the
runtime rig may be repointed or any animation rendered.
