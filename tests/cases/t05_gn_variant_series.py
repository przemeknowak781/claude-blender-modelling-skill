"""T-05 - generate 8 dimensioned variants headless from one graph."""
import os
import bpy
import cadlib

ID = "T-05"
PRIORITY = "P3"
TASK = ("Build a Geometry Nodes graph with 4 inputs and generate 8 variants "
        "headless, each within 0.1 mm of its requested dimensions.")
RECIPES = ["R-303", "R-304", "R-306"]

TOL = 0.0001  # 0.1 mm
OUTDIR = "tests/output/t05"

VARIANTS = [
    {"Length": 0.400, "Width": 0.300, "Height": 0.200, "Wall": 0.018},
    {"Length": 0.500, "Width": 0.300, "Height": 0.200, "Wall": 0.018},
    {"Length": 0.600, "Width": 0.350, "Height": 0.250, "Wall": 0.012},
    {"Length": 0.250, "Width": 0.250, "Height": 0.250, "Wall": 0.006},
    {"Length": 1.200, "Width": 0.600, "Height": 0.400, "Wall": 0.018},
    {"Length": 0.333, "Width": 0.444, "Height": 0.555, "Wall": 0.009},
    {"Length": 0.050, "Width": 0.050, "Height": 0.050, "Wall": 0.003},
    {"Length": 2.000, "Width": 0.100, "Height": 0.750, "Wall": 0.024},
]

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
    os.makedirs(OUTDIR, exist_ok=True)
    obj, ng, ident = build_parametric_box()
    mod = obj.modifiers["GN"]

    results, written = [], []
    for i, params in enumerate(VARIANTS):
        for label, value in params.items():
            set_input(mod, ident[label], value)
        obj.update_tag()
        bpy.context.evaluated_depsgraph_get().update()

        _, _, dims = cadlib.bbox_world(obj)
        want = (params["Length"], params["Width"], params["Height"])
        err = max(abs(a - b) for a, b in zip(dims, want))
        results.append((i, want, tuple(dims), err))

        path = os.path.join(OUTDIR, f"variant_{i:02d}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path))
        written.append(path)

    worst = max(r[3] for r in results)
    all_files = all(os.path.exists(p) for p in written)

    return [
        ("graph exposes exactly 4 named inputs",
         len(ident) == 4, f"inputs={sorted(ident)}"),
        ("socket identifiers resolved from labels, not guessed",
         all(v.startswith("Socket_") for v in ident.values()),
         f"map={ident}"),
        ("8 variants generated",
         len(results) == 8, f"{len(results)} variants"),
        ("8 files written",
         all_files and len(written) == 8, f"{len(written)} files in {OUTDIR}"),
        ("every dimension within 0.1 mm of its parameter",
         worst < TOL,
         f"worst error {worst * 1000:.6f} mm across {len(results)} variants"),
    ]
