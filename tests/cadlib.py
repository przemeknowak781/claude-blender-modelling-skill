"""Measurement and validation helpers, verified against Blender 5.2.0 LTS.

This module is the executable form of recipe R-101. The eval suite imports it;
the skill's reference files quote it. Both must stay in sync — the identifier
validator enforces that every API name used here exists in api_dump.json.

Everything here is read-only unless the name says otherwise, and nothing uses
``bpy.ops`` for measurement, so it is safe in background mode and in loops.
"""
import bmesh
import bpy
from mathutils import Vector


# --------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------
def evaluated_bmesh(obj, depsgraph=None):
    """Return a NEW bmesh of *obj* WITH modifiers applied.

    Measuring ``obj.data`` instead of this is the single most common reason an
    assertion passes while the geometry is wrong (diagnostics D-04).
    Caller owns the result and must call ``.free()``.
    """
    depsgraph = depsgraph or bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    me = eval_obj.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    eval_obj.to_mesh_clear()
    return bm


def base_bmesh(obj):
    """Return a NEW bmesh of *obj* WITHOUT modifiers. Caller must free it."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    return bm


# --------------------------------------------------------------------------
# topology
# --------------------------------------------------------------------------
def non_manifold_edges(bm):
    """Edges not shared by exactly two faces. Wire and boundary edges count."""
    return [e for e in bm.edges if not e.is_manifold]


def boundary_edges(bm):
    """Edges with exactly one face: the mesh's open border."""
    return [e for e in bm.edges if e.is_boundary]


def is_closed(bm):
    """True when the mesh has no boundary. Volume is meaningless otherwise."""
    return len(boundary_edges(bm)) == 0


def is_manifold(bm):
    """Closed AND every edge shared by exactly two faces.

    Closed and manifold are different tests; a mesh can be watertight and still
    have an edge shared by three faces.
    """
    return is_closed(bm) and len(non_manifold_edges(bm)) == 0


def inconsistent_normal_edges(bm):
    """Manifold edges whose two faces disagree about winding direction.

    Manifoldness does NOT catch flipped normals: a flipped patch still leaves
    every edge shared by exactly two faces. This is the separate test, and it
    is what R-105 asserts against.
    """
    bad = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        dirs = []
        for f in e.link_faces:
            for loop in f.loops:
                if loop.edge == e:
                    dirs.append(loop.vert == e.verts[0])
                    break
        if len(dirs) == 2 and dirs[0] == dirs[1]:
            bad.append(e)
    return bad


def loose_verts(bm):
    return [v for v in bm.verts if not v.link_edges]


def loose_edges(bm):
    return [e for e in bm.edges if not e.link_faces]


def shells(bm):
    """Partition faces into connected components. Returns a list of face lists."""
    seen, out = set(), []
    for face in bm.faces:
        if face.index in seen:
            continue
        stack, comp = [face], []
        seen.add(face.index)
        while stack:
            f = stack.pop()
            comp.append(f)
            for edge in f.edges:
                for nf in edge.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index)
                        stack.append(nf)
        out.append(comp)
    return out


def duplicate_vert_count(bm, threshold=1e-5):
    """How many vertices Merge by Distance would remove at *threshold*.

    Non-destructive: runs the merge on a copy.
    """
    tmp = bm.copy()
    before = len(tmp.verts)
    bmesh.ops.remove_doubles(tmp, verts=tmp.verts[:], dist=threshold)
    removed = before - len(tmp.verts)
    tmp.free()
    return removed


# --------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------
def volume(bm, signed=False):
    """Enclosed volume. Only meaningful when ``is_closed(bm)``.

    A negative signed volume means the normals point inward.
    """
    vol = bm.calc_volume(signed=True)
    return vol if signed else abs(vol)


def surface_area(bm):
    return sum(f.calc_area() for f in bm.faces)


def bbox_local(bm):
    """(min_corner, max_corner, dimensions) in the bmesh's own coordinates."""
    if not bm.verts:
        return Vector((0, 0, 0)), Vector((0, 0, 0)), Vector((0, 0, 0))
    xs = [v.co for v in bm.verts]
    lo = Vector((min(c.x for c in xs), min(c.y for c in xs), min(c.z for c in xs)))
    hi = Vector((max(c.x for c in xs), max(c.y for c in xs), max(c.z for c in xs)))
    return lo, hi, hi - lo


def bbox_world(obj, depsgraph=None):
    """World-space (min, max, dimensions) of the EVALUATED object.

    ``obj.dimensions`` reflects the base mesh and object scale only; it does not
    see modifiers. This does.
    """
    bm = evaluated_bmesh(obj, depsgraph)
    mat = obj.matrix_world
    pts = [mat @ v.co for v in bm.verts]
    bm.free()
    if not pts:
        return Vector((0, 0, 0)), Vector((0, 0, 0)), Vector((0, 0, 0))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi, hi - lo


def centre_of_mass(bm):
    """Area-weighted centroid of the surface."""
    total, acc = 0.0, Vector((0.0, 0.0, 0.0))
    for f in bm.faces:
        a = f.calc_area()
        total += a
        acc += f.calc_center_median() * a
    return acc / total if total else Vector((0.0, 0.0, 0.0))


