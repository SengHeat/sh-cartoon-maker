"""Build a standalone, unrigged KIKO hero model from the project reference.

Run from the project root:
    blender --background --python-exit-code 1 --python blender/kiko_final_model.py

Outputs KIKO_visual_model_v1.blend, assets/characters/kiko_final/KIKO.glb,
and full-body beauty views under review/kiko_visual/. All modeling geometry is
generated as custom, smooth swept/parametric meshes; no source master is edited.
"""
from __future__ import annotations

import json
import math
import array
import sys
from pathlib import Path

import bpy
from mathutils import Vector

BLENDER_DIR = Path(__file__).resolve().parent
ROOT = BLENDER_DIR.parent
REF = ROOT / "assets/hero/kiko.png"
MASTER = BLENDER_DIR / "KIKO_visual_model_v1.blend"
GLB = ROOT / "assets/characters/kiko_final/KIKO.glb"
REVIEW = ROOT / "review/kiko_visual"
TAU = math.tau


def clamp(x, a=0., b=1.):
    return max(a, min(b, x))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def link_object(name, mesh):
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.children.get("KIKO_CHARACTER").objects.link(obj)
    return obj


def assign_uv(mesh, vertices):
    """Give every separated mesh deterministic front-projected UVs."""
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    xs = [v[0] for v in vertices]
    zs = [v[2] for v in vertices]
    xmin, xmax = min(xs), max(xs)
    zmin, zmax = min(zs), max(zs)
    dx, dz = max(xmax - xmin, 1e-5), max(zmax - zmin, 1e-5)
    uv = mesh.uv_layers.active.data
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi = mesh.loops[li].vertex_index
            x, y, z = vertices[vi]
            uv[li].uv = ((x - xmin) / dx, (z - zmin) / dz)


def mesh_object(name, vertices, faces, material, *, smooth_faces=True, materials=()):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    for m in materials:
        mesh.materials.append(m)
    assign_uv(mesh, vertices)
    obj = link_object(name, mesh)
    for face in mesh.polygons:
        face.use_smooth = smooth_faces
    return obj


def profile_object(name, center, radius, material, *, sections=64, rings=40, power=1.):
    """Smooth closed superellipsoid with a round, non-toy profile."""
    cx, cy, cz = center
    rx, ry, rz = radius
    verts, faces = [], []
    for i in range(1, rings):
        lat = -math.pi / 2 + math.pi * i / rings
        c = math.cos(lat)
        spow = lambda v, p: math.copysign(abs(v) ** p, v)
        for j in range(sections):
            a = TAU * j / sections
            verts.append((cx + rx * spow(c * math.cos(a), power),
                          cy + ry * spow(c * math.sin(a), power),
                          cz + rz * spow(math.sin(lat), power)))
    bottom, top = len(verts), len(verts) + 1
    verts += [(cx, cy, cz - rz), (cx, cy, cz + rz)]
    rows = rings - 1
    for i in range(rows - 1):
        for j in range(sections):
            a = i * sections + j
            b = i * sections + (j + 1) % sections
            faces.append((a, b, b + sections, a + sections))
    for j in range(sections):
        nxt = (j + 1) % sections
        faces.append((bottom, nxt, j))
        a = (rows - 1) * sections + j
        b = (rows - 1) * sections + nxt
        faces.append((top, a, b))
    obj = mesh_object(name, verts, faces, material)
    return obj


def catmull(points, steps=8):
    p = [Vector(q) for q in points]
    out = []
    for i in range(len(p) - 1):
        a = p[max(0, i - 1)]
        b, c = p[i], p[i + 1]
        d = p[min(len(p) - 1, i + 2)]
        for j in range(steps):
            t = j / steps
            t2, t3 = t * t, t * t * t
            q = .5 * ((2 * b) + (-a + c) * t + (2*a - 5*b + 4*c - d) * t2 + (-a + 3*b - 3*c + d) * t3)
            out.append(q)
    out.append(p[-1])
    return out


def sweep(name, path, widths, depths, material, *, sides=24, reference=None, band_materials=(), band_ranges=()):
    """Closed high-resolution organic tube along a smoothed centerline."""
    raw = [Vector(p) for p in path]
    points = catmull(raw, 8)
    radii = catmull([(float(w), float(d), 0) for w, d in zip(widths, depths)], 8)
    verts, faces = [], []
    ref = Vector(reference or (0, 1, 0))
    for i, point in enumerate(points):
        tangent = (points[min(i + 1, len(points) - 1)] - points[max(0, i - 1)]).normalized()
        u = ref.cross(tangent)
        if u.length < 1e-5:
            u = Vector((1, 0, 0)).cross(tangent)
        u.normalize()
        v = tangent.cross(u).normalized()
        t = i / (len(points) - 1)
        w, d = max(.002, radii[i].x), max(.002, radii[i].y)
        for j in range(sides):
            a = TAU * j / sides
            co = point + u * (math.cos(a) * w) + v * (math.sin(a) * d)
            verts.append(tuple(co))
    for i in range(len(points) - 1):
        for j in range(sides):
            a, b = i*sides+j, i*sides+(j+1)%sides
            faces.append((a, b, b+sides, a+sides))
    verts.extend([tuple(points[0]), tuple(points[-1])])
    lo, hi = len(verts) - 2, len(verts) - 1
    for j in range(sides):
        faces.append((lo,(j+1)%sides,j))
        a=(len(points)-1)*sides+j
        b=(len(points)-1)*sides+(j+1)%sides
        faces.append((hi,a,b))
    obj = mesh_object(name, verts, faces, material, materials=band_materials)
    if band_materials:
        for poly in obj.data.polygons:
            i = poly.index // sides
            t = i / max(1, len(points)-1)
            for material_index, (start, end) in enumerate(band_ranges, 1):
                if start <= t < end:
                    poly.material_index = material_index
                    break
    return obj


