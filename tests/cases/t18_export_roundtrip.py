"""T-18 - round-trip verification is what makes an export believable."""
import os
import bpy
import bmesh
import cadlib

ID = "T-18"
PRIORITY = "P4"
TASK = ("Export to STL and OBJ, reimport into a clean scene, and confirm "
        "bounding box and volume survive within tolerance.")
RECIPES = ["R-402", "R-405"]

TOL = 1e-5
OUTDIR = "tests/output/t18"


def build_part():
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=48,
                          radius1=0.150, radius2=0.100, depth=0.240)
    me = bpy.data.meshes.new("Part")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Part", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def reimport(path, kind):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.data.objects.keys())
    if kind == "stl":
        bpy.ops.wm.stl_import(filepath=path, global_scale=1.0)
    else:
        # Blender-native axes on BOTH sides. The operator DEFAULTS
        # (NEGATIVE_Z / Y) do NOT round-trip -- see T-19.
        bpy.ops.wm.obj_import(filepath=path, global_scale=1.0,
                              forward_axis='Y', up_axis='Z')
    new = [o for o in bpy.data.objects if o.name not in before]
    return new[0] if new else None


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(OUTDIR, exist_ok=True)
    obj = build_part()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    original = cadlib.diagnose(obj, check_self_intersect=False)

    stl_path = os.path.abspath(os.path.join(OUTDIR, "part.stl"))
    obj_path = os.path.abspath(os.path.join(OUTDIR, "part.obj"))
    bpy.ops.wm.stl_export(filepath=stl_path, export_selected_objects=True,
                          global_scale=1.0, apply_modifiers=True)
    bpy.ops.wm.obj_export(filepath=obj_path, export_selected_objects=True,
                          global_scale=1.0, apply_modifiers=True,
                          forward_axis='Y', up_axis='Z')

    out = []
    for kind, path in (("stl", stl_path), ("obj", obj_path)):
        back = reimport(path, kind)
        if back is None:
            out.append((f"{kind}: reimported an object", False, "nothing imported"))
            continue
        rep = cadlib.diagnose(back, check_self_intersect=False)
        dim_err = max(abs(a - b)
                      for a, b in zip(rep["dimensions"], original["dimensions"]))
        vol_err = abs(rep["volume"] - original["volume"]) / original["volume"]
        out.append((f"{kind}: bounding box survives the round trip",
                    dim_err < TOL,
                    f"max dim error {dim_err:.3e} m"))
        out.append((f"{kind}: volume survives the round trip",
                    vol_err < 1e-4,
                    f"{original['volume']:.8f} -> {rep['volume']:.8f} "
                    f"({vol_err * 100:.6f}%)"))
        out.append((f"{kind}: still manifold after the round trip",
                    rep["manifold"],
                    f"non_manifold={rep['non_manifold_edges']}"))

    out.insert(0, ("export files were actually written",
                   os.path.getsize(stl_path) > 0 and os.path.getsize(obj_path) > 0,
                   f"stl={os.path.getsize(stl_path)}B obj={os.path.getsize(obj_path)}B"))
    return out
