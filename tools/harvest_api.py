"""Harvest Blender API identifiers by live introspection.

Run:  blender --background --factory-startup --python tools/harvest_api.py -- <outfile>

Emits a JSON dump that is the ONLY permitted source of API identifiers used in
the skill's Markdown. See tools/validate_identifiers.py for the enforcement side.
"""
import bpy
import json
import sys
import platform

MODIFIERS = [
    'SOLIDIFY', 'BEVEL', 'BOOLEAN', 'ARRAY', 'MIRROR', 'SCREW', 'REMESH',
    'DECIMATE', 'WELD', 'SHRINKWRAP', 'NODES', 'SUBSURF', 'TRIANGULATE',
    'WEIGHTED_NORMAL', 'EDGE_SPLIT', 'SMOOTH', 'CORRECTIVE_SMOOTH', 'CAST',
    'DISPLACE', 'SIMPLE_DEFORM', 'CURVE', 'LATTICE', 'WIREFRAME', 'SKIN',
    'MASK', 'BUILD', 'MULTIRES',
]

# Geometry Nodes node types relevant to CAD-style parametric work.
GN_NODES = [
    'GeometryNodeExtrudeMesh', 'GeometryNodeMeshBoolean', 'GeometryNodeBevel',
    'GeometryNodeInstanceOnPoints', 'GeometryNodeRealizeInstances',
    'GeometryNodeTransform', 'GeometryNodeSetPosition', 'GeometryNodeJoinGeometry',
    'GeometryNodeMergeByDistance', 'GeometryNodeMeshLine', 'GeometryNodeMeshCube',
    'GeometryNodeMeshCylinder', 'GeometryNodeMeshCircle', 'GeometryNodeMeshGrid',
    'GeometryNodeCurveToMesh', 'GeometryNodeCurvePrimitiveCircle',
    'GeometryNodeCurvePrimitiveLine', 'GeometryNodeFillCurve',
    'GeometryNodeCurveToPoints', 'GeometryNodeResampleCurve',
    'GeometryNodeFilletCurve', 'GeometryNodeTrimCurve',
    'GeometryNodeSubdivisionSurface', 'GeometryNodeDualMesh',
    'GeometryNodeFlipFaces', 'GeometryNodeScaleElements',
    'GeometryNodeSeparateGeometry', 'GeometryNodeDeleteGeometry',
    'GeometryNodeSeparateComponents', 'GeometryNodeBoundBox',
    'GeometryNodeConvexHull', 'GeometryNodeTriangulate',
    'GeometryNodeSetShadeSmooth', 'GeometryNodeInputMeshFaceArea',
    'GeometryNodeInputMeshEdgeAngle', 'GeometryNodeInputNormal',
    'GeometryNodeInputPosition', 'GeometryNodeInputIndex',
    'GeometryNodeCaptureAttribute', 'GeometryNodeStoreNamedAttribute',
    'GeometryNodeSampleIndex', 'GeometryNodeAttributeStatistic',
    'GeometryNodeRaycast', 'GeometryNodeProximity',
    'GeometryNodeSwitch', 'GeometryNodeIndexSwitch',
    'GeometryNodeMeshToCurve', 'GeometryNodeMeshToPoints',
    'GeometryNodeSplitEdges', 'GeometryNodeEdgePathsToCurves',
    'ShaderNodeMath', 'ShaderNodeVectorMath', 'ShaderNodeMapRange',
    'ShaderNodeCombineXYZ', 'ShaderNodeSeparateXYZ', 'ShaderNodeClamp',
    'FunctionNodeCompare', 'FunctionNodeRandomValue', 'FunctionNodeBooleanMath',
    'FunctionNodeAlignRotationToVector', 'FunctionNodeInputVector',
    'NodeGroupInput', 'NodeGroupOutput',
]