def curve(name, points, radius, material, *, resolution=16, cyclic=False):
    data = bpy.data.curves.new(name + "_curve", "CURVE")
    data.dimensions, data.resolution_u = "3D", resolution
    data.bevel_depth, data.bevel_resolution = radius, 5
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points)-1)
    for b, point in zip(spline.bezier_points, points):
        b.co = point
        b.handle_left_type = b.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    data.materials.append(material)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.children.get("KIKO_CHARACTER").objects.link(obj)
    return obj


def material(name, color, roughness=.78, *, metallic=0., noise=0., bump=0.):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Specular IOR Level"].default_value = .3 if roughness > .5 else .48
    if noise:
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise
        tex.inputs["Detail"].default_value = 3
        tex.inputs["Roughness"].default_value = .72
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = .28
        ramp.color_ramp.elements[0].color = (*[c*.84 for c in color], 1)
        ramp.color_ramp.elements[1].position = .74
        ramp.color_ramp.elements[1].color = (*[min(c*1.12, 1) for c in color], 1)
        links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        if bump:
            bump_node = nodes.new("ShaderNodeBump")
            bump_node.inputs["Strength"].default_value = .16
            bump_node.inputs["Distance"].default_value = bump
            links.new(tex.outputs["Fac"], bump_node.inputs["Height"])
            links.new(bump_node.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def palette():
    return {
        "fur": material("Fur | deep teal blue-gray", (.075, .15, .18), .90, noise=42, bump=.009),
        "fur_light": material("Fur | soft teal highlights", (.12, .23, .245), .92, noise=38, bump=.007),
        "fur_shadow": material("Fur | deep shadow", (.055, .11, .14), .9, noise=24, bump=.012),
        "cream": material("Fur | warm integrated cream", (.72, .63, .50), .93, noise=34, bump=.006),
        "cream_light": material("Fur | pale muzzle", (.83, .74, .60), .9, noise=36, bump=.005),
        "orange": material("Fur | burnt apricot", (.77, .28, .10), .88, noise=26, bump=.012),
        "coral": material("Ear | warm coral velvet", (.72, .28, .25), .88, noise=24, bump=.008),
        "coral_light": material("Ear | soft coral center", (.92, .42, .31), .9, noise=22, bump=.006),
        "sclera": material("Eye | warm ivory", (.96, .91, .79), .27),
        "iris": material("Eye | amber iris", (.82, .32, .035), .3),
        "iris_light": material("Eye | honey iris center", (.98, .57, .095), .31),
        "pupil": material("Eye | deep warm pupil", (.025, .012, .009), .2),
        "glint": material("Eye | soft catchlight", (1., .96, .86), .16),
        "nose": material("Nose | rosewood", (.30, .105, .09), .4),
        "mouth": material("Mouth | warm dark umber", (.105, .028, .024), .8),
        "tongue": material("Mouth | muted rose", (.68, .22, .26), .62),
        "teeth": material("Teeth | soft ivory", (.95, .86, .70), .45),
        "scarf": material("Cloth | persimmon scarf", (.79, .17, .038), .94, noise=86, bump=.004),
        "scarf_light": material("Cloth | scarf highlights", (.96, .35, .085), .9, noise=76, bump=.003),
        "cloth": material("Cloth | worn jungle teal", (.14, .235, .17), .94, noise=110, bump=.003),
        "cloth_light": material("Cloth | faded olive panels", (.31, .34, .20), .95, noise=94, bump=.003),
        "leather": material("Leather | dark walnut", (.19, .075, .037), .84, noise=90, bump=.005),
        "leather_light": material("Leather | worn saddle", (.38, .19, .075), .83, noise=84, bump=.004),
        "stitch": material("Thread | flax", (.79, .55, .28), .95),
        "metal": material("Hardware | aged brass", (.53, .30, .075), .33, metallic=.58),
    }


def packed_color_textures(mats,size=256):
    """Bake repeatable fine color breakup into packed images for the GLB."""
    def lattice(ix,iy,seed,period):
        ix%=period; iy%=period
        value=(ix*374761393+iy*668265263+seed*1442695041)&0xffffffff
        value=((value^(value>>13))*1274126177)&0xffffffff
        value^=value>>16
        return value/4294967295
    def noise(x,y,seed,period):
        ix,iy=math.floor(x),math.floor(y)
        fx,fy=x-ix,y-iy
        sx,sy=smooth(fx),smooth(fy)
        a=lattice(ix,iy,seed,period)*(1-sx)+lattice(ix+1,iy,seed,period)*sx
        b=lattice(ix,iy+1,seed,period)*(1-sx)+lattice(ix+1,iy+1,seed,period)*sx
        return a*(1-sy)+b*sy
    variation=[]
    for y in range(size):
        for x in range(size):
            fx,fy=x/size,y/size
            n=(.52*noise(fx*8,fy*8,17,8)+.27*noise(fx*16,fy*16,31,16)
               +.14*noise(fx*32,fy*32,47,32)+.07*noise(fx*64,fy*64,61,64))
            variation.append(.90+.20*n)
    embedded=[]
    for m in mats.values():
        if not m.name.startswith(("Fur |","Cloth |","Leather |","Ear |")):
            continue
        bsdf=m.node_tree.nodes.get("Principled BSDF")
        color=tuple(bsdf.inputs["Base Color"].default_value[:3])
        pixels=array.array("f")
        for n in variation:
            pixels.extend(min(1.,c*n) for c in color)
            pixels.append(1.)
        image=bpy.data.images.new(m.name+" | embedded color",width=size,height=size,alpha=True)
        image.pixels.foreach_set(pixels)
        image.file_format="PNG"
        image.pack()
        texture=m.node_tree.nodes.new("ShaderNodeTexImage")
        texture.name=m.name+" | GLB color texture"
        texture.image=image
        m.node_tree.links.new(texture.outputs["Color"],bsdf.inputs["Base Color"])
        noises=[node for node in m.node_tree.nodes if node.type=="TEX_NOISE"]
        ramps=[node for node in m.node_tree.nodes if node.type=="VALTORGB"]
        if noises and ramps:
            ramp=ramps[0]
            m.node_tree.links.new(noises[0].outputs["Fac"],ramp.inputs["Fac"])
            for element,value in zip(ramp.color_ramp.elements,(.82,.96)):
                element.color=(value,value,value,1)
            m.node_tree.links.new(ramp.outputs["Color"],bsdf.inputs["Roughness"])
        embedded.append(image.name)
    return embedded


def build_skull(m):
    # Head is broad through the cheeks, tapering softly above the eye sockets.
    head = profile_object("KIKO | head and skull", (0, .015, 2.18), (.70, .52, .72), m["fur"], power=.92)
    # Cream field follows a broad convex face profile; raised center rounds into a
    # compact muzzle, while wide lower corners read as connected cheeks.
    verts, faces = [], []
    nz, nx = 31, 36
    for iz in range(nz):
        v = iz/(nz-1)
        z = 1.62 + v*.66
        width = (.035 + .435*math.sin(math.pi*v)**.78) * (.86 + .14*smooth(v/.22))
        for ix in range(nx):
            u = 2*ix/(nx-1)-1
            x = u*width
            # Conform around the face and flare the muzzle/cheek pad gently.
            skull = (x/.70)**2 + ((z-2.18)/.72)**2
            y = .015 - .52*math.sqrt(max(.03, 1-skull)) - .012
            muzzle_bulge = .12*math.exp(-((z-1.94)/.22)**2) * (1-.34*abs(u))
            cheek_full = .045*math.exp(-((abs(u)-.72)/.21)**2-((z-1.96)/.22)**2)
            verts.append((x, y-muzzle_bulge-cheek_full, z))
    for iz in range(nz-1):
        for ix in range(nx-1):
            a=iz*nx+ix
            faces.append((a,a+1,a+1+nx,a+nx))
    mask=mesh_object("KIKO | integrated cream cheeks and muzzle",verts,faces,m["cream_light"])
    solid=mask.modifiers.new("Fine integrated fur shell", "SOLIDIFY")
    solid.thickness=.018
    solid.offset=-.35
    sub=mask.modifiers.new("Soft facial surface", "SUBSURF")
    sub.levels=1
    sub.render_levels=2
    # Cheek tufts blend the painted mask edge into the blue-gray fur.
    for side, sign in (("L",1),("R",-1)):
        for i in range(3):
            z=1.91+i*.09
            x=sign*(.49+i*.035)
            sweep(f"KIKO | cheek tuft {side} {i+1}",
                  [(x,.0,z+.055),(x+sign*.075,-.06,z+.01),(x+sign*.13,-.02,z-.035)],
                  [.078,.05,.002],[.055,.035,.002],m["cream"],sides=18,reference=(0,1,0))
    def face_front(x,z):
        q=1-(x/.70)**2-((z-2.18)/.72)**2
        base=.015-.52*math.sqrt(max(.025,q))
        v=clamp((z-1.62)/.66)
        u=x/max(.035+.435*math.sin(math.pi*v)**.78,.1)
        return base-.12*math.exp(-((z-1.94)/.22)**2)*(1-.34*abs(u))

    # Oversized eyes are seated deeply into the skull, with a soft warm sclera.
    # The sculpted brow and lids come from the head silhouette, not raised rings.
    for side, sign in (("L",1),("R",-1)):
        cx=sign*.285
        profile_object(f"KIKO | eye sclera {side}",(cx,-.355,2.33),(.245,.145,.286),m["sclera"],sections=64,rings=40,power=.92)
        profile_object(f"KIKO | amber iris {side}",(cx-sign*.018,-.473,2.326),(.139,.039,.178),m["iris"],sections=48,rings=32,power=.88)
        profile_object(f"KIKO | honey iris inner {side}",(cx-sign*.015,-.503,2.316),(.080,.018,.111),m["iris_light"],sections=40,rings=28,power=.9)
        profile_object(f"KIKO | pupil {side}",(cx-sign*.012,-.518,2.326),(.066,.016,.116),m["pupil"],sections=40,rings=28,power=.82)
        profile_object(f"KIKO | eye glint large {side}",(cx-.052,-.531,2.405),(.032,.008,.041),m["glint"],sections=24,rings=18)
        profile_object(f"KIKO | eye glint small {side}",(cx+.047,-.529,2.35),(.012,.005,.016),m["glint"],sections=20,rings=14)
    # Small heart-triangle nose, its own smooth sculpted mesh.
    profile_object("KIKO | soft nose",(0,face_front(0,2.045)-.012,2.045),(.078,.048,.052),m["nose"],sections=40,rings=28,power=.7)
    # Compact smile, centered below a short muzzle. A tiny lower lip catches light.
    curve("KIKO | mouth smile line",[(x,face_front(x,z)-.016,z) for x,z in ((-.15,1.94),(-.085,1.905),(0,1.895),(.085,1.905),(.15,1.94))],.011,m["mouth"])
    curve("KIKO | lower lip",[(x,face_front(x,z)-.020,z) for x,z in ((-.065,1.888),(0,1.879),(.065,1.888))],.007,m["cream"])
    # Subtle freckles add a handmade face cue while keeping the eyes dominant.
    for side, sign in (("L",1),("R",-1)):
        for i,(x,z) in enumerate(((.40,1.99),(.48,2.03),(.39,2.07))):
            profile_object(f"KIKO | cheek freckle {side} {i+1}",(sign*x,face_front(sign*x,z)-.008,z),(.009,.005,.007),m["orange"],sections=16,rings=12)


def build_ears_and_crest(m):
    # Broad asymmetric fennec ears with a thick swept shell and recessed coral
    # bowl. Local centerline lives on the face side; both lean outward naturally.
    for side, sign, asym in (("L",1,.045),("R",-1,-.018)):
        path=[(sign*.46,.005,2.46),(sign*.78,.02,2.61),(sign*1.12,.035,2.78+asym),(sign*1.47,.05,2.89+asym),(sign*1.72,.075,2.87+asym)]
        widths=[.13,.29,.34,.26,.008]
        depths=[.12,.20,.19,.15,.006]
        path_points=catmull(path,8)
        sweep(f"KIKO | broad organic ear shell {side}",path,widths,depths,m["fur_light"],sides=32,reference=(0,1,0))
        # concave colored inset surface constructed as a domed, tapered grid.
        vtx, faces=[],[]
        rows, cols=28,24
        for i in range(rows):
            t=.12+.75*i/(rows-1)
            center=path_points[round(t*(len(path_points)-1))]
            tangent=(Vector(path[-1])-Vector(path[0])).normalized()
            side_axis=Vector((-sign*tangent.z,0,sign*tangent.x)).normalized()
            ri=clamp(t)*(len(widths)-1)
            interval=min(int(ri),len(widths)-2)
            frac=ri-interval
            shell_depth=depths[interval]*(1-frac)+depths[interval+1]*frac
            outer_width=widths[interval]*(1-frac)+widths[interval+1]*frac
            width=outer_width*.64*(math.sin(math.pi*(t-.09)/.84)**.55)
            for j in range(cols):
                u=2*j/(cols-1)-1
                point=center+side_axis*(u*width*.78)
                canal=.032*(1-u*u)*math.sin(math.pi*(t-.12)/.75)
                vtx.append((point.x,point.y-shell_depth-canal-.012,point.z))
        for i in range(rows-1):
            for j in range(cols-1):
                a=i*cols+j
                faces.append((a,a+1,a+1+cols,a+cols))
        inset=mesh_object(f"KIKO | recessed coral inner ear {side}",vtx,faces,m["coral"])
        solid=inset.modifiers.new("Velvet ear inset thickness","SOLIDIFY")
        solid.thickness=.016
        sub=inset.modifiers.new("Soft ear bowl","SUBSURF")
        sub.levels=1
        sub.render_levels=2
        # Warm central ridge follows the bowl's natural depth, never a flat triangle.
    # Nine swept locks overlap the forehead and sweep back asymmetrically.
    locks=[
        ([(0,-.01,2.69),(-.06,-.015,2.98),(-.21,.01,3.30),(-.36,.035,3.46)], [.17,.16,.10,.002], m["fur"]),
        ([(0,-.01,2.68),(-.08,-.015,2.94),(-.24,.01,3.24),(-.40,.035,3.38)], [.135,.13,.082,.002],m["fur"]),
        ([(.08,-.015,2.69),(.23,-.015,2.94),(.47,.025,3.15),(.65,.055,3.23)], [.135,.13,.078,.002],m["fur_light"]),
        ([(-.13,-.02,2.68),(-.28,-.01,2.88),(-.43,.025,3.01),(-.55,.06,3.08)], [.095,.08,.046,.002],m["orange"]),
        ([(.02,-.035,2.68),(.015,-.04,2.88),(-.12,-.02,3.12),(-.16,.02,3.23)], [.11,.12,.074,.002],m["fur_light"]),
        ([(.23,.005,2.66),(.37,.02,2.84),(.60,.055,2.99),(.80,.09,3.04)], [.10,.10,.062,.002],m["fur"]),
        ([(-.27,.015,2.62),(-.39,.045,2.78),(-.66,.08,2.90),(-.85,.10,2.94)], [.10,.085,.052,.002],m["fur_light"]),
        ([(.0,-.18,2.69),(-.08,-.23,2.90),(-.23,-.18,3.08),(-.33,-.12,3.16)], [.075,.070,.043,.002],m["orange"]),
        ([(.12,-.13,2.71),(.26,-.17,2.89),(.44,-.11,3.00),(.58,-.08,3.06)], [.085,.072,.045,.002],m["fur"]),
        ([(-.16,.08,2.65),(-.33,.13,2.81),(-.50,.16,2.90),(-.62,.18,2.96)], [.085,.068,.042,.002],m["fur_shadow"]),
    ]
    for i,(path,widths,mat) in enumerate(locks):
        sweep(f"KIKO | layered crest lock {i+1:02d}",path,widths,[w*.74 for w in widths],mat,sides=24,reference=(0,1,0))


def build_body(m):
    # Compact broad-chested silhouette with a soft shoulder-to-pelvis transition.
    body=profile_object("KIKO | compact torso",(0,.005,1.34),(.53,.39,.64),m["fur"],sections=64,rings=48,power=.88)
    pelvis=profile_object("KIKO | sturdy pelvis",(0,.025,.84),(.42,.34,.36),m["fur"],sections=56,rings=36,power=.9)
    # Large sculpted chest bib follows the torso front and has a fur-shaped hem.
    verts,faces=[],[]
    rows,cols=26,28
    for i in range(rows):
        v=i/(rows-1)
        z=1.68-v*.65
        half=.31*(.82+.18*math.sin(math.pi*v))
        for j in range(cols):
            u=2*j/(cols-1)-1
            x=u*half
            body_front=.005-.39*math.sqrt(max(.04,1-(x/.53)**2-((z-1.34)/.64)**2))
            scallop=.025*abs(u)**6
            verts.append((x,body_front-.015-scallop,z))
    for i in range(rows-1):
        for j in range(cols-1):
            a=i*cols+j
            faces.append((a,a+1,a+1+cols,a+cols))
    bib=mesh_object("KIKO | cream chest bib",verts,faces,m["cream"])
    solid=bib.modifiers.new("Soft chest fur thickness","SOLIDIFY"); solid.thickness=.025
    sub=bib.modifiers.new("Chest bib softness","SUBSURF"); sub.levels=1; sub.render_levels=2
    # Soft shoulder and elbow masses give the short limbs real anatomy.
    for side,sign in (("L",1),("R",-1)):
        profile_object(f"KIKO | shoulder {side}",(sign*.43,.005,1.58),(.27,.30,.27),m["fur"],sections=40,rings=28)
        profile_object(f"KIKO | elbow {side}",(sign*.60,-.015,1.20),(.18,.20,.19),m["fur_light"],sections=36,rings=24)
        # Open A-pose follows a broad diagonal from the shoulder, clear of vest
        # and pelvis, with a readable elbow and relaxed wrist.
        arm_path=[(sign*.43,.005,1.58),(sign*.68,-.015,1.75),(sign*.96,-.035,1.94),(sign*1.20,-.085,2.02)]
        sweep(f"KIKO | tapered forearm {side}",arm_path,[.225,.195,.152,.112],[.23,.18,.15,.11],m["fur"],sides=28,reference=(0,1,0))
        # Broad palm and separately articulated-looking organic fingers.
        sweep(f"KIKO | sculpted adventurer palm {side}",
              [(sign*1.20,-.08,2.02),(sign*1.27,-.135,2.015),(sign*1.25,-.18,1.99)],
              [.105,.175,.145],[.105,.14,.115],m["fur_light"],sides=28,reference=(0,1,0))
        for i in range(4):
            spread=(i-1.5)*.092
            root=(sign*(1.23+spread),-.25,2.01)
            mid=(root[0]+sign*spread*.15,-.29,1.93+abs(i-1.5)*.012)
            tip=(root[0]+sign*spread*.30,-.265,1.86+abs(i-1.5)*.020)
            sweep(f"KIKO | relaxed finger {side} {i+1}",[root,mid,tip],[.068,.058,.025],[.059,.05,.025],m["fur_light"],sides=18,reference=(0,1,0))
        thumb=[(sign*1.13,-.20,2.04),(sign*1.06,-.25,1.96),(sign*1.09,-.27,1.90)]
        sweep(f"KIKO | expressive thumb {side}",thumb,[.085,.07,.035],[.07,.06,.03],m["fur_light"],sides=18,reference=(0,1,0))
        # Thighs and calves retain rounded mass around knees and ankles.
        profile_object(f"KIKO | thigh {side}",(sign*.235,.02,.70),(.255,.28,.35),m["fur"],sections=40,rings=30,power=.9)
        profile_object(f"KIKO | knee {side}",(sign*.24,-.015,.48),(.18,.22,.19),m["fur_light"],sections=36,rings=26)
        leg_path=[(sign*.235,.02,.72),(sign*.245,.005,.58),(sign*.25,.005,.44),(sign*.25,-.045,.22)]
        sweep(f"KIKO | sturdy calf {side}",leg_path,[.24,.19,.15,.13],[.24,.205,.16,.13],m["fur"],sides=28,reference=(0,1,0))
        # Oversized soft boot-like paws with three readable toes.
        profile_object(f"KIKO | broad foot {side}",(sign*.25,-.16,.145),(.235,.40,.14),m["cream"],sections=48,rings=30,power=.75)
        for i in range(3):
            x=sign*.25+(i-1)*.105
            sweep(f"KIKO | toe {side} {i+1}",[(x,-.36,.17),(x+(i-1)*.018,-.49,.145),(x+(i-1)*.02,-.54,.13)],
                  [.084,.076,.035],[.073,.062,.032],m["cream_light"],sides=18,reference=(0,1,0))
        # Coral/cream knuckle tufts identify paws as furry and expressive.
        for i in range(3):
            x=sign*(1.16+i*.08)
            sweep(f"KIKO | palm fur tuft {side} {i+1}",[(x,-.255,2.13),(x+sign*.015,-.275,2.09),(x+sign*.025,-.265,2.06)],
                  [.034,.03,.002],[.028,.024,.002],m["cream"],sides=14,reference=(0,1,0))


def build_tail(m):
    # One smooth, broad swept plume. Its centerline curls left/up and terminates
    # in a tapered brush; material bands continue around the full circumference.
    path=[(-.08,.17,.86),(-.43,.36,.72),(-.86,.48,.70),(-1.22,.48,.83),(-1.47,.43,1.08),(-1.55,.34,1.36),(-1.49,.24,1.58),(-1.35,.12,1.72)]
    widths=[.17,.29,.40,.46,.45,.38,.27,.015]
    depths=[.17,.23,.29,.33,.34,.30,.23,.015]
    tail=sweep("KIKO | dominant curved plume tail",path,widths,depths,m["fur_light"],sides=36,reference=(0,1,0),
               band_materials=(m["cream"],m["orange"]),band_ranges=((.22,.34),(.48,.60),(.74,.86)))
    # Fine scalloped locks around outer silhouette reinforce plushness.
    for i in range(8):
        t=.27+i*.075
        pts=catmull(path,8)
        idx=round(t*(len(pts)-1))
        p=pts[idx]
        width=widths[min(round(t*(len(widths)-1)),len(widths)-1)]
        depth=depths[min(round(t*(len(depths)-1)),len(depths)-1)]
        sign=-1 if i%2 else 1
        origin=p+Vector((0,-depth*.72,width*.54))
        sweep(f"KIKO | tail plume lock {i+1:02d}",
              [origin,origin+Vector((sign*.055,-.025,.045)),origin+Vector((sign*.095,.005,.070))],
              [.060,.040,.002],[.038,.026,.002],m["cream"] if i%4==1 else (m["orange"] if i%5==2 else m["fur"]),
              sides=16,reference=(0,1,0))


def build_outfit(m):
    # Close-fitting layered vest panels follow the torso, with soft cloth response.
    vest=profile_object("KIKO | tailored explorer vest",(0,.015,1.34),(.555,.405,.60),m["cloth"],sections=64,rings=44,power=.90)
    # Open a centered front placket so the cream sculpted chest remains visible.
    # The body and chest bib remain continuous beneath this intentionally open garment.
    opening=[]
    for poly in vest.data.polygons:
        center=sum((vest.data.vertices[i].co for i in poly.vertices),Vector())/len(poly.vertices)
        if center.y < -.20 and abs(center.x) < .175 and .99 < center.z < 1.69:
            opening.append(poly.index)
    for index in opening:
        vest.data.polygons[index].use_smooth=False
    if opening:
        # Preserve a true open front by rebuilding the original parametric faces
        # without center-front panels, while retaining their shared side vertices.
        verts=[tuple(v.co) for v in vest.data.vertices]
        faces=[]
        for poly in vest.data.polygons:
            if poly.index not in opening:
                faces.append(tuple(poly.vertices))
        old=vest.data
        replacement=bpy.data.meshes.new("KIKO_Vest_open_front_mesh")
        replacement.from_pydata(verts,[],faces)
        replacement.materials.clear()
        for mat in old.materials:
            replacement.materials.append(mat)
        assign_uv(replacement,verts)
        vest.data=replacement
    # Open split center reveals the cream bib; two hand-shaped panels flank it.
    for sign,side in ((-1,"R"),(1,"L")):
        pts=[(sign*.095,-.377,1.70),(sign*.28,-.355,1.57),(sign*.34,-.37,1.30),(sign*.28,-.34,1.05),(sign*.18,-.335,.96)]
        widths=[.06,.12,.14,.13,.08]
        sweep(f"KIKO | vest front panel {side}",pts,widths,[w*.30 for w in widths],m["cloth_light"],sides=20,reference=(0,1,0))
        curve(f"KIKO | vest stitched edge {side}",[(x-sign*.07,y-.012,z) for x,y,z in pts],.008,m["stitch"])
    # Scarf is a broad sculpted cloth wrap, overlapping around the neck.
    scarf_path=[(-.37,-.08,1.79),(-.26,-.28,1.72),(0,-.365,1.71),(.26,-.28,1.73),(.37,-.08,1.79),(.26,.20,1.82),(0,.29,1.82),(-.25,.20,1.82),(-.37,-.08,1.79)]
    scarf=curve("KIKO | wrapped orange red scarf",scarf_path,.105,m["scarf"],cyclic=False)
    scarf.data.bevel_resolution=7
    # Two long, soft asymmetric scarf ends drape over the chest.
    sweep("KIKO | scarf tail flowing left",[(-.23,-.27,1.75),(-.39,-.32,1.54),(-.46,-.34,1.30),(-.38,-.39,1.16)],
          [.095,.095,.072,.004],[.032,.03,.025,.002],m["scarf"],sides=20,reference=(0,1,0))
    sweep("KIKO | scarf tail flowing right",[(.21,-.29,1.74),(.34,-.34,1.58),(.37,-.37,1.40),(.29,-.40,1.32)],
          [.085,.076,.06,.003],[.028,.026,.02,.002],m["scarf_light"],sides=20,reference=(0,1,0))
    # Cross-body harness, shoulder pads, stitching and aged brass hardware.
    curve("KIKO | left leather harness",[(-.38,-.02,1.65),(-.31,-.31,1.50),(-.20,-.38,1.28),(-.11,-.34,.98)],.038,m["leather"])
    curve("KIKO | right leather harness",[(.38,-.02,1.65),(.31,-.31,1.50),(.20,-.38,1.28),(.11,-.34,.98)],.038,m["leather"])
    curve("KIKO | cross chest strap",[(-.26,-.36,1.49),(0,-.405,1.35),(.26,-.36,1.49)],.034,m["leather_light"])
    profile_object("KIKO | chest harness brass clasp",(0,-.424,1.36),(.073,.028,.083),m["metal"],sections=32,rings=20,power=.82)
    # Belt wraps around pelvis; separate edge stitches and buckle.
    belt_pts=[]
    for i in range(17):
        a=TAU*i/16
        belt_pts.append((.395*math.cos(a),.31*math.sin(a),.91+.018*math.cos(a)))
    curve("KIKO | worn leather utility belt",belt_pts,.056,m["leather"],cyclic=True)
    curve("KIKO | belt flax stitching",[(.39*math.cos(TAU*i/20),.305*math.sin(TAU*i/20),.944) for i in range(20)],.006,m["stitch"],cyclic=True)
    profile_object("KIKO | brass belt buckle",(.0,-.352,.91),(.12,.035,.09),m["metal"],sections=32,rings=20,power=.82)
    profile_object("KIKO | buckle inset",(0,-.385,.91),(.065,.012,.047),m["leather"],sections=24,rings=16,power=.9)
    # Soft rolled pouches with flap, seams, straps, button and stitching.
    for side,sign in (("L",1),("R",-1)):
        x=sign*.39
        profile_object(f"KIKO | belt pouch body {side}",(x,-.20,.84),(.17,.14,.18),m["leather_light"],sections=36,rings=24,power=.82)
        profile_object(f"KIKO | belt pouch flap {side}",(x,-.292,.94),(.16,.035,.075),m["leather"],sections=32,rings=20,power=.88)
        curve(f"KIKO | pouch stitched seam {side}",[(x-.115,-.326,.94),(x,-.33,.915),(x+.115,-.326,.94)],.006,m["stitch"])
        profile_object(f"KIKO | pouch brass stud {side}",(x,-.335,.93),(.018,.009,.018),m["metal"],sections=16,rings=12)
    # Backpack is an independent softly structured pack, not a cuboid.
    profile_object("KIKO | padded explorer backpack",(0,.375,1.40),(.37,.24,.46),m["leather"],sections=48,rings=32,power=.86)
    profile_object("KIKO | backpack front pocket",(0,.565,1.30),(.24,.07,.20),m["backpack"] if "backpack" in m else m["leather_light"],sections=40,rings=28,power=.83)
    curve("KIKO | backpack pocket seam",[(-.16,.612,1.31),(0,.632,1.22),(.16,.612,1.31)],.008,m["stitch"])
    curve("KIKO | backpack left strap",[(-.34,.26,1.69),(-.32,.32,1.53),(-.27,.35,1.34),(-.22,.30,1.09)],.035,m["leather_light"])
    curve("KIKO | backpack right strap",[(.34,.26,1.69),(.32,.32,1.53),(.27,.35,1.34),(.22,.30,1.09)],.035,m["leather_light"])
    # Bedroll, water flask, map tube, compass and handmade bead charm.
    sweep("KIKO | rolled bedroll",[(-.33,.56,1.73),(-.12,.65,1.79),(.12,.65,1.79),(.33,.56,1.73)],
          [.10,.11,.11,.10],[.12,.13,.13,.12],m["cloth_light"],sides=24,reference=(0,0,1))
    profile_object("KIKO | brass compass on harness",(.25,-.403,1.12),(.075,.035,.086),m["metal"],sections=32,rings=20,power=.8)
    curve("KIKO | compass leather loop",[(.25,-.37,1.20),(.31,-.39,1.27),(.36,-.35,1.20)],.018,m["leather"])
    profile_object("KIKO | small travel flask",(-.47,.10,1.08),(.12,.12,.20),m["leather_light"],sections=32,rings=24,power=.8)
    curve("KIKO | flask neck",[(-.47,.10,1.28),(-.47,.10,1.35)],.035,m["metal"])
    # Wrapped forearms and calves: spiral leather strips follow limb contours.
    for side,sign in (("L",1),("R",-1)):
        for j in range(3):
            t=.60+j*.065
            u=(t-.54)/.46
            x=sign*(.43+(.96-.43)*u)
            z=1.58+.36*u
            curve(f"KIKO | forearm wrap {side} {j+1}",[(x-.105,-.06,z-.035),(x,-.245,z),(x+.105,-.06,z+.035)],.027,m["cloth_light"] if j==1 else m["leather"])
        for j in range(3):
            z=.22+j*.08
            x=sign*.25
            curve(f"KIKO | calf wrap {side} {j+1}",[(x-.105,-.05,z-.035),(x,-.16,z),(x+.105,-.05,z+.035)],.026,m["cloth_light"] if j==1 else m["leather"])
    # Small hand-sewn crest patch on the vest.
    profile_object("KIKO | stitched explorer emblem",(-.25,-.377,1.31),(.075,.016,.105),m["leather_light"],sections=28,rings=18,power=.86)
    curve("KIKO | emblem stitched mark",[(-.27,-.396,1.27),(-.25,-.403,1.34),(-.22,-.396,1.29)],.008,m["stitch"])


def fuse_skin_foundation(fur_material):
    """Voxel-blend the connected skin masses into a single rig-ready surface."""
    prefixes=("KIKO | head and skull","KIKO | compact torso","KIKO | sturdy pelvis",
              "KIKO | shoulder ","KIKO | elbow ","KIKO | tapered forearm ",
              "KIKO | thigh ","KIKO | knee ","KIKO | sturdy calf ","KIKO | broad organic ear shell ")
    parts=[o for o in bpy.data.objects if o.type=="MESH" and o.name.startswith(prefixes)]
    if len(parts)<15:
        raise RuntimeError(f"Skin foundation unexpectedly has only {len(parts)} connected sculpt masses")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
        obj.data.materials.clear()
        obj.data.materials.append(fur_material)
        for poly in obj.data.polygons:
            poly.material_index=0
    bpy.context.view_layer.objects.active=parts[0]
    bpy.ops.object.join()
    skin=bpy.context.object
    skin.name="KIKO | continuous sculpted body, head and ears"
    skin.data.name="KIKO_Continuous_Skin_Topology"
    remesh=skin.modifiers.new("Organic voxel-unified anatomy","REMESH")
    remesh.mode="VOXEL"
    remesh.voxel_size=.022
    remesh.use_smooth_shade=True
    bpy.context.view_layer.objects.active=skin
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth=bpy.ops.object.modifier_add(type="SMOOTH")
    modifier=skin.modifiers[-1]
    modifier.factor=1.15
    modifier.iterations=3
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    for p in skin.data.polygons:
        p.use_smooth=True
    assign_uv(skin.data,[tuple(v.co) for v in skin.data.vertices])
    return skin


def make_stage():
    world=bpy.context.scene.world
    if world is None:
        world=bpy.data.worlds.new("KIKO studio world")
        bpy.context.scene.world=world
    world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(.19,.22,.26,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=.34
    floor_mat=material("Studio | muted dusk",(.12,.16,.20),.84)
    bpy.ops.mesh.primitive_plane_add(size=2000, location=(0,0,-.018))
    floor=bpy.context.object
    floor.name="STUDIO | ground"
    floor.data.materials.append(floor_mat)
    for collection in list(floor.users_collection):
        collection.objects.unlink(floor)
    bpy.context.scene.collection.children.get("STUDIO").objects.link(floor)
    floor["exclude_from_glb"]=True
    def area(name,loc,power,color,size,target=(0,0,1.65)):
        data=bpy.data.lights.new(name,"AREA")
        data.energy,data.color,data.shape=power,color,"DISK"
        data.size=size
        obj=bpy.data.objects.new(name,data)
        bpy.context.scene.collection.children.get("STUDIO").objects.link(obj)
        obj.location=loc
        obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
        obj["exclude_from_glb"]=True
    area("STUDIO | warm key",(-3.7,-4.3,6.2),1050,(1.,.82,.67),4.0)
    area("STUDIO | cool fill",(4.2,-3.2,3.7),780,(.62,.77,1.),4.2)
    area("STUDIO | warm rim",(-1.2,3.2,5.0),1250,(1.,.48,.25),3.0)
    data=bpy.data.cameras.new("KIKO hero camera")
    cam=bpy.data.objects.new("KIKO hero camera",data)
    bpy.context.scene.collection.children.get("STUDIO").objects.link(cam)
    cam.location=(4.7,-8.8,4.05)
    target=Vector((0,0,1.77))
    cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.lens=58
    bpy.context.scene.camera=cam
    cam["exclude_from_glb"]=True


def prepare():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    model=bpy.data.collections.new("KIKO_CHARACTER")
    stage=bpy.data.collections.new("STUDIO")
    scene.collection.children.link(model)
    scene.collection.children.link(stage)
    # Mesh routines link directly into this collection.
    return model


def export_glb(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    assets=[o for o in bpy.data.objects if not o.get("exclude_from_glb")]
    for obj in assets:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=assets[0]
    bpy.ops.export_scene.gltf(filepath=str(path),export_format="GLB",use_selection=True,
                              export_apply=True,export_animations=False,export_skins=False,
                              export_materials="EXPORT",export_texcoords=True,export_normals=True,
                              export_cameras=False,export_lights=False,export_yup=True)
    for obj in assets:
        obj.select_set(False)


def render_review():
    REVIEW.mkdir(parents=True,exist_ok=True)
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in scene.render.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
    if hasattr(scene.eevee,"taa_render_samples"):
        scene.eevee.taa_render_samples=64
    elif hasattr(scene.eevee,"taa_samples"):
        scene.eevee.taa_samples=64
    scene.render.resolution_x=1024
    scene.render.resolution_y=1024
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    scene.render.film_transparent=False
    scene.view_settings.view_transform="AgX"
    scene.view_settings.look="AgX - Medium High Contrast"
    scene.render.image_settings.color_mode="RGB"
    scene.render.filepath=str(REVIEW/"three_quarter.png")
    bpy.ops.render.render(write_still=True)
    cam=scene.camera
    target=Vector((0,0,1.75))
    views={"front":(0,-9,2.0),"side":(9,0,2.0),"back":(0,9,2.0),"three_quarter":(4.7,-8.8,4.05)}
    for name,loc in views.items():
        cam.location=loc
        cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
        cam.data.lens=58
        scene.render.filepath=str(REVIEW/(name+".png"))
        bpy.ops.render.render(write_still=True)
    cam.location=(.30,-5.4,2.45)
    cam.rotation_euler=(Vector((0,-.1,2.29))-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.lens=68
    scene.render.resolution_x=1024
    scene.render.resolution_y=768
    scene.render.filepath=str(REVIEW/"face_closeup.png")
    bpy.ops.render.render(write_still=True)


def report_model():
    objects=[o for o in bpy.data.objects if o.name.startswith("KIKO |")]
    meshes=[o for o in objects if o.type=="MESH"]
    uv_missing=[o.name for o in meshes if not o.data.uv_layers]
    material_missing=[o.name for o in meshes if not o.data.materials]
    nonmanifold=[]
    for obj in meshes:
        bm=None
        # The export preflight uses polygon edge-use counts without external modules.
        counts={}
        for poly in obj.data.polygons:
            for key in poly.edge_keys:
                edge=tuple(sorted(key));counts[edge]=counts.get(edge,0)+1
        open_edges=sum(count!=2 for count in counts.values())
        if open_edges:
            nonmanifold.append({"object":obj.name,"boundary_or_nonmanifold_edges":open_edges,
                                "surface":obj.name.startswith(("KIKO | integrated cream","KIKO | cream chest","KIKO | recessed coral","KIKO | tailored explorer vest"))})
    stats={"object_count":len(objects),"mesh_objects":len(meshes),
           "vertices":sum(len(o.data.vertices) for o in meshes),
           "polygons":sum(len(o.data.polygons) for o in meshes),
           "materials":sorted({m.name for o in meshes for m in o.data.materials if m}),
           "uv_missing":uv_missing,"material_missing":material_missing,
           "open_surfaces_expected":[e["object"] for e in nonmanifold if e["surface"]],
           "other_nonmanifold": [e for e in nonmanifold if not e["surface"]],
           "facing":"front is -Y; world Z is up","rigged":False}
    return stats


def main():
    if not REF.is_file() or not REF.stat().st_size:
        raise RuntimeError(f"Authoritative KIKO image is missing: {REF}")
    model=prepare()
    m=palette()
    build_skull(m)
    build_ears_and_crest(m)
    build_body(m)
    build_tail(m)
    build_outfit(m)
    fuse_skin_foundation(m["fur"])
    packed=packed_color_textures(m)
    make_stage()
    stats=report_model()
    if stats["uv_missing"] or stats["material_missing"] or stats["other_nonmanifold"]:
        raise RuntimeError("Model preflight failed: "+json.dumps({k:stats[k] for k in ("uv_missing","material_missing","other_nonmanifold")}))
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in scene.render.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
    scene.unit_settings.system="METRIC"
    scene["character_name"]="KIKO"
    scene["asset_description"]="Unrigged stylized jungle explorer, modeled to assets/hero/kiko.png"
    scene["reference_image"]="assets/hero/kiko.png"
    bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
    render_review()
    export_glb(GLB)
    stats.update({"blend":str(MASTER.relative_to(ROOT)),"glb":str(GLB.relative_to(ROOT)),
                  "reference":str(REF.relative_to(ROOT)),"render_views":[str((REVIEW/(n+".png")).relative_to(ROOT)) for n in ("front","three_quarter","side","back","face_closeup")],
                  "export_selection_objects":len([o for o in bpy.data.objects if not o.get("exclude_from_glb")]),
                  "embedded_textures":packed,"texture_count":len(packed),"uv_missing":stats["uv_missing"]})
    report=ROOT/"reports/kiko_visual_model_v1.json"
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(stats,indent=2)+"\n")
    # Save the delivered native file with studio, materials and camera configured.
    bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
    print(f"MODEL PREFLIGHT PASS: {stats['vertices']} vertices, {stats['polygons']} polygons, {stats['mesh_objects']} separated meshes")
    print(f"BLEND: {MASTER}\nGLB: {GLB}\nREPORT: {report}",flush=True)


if __name__=="__main__":
    main()
