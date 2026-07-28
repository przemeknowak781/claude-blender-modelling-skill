"""T-14 - float precision collapses in a far-from-origin scene."""
import bpy
import bmesh
import cadlib

ID = "T-14"
PRIORITY = "P2"
TASK = ("Show that millimetre detail is destroyed at survey-grid coordinates "
        "and preserved when the same work happens in a local frame.")
RECIPES = ["R-003", "R-001"]

OFFSET = 6.0e5     # a realistic national-grid easting, in metres
DETAIL = 0.001     # 1 mm feature
TOL = 1e-5


def build_detail_at(origin_x):
    """A block with a 1 mm step, built with vertex coordinates at origin_x."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(origin_x, 0.0, 0.0))
    # Nudge the +X face outward by exactly 1 mm.
    for v in bm.verts:
        if v.co.x > origin_x:
            v.co.x += DETAIL
    me = bpy.data.meshes.new("B")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("B", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def run():
    # Case A: geometry authored directly at grid coordinates.
    far = build_detail_at(OFFSET)
    far_dims = cadlib.diagnose(far, check_self_intersect=False)["dimensions"]
    far_err = abs(far_dims[0] - (1.0 + DETAIL))

    # Case B: R-003 -- author at the origin, place with the object transform.
    near = build_detail_at(0.0)
    near.location.x = OFFSET
    near_dims = cadlib.diagnose(near, check_self_intersect=False)["dimensions"]
    near_err = abs(near_dims[0] - (1.0 + DETAIL))

    ratio = OFFSET / DETAIL

    return [
        ("the scene exceeds the 1e6 precision-budget threshold",
         ratio > 1e6, f"extent/detail = {ratio:.2e}"),
        ("detail authored at grid coordinates loses precision",
         far_err > TOL,
         f"1 mm feature measured with {far_err * 1000:.6f} mm error at "
         f"x={OFFSET:.0f} m"),
        # Blender stores vertex coordinates as float32, so even at the origin
        # the floor is ~1e-7 m, not zero. That is still three orders of
        # magnitude better than the same feature at grid coordinates.
        ("detail authored at the origin keeps full precision",
         near_err < 1e-6,
         f"error {near_err * 1e6:.4f} um at the origin "
         "(float32 storage floor, not a modelling error)"),
        ("the local frame is measurably better",
         near_err < far_err / 100,
         f"local {near_err:.3e} vs global {far_err:.3e} m"),
        ("the object still sits at the right world position",
         abs(near.matrix_world.translation.x - OFFSET) < 1e-3,
         f"world x = {near.matrix_world.translation.x:.3f}"),
    ]