OPERATORS = [
    ('mesh', 'select_non_manifold'), ('mesh', 'remove_doubles'),
    ('mesh', 'normals_make_consistent'), ('mesh', 'select_all'),
    ('mesh', 'separate'), ('mesh', 'select_linked'), ('mesh', 'delete_loose'),
    ('mesh', 'dissolve_degenerate'), ('mesh', 'dissolve_limited'),
    ('mesh', 'quads_convert_to_tris'), ('mesh', 'bisect'),
    ('mesh', 'extrude_region_move'), ('mesh', 'bridge_edge_loops'),
    ('mesh', 'bevel'), ('mesh', 'inset'), ('mesh', 'fill_holes'),
    ('mesh', 'face_make_planar'), ('mesh', 'select_interior_faces'),
    ('mesh', 'primitive_cube_add'), ('mesh', 'primitive_cylinder_add'),
    ('object', 'transform_apply'), ('object', 'modifier_apply'),
    ('object', 'modifier_add'), ('object', 'convert'),
    ('object', 'origin_set'), ('object', 'shade_smooth'),
    ('object', 'shade_auto_smooth'), ('object', 'duplicate'),
    ('object', 'join'), ('object', 'select_all'),
    ('wm', 'stl_import'), ('wm', 'stl_export'),
    ('wm', 'obj_import'), ('wm', 'obj_export'),
    ('wm', 'ply_import'), ('wm', 'ply_export'),
    ('wm', 'save_as_mainfile'), ('wm', 'open_mainfile'),
    ('wm', 'read_factory_settings'), ('wm', 'read_homefile'),
    ('wm', 'quit_blender'), ('wm', 'save_mainfile'),
    ('object', 'modifier_move_to_index'), ('object', 'modifier_remove'),
    ('object', 'modifier_move_up'), ('object', 'modifier_move_down'),
    ('object', 'parent_set'), ('object', 'delete'),
    ('mesh', 'select_mode'), ('mesh', 'edge_split'),
    ('wm', 'ply_export'), ('wm', 'usd_export'), ('wm', 'usd_import'),
    ('wm', 'grease_pencil_export_svg'), ('wm', 'grease_pencil_export_pdf'),
    ('wm', 'grease_pencil_import_svg'), ('import_curve', 'svg'),
    ('export_scene', 'gltf'), ('import_scene', 'gltf'),
    ('render', 'render'), ('render', 'opengl'),
]

# Node TREE bl_idnames (not nodes): valid identifiers of a different kind.
NODE_TREES = ['GeometryNodeTree', 'ShaderNodeTree', 'CompositorNodeTree']

STRUCTS = [
    'UnitSettings', 'Scene', 'Object', 'Mesh', 'MeshPolygon', 'MeshVertex',
    'MeshEdge', 'View3DOverlay', 'SpaceView3D', 'ToolSettings',
    'NodesModifier', 'Collection', 'Curve', 'SplinePoint', 'Spline',
]


def prop_info(p, owner=None):
    """Describe one RNA property.

    ``enum`` is what ``bl_rna`` advertises; ``enum_settable`` is what the live
    instance actually accepts. They differ on polymorphic nodes (Compare
    advertises 24 data types and accepts 11), so only ``enum_settable`` may be
    quoted in the skill text.
    """
    d = {"type": p.type, "readonly": p.is_readonly}
    if p.type == 'ENUM':
        try:
            d["enum"] = [i.identifier for i in p.enum_items]
        except Exception:
            d["enum"] = None
        if owner is not None and not p.is_readonly and d.get("enum"):
            settable, original = [], getattr(owner, p.identifier, None)
            for ident in d["enum"]:
                try:
                    setattr(owner, p.identifier, ident)
                except Exception:
                    continue
                settable.append(ident)
            if original is not None:
                try:
                    setattr(owner, p.identifier, original)
                except Exception:
                    pass
            d["enum_settable"] = settable
    for attr in ("default", "unit", "subtype"):
        try:
            v = getattr(p, attr, None)
            if v is not None and not hasattr(v, "__len__") or isinstance(v, str):
                d[attr] = v
            elif v is not None:
                d[attr] = list(v)
        except Exception:
            pass
    return d


