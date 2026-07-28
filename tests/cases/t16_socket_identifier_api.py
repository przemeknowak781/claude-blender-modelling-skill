"""T-16 - the 5.2 Geometry Nodes modifier input API, and what broke."""
import bpy
import cadlib

ID = "T-16"
PRIORITY = "P3"
TASK = ("Resolve modifier inputs by label at runtime and confirm the 4.x "
        "dict-style socket access no longer works in 5.2.")
RECIPES = ["R-303"]

def build_parametric_box(name="Part"):
    """A 4-parameter box graph. Returns (object, node_group, {label: identifier})."""
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    out_sock = ng.interface.new_socket(name="Geometry", in_out='OUTPUT',
                                       socket_type='NodeSocketGeometry')
    specs = [("Length", 0.400), ("Width", 0.300), ("Height", 0.200),
             ("Wall", 0.018)]
    for label, default in specs:
        s = ng.interface.new_socket(name=label, in_out='INPUT',
                                    socket_type='NodeSocketFloat')
        s.default_value = default
        s.min_value = 0.001

    gi = ng.nodes.new('NodeGroupInput')
    go = ng.nodes.new('NodeGroupOutput')
    cube = ng.nodes.new('GeometryNodeMeshCube')
    combine = ng.nodes.new('ShaderNodeCombineXYZ')

    ident = {i.name: i.identifier for i in ng.interface.items_tree
             if i.item_type == 'SOCKET' and i.in_out == 'INPUT'}

    ng.links.new(gi.outputs[ident["Length"]], combine.inputs['X'])
    ng.links.new(gi.outputs[ident["Width"]], combine.inputs['Y'])
    ng.links.new(gi.outputs[ident["Height"]], combine.inputs['Z'])
    ng.links.new(combine.outputs['Vector'], cube.inputs['Size'])
    ng.links.new(cube.outputs['Mesh'], go.inputs[out_sock.identifier])

    me = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new(name="GN", type='NODES')
    mod.node_group = ng
    return obj, ng, ident


def set_input(mod, identifier, value):
    """Set a Geometry Nodes modifier input in Blender 5.2.

    5.2 REMOVED the 4.x dict-style ``mod["Socket_2"] = v``; it now raises
    TypeError. The current form is attribute access on
    ``mod.properties.inputs`` by socket IDENTIFIER, then ``.value``.
    """
    getattr(mod.properties.inputs, identifier).value = value


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj, ng, ident = build_parametric_box()
    mod = obj.modifiers["GN"]

    # The 4.x idiom every model reproduces from memory. In 5.2 it raises.
    legacy_read_error = None
    try:
        _ = mod[ident["Length"]]
    except Exception as exc:
        legacy_read_error = type(exc).__name__

    legacy_write_error = None
    try:
        mod[ident["Length"]] = 0.9
    except Exception as exc:
        legacy_write_error = type(exc).__name__

    legacy_keys_error = None
    try:
        mod.keys()
    except Exception as exc:
        legacy_keys_error = type(exc).__name__

    # The 5.2 form.
    set_input(mod, ident["Length"], 0.750)
    obj.update_tag()
    bpy.context.evaluated_depsgraph_get().update()
    readback = getattr(mod.properties.inputs, ident["Length"]).value
    _, _, dims = cadlib.bbox_world(obj)

    # Reordering the interface changes identifiers, so labels must be
    # re-resolved each run rather than hard-coded.
    remap = {i.name: i.identifier for i in ng.interface.items_tree
             if i.item_type == 'SOCKET' and i.in_out == 'INPUT'}

    return [
        ("legacy dict-style READ raises in 5.2",
         legacy_read_error == "TypeError", f"raised {legacy_read_error}"),
        ("legacy dict-style WRITE raises in 5.2",
         legacy_write_error == "TypeError", f"raised {legacy_write_error}"),
        ("modifier.keys() raises in 5.2",
         legacy_keys_error == "TypeError", f"raised {legacy_keys_error}"),
        ("properties.inputs.<identifier>.value reads back the set value",
         abs(readback - 0.750) < 1e-9, f"readback={readback}"),
        ("the set value actually drives evaluated geometry",
         abs(dims[0] - 0.750) < 1e-6, f"evaluated X={dims[0]:.6f}"),
        ("labels re-resolve to identifiers at runtime",
         remap == ident, f"{remap}"),
    ]
