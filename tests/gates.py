"""W-000 gate checks G1-G4, as executable functions. This is recipe R-007.

Each gate returns (passed: bool, report: dict). A gate that fails sends you
back to the phase that caused it -- never forward with the error masked.
"""
import os

import bpy
import cadlib


def gate_g1(scene=None, objects=None, expect_unit_scale=1.0,
            expect_system='METRIC', require_saved=True):
    """G1 - scene setup: units, unit scale, object scale, file saved."""
    scene = scene or bpy.context.scene
    objects = objects if objects is not None else [
        o for o in scene.objects if o.type == 'MESH'
    ]
    us = scene.unit_settings
    unscaled = [o.name for o in objects
                if not all(abs(s - 1.0) < 1e-6 for s in o.scale)]
    saved = bool(bpy.data.filepath) if require_saved else True

    report = {
        "unit_system": us.system,
        "unit_scale": us.scale_length,
        "length_unit": us.length_unit,
        "objects_checked": len(objects),
        "objects_with_unapplied_scale": unscaled,
        "file_saved_as": bpy.data.filepath or None,
    }
    passed = (us.system == expect_system
              and abs(us.scale_length - expect_unit_scale) < 1e-9
              and not unscaled
              and saved)
    return passed, report


def gate_g2(objects_nominal, tolerance):
    """G2 - dimensional blockout: measured bounding boxes match the table.

    *objects_nominal* maps object name -> (x, y, z) nominal dimensions.
    """
    rows, worst = {}, 0.0
    for name, nominal in objects_nominal.items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            rows[name] = {"error": "object not found"}
            worst = float("inf")
            continue
        _, _, dims = cadlib.bbox_world(obj)
        err = max(abs(a - b) for a, b in zip(dims, nominal))
        worst = max(worst, err)
        rows[name] = {"nominal": tuple(nominal),
                      "measured": tuple(round(d, 6) for d in dims),
                      "max_error": err}
    return worst <= tolerance, {"tolerance": tolerance,
                                "worst_error": worst,
                                "objects": rows}


def gate_g3(objects, merge_threshold=1e-5, allow_open=False,
            check_self_intersect=True):
    """G3 - geometric validation: manifold, clean, no self-intersections."""
    rows, ok = {}, True
    for obj in objects:
        rep = cadlib.diagnose(obj, merge_threshold=merge_threshold,
                              check_self_intersect=check_self_intersect)
        problems = []
        if rep["non_manifold_edges"]:
            problems.append(f"{rep['non_manifold_edges']} non-manifold edges")
        if not allow_open and not rep["closed"]:
            problems.append(f"{rep['boundary_edges']} boundary edges")
        if rep["duplicate_verts"]:
            problems.append(f"{rep['duplicate_verts']} duplicate verts")
        if rep["inconsistent_normal_edges"]:
            problems.append(
                f"{rep['inconsistent_normal_edges']} inconsistent normals")
        if check_self_intersect and rep["self_intersecting_faces"]:
            problems.append(
                f"{rep['self_intersecting_faces']} self-intersecting faces")
        if rep["degenerate_faces"]:
            problems.append(f"{rep['degenerate_faces']} degenerate faces")
        rows[obj.name] = {"problems": problems,
                          "volume": rep["volume"],
                          "area": rep["area"]}
        ok = ok and not problems
    return ok, {"objects": rows}