def dump_struct(rna, owner=None):
    out = {}
    for p in rna.bl_rna.properties:
        if p.identifier == 'rna_type':
            continue
        try:
            out[p.identifier] = prop_info(p, owner)
        except Exception as exc:  # pragma: no cover - defensive
            out[p.identifier] = {"error": str(exc)}
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    outfile = argv[0] if argv else "api_dump.json"

    data = {
        "blender_version": bpy.app.version_string,
        "blender_version_tuple": list(bpy.app.version),
        "build_hash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
        "build_date": bpy.app.build_date.decode() if isinstance(bpy.app.build_date, bytes) else str(bpy.app.build_date),
        "python_version": platform.python_version(),
        "modifiers": {},
        "nodes": {},
        "operators": {},
        "structs": {},
        "bmesh_ops": [],
        "node_trees": NODE_TREES,
    }

    # --- modifiers -------------------------------------------------------
    bpy.ops.mesh.primitive_cube_add(size=2)
    ob = bpy.context.object
    for mtype in MODIFIERS:
        try:
            m = ob.modifiers.new(name="H_" + mtype, type=mtype)
        except Exception as exc:
            data["modifiers"][mtype] = {"__error__": str(exc)}
            continue
        data["modifiers"][mtype] = {
            "bl_rna_identifier": type(m).__name__,
            "properties": dump_struct(m, m),
        }
        ob.modifiers.remove(m)

    # --- geometry nodes --------------------------------------------------
    ng = bpy.data.node_groups.new("HARVEST", 'GeometryNodeTree')
    for ntype in GN_NODES:
        try:
            n = ng.nodes.new(ntype)
        except Exception as exc:
            data["nodes"][ntype] = {"__error__": str(exc)}
            continue
        entry = {
            "bl_label": n.bl_label,
            "properties": dump_struct(n, n),
            "inputs": [
                {"identifier": s.identifier, "name": s.name, "type": s.type}
                for s in n.inputs
            ],
            "outputs": [
                {"identifier": s.identifier, "name": s.name, "type": s.type}
                for s in n.outputs
            ],
        }
        # Polymorphic nodes expose different sockets per data_type / mode.
        for switch in ("data_type", "mode", "operation", "domain"):
            prop = n.bl_rna.properties.get(switch)
            if prop is None or prop.type != 'ENUM' or prop.is_readonly:
                continue
            variants = {}
            original = getattr(n, switch)
            for item in prop.enum_items:
                try:
                    setattr(n, switch, item.identifier)
                except Exception:
                    continue
                variants[item.identifier] = {
                    "inputs": [s.identifier for s in n.inputs if s.enabled],
                    "outputs": [s.identifier for s in n.outputs if s.enabled],
                }
            try:
                setattr(n, switch, original)
            except Exception:
                pass
            if variants:
                entry.setdefault("sockets_by", {})[switch] = variants
        data["nodes"][ntype] = entry
        ng.nodes.remove(n)
    bpy.data.node_groups.remove(ng)

    # --- operators -------------------------------------------------------
    for mod, name in OPERATORS:
        key = f"{mod}.{name}"
        try:
            op = getattr(getattr(bpy.ops, mod), name)
            rna = op.get_rna_type()
        except Exception as exc:
            data["operators"][key] = {"__error__": str(exc)}
            continue
        props = {}
        for p in rna.properties:
            if p.identifier == 'rna_type':
                continue
            props[p.identifier] = prop_info(p)
        data["operators"][key] = {"description": rna.description, "properties": props}

    # --- structs ---------------------------------------------------------
    for sname in STRUCTS:
        try:
            rna = getattr(bpy.types, sname)
        except Exception as exc:
            data["structs"][sname] = {"__error__": str(exc)}
            continue
        out = {}
        for p in rna.bl_rna.properties:
            if p.identifier == 'rna_type':
                continue
            try:
                out[p.identifier] = prop_info(p)
            except Exception as exc:
                out[p.identifier] = {"error": str(exc)}
        data["structs"][sname] = out

    # --- runtime-only types ----------------------------------------------
    # Some 5.2 types are reachable only from a live instance, not via
    # bpy.types (e.g. the Geometry Nodes modifier input interface). Record
    # their real class names so documentation may refer to them.
    runtime = {}
    ng_rt = bpy.data.node_groups.new("RT", 'GeometryNodeTree')
    ng_rt.interface.new_socket(name="Geometry", in_out='OUTPUT',
                               socket_type='NodeSocketGeometry')
    sock_rt = ng_rt.interface.new_socket(name="Value", in_out='INPUT',
                                         socket_type='NodeSocketFloat')
    mod_rt = ob.modifiers.new(name="RT", type='NODES')
    mod_rt.node_group = ng_rt
    runtime[type(mod_rt.properties).__name__] = {
        "reached_via": "modifier.properties",
        "properties": [p.identifier for p in mod_rt.properties.bl_rna.properties
                       if p.identifier != 'rna_type'],
    }
    inputs_rt = mod_rt.properties.inputs
    runtime[type(inputs_rt).__name__] = {
        "reached_via": "modifier.properties.inputs",
        "properties": [p.identifier for p in inputs_rt.bl_rna.properties
                       if p.identifier != 'rna_type'],
    }
    sock_acc = getattr(inputs_rt, sock_rt.identifier)
    runtime["_socket_accessor_properties"] = {
        "reached_via": "modifier.properties.inputs.<Socket_N>",
        "properties": [p.identifier for p in sock_acc.bl_rna.properties
                       if p.identifier != 'rna_type'],
    }
    ob.modifiers.remove(mod_rt)
    bpy.data.node_groups.remove(ng_rt)
    data["runtime_types"] = runtime

    # --- bmesh.ops -------------------------------------------------------
    import bmesh
    data["bmesh_ops"] = sorted(n for n in dir(bmesh.ops) if not n.startswith("_"))

    with open(outfile, "w") as fh:
        json.dump(data, fh, indent=1, sort_keys=True, default=str)
    print(f"HARVEST_OK {outfile}")
    print("modifiers", len(data["modifiers"]), "nodes", len(data["nodes"]),
          "operators", len(data["operators"]), "structs", len(data["structs"]),
          "bmesh_ops", len(data["bmesh_ops"]))


main()
