"""Add the manual Stage 5 gate assessment and publish its readable audit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "projects/characters/kiko/reports/KIKO_STAGE5_VERIFICATION.json"
MARKDOWN = ROOT / "projects/characters/kiko/reports/KIKO_STAGE5_FINAL_VISUAL_AUDIT.md"
STATUS = ROOT / "KIKO_IMPLEMENTATION_STATUS.md"

SCORES = {
    "face_likeness": 20,
    "eyes_and_expression": 20,
    "ear_silhouette": 58,
    "crest_silhouette": 20,
    "tail_silhouette": 35,
    "body_proportions": 35,
    "outfit_identity": 60,
    "overall_kiko_identity": 28,
}
FAILURES = [
    "plastic/rubber mascot appearance remains in the neutral studio render",
    "face reads as a generic mouse-like mascot rather than the reference KIKO",
    "large smooth oval cream muzzle remains detached-looking",
    "eyes read as protruding white eye forms with no meaningful eyelid volume",
    "crest reads as separate hard spike/lock forms",
    "tail has a broad striped shape but lacks a fluffy plume silhouette",
    "overall silhouette is generic and does not pass the KIKO identity gate",
]
BLOCKERS = [
    "Visual likeness thresholds fail for face, eyes, ears, crest, tail, body, outfit, and overall identity.",
    "Automatic visual failures are present; Stage 5 does not pass.",
    "The main body has dense triangulated geometry with no deformation loops around face or joints.",
    "The muzzle and tail are open-shell meshes; 36 imported meshes have boundary edges.",
    "No armature, skin weights, or animation data are present.",
    "Stage 7 rig transfer is not safe to begin until the visual source is replaced and topology is prepared.",
]


def main():
    d = json.loads(REPORT.read_text())
    candidate = ROOT / d["candidate"]
    d.update({
        "stage5_pass": False,
        "gate_result": "FAIL",
        "scores": SCORES,
        "automatic_failures": FAILURES,
        "blockers": BLOCKERS,
        "origin_position": {"mesh_object_origins": [0.0, 0.0, 0.0],
                             "mesh_object_rotations": [0.0, 0.0, 0.0],
                             "mesh_object_scales": [1.0, 1.0, 1.0]},
        "world_scale": "1 GLB unit imported as 1 Blender meter",
        "curve_count": d.get("curves", 0),
        "image_texture_count": d["textures"],
        "candidate_bytes": candidate.stat().st_size,
        "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "material_texture_summary": {
            "missing_or_broken_images": len(d["material_audit"]["missing_textures"]),
            "unsupported_nodes": len(d["material_audit"]["unsupported_nodes"]),
            "transparency_materials": len(d["material_audit"]["transparency_materials"]),
            "low_roughness_materials": d["material_audit"]["glossy_principled_materials"],
            "texture_dimensions": sorted({tuple(x["size"]) for x in d["material_audit"]["images"]}),
            "base_color_image_colorspaces": sorted({x["colorspace"] for x in d["material_audit"]["images"]}),
            "assessment": "All 13 embedded 256x256 images decoded; no broken dependencies or unsupported shader nodes. All are sRGB base-color images. No transparency problems found. Six low-roughness materials include eye and brass materials; eye whites/pupils and catchlights appear overly glossy under neutral review lighting. Fur surfaces still read smooth; no roughness or normal maps are present.",
        },
        "topology_status": "Main fused body/head/ear mesh is closed/manifold (40,908 vertices, 81,812 triangles) with no zero-area faces or zero-length normals, but it is densely triangulated and lacks organized deformation loops around eyes, mouth, shoulders, elbows, wrists, hips, knees, ankles, or tail base. The cream muzzle shell has 1,010 boundary edges; the dominant plume tail has 432. 36 of 125 meshes have boundary edges; no duplicate faces or zero-area faces were detected. Coincident-vertex flags occur on swept/open-shell parts and need artist review.",
        "performance_status": "Estimated practical for inspection and animation previews on a 16 GB M2 Pro: 287,012 triangles and 13 small 256x256 textures are modest; Blender GLB import took {:.3f}s and the ten Eevee renders took {:.1f}s total. Interactive viewport responsiveness and peak memory were not measured on the target Mac. Retopology is mandatory for the deforming body/face before production rigging; no decimation is recommended for performance alone. Rigid-parenting accessories is preferable after body retopology.".format(
            d["import_seconds"], sum(d.get("render_seconds", {}).values())),
        "recommended_rig_strategy": "OPTION B before rig transfer: retopologize the deforming body and facial regions. Then use the OPTION C hybrid: weight body and flexible clothing; bone-parent rigid backpack hardware, compass, flask, buckles, and selected pouches. Stage 7 is NOT safe to begin while Stage 5 fails.",
        "visual_reference_comparison": {
            "method": "Manual side-by-side inspection of assets/hero/kiko.png and neutral Eevee review renders/contact sheet.",
            "strongest_areas": ["large ears with coral insets", "teal/cream/coral palette", "recognizable scarf, vest, harness, pouches, backpack", "large curved striped tail mass"],
            "weakest_areas": ["round smooth head and giant oval muzzle", "detached white eye forms and absent eyelid volume", "no cheek fur silhouette", "crest reads as hard spikes", "body and limbs read smooth and toy-like", "tail reads as a smooth banded paddle rather than layered plume fur", "expression is static and generic"],
            "black_silhouette_result": "Fails identity threshold: ears and tail mass are visible, but cheeks/crest/body lack enough distinctive organic breakup and the A-pose reads like a generic mascot.",
        },
        "review_resolution": {"long_side_px": 1200, "contact_sheet": "projects/characters/kiko/review/stage5_candidate/contact_sheet.png"},
        "stage6_started": False,
        "stage7_started": False,
        "source_candidate_modified": False,
    })
    for row in d["object_classification"]:
        name = row["name"].lower()
        if "continuous sculpted body" in name:
            row.update(classification="A. DEFORM WITH BODY",
                       recommended_parent="root/spine/head/limb bones after retopology", weighting_required=True)
        elif "cheek" in name:
            row.update(classification="A. DEFORM WITH BODY",
                       recommended_parent="head / cheek control", weighting_required=True)
        elif any(k in name for k in ("brass clasp", "pouch", "backpack", "compass", "flask", "buckle", "bedroll")):
            row.update(classification="C. RIGID BONE PARENT",
                       recommended_parent="belt / spine / chest bone by attachment", weighting_required=False)
        elif any(k in name for k in ("scarf", "vest", "harness", "belt", "wrap", "chest bib", "tunic")):
            row.update(classification="D. CLOTHING NEEDING WEIGHTS",
                       recommended_parent="nearby body region; flexible parts need weights", weighting_required=True)
        elif any(k in name for k in ("tail", "ear", "crest", "hair")):
            row.update(classification="B. DEFORM / SECONDARY RIG",
                       recommended_parent="tail / ear / crest control", weighting_required=True)
    d["render_dimensions"] = {}
    for path in d["render_paths"]:
        with Image.open(ROOT / path) as img:
            d["render_dimensions"][path] = list(img.size)
    contact = ROOT / "projects/characters/kiko/review/stage5_candidate/contact_sheet.png"
    d["contact_sheet"] = str(contact.relative_to(ROOT))
    with Image.open(contact) as img:
        d["contact_sheet_dimensions"] = list(img.size)
    REPORT.write_text(json.dumps(d, indent=2) + "\n")

    table = ["| Object | Vertices | Class | Recommended parent | Weights? |",
             "|---|---:|---|---|---:|"]
    for row in d["object_classification"]:
        category = row["classification"]
        parent = row["recommended_parent"]
        n = row["name"].replace("|", "\\|")
        parent = parent.replace("|", "\\|")
        table.append(f"| `{n}` | {row['vertices']} | {category} | {parent} | {'Yes' if row['weighting_required'] else 'No'} |")
    topology = d["topology"]
    failed_meshes = topology["nonmanifold_meshes"]
    visual = d["visual_reference_comparison"]
    md = f'''# KIKO Stage 5 Final Visual Audit

**Result: FAIL. Stage 5 is incomplete. Stage 6 and Stage 7 were not started.**

Candidate inspected: [`{d['candidate']}`](../../../../{d['candidate']})  
Authoritative reference: [`{d['reference']}`](../../../../{d['reference']})  
Non-destructive validation scene: [`{d['validation_blend']}`](../../../../{d['validation_blend']})  
Contact sheet: [`{d['contact_sheet']}`](../../../../{d['contact_sheet']})

The newest eligible non-archived GLB was `assets/characters/kiko_final/KIKO.glb`; it was imported into an empty Blender scene. The source GLB was not modified. Review used neutral Eevee lighting and ten 1200 × 1200 renders. The contact sheet was inspected against the authoritative reference. Complexity and successful import do not satisfy the likeness gate.

## Measured candidate data

| Measure | Result |
|---|---:|
| Bounding dimensions (X × Y × Z) | {d['dimensions']['x']} × {d['dimensions']['y']} × {d['dimensions']['z']} m |
| Bounding box min / max | `{d['bounding_box']['min']}` / `{d['bounding_box']['max']}` |
| Forward / up | {d['forward_axis']} / {d['up_axis']} |
| Imported mesh-object origins | {d['origin_position']['mesh_object_origins']} (all imported object transforms are identity) |
| Objects / meshes / curves | {d['objects']} / {d['meshes']} / {d['curves']} |
| Vertices | {d['vertices']:,} |
| Polygons / triangles | {d['polygons']:,} / {d['triangles']:,} |
| Materials / embedded image textures | {d['materials']} / {d['textures']} |
| Armatures / glTF skins / animations | {d['armatures']} / {d['skins']} / {d['animations']} |
| Skinned meshes | {len(d['skinned_meshes'])} |
| Blender import time | {d['import_seconds']:.3f} s |

All {d['textures']} embedded 256 × 256 images decoded; there are no missing image dependencies, unsupported material nodes, or alpha/transparency issues. The images are sRGB base-color maps. Six materials have roughness below 0.35, including eye, catchlight, and brass materials. The eye and nose response is visibly shiny under neutral lighting; body surfaces still look smooth. No normal or roughness maps were found.

## Visual likeness scores

Scores are conservative manual judgments against the reference, not geometry-complexity scores.

| Area | Score | Required | Result |
|---|---:|---:|---|
| Face likeness | {SCORES['face_likeness']} | 80 | FAIL |
| Eyes and expression | {SCORES['eyes_and_expression']} | 80 | FAIL |
| Ear silhouette | {SCORES['ear_silhouette']} | 80 | FAIL |
| Crest silhouette | {SCORES['crest_silhouette']} | 80 | FAIL |
| Tail silhouette | {SCORES['tail_silhouette']} | 80 | FAIL |
| Body proportions | {SCORES['body_proportions']} | 75 | FAIL |
| Outfit identity | {SCORES['outfit_identity']} | 75 | FAIL |
| Overall KIKO identity | {SCORES['overall_kiko_identity']} | 80 | FAIL |

Strongest areas are the large coral-lined ears, palette, explorer clothing arrangement, and broad striped tail mass. The major failures are the round smooth head, large oval cream muzzle patch, protruding white eye forms without meaningful eyelids, absent cheek silhouette fur, hard separated crest locks, smooth toy-like limbs, and a tail that reads as a banded paddle rather than a fluffy plume. The black silhouette is not recognizably KIKO enough to pass.

Automatic failures present: {', '.join(FAILURES)}.

## Topology and rigging audit

The principal body/head/ear mesh is manifold with 40,908 vertices and 81,812 triangles. It is dense, uniformly triangulated topology, with no organized loops for eyes, mouth, shoulders, elbows, wrists, hips, knees, ankles, or the tail base. The cream muzzle shell has 1,010 boundary edges; the dominant tail mesh has 432. {len(failed_meshes)} of 125 mesh objects contain boundary edges. No duplicate faces, zero-area faces, or zero-length normals were detected. Coincident-vertex reports on swept shells require artist review; they are not treated as proof of duplicate faces.

No armature, skin weights, or animation data exist. The model is therefore not rig ready. Retopologize the deforming body and face first (Option B); after that, use the preferred hybrid approach (Option C) by weighting body/flexible clothing and bone-parenting rigid accessories. Do not start Stage 7 until a replacement source passes Stage 5.

At 287k triangles and thirteen 256 × 256 images, the asset is modest enough for previews on a 16 GB M2 Pro; Blender imported it in {d['import_seconds']:.3f} seconds and produced the ten renders in {sum(d.get('render_seconds', {}).values()):.1f} seconds. Target-machine viewport responsiveness and peak memory were not directly measured. Retopology is required for deformation quality, not because polygon count alone is too high. Decimation is not recommended as a performance fix.

## Object classification for future rig planning

These are recommendations only; no parenting or weighting was performed.

{chr(10).join(table)}

## Review outputs

'''+"\n".join(f"- [`{Path(p).name}`]({Path(p).name}) — {d['render_dimensions'][p][0]} × {d['render_dimensions'][p][1]} px" for p in d["render_paths"])+f'''
- [`contact_sheet.png`](contact_sheet.png) — {d['contact_sheet_dimensions'][0]} × {d['contact_sheet_dimensions'][1]} px

**Stage 5: FAIL. Stage 7 is not safe to begin.** No source model was modified, and no Stage 6 or Stage 7 work was performed.
'''
    MARKDOWN.write_text(md)

    status = STATUS.read_text()
    marker = "Stage 5 final candidate audit: FAIL."
    if marker in status:
        status = status[:status.index(marker)].rstrip() + "\n"
    status += "\nStage 5 final candidate audit: FAIL. `assets/characters/kiko_final/KIKO.glb` was imported non-destructively and manually compared with `assets/hero/kiko.png`. The mesh is technically importable but fails the visual likeness gate: face 20/100, eyes 20, ears 58, crest 20, tail 35, body 35, outfit 60, overall identity 28. No rig transfer or Stage 6 work was started. Full measured audit and per-object rig-planning table: `projects/characters/kiko/reports/KIKO_STAGE5_FINAL_VISUAL_AUDIT.md`; structured data: `projects/characters/kiko/reports/KIKO_STAGE5_VERIFICATION.json`. Stage 7 is not safe to begin.\n"
    STATUS.write_text(status)
    print(f"Wrote {MARKDOWN.relative_to(ROOT)} and updated {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
