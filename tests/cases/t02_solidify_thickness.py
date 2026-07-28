"""T-02 - constant 18 mm thickness on a curved open surface."""
import bpy
import cadlib

ID = "T-02"
PRIORITY = "P1"
TASK = "Give a variable-curvature open surface a uniform 18 mm wall thickness."
RECIPES = ["R-201", "R-202"]

THICKNESS = 0.018


def sample_points(obj, samples):
    """Face centres and normals from the BASE surface, away from the border.

    Sampling the solidified result directly does not work: its rim strips are
    faces too, and a ray cast from one rim face hits the opposite rim a
    fraction of a millimetre away. Thickness must be probed from the original
    surface, not from the shell it produced.
    """
    bm = cadlib.base_bmesh(obj)
    bm.faces.ensure_lookup_table()
    interior = [f for f in bm.faces
                if not any(e.is_boundary for e in f.edges)
                and not any(e.is_boundary for v in f.verts for e in v.link_edges)]
    step = max(len(interior) // samples, 1)
    picked = [(f.calc_center_median().copy(), f.normal.copy())
              for f in interior[::step]][:samples]
    bm.free()
    return picked


def measure_thickness(obj, samples=10):
    """Measure wall thickness at *samples* points. Returns metres.

    Two casts per point: the first finds the outer skin, the second finds the
    inner skin behind it. The gap between them is the wall.
    """
    from mathutils.bvhtree import BVHTree
    bm = cadlib.evaluated_bmesh(obj)
    tree = BVHTree.FromBMesh(bm)
    eps = 1e-6
    out = []
    for centre, normal in sample_points(obj, samples):
        origin = centre + normal * (THICKNESS * 2.0)
        hit1, _, _, d1 = tree.ray_cast(origin, -normal, THICKNESS * 6)
        if hit1 is None:
            continue
        hit2, _, _, d2 = tree.ray_cast(hit1 - normal * eps, -normal,
                                       THICKNESS * 6)
        if hit2 is None:
            continue
        out.append((hit1 - hit2).length + eps)
    bm.free()
    return out


def run():
    bpy.ops.wm.open_mainfile(filepath="tests/fixtures/curved_surface.blend")
    obj = bpy.data.objects["Surface"]

    before = cadlib.diagnose(obj)

    # R-201: Solidify in NON_MANIFOLD mode gives even thickness on open surfaces.
    mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    mod.solidify_mode = 'NON_MANIFOLD'
    mod.thickness = THICKNESS
    mod.offset = -1.0
    mod.use_even_offset = True

    after = cadlib.diagnose(obj)
    samples = measure_thickness(obj)
    in_range = [t for t in samples if 0.0175 <= t <= 0.0185]

    # Volume of a thin shell should approach (one-sided area) x thickness.
    expected_vol = before["area"] * THICKNESS
    vol_err = abs(after["volume"] - expected_vol) / expected_vol

    return [
        ("input surface was open",
         before["closed"] is False, f"boundary_edges={before['boundary_edges']}"),
        ("object scale applied before Solidify",
         before["scale_applied"], f"scale={before['object_scale']}"),
        ("result is closed",
         after["closed"], f"boundary_edges={after['boundary_edges']}"),
        ("result is manifold",
         after["manifold"], f"non_manifold={after['non_manifold_edges']}"),
        ("no self-intersections introduced",
         after["self_intersecting_faces"] == 0,
         f"self_intersecting={after['self_intersecting_faces']}"),
        ("10 sampled thicknesses in 17.5-18.5 mm",
         len(samples) == 10 and len(in_range) == 10,
         f"{len(in_range)}/{len(samples)} in range; "
         f"min={min(samples) * 1000:.3f}mm max={max(samples) * 1000:.3f}mm"),
        ("volume matches area x thickness within 5%",
         vol_err < 0.05,
         f"expected={expected_vol:.6f} actual={after['volume']:.6f} "
         f"({vol_err * 100:.2f}%)"),
    ]
