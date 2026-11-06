"""Append a bedding edit call to this file before sending it to 3D Jutsu."""

import re

import bpy
from mathutils import Matrix, Vector

# Original showroom mesh names and their pivots in the original mesh coordinates.
_LEGACY_PARTS = {
    "Oak platform": ("frame", "Frame", (0, 0, 0)),
    "Oak shadow line": ("frame_trim", "Frame trim", (0, 0, 0)),
    "Mattress": ("mattress", "Mattress", (0, 0, 0)),
    "Draped duvet": ("duvet", "Duvet", (0, 0, 0.66)),
    "Bed pillow 1": ("pillow_left", "Left pillow", (-0.43, 0.77, 0.632)),
    "Bed pillow 2": ("pillow_right", "Right pillow", (0.43, 0.77, 0.632)),
}
_LEGACY_PRINTS = {
    "Duvet / Cherry stitches": "duvet",
    "Bed pillow 1 / Cherry stitches": "pillow_left",
    "Bed pillow 2 / Cherry stitches": "pillow_right",
}


def _ref_id(obj):
    return obj.name.split(" / ", 1)[0]


def _reference(reference, category):
    key = reference.strip().lower()
    matches = []
    for obj in bpy.context.scene.objects:
        if obj.get("reference_category") != category:
            continue
        path = obj.get("source_image", "").lower()
        filename = path.rsplit("/", 1)[-1]
        if key in {_ref_id(obj).lower(), obj.name.lower(), path, filename, filename.removesuffix(".jpg")}:
            matches.append(obj)
    if len(matches) != 1:
        raise ValueError(f"Expected one {category} reference for {reference!r}; found {len(matches)}.")
    return matches[0]


def _part(bed, role):
    matches = [obj for obj in bed.children if obj.type == "MESH" and obj.get("bedding_part") == role]
    if len(matches) != 1:
        raise ValueError(f"Expected one {role!r} in {bed.name}; found {len(matches)}. "
                         "Check the part ID or upgrade an older showroom with upgrade_bedding_parts().")
    return matches[0]


def _center_anchors(duvet):
    return [obj for obj in duvet.children if obj.get("bedding_anchor") == "duvet_center"]


def _legacy_name(obj):
    return re.sub(r"\.\d{3,}$", "", obj.name)


def upgrade_bedding_parts():
    """Add part IDs, pivots, and anchors to existing showrooms."""
    beds = [obj for obj in bpy.context.scene.objects if obj.get("reference_category") == "bed"]
    if not beds:
        raise ValueError("No bedding references were found in this showroom.")

    plans = []
    for bed in beds:
        parts, rename = {}, {}
        for old_name, (role, label, pivot) in _LEGACY_PARTS.items():
            candidates = [obj for obj in bed.children if obj.type == "MESH"
                          and (obj.get("bedding_part") == role
                               or (not obj.get("bedding_part") and _legacy_name(obj) == old_name))]
            if len(candidates) != 1:
                raise ValueError(f"Cannot resolve {role!r} in {bed.name}.")
            part = candidates[0]
            parts[role] = part
            if not part.get("bedding_part"):
                rename[role] = (label, Vector(pivot))
        prints = [(child, parts[_LEGACY_PRINTS[_legacy_name(child)]])
                  for child in bed.children if _legacy_name(child) in _LEGACY_PRINTS]

        duvet = parts["duvet"]
        anchors = _center_anchors(duvet)
        if len(anchors) > 1:
            raise ValueError(f"Multiple center anchors in {bed.name}.")
        point = None
        if not anchors:
            offset = rename["duvet"][1] if "duvet" in rename else Vector((0, 0, 0))
            hit, surface, _, _ = duvet.ray_cast(offset + Vector((0, 0, 2)), (0, 0, -1))
            if not hit:
                raise ValueError(f"Cannot locate the center of {duvet.name}.")
            point = surface - offset
        if rename or prints or point is not None:
            plans.append((bed, parts, rename, prints, point))

    for bed, parts, rename, prints, point in plans:
        prefix = _ref_id(bed)
        for role, (label, pivot) in rename.items():
            part = parts[role]
            if pivot.length:
                if part.data.users > 1:
                    part.data = part.data.copy()
                part.data.transform(Matrix.Translation(-pivot))
                part.matrix_basis = part.matrix_basis @ Matrix.Translation(pivot)
            part.name = f"{prefix} / {label}"
            part["bedding_part"] = role
        bpy.context.view_layer.update()

        for detail, part in prints:
            inverse = part.matrix_world.inverted() @ bed.matrix_world @ detail.matrix_parent_inverse
            detail.parent = part
            detail.matrix_parent_inverse = inverse
            detail.name = f"{part.name} / Cherry stitches"
            detail["bedding_detail"] = "print"

        if point is not None:
            duvet = parts["duvet"]
            anchor = bpy.data.objects.new(f"{prefix} / Duvet center", None)
            duvet.users_collection[0].objects.link(anchor)
            anchor.parent = duvet
            anchor.location = point
            anchor.empty_display_size = 0.10
            anchor["bedding_anchor"] = "duvet_center"

    return {"bed_sets": len(beds), "updated_bed_sets": len(plans)}


