"""Build the Kirsh Home product preview in an empty Blender/3D Jutsu scene."""

import math

import bpy
from mathutils import Vector

# IDs follow the filenames in image/. Each root keeps its exact source path.
REFERENCES = [
    ("Cherry print bed", "0b4fec116e960bd32069bdeb62c2248a", "bed", "cherry"),
    ("Ivory bed", "1452932dfc5ea9b84c220bc8d3d93b61", "bed", "ivory"),
    ("Navy pillow", "25fb0f61a4f1177801800fd875212452", "pillow", "navy"),
    ("Blush quilted pad", "2c9fdc65ab74137f780ab55686b11b92", "pad", "pink"),
    ("Gray gingham bed", "2cbf9bbe01a737c1a91c7634795f2902", "bed", "gingham"),
    ("Berry pinstripe bed", "41b4c6a0ac5f05e348c2954fdb926f21", "bed", "rib"),
    ("Ivory heart", "531bdcccd2d3a0cff1722b9f25f2dd7c", "heart", "ivory"),
    ("Ivory pillow", "550a4809cd6fbae5cb4c55154f301436", "pillow", "ivory"),
    ("Blush bed", "55518d2f3f207db93eb349a91a4519b0", "bed", "pink"),
    ("Navy bed", "7074c7e0990d134f6f2af6c824bc75a2", "bed", "navy"),
    ("Pastel stripe pillow", "72fd9c8ed3d07ec34034643ac35a16d4", "pillow", "pastel"),
    ("Berry ruffle pillow", "74527b6181b98a7163d6d830dec7c56b", "pillow", "rib_horizontal"),
    ("Red stripe bed", "74a632303a7e3cdad247d1a241d4ecc3", "bed", "red_stripe"),
    ("Gingham ruffle pillow", "74aee43a562365f05f32ad231154b055", "pillow", "gingham"),
    ("Heart colorways", "80371d3ab9d52a5627c40887d40accb7", "heart_set", None),
    ("Berry quilted pad", "8c2ddffc9504db389d3eb7162082519e", "pad", "berry"),
    ("Blue stripe bed", "ac175f5adab7df7a62c85f36242581b1", "bed", "blue_stripe"),
    ("Red stripe pillow", "b3caf4496b040dc8deebd36fdea431bd", "pillow", "red_block"),
    ("Ivory ruffle pillow", "c592120b5096c424e323e8f97c634362", "pillow", "ivory"),
    ("Cherry print pillow", "dc26a3f8ce74d55f826fb4e20d6a7ac7", "pillow", "cherry"),
    ("Blush ruffle pillow", "ee6a6cf8cd00241edee54b7bd825cf64", "pillow", "pink"),
    ("Ivory pad", "fc8faa93d69a8427bacb156549ddb526", "pad", "ivory"),
]

# Colors are sRGB. The bands are assigned to mesh faces so they travel in a GLB.
SWATCHES = {
    "Ivory": "F2EBE3", "Petal": "F0AECA", "Petal seam": "C76C93",
    "Midnight": "202847", "Berry": "951F42", "Berry shadow": "69152C",
    "Cherry": "BD233B", "Cherry leaf": "42705E", "Poppy": "BD3648",
    "Porcelain blue": "9EAAC1", "Pebble": "B6ADAA", "Charcoal": "736969",
    "Mint": "A5BDB7", "Powder": "D9AAB4", "Buttercream": "E3D4B7",
}
FABRICS = {
    "ivory": ("u", 1, ("Ivory",)),
    "cherry": ("u", 1, ("Ivory",)),
    "pink": ("u", 1, ("Petal",)),
    "navy": ("u", 1, ("Midnight",)),
    "berry": ("u", 1, ("Berry",)),
    "gingham": ("check", 8, ("Ivory", "Pebble", "Charcoal")),
    "rib": ("u", 14, ("Berry", "Berry shadow", "Berry")),
    "rib_horizontal": ("v", 8, ("Berry", "Berry", "Berry shadow")),
    "red_stripe": ("u", 4, ("Ivory", "Ivory", "Poppy", "Poppy", "Ivory", "Ivory")),
    "red_block": ("u", 2, ("Ivory", "Ivory", "Poppy", "Poppy", "Ivory", "Ivory")),
    "blue_stripe": ("u", 8, ("Ivory", "Porcelain blue", "Porcelain blue", "Ivory")),
    "pastel": ("v", 3, ("Ivory", "Mint", "Ivory", "Powder", "Ivory", "Porcelain blue")),
}

scene = bpy.context.scene
if scene.objects:
    raise RuntimeError("Open a new empty scene before building the product preview.")
