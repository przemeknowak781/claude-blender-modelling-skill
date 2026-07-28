"""T-03 - boolean difference between solids with coplanar faces."""
import bpy
import cadlib

ID = "T-03"
PRIORITY = "P1"
TASK = "Boolean-difference two solids that share exactly coplanar faces."
RECIPES = ["R-206", "R-207"]

NUDGE = 1e-4


def run():
    bpy.ops.wm.open_mainfile(filepath="tests/fixtures/coplanar_pair.blend")
    base = bpy.data.objects["Base"]
    cutter = bpy.data.objects["Cutter"]

    base_d = cadlib.diagnose(base)
    cut_d = cadlib.diagnose(cutter)

    # R-206 precondition: BOTH inputs must be manifold before any boolean.
    inputs_ok = base_d["manifold"] and cut_d["manifold"]

    # R-207: break exact coplanarity. The cutter's -X and +Z faces sit exactly
    # on the base's, which makes the solver's classification ambiguous there.
    # Push the cutter out along both so the cut passes cleanly through.
    cutter.location.x -= NUDGE
    cutter.location.z += NUDGE
    bpy.context.view_layer.update()

    mod = base.modifiers.new(name="Boolean", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter

    after = cadlib.diagnose(base)

    # Base is 2x2x2 = 8. The cutter is 1x1x1 = 1 and sits fully inside the
    # base's X/Z extent after the nudge, so exactly 1.0 should be removed.
    expected = base_d["volume"] - cut_d["volume"]
    vol_err = abs(after["volume"] - expected) / expected

    return [
        ("both boolean inputs manifold before the operation",
         inputs_ok,
         f"base_manifold={base_d['manifold']} cutter_manifold={cut_d['manifold']}"),
        ("result is manifold",
         after["manifold"],
         f"non_manifold={after['non_manifold_edges']} closed={after['closed']}"),
        ("no degenerate faces below 1e-9",
         after["degenerate_faces"] == 0,
         f"degenerate={after['degenerate_faces']}"),
        ("normals consistent",
         after["inconsistent_normal_edges"] == 0,
         f"inconsistent={after['inconsistent_normal_edges']}"),
        ("volume equals base minus cutter within 0.5%",
         vol_err < 0.005,
         f"expected={expected:.6f} actual={after['volume']:.6f} "
         f"({vol_err * 100:.3f}%)"),
        ("result is a single shell",
         after["shells"] == 1, f"shells={after['shells']}"),
    ]