def degenerate_faces(bm, min_area=1e-9):
    return [f for f in bm.faces if f.calc_area() < min_area]


def ngons(bm, max_sides=4):
    return [f for f in bm.faces if len(f.verts) > max_sides]


# --------------------------------------------------------------------------
# self-intersection (R-111)
# --------------------------------------------------------------------------
def self_intersecting_face_count(bm):
    """Count faces involved in self-intersection.

    Uses ``bmesh.ops.triangulate`` on a copy plus the BVH tree overlap test.
    No built-in operator reports this, so it is computed rather than queried.
    """
    from mathutils.bvhtree import BVHTree
    tmp = bm.copy()
    bmesh.ops.triangulate(tmp, faces=tmp.faces[:])
    tmp.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(tmp, epsilon=0.0)
    overlap = tree.overlap(tree)
    bad = set()
    for i, j in overlap:
        if i == j:
            continue
        fi, fj = tmp.faces[i], tmp.faces[j]
        # Faces sharing a vertex touch legitimately; only count genuine crossings.
        if set(v.index for v in fi.verts) & set(v.index for v in fj.verts):
            continue
        bad.add(i)
        bad.add(j)
    tmp.free()
    return len(bad)


# --------------------------------------------------------------------------
# the R-101 report
# --------------------------------------------------------------------------
def diagnose(obj, evaluated=True, merge_threshold=1e-5, check_self_intersect=True):
    """Full diagnostic report for *obj*. This is recipe R-101.

    Every repair recipe re-runs this and diffs the numbers; a repair that fixes
    one metric while wrecking another has failed.
    """
    bm = evaluated_bmesh(obj) if evaluated else base_bmesh(obj)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    closed = is_closed(bm)
    lo, hi, dim = bbox_local(bm)
    report = {
        "name": obj.name,
        "evaluated": evaluated,
        "verts": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "tris": sum(len(f.verts) - 2 for f in bm.faces),
        "ngons": len(ngons(bm)),
        "non_manifold_edges": len(non_manifold_edges(bm)),
        "inconsistent_normal_edges": len(inconsistent_normal_edges(bm)),
        "boundary_edges": len(boundary_edges(bm)),
        "closed": closed,
        "manifold": is_manifold(bm),
        "loose_verts": len(loose_verts(bm)),
        "loose_edges": len(loose_edges(bm)),
        "shells": len(shells(bm)),
        "duplicate_verts": duplicate_vert_count(bm, merge_threshold),
        "degenerate_faces": len(degenerate_faces(bm)),
        "area": surface_area(bm),
        "volume": volume(bm) if closed else None,
        "signed_volume": volume(bm, signed=True) if closed else None,
        "normals_inward": (volume(bm, signed=True) < 0) if closed else None,
        "bbox_min": tuple(lo),
        "bbox_max": tuple(hi),
        "dimensions": tuple(dim),
        "object_scale": tuple(obj.scale),
        "scale_applied": all(abs(s - 1.0) < 1e-6 for s in obj.scale),
    }
    report["self_intersecting_faces"] = (
        self_intersecting_face_count(bm) if check_self_intersect else None
    )
    bm.free()
    return report


def format_report(rep):
    order = ["name", "verts", "faces", "tris", "shells", "non_manifold_edges",
             "inconsistent_normal_edges", "boundary_edges", "closed", "manifold", "loose_verts",
             "duplicate_verts", "degenerate_faces", "ngons",
             "self_intersecting_faces", "normals_inward", "area", "volume",
             "dimensions", "scale_applied"]
    lines = []
    for k in order:
        v = rep.get(k)
        if isinstance(v, float):
            v = f"{v:.6g}"
        elif isinstance(v, tuple):
            v = "(" + ", ".join(f"{c:.6g}" for c in v) + ")"
        lines.append(f"  {k:24s} {v}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# offset feasibility (R-202)
# --------------------------------------------------------------------------
def concave_offset_conflicts(obj, thickness):
    """Concave folds too tight to survive an inward offset of *thickness*.

    Offsetting both faces of a concave fold inward by t makes them meet at
    ``t / tan(theta/2)`` from the shared edge, where theta is the interior
    angle. If either face does not extend that far, the offset surface runs
    past it and self-intersects. Solidify will not warn you; it just produces
    inverted geometry that survives to the exporter.

    Returns a list of (edge_index, interior_angle_deg, required_reach, actual).

    NOTE on the sign convention: ``calc_face_angle_signed`` returns the
    deviation from flat, not the interior angle, and NEGATIVE means concave.
    Interior angle is ``pi - abs(signed)``.
    """
    import math

    bm = evaluated_bmesh(obj)
    bm.normal_update()
    out = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        signed = e.calc_face_angle_signed(0.0)
        if signed >= 0:                       # convex or flat: no conflict
            continue
        interior = math.pi - abs(signed)
        if interior <= 1e-6:
            continue
        reach = thickness / math.tan(interior / 2.0)
        origin = e.verts[0].co
        along = (e.verts[1].co - origin).normalized()
        for f in e.link_faces:
            far = max((v.co - origin - along * ((v.co - origin).dot(along))).length
                      for v in f.verts)
            if far < reach:
                out.append((e.index, math.degrees(interior), reach, far))
                break
    bm.free()
    return out
