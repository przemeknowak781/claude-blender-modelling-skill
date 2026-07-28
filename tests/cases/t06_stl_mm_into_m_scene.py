"""T-06 - import a millimetre STL into a metre scene."""
import bpy
import cadlib

ID = "T-06"
PRIORITY = "P4"
TASK = ("Import an STL authored in millimetres into a scene working in metres "
        "and land at the nominal size with scale applied.")
RECIPES = ["R-401", "R-403"]

NOMINAL_MM = (40.0, 25.0, 12.0)


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = 'METERS'

    before = set(bpy.data.objects.keys())
    # STL stores bare numbers with no unit. The file holds 40/25/12, meaning
    # millimetres; global_scale converts them into the scene's metres.
    bpy.ops.wm.stl_import(filepath="tests/fixtures/part_mm.stl",
                          global_scale=0.001)
    new = [o for o in bpy.data.objects if o.name not in before]
    obj = new[0]

    # VERIFIED 5.2 BEHAVIOUR: stl_import writes global_scale into the OBJECT
    # SCALE, leaving obj.scale = 0.001 and the mesh still holding raw numbers.
    # Left alone that is antipattern #1 and will corrupt any later Bevel,
    # Solidify, Array or export. Apply it immediately.
    scale_before_apply = tuple(obj.scale)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    rep = cadlib.diagnose(obj, check_self_intersect=False)
    dims_mm = tuple(d * 1000.0 for d in rep["dimensions"])
    err_mm = max(abs(a - b) for a, b in zip(dims_mm, NOMINAL_MM))

    return [
        ("exactly one object imported",
         len(new) == 1, f"imported {[o.name for o in new]}"),
        ("import put the conversion into object scale, not the mesh",
         abs(scale_before_apply[0] - 0.001) < 1e-9,
         f"scale straight after import = {scale_before_apply}"),
        ("object scale is 1.0 after Apply Scale",
         rep["scale_applied"], f"scale={rep['object_scale']}"),
        ("bounding box matches nominal within 0.01 mm",
         err_mm < 0.01,
         f"nominal={NOMINAL_MM} got=({dims_mm[0]:.4f}, {dims_mm[1]:.4f}, "
         f"{dims_mm[2]:.4f}) mm"),
        ("mesh is closed and manifold",
         rep["manifold"], f"non_manifold={rep['non_manifold_edges']}"),
        ("scene unit scale left at 1.0 metre",
         scene.unit_settings.scale_length == 1.0,
         f"scale_length={scene.unit_settings.scale_length}"),
    ]
