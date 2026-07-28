"""T-08 - voxel remesh with a declared error bound."""
import bpy
import cadlib

ID = "T-08"
PRIORITY = "P0"
TASK = ("Voxel-remesh a badly-topologised solid at a declared voxel size and "
        "confirm the volume error stays inside the stated bound.")
RECIPES = ["R-110", "R-101"]

VOXEL = 0.02


def run():
    bpy.ops.wm.open_mainfile(filepath="tests/fixtures/stepped_solid.blend")
    obj = bpy.data.objects["Stepped"]
    before = cadlib.diagnose(obj, check_self_intersect=True)

    # R-110: voxel remesh rebuilds topology from scratch. It guarantees a
    # manifold result; the price is a volume error bounded by the voxel size.
    mod = obj.modifiers.new(name="Remesh", type='REMESH')
    mod.mode = 'VOXEL'
    mod.voxel_size = VOXEL
    mod.adaptivity = 0.0

    after = cadlib.diagnose(obj, check_self_intersect=True)
    vol_err = abs(after["volume"] - before["volume"]) / before["volume"]

    # A voxel remesh perturbs the surface by up to ~1 voxel. For a part whose
    # bounding box is ~1 m, that is a few percent of volume at 20 mm voxels.
    bound = 0.10

    return [
        ("input was multi-shell and self-intersecting",
         before["shells"] > 1 and before["self_intersecting_faces"] > 0,
         f"shells={before['shells']} "
         f"self_intersecting={before['self_intersecting_faces']}"),
        ("remesh produced a single shell",
         after["shells"] == 1, f"shells={after['shells']}"),
        ("result is manifold",
         after["manifold"],
         f"non_manifold={after['non_manifold_edges']} closed={after['closed']}"),
        ("normals consistent and outward",
         after["inconsistent_normal_edges"] == 0
         and after["normals_inward"] is False,
         f"inconsistent={after['inconsistent_normal_edges']} "
         f"inward={after['normals_inward']}"),
        ("self-intersections eliminated",
         after["self_intersecting_faces"] == 0,
         f"self_intersecting={after['self_intersecting_faces']}"),
        ("volume error inside the declared bound",
         vol_err < bound,
         f"{before['volume']:.6f} -> {after['volume']:.6f} "
         f"({vol_err * 100:.2f}%, bound {bound * 100:.0f}%)"),
    ]
