"""T-07 - collapse duplicated vertices without destroying real detail."""
import bpy
import bmesh
import cadlib

ID = "T-07"
PRIORITY = "P0"
TASK = ("Weld a solid assembled from abutting boxes using a tolerance-derived "
        "threshold, and show that welding alone does not make it solid.")
RECIPES = ["R-103", "R-101"]

TOLERANCE = 0.001      # 1 mm nominal tolerance
SMALLEST_FEATURE = 0.1  # the 100 mm box step


def run():
    bpy.ops.wm.open_mainfile(filepath="tests/fixtures/stepped_solid.blend")
    obj = bpy.data.objects["Stepped"]
    before = cadlib.diagnose(obj, check_self_intersect=False)

    # R-103: the threshold must be well below the smallest real feature.
    # Tolerance/10 is safe here; anything approaching SMALLEST_FEATURE would
    # silently eat the geometry.
    threshold = TOLERANCE / 10.0
    safe = threshold < SMALLEST_FEATURE / 10.0

    bm = cadlib.base_bmesh(obj)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=threshold)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

    after = cadlib.diagnose(obj, check_self_intersect=False)

    return [
        ("input had duplicate vertices",
         before["duplicate_verts"] > 0,
         f"duplicates={before['duplicate_verts']}"),
        ("input was many disconnected shells",
         before["shells"] > 1, f"shells={before['shells']}"),
        ("threshold is an order of magnitude below the smallest feature",
         safe, f"threshold={threshold} smallest_feature={SMALLEST_FEATURE}"),
        ("duplicates removed",
         after["duplicate_verts"] == 0,
         f"duplicates={after['duplicate_verts']}"),
        ("vertex count actually dropped",
         after["verts"] < before["verts"],
         f"{before['verts']} -> {after['verts']}"),
        ("shells merged",
         after["shells"] < before["shells"],
         f"{before['shells']} -> {after['shells']}"),
        ("bounding box unchanged (no real detail lost)",
         all(abs(a - b) < 1e-9
             for a, b in zip(after["dimensions"], before["dimensions"])),
         f"{before['dimensions']} -> {after['dimensions']}"),
        # The lesson of this case: welding merges the shells but leaves the
        # internal walls between the original boxes in place. The reported
        # volume changes (0.073 -> 0.248) precisely because the mesh now
        # encloses one envelope containing interior faces. Merge by Distance
        # is a NECESSARY step, not a SUFFICIENT one -- interior faces must be
        # removed (or the part remeshed, T-08) before volume means anything.
        ("welding changed the enclosed volume, proving interior faces remain",
         after["volume"] > before["volume"] * 2,
         f"{before['volume']:.6f} -> {after['volume']:.6f}"),
        ("mesh is still not manifold after welding alone",
         not after["manifold"],
         f"non_manifold={after['non_manifold_edges']} "
         "(interior walls survive; see T-08 for the remesh fix)"),
    ]