def _solid_material(part, finish):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", finish):
        raise ValueError("Use a six-digit sRGB color such as #2459B6.")
    name = f"{part.name} / {finish.upper()}"
    mat = bpy.data.materials.get(name)
    if mat is not None and mat.get("bedding_color") == finish.upper():
        return mat

    def linear(value):
        return value / 12.92 if value < 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    rgba = tuple(linear(int(finish[i:i + 2], 16) / 255) for i in (1, 3, 5)) + (1.0,)
    mat = bpy.data.materials.new(name)
    mat["bedding_color"] = finish.upper()
    mat.diffuse_color = rgba
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Roughness"].default_value = 0.56 if part["bedding_part"] in {"frame", "frame_trim"} else 0.79
    return mat


def set_bedding_material(reference, role, finish):
    """Set one part's material by exact name or hex color."""
    bed = _reference(reference, "bed")
    part = _part(bed, role)
    material = _solid_material(part, finish) if finish.startswith("#") else bpy.data.materials.get(finish)
    if material is None:
        raise ValueError(f"Material {finish!r} was not found.")
    printed_details = [obj for obj in part.children if obj.get("bedding_detail") == "print"]
    for obj in [part, *printed_details]:
        for slot in obj.material_slots:
            slot.link = "OBJECT"
            slot.material = material
    return {"reference": _ref_id(bed), "part": role, "object": part.name, "material": material.name}


def _heart_source(variant):
    if variant == "REF-07":
        return _reference(variant, "heart")
    palette = _reference("REF-15", "heart")
    matches = [obj for obj in palette.children if _ref_id(obj) == variant]
    if len(matches) != 1:
        raise ValueError("Choose REF-07 or a HEART-01 through HEART-08 variant.")
    return matches[0]


def _copy_children(source, parent, group):
    for child in source.children:
        copy = child.copy()
        if child.data is not None:
            copy.data = child.data.copy()
        group.objects.link(copy)
        copy.name = f"{parent.name} / {child.name}"
        copy.parent = parent
        _copy_children(child, copy, group)


def place_center_heart(reference, variant="REF-07"):
    """Place a copy of a showroom heart on the center of the duvet."""
    bed = _reference(reference, "bed")
    duvet = _part(bed, "duvet")
    anchors = _center_anchors(duvet)
    if len(anchors) != 1:
        raise ValueError(f"Expected one duvet center anchor in {bed.name}; found {len(anchors)}.")
    anchor = anchors[0]
    variant = variant.strip().upper()
    source = _heart_source(variant)
    placed = [obj for obj in anchor.children if obj.get("bedding_attachment") == "center_heart"]
    if placed:
        if len(placed) != 1 or placed[0].get("heart_variant") != variant:
            raise ValueError(f"{bed.name} already has a heart at its center.")
        heart = placed[0]
    else:
        group = anchor.users_collection[0]
        heart = bpy.data.objects.new(f"{_ref_id(bed)} / Center heart", None)
        group.objects.link(heart)
        heart.parent = anchor
        heart["bedding_attachment"] = "center_heart"
        heart["heart_variant"] = variant
        heart.empty_display_size = 0.10
        _copy_children(source, heart, group)
    heart.location = (0, 0, 0.002)
    return {"reference": _ref_id(bed), "object": heart.name, "anchor": anchor.name, "heart": variant}
