"""T-10 - volume is only meaningful on a closed mesh."""
import bpy
import bmesh
import math
import cadlib

ID = "T-10"
PRIORITY = "P0"
TASK = ("Measure volume, area and centre of mass, and refuse to report volume "
        "for an open mesh.")
RECIPES = ["R-113", "R-101"]

R = 0.5
H = 2.0


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Closed cylinder with analytically known volume and area.
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=256,
                          radius1=R, radius2=R, depth=H)
    me = bpy.data.meshes.new("Closed")
    bm.to_mesh(me)
    bm.free()
    closed_obj = bpy.data.objects.new("Closed", me)
    bpy.context.scene.collection.objects.link(closed_obj)

    # The same cylinder with both caps removed: open.
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, cap_tris=False, segments=256,
                          radius1=R, radius2=R, depth=H)
    me2 = bpy.data.meshes.new("Open")
    bm.to_mesh(me2)
    bm.free()
    open_obj = bpy.data.objects.new("Open", me2)
    bpy.context.scene.collection.objects.link(open_obj)

    closed_d = cadlib.diagnose(closed_obj, check_self_intersect=False)
    open_d = cadlib.diagnose(open_obj, check_self_intersect=False)

    # A 256-gon prism, not a true cylinder: use the polygon formulae.
    n = 256
    poly_area = 0.5 * n * R * R * math.sin(2 * math.pi / n)
    perimeter = 2 * n * R * math.sin(math.pi / n)
    exp_vol = poly_area * H
    exp_area = perimeter * H + 2 * poly_area

    vol_err = abs(closed_d["volume"] - exp_vol) / exp_vol
    area_err = abs(closed_d["area"] - exp_area) / exp_area

    bmc = cadlib.evaluated_bmesh(closed_obj)
    com = cadlib.centre_of_mass(bmc)
    bmc.free()

    return [
        ("closed mesh reports a volume",
         closed_d["volume"] is not None, f"volume={closed_d['volume']}"),
        ("volume matches the analytic prism value within 0.01%",
         vol_err < 0.0001, f"expected={exp_vol:.8f} got={closed_d['volume']:.8f}"),
        ("surface area matches within 0.01%",
         area_err < 0.0001, f"expected={exp_area:.8f} got={closed_d['area']:.8f}"),
        ("open mesh reports NO volume rather than a wrong number",
         open_d["volume"] is None and open_d["closed"] is False,
         f"volume={open_d['volume']} closed={open_d['closed']}"),
        ("open mesh still reports a valid area",
         open_d["area"] > 0, f"area={open_d['area']:.6f}"),
        ("centre of mass is on the axis of symmetry",
         abs(com.x) < 1e-6 and abs(com.y) < 1e-6 and abs(com.z) < 1e-6,
         f"com=({com.x:.3e}, {com.y:.3e}, {com.z:.3e})"),
    ]
