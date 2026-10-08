#!/usr/bin/env python3
"""Repair inherited V1 digit/toe fallback weights without changing the rig."""
from pathlib import Path
import bpy

root=Path.cwd(); path=root/"KIKO_master_v1_1.blend"
bpy.ops.wm.open_mainfile(filepath=str(path))
for o in bpy.data.objects:
    if not o.name.startswith(("KIKO_GEO_digit_","KIKO_GEO_toe_")):
        continue
    side="L" if o.name.endswith("_L") else "R"
    bone=("hand_" if "digit" in o.name else "foot_")+side
    o.vertex_groups.clear(); vg=o.vertex_groups.new(name=bone)
    vg.add([v.index for v in o.data.vertices],1.0,"REPLACE")
bpy.ops.wm.save_as_mainfile(filepath=str(path))
