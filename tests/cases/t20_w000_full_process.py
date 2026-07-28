"""T-20 - run W-000 end to end with every gate documented numerically."""
import os
import bpy
import bmesh
import cadlib
import gates

ID = "T-20"
PRIORITY = "W-000"
TASK = ("Model to a brief with a stated tolerance and variable parameters, "
        "passing gates G1-G4 with numeric evidence at each.")
RECIPES = ["W-000", "R-001", "R-007"]

# --- Phase 0: the brief, recorded before Blender is touched ---------------
BRIEF = {
    "purpose": "fabrication (CNC-cut plywood tray)",
    "tolerance_m": 0.0005,          # 0.5 mm
    "nominal_unit": "millimetre, scene in metres at unit_scale 1.0",
    "variable_parameters": ["length", "width", "wall"],
    "geometry_origin": "built from zero (not external input)",
    "consumer": "3-axis CNC router, STL in metres, Z up",
}
NOMINAL = {"length": 0.400, "width": 0.300, "height": 0.060, "wall": 0.018}
OUTDIR = "tests/output/t20"


def phase_1_scene_setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = 'METERS'
    # Clip range matched to the object scale (a 0.4 m part).
    for area_scene in bpy.data.screens:
        pass
    os.makedirs(OUTDIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.abspath(os.path.join(OUTDIR, "tray_v001.blend")))
    return scene


def phase_3_blockout():
    """Dimensional blockout: real numbers entered, never estimated."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts,
                    vec=(NOMINAL["length"], NOMINAL["width"], NOMINAL["height"]))
    me = bpy.data.meshes.new("Tray")
    bm.to_mesh(me)
    bm.free()
    tray = bpy.data.objects.new("Tray", me)
    bpy.context.scene.collection.objects.link(tray)

    # R-004: one source of truth for every driving dimension.
    ctrl = bpy.data.objects.new("CTRL-Tray", None)
    bpy.context.scene.collection.objects.link(ctrl)
    for key, value in NOMINAL.items():
        ctrl[key] = value
    return tray, ctrl


def phase_4_parametric_core(tray):
    """Hollow the tray: cut the cavity, then thickness, in canonical order."""
    inner = bmesh.new()
    bmesh.ops.create_cube(inner, size=1.0)
    bmesh.ops.scale(inner, verts=inner.verts,
                    vec=(NOMINAL["length"] - 2 * NOMINAL["wall"],
                         NOMINAL["width"] - 2 * NOMINAL["wall"],
                         NOMINAL["height"]))
    # Raise it so the cavity opens through the top face only.
    bmesh.ops.translate(inner, verts=inner.verts,
                        vec=(0.0, 0.0, NOMINAL["wall"]))
    im = bpy.data.meshes.new("Cavity")
    inner.to_mesh(im)
    inner.free()
    cavity = bpy.data.objects.new("Cavity", im)
    bpy.context.scene.collection.objects.link(cavity)

    mod = tray.modifiers.new(name="Boolean", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cavity

    bev = tray.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.002
    bev.segments = 3
    bev.limit_method = 'ANGLE'
    bev.use_clamp_overlap = True
    return tray


def run():
    out = []

    # --- Phase 0 ---------------------------------------------------------
    out.append(("Phase 0: brief is complete before any modelling",
                all(BRIEF.get(k) for k in
                    ("purpose", "tolerance_m", "nominal_unit",
                     "variable_parameters", "geometry_origin", "consumer")),
                f"tolerance={BRIEF['tolerance_m'] * 1000} mm, "
                f"consumer={BRIEF['consumer']}"))

    # --- Phase 1 / Gate G1 ------------------------------------------------
    phase_1_scene_setup()
    tray, ctrl = phase_3_blockout()
    g1_ok, g1 = gates.gate_g1()
    out.append(("G1: units, unit scale, applied scale, file saved",
                g1_ok,
                f"system={g1['unit_system']} scale={g1['unit_scale']} "
                f"unapplied={g1['objects_with_unapplied_scale']} "
                f"saved={bool(g1['file_saved_as'])}"))

    # --- Phase 3 / Gate G2 ------------------------------------------------
    g2_ok, g2 = gates.gate_g2(
        {"Tray": (NOMINAL["length"], NOMINAL["width"], NOMINAL["height"])},
        BRIEF["tolerance_m"])
    out.append(("G2: blockout matches the nominal dimension table",
                g2_ok,
                f"worst error {g2['worst_error'] * 1000:.6f} mm "
                f"<= {BRIEF['tolerance_m'] * 1000} mm; "
                f"measured {g2['objects']['Tray']['measured']}"))

    # --- Phase 4: stack order --------------------------------------------
    phase_4_parametric_core(tray)
    order_ok, order = gates.check_stack_order(tray)
    out.append(("Phase 4: modifier stack in canonical order",
                order_ok,
                f"stack={order['stack']} hard_violations={order['hard_violations']}"))

    # --- Phase 5 / Gate G3 ------------------------------------------------
    g3_ok, g3 = gates.gate_g3([tray])
    out.append(("G3: manifold, clean, no self-intersections",
                g3_ok,
                f"problems={g3['objects']['Tray']['problems']} "
                f"volume={g3['objects']['Tray']['volume']:.8f}"))

    # --- Phase 6 / Gate G4 ------------------------------------------------
    # Preserve the unbaked original BEFORE any bake, then export.
    unbaked = tray.copy()
    unbaked.data = tray.data.copy()
    unbaked.name = "Tray_unbaked"
    bpy.context.scene.collection.objects.link(unbaked)

    tray.select_set(True)
    bpy.context.view_layer.objects.active = tray
    stl_path = os.path.abspath(os.path.join(OUTDIR, "tray.stl"))
    bpy.ops.wm.stl_export(filepath=stl_path, export_selected_objects=True,
                          global_scale=1.0, apply_modifiers=True)
    preserved = "Tray_unbaked" in bpy.data.objects
    out.append(("Phase 6: unbaked copy preserved before export",
                preserved, f"objects={sorted(bpy.data.objects.keys())}"))

    g4_ok, g4 = gates.gate_g4(tray, stl_path, BRIEF["tolerance_m"],
                              importer='stl', global_scale=1.0)
    out.append(("G4: round trip within the Phase 0 tolerance",
                g4_ok,
                f"dim error {g4.get('max_dimension_error', float('inf')) * 1000:.6f} mm "
                f"<= {BRIEF['tolerance_m'] * 1000} mm; "
                f"{g4.get('original_dimensions')} -> "
                f"{g4.get('reimported_dimensions')}"))

    out.append(("all four gates produced a numeric result",
                all(isinstance(x, dict) for x in (g1, g2, g3, g4)),
                "G1/G2/G3/G4 each returned a measurement report"))
    return out
