"""T-01 — repair a dense marching-cubes export and reduce it to a budget."""
import bpy
import bmesh
import cadlib

ID = "T-01"
PRIORITY = "P0"
TASK = ("Repair a ~1.7M-triangle marching-cubes mesh: drop isolated debris and "
        "loose geometry, make normals consistent, reduce to 100k triangles "
        "while preserving volume.")
RECIPES = ["R-101", "R-102", "R-105", "R-106", "R-107"]

TARGET_TRIS = 100_000


def run():
    bpy.ops.wm.open_mainfile(filepath="tests/fixtures/marching_cubes_blob.blend")
    obj = bpy.data.objects["Blob"]

    before = cadlib.diagnose(obj, check_self_intersect=False)

    # --- R-102: drop loose geometry, then R-106: keep the largest shell -----
    bm = cadlib.base_bmesh(obj)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    bmesh.ops.delete(bm, geom=cadlib.loose_verts(bm), context='VERTS')
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    comps = cadlib.shells(bm)
    if len(comps) > 1:
        # Rank shells by face count and delete everything but the largest.
        comps.sort(key=len, reverse=True)
        doomed = [f for comp in comps[1:] for f in comp]
        bmesh.ops.delete(bm, geom=doomed, context='FACES')
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

    # --- R-105: consistent outward normals ---------------------------------
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

    mid = cadlib.diagnose(obj, check_self_intersect=False)

    # --- R-107: collapse decimation to the triangle budget -----------------
    # Ratio is computed from the CURRENT count, after cleanup, not the original.
    mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = min(1.0, TARGET_TRIS / max(mid["tris"], 1))
    mod.use_collapse_triangulate = True

    after = cadlib.diagnose(obj, check_self_intersect=False)

    vol_err = abs(after["volume"] - before["volume"]) / before["volume"]

    return [
        ("input was dense enough to be representative",
         before["tris"] > 1_000_000, f"{before['tris']} tris"),
        ("input had detectable damage",
         before["shells"] > 1 and before["loose_verts"] > 0
         and before["inconsistent_normal_edges"] > 0,
         f"shells={before['shells']} loose={before['loose_verts']} "
         f"flipped_edges={before['inconsistent_normal_edges']}"),
        ("isolated components removed",
         after["shells"] == 1, f"shells={after['shells']}"),
        ("loose vertices removed",
         after["loose_verts"] == 0, f"loose={after['loose_verts']}"),
        ("normals consistent",
         after["inconsistent_normal_edges"] == 0,
         f"inconsistent={after['inconsistent_normal_edges']}"),
        ("normals point outward",
         after["normals_inward"] is False,
         f"signed_volume={after['signed_volume']:.6f}"),
        ("zero non-manifold edges",
         after["non_manifold_edges"] == 0,
         f"non_manifold={after['non_manifold_edges']}"),
        ("triangle count under 110k",
         after["tris"] < 110_000, f"{after['tris']} tris"),
        ("volume preserved within 2%",
         vol_err < 0.02,
         f"{before['volume']:.6f} -> {after['volume']:.6f} ({vol_err * 100:.3f}%)"),
    ]
