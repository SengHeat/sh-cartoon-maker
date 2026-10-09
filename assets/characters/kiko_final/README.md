# KIKO visual model

`KIKO.glb` is the unrigged visual model built from the project reference at
`assets/hero/kiko.png`. It is a stylized, manually generated 3D interpretation
with broad coral-lined ears, a cream muzzle/chest, amber eyes, a tall fur crest,
an explorer outfit, backpack, and a large banded plume tail.

The GLB has 125 mesh primitives, 22 materials, UVs, and 13 embedded image
textures. The Blender source is `blender/KIKO_visual_model_v1.blend` in the repository; its studio camera, floor, and lights are excluded from the GLB. Geometry
is approximately 3.0 Blender units tall. The character faces -Y with +Z up.
Objects are separated for later editing and rigging. The body foundation is
connected; clothing, facial details, hands, and accessories remain separate.

This is a first visual-model pass, not a production sculpt or rig-ready final.
The face and overall likeness still need artist review against the reference;
the eyelids and mouth are simple static forms. No rig, skin weights, facial
controls, or deformation validation are included. The render views and contact
sheet are in `review/kiko_visual/`.

The source builder is `blender/kiko_final_model.py`. Run it with
Blender 5.2 or a compatible version to rebuild the BLEND, review renders, and
GLB. The companion preflight report is `reports/kiko_visual_model_v1.json`.
