"""T-09 - planar decimation must keep sharp mechanical features."""
import bpy
import bmesh
import cadlib

ID = "T-09"
PRIORITY = "P0"
TASK = ("Reduce a densely-tessellated prismatic part without rounding off its "
        "sharp edges, and show that collapse decimation would have.")
RECIPES = ["R-107", "R-108"]


def build_dense_prism():
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=14,
                              use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("Prism")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Prism", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = build_dense_prism()
    before = cadlib.diagnose(obj, check_self_intersect=False)

    # R-108: PLANAR dissolves coplanar faces and leaves real edges alone.
    planar = obj.modifiers.new(name="Planar", type='DECIMATE')
    planar.decimate_type = 'DISSOLVE'
    planar.angle_limit = 0.0872665  # 5 degrees
    planar_res = cadlib.diagnose(obj, check_self_intersect=False)
    obj.modifiers.remove(planar)

    # R-107: COLLAPSE at a comparable budget, for contrast.
    collapse = obj.modifiers.new(name="Collapse", type='DECIMATE')
    collapse.decimate_type = 'COLLAPSE'
    collapse.ratio = planar_res["tris"] / before["tris"]
    collapse_res = cadlib.diagnose(obj, check_self_intersect=False)
    obj.modifiers.remove(collapse)

    planar_vol_err = abs(planar_res["volume"] - before["volume"]) / before["volume"]
    collapse_vol_err = abs(collapse_res["volume"] - before["volume"]) / before["volume"]

    dims_kept = all(abs(a - b) < 1e-6
                    for a, b in zip(planar_res["dimensions"], before["dimensions"]))

    return [
        ("input was densely tessellated",
         before["tris"] > 2000, f"{before['tris']} tris"),
        ("planar decimation reduced the count substantially",
         planar_res["tris"] < before["tris"] / 10,
         f"{before['tris']} -> {planar_res['tris']} tris"),
        ("planar decimation preserved the bounding box exactly",
         dims_kept,
         f"{before['dimensions']} -> {planar_res['dimensions']}"),
        ("planar decimation preserved volume within 0.01%",
         planar_vol_err < 0.0001,
         f"{planar_vol_err * 100:.6f}%"),
        ("planar result is still manifold",
         planar_res["manifold"],
         f"non_manifold={planar_res['non_manifold_edges']}"),
        ("collapse at the same budget loses more volume (the antipattern)",
         collapse_vol_err > planar_vol_err,
         f"collapse={collapse_vol_err * 100:.4f}% vs "
         f"planar={planar_vol_err * 100:.6f}%"),
    ]
