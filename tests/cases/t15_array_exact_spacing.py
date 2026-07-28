"""T-15 - a structural bay array must land on exact grid lines."""
import bpy
import bmesh
import cadlib

ID = "T-15"
PRIORITY = "P2"
TASK = ("Array a column on a 7.2 m structural grid and confirm every bay "
        "centre lands within 0.1 mm of nominal.")
RECIPES = ["R-217", "R-001"]

BAY = 7.200
N_BAYS = 6
COL = 0.400
TOL = 0.0001


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(COL, COL, 3.600))
    me = bpy.data.meshes.new("Column")
    bm.to_mesh(me)
    bm.free()
    col = bpy.data.objects.new("Column", me)
    bpy.context.scene.collection.objects.link(col)

    # CONSTANT offset, not RELATIVE: relative offset is a multiple of the
    # object's own bounding box, so it silently changes if the column size
    # changes. Constant offset is the grid dimension itself.
    mod = col.modifiers.new(name="Array", type='ARRAY')
    mod.fit_type = 'FIXED_COUNT'
    mod.count = N_BAYS
    mod.use_relative_offset = False
    mod.use_constant_offset = True
    mod.constant_offset_displace = (BAY, 0.0, 0.0)

    bmv = cadlib.evaluated_bmesh(col)
    xs = sorted({round(v.co.x, 6) for v in bmv.verts})
    bmv.free()

    # Each column contributes two X planes: centre -/+ half its width.
    centres = []
    for i in range(N_BAYS):
        lo = -COL / 2 + i * BAY
        hi = COL / 2 + i * BAY
        centres.append((lo, hi))
    expected = sorted({round(v, 6) for pair in centres for v in pair})
    err = (max(abs(a - b) for a, b in zip(xs, expected))
           if len(xs) == len(expected) else float("inf"))

    _, _, dims = cadlib.bbox_world(col)
    expected_len = COL + (N_BAYS - 1) * BAY

    return [
        ("constant offset used, not relative",
         mod.use_constant_offset and not mod.use_relative_offset,
         f"constant={mod.use_constant_offset} relative={mod.use_relative_offset}"),
        ("correct number of bays",
         len(xs) == len(expected), f"{len(xs)} X planes, expected {len(expected)}"),
        ("every grid line within 0.1 mm",
         err < TOL, f"max grid error {err * 1000:.6f} mm"),
        ("overall length matches nominal",
         abs(dims[0] - expected_len) < TOL,
         f"measured {dims[0]:.4f} expected {expected_len:.4f}"),
        ("last bay centre is exactly 5 x 7.2 m from the first",
         abs((xs[-1] - COL / 2) - (N_BAYS - 1) * BAY) < TOL,
         f"span {(xs[-1] - COL / 2):.6f} vs {(N_BAYS - 1) * BAY:.6f}"),
    ]