def gate_g4(obj, export_path, tolerance, importer='stl', **import_kwargs):
    """G4 - export round trip: reimport and compare against the original.

    Leaves the current file untouched: the reimport happens in a fresh scene,
    so call this last, after saving.
    """
    original = cadlib.diagnose(obj, check_self_intersect=False)
    if not os.path.exists(export_path):
        return False, {"error": f"export file missing: {export_path}"}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.data.objects.keys())
    if importer == 'stl':
        bpy.ops.wm.stl_import(filepath=export_path, **import_kwargs)
    elif importer == 'obj':
        bpy.ops.wm.obj_import(filepath=export_path, **import_kwargs)
    else:
        return False, {"error": f"unsupported importer {importer!r}"}

    new = [o for o in bpy.data.objects if o.name not in before]
    if not new:
        return False, {"error": "reimport produced no object"}
    back = new[0]
    if not all(abs(s - 1.0) < 1e-6 for s in back.scale):
        back.select_set(True)
        bpy.context.view_layer.objects.active = back
        bpy.ops.object.transform_apply(location=False, rotation=False,
                                       scale=True)
    rep = cadlib.diagnose(back, check_self_intersect=False)

    dim_err = max(abs(a - b)
                  for a, b in zip(rep["dimensions"], original["dimensions"]))
    vol_err = (abs(rep["volume"] - original["volume"]) / original["volume"]
               if original["volume"] else float("inf"))
    report = {
        "original_dimensions": tuple(round(d, 6) for d in original["dimensions"]),
        "reimported_dimensions": tuple(round(d, 6) for d in rep["dimensions"]),
        "max_dimension_error": dim_err,
        "volume_error_fraction": vol_err,
        "tolerance": tolerance,
        "reimported_manifold": rep["manifold"],
    }
    return (dim_err <= tolerance and rep["manifold"]), report


# --- W-000 Phase 4: canonical modifier stack order -------------------------
CANONICAL_ORDER = [
    'MIRROR', 'ARRAY', 'SCREW',          # 1. topology generators
    'BOOLEAN',                            # 2. cuts, before bevelling
    'SOLIDIFY',                           # 3. thickness on a settled shape
    'WELD',                               # 4. cleanup
    'BEVEL',                              # 5. rounding, late
    'SUBSURF', 'REMESH',                  # 6. subdivision or remesh
    'TRIANGULATE', 'DECIMATE',            # 7. export only
    'WEIGHTED_NORMAL',                    # 8. shading only, always last
]

# Pairs whose inversion is a known, specific failure rather than a style point.
HARD_RULES = [
    ('BOOLEAN', 'BEVEL',
     "Boolean must precede Bevel, or the new cut edges are left sharp."),
    ('MIRROR', 'BEVEL',
     "Mirror must precede Bevel, or the bevel runs through the mirror plane."),
    ('SOLIDIFY', 'BEVEL',
     "Solidify must precede Bevel, or the bevel is applied to a surface that "
     "has not got its thickness yet."),
]


def check_stack_order(obj):
    """Report modifier-stack ordering violations. Returns (ok, report).

    The canonical order is a DEFAULT, not a law; unusual geometry can justify
    departing from it. The HARD_RULES, though, have a specific broken outcome
    each, so they are reported separately from soft ordering drift.
    """
    types = [m.type for m in obj.modifiers]
    rank = {t: i for i, t in enumerate(CANONICAL_ORDER)}

    soft = []
    known = [t for t in types if t in rank]
    for i in range(len(known) - 1):
        if rank[known[i]] > rank[known[i + 1]]:
            soft.append(f"{known[i]} appears before {known[i + 1]}")

    hard = []
    for earlier, later, why in HARD_RULES:
        if earlier in types and later in types:
            if types.index(earlier) > types.index(later):
                hard.append({"found": f"{later} before {earlier}",
                             "rule": f"{earlier} -> {later}",
                             "why": why})

    return (not hard), {"stack": types,
                        "hard_violations": hard,
                        "soft_violations": soft}


def reorder_to_canonical(obj):
    """Sort the stack into canonical order, returning the new type sequence.

    Uses ``modifier_move_to_index`` rather than deleting and recreating, so
    every modifier keeps its settings.
    """
    rank = {t: i for i, t in enumerate(CANONICAL_ORDER)}
    target = sorted(obj.modifiers,
                    key=lambda m: rank.get(m.type, len(CANONICAL_ORDER)))
    for want_index, mod in enumerate(target):
        current = list(obj.modifiers).index(mod)
        if current != want_index:
            with bpy.context.temp_override(object=obj):
                bpy.ops.object.modifier_move_to_index(modifier=mod.name,
                                                      index=want_index)
    return [m.type for m in obj.modifiers]
