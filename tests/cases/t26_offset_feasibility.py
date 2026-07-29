"""T-26 - detect concave folds too tight for the requested wall thickness."""
import math
import bpy
import bmesh
import cadlib

ID = "T-26"
PRIORITY = "P1"
TASK = ("Detect, before running Solidify, that a concave fold is too tight for "
        "the requested thickness, and show the silent dimensional error it "
        "causes.")
RECIPES = ["R-201", "R-202"]

THICKNESS = 0.018


def v_groove(interior_deg, arm=0.05):
    """An open V fold with a known interior angle."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    half = math.radians(interior_deg) / 2.0
    x, z = arm * math.sin(half), arm * math.cos(half)
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in
          [(-x, -0.5, z), (0.0, -0.5, 0.0), (x, -0.5, z),
           (-x, 0.5, z), (0.0, 0.5, 0.0), (x, 0.5, z)]]
    bm.faces.new((vs[0], vs[1], vs[4], vs[3]))
    bm.faces.new((vs[1], vs[2], vs[5], vs[4]))
    me = bpy.data.meshes.new("V")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("V", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def run():
    tight = v_groove(15.0)
    tight_conflicts = cadlib.concave_offset_conflicts(tight, THICKNESS)
    tight_ok_thin = cadlib.concave_offset_conflicts(tight, 0.0005)

    gentle = v_groove(150.0)
    gentle_conflicts = cadlib.concave_offset_conflicts(gentle, THICKNESS)

    bpy.ops.wm.open_mainfile(filepath="tests/fixtures/curved_surface.blend")
    smooth = bpy.data.objects["Surface"]
    smooth_conflicts = cadlib.concave_offset_conflicts(smooth, THICKNESS)

    # Confirm the prediction by solidifying the tight fold.
    tight2 = v_groove(15.0)
    before_dims = cadlib.diagnose(tight2)["dimensions"]
    mod = tight2.modifiers.new(name="Solidify", type='SOLIDIFY')
    mod.solidify_mode = 'NON_MANIFOLD'
    mod.thickness = THICKNESS
    mod.offset = -1.0
    mod.use_even_offset = True
    after = cadlib.diagnose(tight2)

    measured_interior = tight_conflicts[0][1] if tight_conflicts else None
    predicted_reach = tight_conflicts[0][2] if tight_conflicts else None

    # The damage is NOT self-intersection: the result is closed and manifold.
    # The offset apex overshoots the original apex by ~ t/tan(theta/2), so the
    # part grows far beyond nominal in Z while passing every topology check.
    grew = after["dimensions"][2] - before_dims[2]
    sane_growth = THICKNESS                      # what a gentle fold would add
    reach_err = (abs(grew - predicted_reach) / predicted_reach
                 if predicted_reach else float("inf"))

    return [
        ("tight 15-degree fold is flagged at 18 mm",
         len(tight_conflicts) == 1,
         f"{len(tight_conflicts)} conflicts; "
         f"interior {measured_interior:.1f} deg, needs "
         f"{tight_conflicts[0][2]:.4f} m of face, has "
         f"{tight_conflicts[0][3]:.4f} m" if tight_conflicts else "none found"),
        ("the measured interior angle matches the constructed 15 degrees",
         measured_interior is not None and abs(measured_interior - 15.0) < 0.1,
         f"measured {measured_interior}"),
        ("the same fold is fine at 0.5 mm",
         len(tight_ok_thin) == 0, f"{len(tight_ok_thin)} conflicts at 0.5 mm"),
        ("a gentle 150-degree fold is not flagged (no false positive)",
         len(gentle_conflicts) == 0, f"{len(gentle_conflicts)} conflicts"),
        ("the smooth T-02 fixture is not flagged (no false positive)",
         len(smooth_conflicts) == 0, f"{len(smooth_conflicts)} conflicts"),
        # This is the part that makes R-202 worth having: every topology check
        # passes, so nothing downstream objects. Only a dimensional check
        # catches it.
        ("the damaged result still passes every topology check",
         after["manifold"] and after["closed"]
         and after["self_intersecting_faces"] == 0,
         f"manifold={after['manifold']} closed={after['closed']} "
         f"self_intersecting={after['self_intersecting_faces']} "
         "- a topology-only gate would pass this"),
        ("but the part overshoots in Z by roughly the predicted reach",
         reach_err < 0.05,
         f"grew {grew:.4f} m vs predicted reach {predicted_reach:.4f} m "
         f"({reach_err * 100:.1f}% off)"),
        ("the overshoot dwarfs the requested wall thickness",
         grew > sane_growth * 5,
         f"an 18 mm wall added {grew * 1000:.1f} mm of height"),
    ]
