"""T-12 - internal corners a round cutter cannot reach need relief."""
import bpy
import bmesh
import math
import cadlib

ID = "T-12"
PRIORITY = "P1"
TASK = ("Cut a rectangular pocket and add dogbone relief so a 6 mm cutter can "
        "actually reach the corners.")
RECIPES = ["R-206", "R-212"]

TOOL_D = 0.006          # 6 mm cutter
TOOL_R = TOOL_D / 2.0
POCKET = (0.080, 0.050)
DEPTH = 0.010
STOCK = (0.150, 0.100, 0.018)


def make_object(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def build(with_relief):
    """Stock with a pocket boolean, optionally with corner relief cutters.

    Each cutter is a SEPARATE object with its own Boolean modifier. Merging
    the corner cylinders into the pocket cutter's mesh would make that cutter
    a self-intersecting multi-shell solid, and the EXACT solver then produces
    nothing at all -- silently. One manifold cutter per boolean (R-206).
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=STOCK)
    stock = make_object("Stock", bm)

    # Pocket cutter: underside exactly at the pocket floor, top clear of the
    # stock so the boolean never sees a coplanar top face.
    cb = bmesh.new()
    bmesh.ops.create_cube(cb, size=1.0)
    bmesh.ops.scale(cb, verts=cb.verts, vec=(POCKET[0], POCKET[1], DEPTH * 2))
    bmesh.ops.translate(cb, verts=cb.verts, vec=(0.0, 0.0, STOCK[2] / 2))
    cutters = [make_object("PocketCutter", cb)]

    if with_relief:
        # R-212: a bore of the tool radius at each corner, offset diagonally
        # outward so the cutter's centre can reach the nominal corner point.
        hx, hy = POCKET[0] / 2.0, POCKET[1] / 2.0
        off = TOOL_R / math.sqrt(2.0)
        for i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)]):
            sub = bmesh.new()
            bmesh.ops.create_cone(sub, cap_ends=True, cap_tris=False,
                                  segments=64, radius1=TOOL_R, radius2=TOOL_R,
                                  depth=DEPTH * 2)
            bmesh.ops.translate(
                sub, verts=sub.verts,
                vec=(sx * (hx - off), sy * (hy - off), STOCK[2] / 2))
            cutters.append(make_object(f"Relief{i}", sub))

    for cutter in cutters:
        mod = stock.modifiers.new(name=f"Bool_{cutter.name}", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.solver = 'EXACT'
        mod.object = cutter
    return stock


def pocket_floor_extent(obj):
    """XY extent of the pocket floor, or None if no pocket was cut."""
    bm = cadlib.evaluated_bmesh(obj)
    floor_z = STOCK[2] / 2.0 - DEPTH
    # Copy the coordinates out: v.co is a view into the bmesh and must not be
    # read after free().
    pts = [(v.co.x, v.co.y) for v in bm.verts
           if abs(v.co.z - floor_z) < 1e-6]
    bm.free()
    if not pts:
        return None
    return (max(p[0] for p in pts) - min(p[0] for p in pts),
            max(p[1] for p in pts) - min(p[1] for p in pts))


def run():
    plain = build(with_relief=False)
    plain_rep = cadlib.diagnose(plain, check_self_intersect=False)
    plain_ext = pocket_floor_extent(plain)

    relieved = build(with_relief=True)
    rel_rep = cadlib.diagnose(relieved, check_self_intersect=False)
    rel_ext = pocket_floor_extent(relieved)

    if plain_ext is None or rel_ext is None:
        return [("both booleans produced a pocket floor", False,
                 f"plain={plain_ext} relieved={rel_ext}")]

    grew_x = rel_ext[0] - plain_ext[0]
    grew_y = rel_ext[1] - plain_ext[1]
    # Each corner bore reaches TOOL_R from a centre pulled in by TOOL_R/sqrt(2),
    # so the pocket grows by that difference at each of the two ends.
    expected_growth = 2 * (TOOL_R - TOOL_R / math.sqrt(2.0))

    return [
        ("plain pocket matches nominal size exactly",
         abs(plain_ext[0] - POCKET[0]) < 1e-6
         and abs(plain_ext[1] - POCKET[1]) < 1e-6,
         f"pocket floor extent "
         f"({plain_ext[0]:.6f}, {plain_ext[1]:.6f}) vs nominal {POCKET}"),
        ("relieved pocket is larger at the corners",
         grew_x > 0 and grew_y > 0,
         f"grew x={grew_x * 1000:.4f} mm y={grew_y * 1000:.4f} mm"),
        ("relief growth matches the tool-radius geometry within 0.05 mm",
         abs(grew_x - expected_growth) < 5e-5
         and abs(grew_y - expected_growth) < 5e-5,
         f"expected {expected_growth * 1000:.4f} mm, got "
         f"x={grew_x * 1000:.4f} y={grew_y * 1000:.4f}"),
        ("relieved part is still manifold",
         rel_rep["manifold"],
         f"non_manifold={rel_rep['non_manifold_edges']} "
         f"closed={rel_rep['closed']}"),
        ("relief removed additional material",
         rel_rep["volume"] < plain_rep["volume"],
         f"plain={plain_rep['volume']:.8f} relieved={rel_rep['volume']:.8f}"),
    ]
