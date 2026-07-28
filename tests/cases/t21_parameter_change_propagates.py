"""T-21 - change a parameter by 30 percent; the model must recompute."""
import bpy
import cadlib
import gates

ID = "T-21"
PRIORITY = "W-000"
TASK = ("After the model is finished, change one driving parameter by 30 "
        "percent and confirm it recomputes with no manual mesh editing, and "
        "that G3 still passes.")
RECIPES = ["W-000", "R-303", "R-304"]

TOL = 0.0001
START_LENGTH = 0.400


def build_parametric_tray():
    """Tray whose length is a graph input, so it is genuinely reparametrisable."""
    ng = bpy.data.node_groups.new("Tray", 'GeometryNodeTree')
    out_sock = ng.interface.new_socket(name="Geometry", in_out='OUTPUT',
                                       socket_type='NodeSocketGeometry')
    specs = [("Length", START_LENGTH), ("Width", 0.300), ("Height", 0.060)]
    for label, default in specs:
        s = ng.interface.new_socket(name=label, in_out='INPUT',
                                    socket_type='NodeSocketFloat')
        s.default_value = default
        s.min_value = 0.001

    ident = {i.name: i.identifier for i in ng.interface.items_tree
             if i.item_type == 'SOCKET' and i.in_out == 'INPUT'}

    gi = ng.nodes.new('NodeGroupInput')
    go = ng.nodes.new('NodeGroupOutput')
    cube = ng.nodes.new('GeometryNodeMeshCube')
    combine = ng.nodes.new('ShaderNodeCombineXYZ')
    ng.links.new(gi.outputs[ident["Length"]], combine.inputs['X'])
    ng.links.new(gi.outputs[ident["Width"]], combine.inputs['Y'])
    ng.links.new(gi.outputs[ident["Height"]], combine.inputs['Z'])
    ng.links.new(combine.outputs['Vector'], cube.inputs['Size'])
    ng.links.new(cube.outputs['Mesh'], go.inputs[out_sock.identifier])

    me = bpy.data.meshes.new("Tray")
    obj = bpy.data.objects.new("Tray", me)
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new(name="GN", type='NODES')
    mod.node_group = ng
    return obj, mod, ident


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0

    obj, mod, ident = build_parametric_tray()

    def evaluate():
        obj.update_tag()
        bpy.context.evaluated_depsgraph_get().update()
        return cadlib.bbox_world(obj)[2]

    first = evaluate()
    mesh_verts_before = len(obj.data.vertices)

    # +30 percent on one parameter. Nothing else is touched, and no vertex is
    # edited by hand -- that is the whole point of the parametric core.
    new_length = START_LENGTH * 1.30
    getattr(mod.properties.inputs, ident["Length"]).value = new_length
    second = evaluate()
    mesh_verts_after = len(obj.data.vertices)

    g3_ok, g3 = gates.gate_g3([obj])

    return [
        ("model starts at the nominal length",
         abs(first[0] - START_LENGTH) < TOL,
         f"measured {first[0]:.6f} expected {START_LENGTH}"),
        ("30 percent parameter change propagates to geometry",
         abs(second[0] - new_length) < TOL,
         f"measured {second[0]:.6f} expected {new_length:.6f}"),
        ("no other dimension moved",
         abs(second[1] - first[1]) < 1e-9 and abs(second[2] - first[2]) < 1e-9,
         f"{tuple(round(v, 6) for v in first)} -> "
         f"{tuple(round(v, 6) for v in second)}"),
        ("the base mesh was never hand-edited",
         mesh_verts_before == mesh_verts_after == 0,
         f"base mesh vertices {mesh_verts_before} -> {mesh_verts_after} "
         "(all geometry comes from the graph)"),
        ("G3 still passes after the change",
         g3_ok, f"problems={g3['objects']['Tray']['problems']}"),
    ]