scene.unit_settings.system = "METRIC"


def collection(name):
    group = bpy.data.collections.new(name)
    scene.collection.children.link(group)
    return group


def linear(value):
    return value / 12.92 if value < 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def material(name, hexcode, roughness=0.79):
    mat = bpy.data.materials.new(name)
    color = tuple(linear(int(hexcode[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)
    mat.diffuse_color = color
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    return mat


cloth = {name: material("Fabric / " + name, color) for name, color in SWATCHES.items()}
wood = material("Bed / Honey oak", "B5835E", 0.54)
wood_edge = material("Bed / Oak edge", "83563E", 0.58)
floor = material("Studio / Limestone", "D7CEC4", 0.58)
plinth = material("Studio / Biscuit", "EEE0D2", 0.61)
rose_plinth = material("Studio / Dusty rose", "DFBEBF", 0.65)
ink = material("Studio / Oxblood ink", "5E2639", 0.69)


def object_from(data, name, group, location=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, data)
    group.objects.link(obj)
    obj.parent = parent
    obj.location = location
    return obj


def mesh(name, group, vertices, faces, materials, parent=None, slots=None, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    for mat in materials:
        data.materials.append(mat)
    for face in data.polygons:
        face.use_smooth = smooth
        if slots is not None:
            face.material_index = slots[face.index]
    data.update()
    return object_from(data, name, group, parent=parent)


def box(name, group, center, size, mat, bevel=0.0, parent=None):
    x, y, z = (length / 2 for length in size)
    vertices = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
                (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7)]
    obj = mesh(name, group, vertices, faces, [mat], parent)
    obj.location = center
    if bevel:
        edge = obj.modifiers.new("Rounded edges", "BEVEL")
        edge.width = bevel
        edge.segments = 3
        edge.harden_normals = True
        obj.modifiers.new("Corner normals", "WEIGHTED_NORMAL")
    return obj


def label(name, body, location, size, group, align="LEFT"):
    # Convert the built-in font to mesh so text needs no fonts in the GLB.
    data = bpy.data.curves.new(name, "FONT")
    data.body, data.size, data.align_x = body, size, align
    data.space_character = 1.12
    source = object_from(data, name, group)
    evaluated = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    geometry = bpy.data.meshes.new_from_object(evaluated)
    bpy.data.objects.remove(source, do_unlink=True)
    bpy.data.curves.remove(data)
    geometry.materials.append(ink)
    return object_from(geometry, name, group, location)


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera(name, position, target, scale):
    data = bpy.data.cameras.new(name)
    data.type, data.ortho_scale = "ORTHO", scale
    obj = object_from(data, name, rig, position)
    aim(obj, target)
    return obj


def light(name, kind, position, energy, target):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    if kind == "SUN":
        data.angle = math.radians(20)
    else:
        data.shadow_soft_size = 4.0
    obj = object_from(data, name, rig, position)
    aim(obj, target)


def fabric_slot(mode, repeats, band_count, u, v):
    if mode == "check":
        return (math.floor((u + 1) * repeats) % 2
                + math.floor((v + 1) * repeats) % 2)
    coordinate = v if mode == "v" else u
    return math.floor((coordinate + 1) * 0.5 * repeats * band_count) % band_count


def cloth_shell(name, group, parent, style, top, bottom, nx, ny):
    mode, repeats, swatches = FABRICS[style]
    unique_swatches = list(dict.fromkeys(swatches))
    bands = [unique_swatches.index(swatch) for swatch in swatches]
    if mode == "check":
        divisions = 2 * repeats
        nx = math.ceil(nx / divisions) * divisions
        ny = math.ceil(ny / divisions) * divisions
    elif len(swatches) > 1:
        divisions = repeats * len(swatches)
        if mode == "u":
            nx = math.ceil(nx / divisions) * divisions
        else:
            ny = math.ceil(ny / divisions) * divisions
    u_steps = [2 * i / nx - 1 for i in range(nx + 1)]
    v_steps = [2 * j / ny - 1 for j in range(ny + 1)]
    upper = [top(u, v) for v in v_steps for u in u_steps]
    lower = [bottom(u, v) for v in v_steps for u in u_steps]
    faces, slots = [], []
    offset, stride = len(upper), nx + 1
    for j in range(ny):
        v = (v_steps[j] + v_steps[j + 1]) / 2
        for i in range(nx):
            u = (u_steps[i] + u_steps[i + 1]) / 2
            a = j * stride + i
            face = (a, a + 1, a + stride + 1, a + stride)
            faces.extend((face, tuple(k + offset for k in reversed(face))))
            band = fabric_slot(mode, repeats, len(swatches), u, v)
            slots.extend((bands[band], bands[band]))

    border = (list(range(nx))
              + [j * stride + nx for j in range(ny)]
              + [ny * stride + i for i in range(nx, 0, -1)]
              + [j * stride for j in range(ny, 0, -1)])
    for a, b in zip(border, border[1:] + border[:1]):
        faces.append((b, a, a + offset, b + offset))
        slots.append(0)
    obj = mesh(name, group, upper + lower, faces, [cloth[s] for s in unique_swatches],
               parent, slots, smooth=True)
    outline = [tuple((a + b) / 2 for a, b in zip(upper[i], lower[i])) for i in border]
    return obj, outline


def cherry_print(name, group, parent, top, columns, rows):
    vertices, faces, slots = [], [], []

    def patch(points, slot):
        start = len(vertices)
        for u, v in points:
            x, y, z = top(u, v)
            vertices.append((x, y, z + 0.005))
        faces.append(tuple(range(start, len(vertices))))
        slots.append(slot)

    for row in range(rows):
        for col in range(columns):
            u = (col + 0.5 + 0.14 * (row % 2)) * 1.72 / columns - 0.86
            v = (row + 0.5) * 1.52 / rows - 0.76
            direction = -1 if (row + col) % 2 else 1
            for side in (-1, 1):
                cu, cv = u + side * 0.018, v - 0.012 * direction
                patch([(cu + 0.016 * math.cos(i * math.tau / 8),
                        cv + 0.021 * math.sin(i * math.tau / 8)) for i in range(8)], 0)
                stem = [(cu - 0.004, cv), (cu + 0.004, cv),
                        (u + 0.004, v + 0.043 * direction),
                        (u - 0.004, v + 0.043 * direction)]
                patch(stem if direction > 0 else reversed(stem), 1)
    return mesh(name, group, vertices, faces, [cloth["Cherry"], cloth["Cherry leaf"]], parent, slots)


def ruffle(name, group, parent, border, center, width, mat):
    vertices = list(border)
    for i, (x, y, z) in enumerate(border):
        wave = math.sin(math.tau * i * 24 / len(border))
        radial = Vector((x - center[0], y - center[1])).normalized()
        vertices.append((x + radial.x * width * (1 + 0.18 * wave),
                         y + radial.y * width * (1 + 0.18 * wave),
                         z + 0.012 * wave))
    count = len(border)
    faces = [(i, i + count, (i + 1) % count + count, (i + 1) % count)
             for i in range(count)]
    mesh(name, group, vertices, faces, [mat], parent, smooth=True)


def soft_panel(name, group, parent, center, size, loft, style, trim=None, quilt=False, bedding_part=None):
    cx, cy, cz = (0, 0, 0) if bedding_part else center
    width, depth = size

    def sample(u, v, upper):
        x = cx + u * width * 0.5 * (0.96 + 0.04 * v * v - 0.085 * v ** 12)
        y = cy + v * depth * 0.5 * (0.89 + 0.11 * u * u - 0.08 * u ** 12)
        puff = ((1 - u * u) * (1 - v * v)) ** 0.49
        if upper:
            relief = 0.0
            if quilt:
                relief = 0.005 * math.cos(5 * math.pi * (u + v)) * math.cos(5 * math.pi * (u - v)) * puff
            z = cz + 0.008 + loft * puff + relief
        else:
            z = cz - 0.008 - loft * 0.57 * puff
        return x, y, z

    top = lambda u, v: sample(u, v, True)
    bottom = lambda u, v: sample(u, v, False)
    nx, ny = (36, 30) if quilt else (18, 14)
    panel, border = cloth_shell(name, group, parent, style, top, bottom, nx, ny)
    if bedding_part:
        panel.location = center
        panel["bedding_part"] = bedding_part
        parent = panel
    if trim:
        ruffle(name + " / Ruffle", group, parent, border, (cx, cy, cz), 0.039, cloth[trim])
    if style == "cherry":
        detail = cherry_print(name + " / Cherry stitches", group, parent, top, 6, 4)
        if bedding_part:
            detail["bedding_detail"] = "print"


def bed(group, parent, style):
    ref_id = parent.name.split(" / ", 1)[0]
    for role, label, height, size, mat, bevel in (
        ("frame", "Frame", 0.145, (1.85, 2.08, 0.28), wood, 0.025),
        ("frame_trim", "Frame trim", 0.034, (1.81, 2.04, 0.066), wood_edge, 0.017),
        ("mattress", "Mattress", 0.42, (1.86, 2.09, 0.28), cloth["Ivory"], 0.095),
    ):
        part = box(f"{ref_id} / {label}", group, (0, 0, height), size, mat, bevel, parent)
        part["bedding_part"] = role

    def duvet(u, v):
        side = abs(u) ** 8
        foot = ((1 - v) * 0.5) ** 12
        drape = max(0.31 * side, 0.34 * foot)
        fold = 0.075 * math.exp(-((v - 0.86) / 0.16) ** 2)
        ripple = 0.012 * (side * math.sin(v * 15) + foot * math.cos(u * 24))
        ripple += 0.009 * math.sin(u * 10 + 2 * v) * math.sin(math.pi * v) ** 2
        return (u * (1.06 + 0.06 * side),
                0.93 * v - 0.18 - 0.22 * (1 - (1 - foot) ** 2.7),
                -drape + fold + ripple)

    def duvet_back(u, v):
        x, y, z = duvet(u, v)
        return x, y, z - 0.018

    duvet_obj, _ = cloth_shell(f"{ref_id} / Duvet", group, parent, style, duvet, duvet_back, 30, 20)
    duvet_obj.location.z = 0.66
    duvet_obj["bedding_part"] = "duvet"
    if style == "cherry":
        detail = cherry_print(f"{duvet_obj.name} / Cherry stitches", group, duvet_obj, duvet, 12, 8)
        detail["bedding_detail"] = "print"
    for side, x in (("left", -0.43), ("right", 0.43)):
        soft_panel(f"{ref_id} / {side.title()} pillow", group, parent, (x, 0.77, 0.632),
                   (0.81, 0.54), 0.115, style, bedding_part=f"pillow_{side}")

    bpy.context.view_layer.update()
    hit, point, _, _ = duvet_obj.ray_cast((0, 0, 2), (0, 0, -1))
    if not hit:
        raise RuntimeError(f"Could not locate the center of {duvet_obj.name}.")
    anchor = object_from(None, f"{ref_id} / Duvet center", group, point, duvet_obj)
    anchor["bedding_anchor"] = "duvet_center"
    anchor.empty_display_size = 0.10


def heart(name, group, parent, center, style, trim=None):
    cx, cy, cz = center
    width, depth, loft = 0.63, 0.60, 0.093

    def profile(angle):
        # Same heart silhouette used for the original ad's cushion, laid flat.
        return (13 * math.cos(angle) - 5 * math.cos(2 * angle)
                - 2 * math.cos(3 * angle) - math.cos(4 * angle) + 2.35) / 16

    def sample(u, v, upper):
        angle = math.asin((0.997 * abs(u)) ** (1 / 3))
        high, low = profile(angle), profile(math.pi - angle)
        x = cx + u * width * 0.5
        y = cy + (low + (high - low) * (v + 1) / 2) * depth * 0.55
        puff = ((1 - u * u) * (1 - v * v)) ** 0.46
        z = cz + 0.006 + loft * puff if upper else cz - 0.006 - loft * 0.57 * puff
        return x, y, z

    top = lambda u, v: sample(u, v, True)
    bottom = lambda u, v: sample(u, v, False)
    _, border = cloth_shell(name, group, parent, style, top, bottom, 24, 16)
    if trim:
        ruffle(name + " / Ruffle", group, parent, border, center, 0.024, cloth[trim])
    if style == "cherry":
        cherry_print(name + " / Cherry stitches", group, parent, top, 5, 4)


studio = collection("00 / Showroom")
rig = collection("05 / Cameras and lighting")
groups = {
    "bed": collection("01 / Bed sets"),
    "pillow": collection("02 / Pillows"),
    "heart": collection("03 / Heart cushions"),
    "pad": collection("04 / Pads"),
}

scene.camera = camera("CAM / Catalog", (3.8, -15.8, 15.5), (0.0, 0.61, 0.04), 14.60)
camera("CAM / Bed sets", (3.5, -4.4, 8.2), (0, 2.86, 0.46), 10.70)
camera("CAM / Pillows and hearts", (-1.0, -6.1, 8.0), (-1.53, -1.60, 0.17), 7.75)
camera("CAM / Pads", (5.9, -4.6, 6.1), (3.70, -1.65, 0.15), 4.30)
scene.world = bpy.data.worlds.new("Studio ambient")
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.42, 0.36, 0.41, 1)
background.inputs["Strength"].default_value = 0.40
light("LGT / Soft window key", "SUN", (-5.5, -3.8, 9.0), 1.75, (0, 1, 0))
light("LGT / Bounce fill", "POINT", (5.0, 1.2, 7.0), 1250.0, (0, 1, 0))

box("Limestone showroom", studio, (0, 0.53, -0.117), (11.48, 11.17, 0.234), floor, 0.110)
box("Bed display / Near tier", studio, (0, 1.60, 0.15), (10.34, 2.56, 0.30), plinth, 0.068)
box("Bed display / Rear tier", studio, (0, 4.29, 0.27), (10.34, 2.68, 0.54), plinth, 0.068)
box("Pillow display", studio, (-3.07, -1.58, 0.09), (4.18, 3.73, 0.18), plinth, 0.057)
box("Heart display", studio, (0.59, -1.58, 0.09), (2.97, 3.73, 0.18), rose_plinth, 0.057)
box("Pad display", studio, (3.69, -1.58, 0.09), (2.91, 3.73, 0.18), plinth, 0.057)

label("Title", "KIRSH HOME", (-5.10, -4.37, 0.003), 0.52, studio)
label("Edition", "B E D D I N G   S T U D Y   /   0 1", (-5.09, -4.70, 0.003), 0.16, studio)
label("Reference count", "22 REFERENCES   /   29 MODELS", (5.10, -4.38, 0.003), 0.19, studio, "RIGHT")
label("Bed section", "01   BED SETS", (-4.94, 0.39, 0.302), 0.15, studio)
label("Pillow section", "02   PILLOWS", (-4.93, -3.23, 0.182), 0.17, studio)
label("Heart section", "03   HEART CUSHIONS", (-0.68, -3.23, 0.182), 0.17, studio)
label("Pad section", "04   PADS", (2.44, -3.23, 0.182), 0.17, studio)

ruffled_pillows = {12: "Berry shadow", 14: "Charcoal", 19: "Buttercream", 21: "Petal seam"}
heart_variants = [
    ("Berry pinstripe", "rib", None), ("Blue stripe", "blue_stripe", None),
    ("Blush ruffle", "pink", "Petal seam"), ("Ivory ruffle", "ivory", "Buttercream"),
    ("Red stripe", "red_block", None), ("Navy", "navy", None),
    ("Cherry print", "cherry", None), ("Gray gingham", "gingham", None),
]
counts = dict.fromkeys(groups, 0)
for ref, (name, stem, kind, style) in enumerate(REFERENCES, 1):
    category = "heart" if kind == "heart_set" else kind
    group = groups[category]
    index = counts[category]
    counts[category] += 1

    if kind == "bed":
        row, column = divmod(index, 4)
        location = (-3.72 + 2.48 * column, (1.73, 4.39)[row], (0.30, 0.54)[row])
    elif kind == "pillow":
        row, column = divmod(index, 3)
        location = (-4.38 + 1.30 * column, -2.64 + 1.09 * row, 0.18)
    elif kind == "pad":
        location = (3.69, -2.59 + 1.09 * index, 0.18)
    elif kind == "heart":
        location = (-0.30, -2.64, 0.18)
    else:
        location = (0, 0, 0.18)

    root = object_from(None, f"REF-{ref:02d} / {name}", group, location)
    root.empty_display_size = 0.12
    root["source_image"] = f"image/{stem}.jpg"
    root["reference_category"] = category

    if kind == "bed":
        bed(group, root, style)
    elif kind == "pillow":
        soft_panel(name, group, root, (0, 0, 0.078), (1.08, 0.79), 0.122,
                   style, trim=ruffled_pillows.get(ref))
    elif kind == "pad":
        soft_panel(name, group, root, (0, 0, 0.026), (0.88, 0.99), 0.031,
                   style, quilt=style != "ivory")
    elif kind == "heart":
        heart(name, group, root, (0, 0, 0.059), style)
    else:
        for variant, (label_text, finish, trim) in enumerate(heart_variants, 1):
            row, column = divmod(variant, 3)
            variant_root = object_from(None, f"HEART-{variant:02d} / {label_text}", group,
                                       (-0.30 + 0.90 * column, -2.64 + 1.09 * row, 0), root)
            heart(label_text + " heart", group, variant_root, (0, 0, 0.059), finish, trim)

# EEVEE has a different engine identifier in Blender 4.3 and 5.2.
scene.render.engine = "BLENDER_EEVEE" if bpy.app.version >= (5, 0, 0) else "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 1600
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.render.image_settings.file_format = "PNG"

bpy.context.view_layer.update()
result = {
    "reference_count": len(REFERENCES),
    "model_count": len(REFERENCES) + len(heart_variants) - 1,
    "reference_groups": counts,
    "camera": scene.camera.name,
}
