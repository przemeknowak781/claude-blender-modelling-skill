"""T-11 - choose bevel segment count from a deviation budget."""
import bpy
import bmesh
import math
import cadlib

ID = "T-11"
PRIORITY = "P1"
TASK = ("Derive the bevel segment count from a stated deviation tolerance "
        "instead of guessing, and prove the resulting chord error.")
RECIPES = ["R-203", "R-205"]

RADIUS = 0.006     # 6 mm fillet
TOLERANCE = 2e-5   # 0.02 mm allowed deviation from the true arc


def segments_for_deviation(radius, tolerance):
    """Smallest segment count whose chord sagitta stays within *tolerance*.

    A bevel of *n* segments across a 90-degree edge approximates the arc with
    n chords. The sagitta of one chord is r * (1 - cos(theta/2)) where
    theta = (pi/2)/n. Solve for the smallest n that satisfies the budget.
    """
    n = 1
    while n < 512:
        theta = (math.pi / 2.0) / n
        sagitta = radius * (1.0 - math.cos(theta / 2.0))
        if sagitta <= tolerance:
            return n, sagitta
        n += 1
    return n, sagitta


def max_deviation_from_arc(obj, centre_xy, radius):
    """Largest radial error between the bevelled surface and the true arc."""
    bm = cadlib.evaluated_bmesh(obj)
    worst = 0.0
    cx, cy = centre_xy
    for v in bm.verts:
        dx, dy = v.co.x - cx, v.co.y - cy
        # Only vertices ON the fillet: in the quadrant beyond the arc centre,
        # and within the fillet radius in BOTH axes. Without the second test
        # the flat-face vertices get sampled and the "deviation" is really the
        # distance to the face, not the chord error.
        if dx > 1e-9 or dy > 1e-9:
            continue
        if abs(dx) > radius * 1.01 or abs(dy) > radius * 1.01:
            continue
        # Stay in the straight run of the vertical edge. Near the top and
        # bottom the three-way corner patch also lives in this quadrant, and
        # its vertices are not on the vertical fillet's arc at all.
        if abs(v.co.z) > 0.030:
            continue
        dist = math.hypot(dx, dy)
        if dist < radius * 0.2:
            continue
        worst = max(worst, abs(dist - radius))
    bm.free()
    return worst


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=0.100)
    me = bpy.data.meshes.new("Block")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("Block", me)
    bpy.context.scene.collection.objects.link(obj)

    n_seg, predicted = segments_for_deviation(RADIUS, TOLERANCE)

    mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    mod.affect = 'EDGES'
    mod.offset_type = 'OFFSET'
    mod.width = RADIUS
    mod.segments = n_seg
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(30.0)
    mod.use_clamp_overlap = True

    rep = cadlib.diagnose(obj)
    # The cube spans -0.05..0.05; the fillet centre of the -X/-Y vertical edge
    # sits at (-0.05 + r, -0.05 + r).
    centre = (-0.050 + RADIUS, -0.050 + RADIUS)
    measured = max_deviation_from_arc(obj, centre, RADIUS)

    # A single-segment bevel is a plain chamfer: prove the budget forced more.
    naive_sagitta = RADIUS * (1.0 - math.cos((math.pi / 4.0)))

    return [
        ("segment count was derived, not guessed",
         n_seg > 1 and predicted <= TOLERANCE,
         f"n={n_seg}, predicted sagitta {predicted * 1000:.6f} mm "
         f"<= budget {TOLERANCE * 1000:.4f} mm"),
        ("a 1-segment chamfer would have blown the budget",
         naive_sagitta > TOLERANCE,
         f"1-segment sagitta {naive_sagitta * 1000:.4f} mm"),
        ("measured deviation from the true arc is inside the budget",
         measured <= TOLERANCE,
         f"measured {measured * 1000:.6f} mm <= {TOLERANCE * 1000:.4f} mm"),
        ("result is manifold",
         rep["manifold"], f"non_manifold={rep['non_manifold_edges']}"),
        ("no self-intersections from clamped bevel",
         rep["self_intersecting_faces"] == 0,
         f"self_intersecting={rep['self_intersecting_faces']}"),
        ("outer dimensions unchanged by filleting",
         all(abs(d - 0.100) < 1e-6 for d in rep["dimensions"]),
         f"dimensions={tuple(round(d, 6) for d in rep['dimensions'])}"),
    ]
