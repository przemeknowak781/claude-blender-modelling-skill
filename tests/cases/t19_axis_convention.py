"""T-19 - OBJ operator axis DEFAULTS do not round-trip. Verified in 5.2."""
import os
import bpy
import bmesh
import cadlib

ID = "T-19"
PRIORITY = "P4"
TASK = ("Show that exporting and reimporting OBJ with the operator defaults "
        "silently rotates the part, and that Blender-native axes do not.")
RECIPES = ["R-404", "R-402"]

OUTDIR = "tests/output/t19"


def build_marker():
    """Deliberately asymmetric: 0.100 x 0.200 x 0.400, so any swap shows up."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(0.100, 0.200, 0.400))
    me = bpy.data.meshes.new("Marker")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Marker", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    return ob


def dims(obj):
    return tuple(round(d, 6) for d in
                 cadlib.diagnose(obj, check_self_intersect=False)["dimensions"])


def roundtrip(path, exp_kwargs, imp_kwargs):
    build_marker()
    bpy.ops.wm.obj_export(filepath=path, export_selected_objects=True,
                          global_scale=1.0, **exp_kwargs)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.data.objects.keys())
    bpy.ops.wm.obj_import(filepath=path, global_scale=1.0, **imp_kwargs)
    new = [o for o in bpy.data.objects if o.name not in before]
    return dims(new[0])


def run():
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.abspath(os.path.join(OUTDIR, "marker.obj"))

    build_marker()
    original = dims(bpy.data.objects["Marker"])

    # The operator defaults on BOTH sides: what you get by calling
    # wm.obj_export / wm.obj_import with no axis arguments at all.
    defaults = {"forward_axis": 'NEGATIVE_Z', "up_axis": 'Y'}
    native = {"forward_axis": 'Y', "up_axis": 'Z'}

    default_rt = roundtrip(path, defaults, defaults)
    native_rt = roundtrip(path, native, native)

    return [
        ("the test part is asymmetric enough to detect a swap",
         len(set(original)) == 3, f"dimensions={original}"),
        ("operator DEFAULTS silently rotate the part on a round trip",
         default_rt != original,
         f"{original} -> {default_rt} using the documented defaults "
         "(forward=NEGATIVE_Z, up=Y) on both sides"),
        ("the default round trip is a rotation, not a rescale",
         sorted(default_rt) == sorted(original),
         f"sorted {sorted(default_rt)} == sorted {sorted(original)}"),
        ("Blender-native axes (forward=Y, up=Z) round-trip exactly",
         native_rt == original, f"{original} -> {native_rt}"),
    ]
