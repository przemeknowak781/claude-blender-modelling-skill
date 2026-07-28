"""T-17 - one dimension derived from another by driver, never retyped."""
import bpy
import cadlib

ID = "T-17"
PRIORITY = "P3"
TASK = ("Drive a shelf's depth from a control object's custom property so a "
        "single edit propagates, with no retyped numbers.")
RECIPES = ["R-301", "R-302"]


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # R-302: one source of truth for every driving dimension.
    ctrl = bpy.data.objects.new("CTRL-Cabinet", None)
    bpy.context.scene.collection.objects.link(ctrl)
    ctrl["depth"] = 0.600
    ctrl["wall"] = 0.018

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    shelf = bpy.context.object
    shelf.name = "Shelf"

    # R-301: shelf depth = cabinet depth - one wall thickness.
    fcurve = shelf.driver_add("scale", 1)
    drv = fcurve.driver
    drv.type = 'SCRIPTED'
    for name, prop in (("d", '["depth"]'), ("w", '["wall"]')):
        var = drv.variables.new()
        var.name = name
        var.type = 'SINGLE_PROP'
        var.targets[0].id = ctrl
        var.targets[0].data_path = prop
    drv.expression = "d - w"

    def evaluate():
        # Both the driven object AND the property's owner must be tagged.
        # Tagging only the driven object leaves the driver reading a stale
        # value -- it silently returns the previous result.
        ctrl.update_tag()
        shelf.update_tag()
        dg = bpy.context.evaluated_depsgraph_get()
        dg.update()
        return cadlib.bbox_world(shelf, dg)[2]

    first = evaluate()

    # Change the single source of truth by 30 percent; nothing else is touched.
    ctrl["depth"] = 0.780
    second = evaluate()

    return [
        ("driver resolves on first evaluation",
         abs(first[1] - (0.600 - 0.018)) < 1e-6,
         f"expected {0.600 - 0.018:.6f} got {first[1]:.6f}"),
        ("changing the control property propagates automatically",
         abs(second[1] - (0.780 - 0.018)) < 1e-6,
         f"expected {0.780 - 0.018:.6f} got {second[1]:.6f}"),
        ("no other dimension moved",
         abs(second[0] - first[0]) < 1e-9 and abs(second[2] - first[2]) < 1e-9,
         f"{tuple(round(v, 6) for v in first)} -> "
         f"{tuple(round(v, 6) for v in second)}"),
        ("the driving value lives on the CTRL object, not in the mesh",
         ctrl.name.startswith("CTRL-") and "depth" in ctrl.keys(),
         f"{ctrl.name} keys={list(ctrl.keys())}"),
    ]
