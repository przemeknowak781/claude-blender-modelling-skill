"""T-13 - dimensioned building mass with storey heights."""
import bpy
import bmesh
import cadlib

ID = "T-13"
PRIORITY = "P2"
TASK = ("Build a 4-storey mass from a dimensioned footprint and confirm every "
        "level lands within 1 mm of its nominal elevation.")
RECIPES = ["R-215", "R-217", "R-001"]

FOOTPRINT = (24.000, 13.500)
STOREY_H = 3.250
N_STOREYS = 4
SLAB = 0.220
TOL = 0.001  # 1 mm over a 24 m building


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0

    # One slab, arrayed by exact storey height. The array is the single source
    # of truth for level spacing -- no elevation is ever retyped.
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(FOOTPRINT[0], FOOTPRINT[1], SLAB))
    me = bpy.data.meshes.new("Slab")
    bm.to_mesh(me)
    bm.free()
    slab = bpy.data.objects.new("Slab", me)
    bpy.context.scene.collection.objects.link(slab)

    mod = slab.modifiers.new(name="Array", type='ARRAY')
    mod.fit_type = 'FIXED_COUNT'
    mod.count = N_STOREYS
    mod.use_relative_offset = False
    mod.use_constant_offset = True
    mod.constant_offset_displace = (0.0, 0.0, STOREY_H)

    rep = cadlib.diagnose(slab, check_self_intersect=False)
    _, hi, dims = cadlib.bbox_world(slab)

    # Recover each slab's soffit elevation from the evaluated geometry.
    bmv = cadlib.evaluated_bmesh(slab)
    zs = sorted({round(v.co.z, 6) for v in bmv.verts})
    bmv.free()
    expected_z = sorted({round(-SLAB / 2 + i * STOREY_H, 6) for i in range(N_STOREYS)}
                        | {round(SLAB / 2 + i * STOREY_H, 6) for i in range(N_STOREYS)})
    z_err = (max(abs(a - b) for a, b in zip(zs, expected_z))
             if len(zs) == len(expected_z) else float("inf"))

    expected_height = SLAB + (N_STOREYS - 1) * STOREY_H

    return [
        ("scene is metric at 1.0 unit scale",
         scene.unit_settings.system == 'METRIC'
         and scene.unit_settings.scale_length == 1.0,
         f"{scene.unit_settings.system} scale={scene.unit_settings.scale_length}"),
        ("footprint matches nominal within 1 mm",
         abs(dims[0] - FOOTPRINT[0]) < TOL and abs(dims[1] - FOOTPRINT[1]) < TOL,
         f"measured ({dims[0]:.4f}, {dims[1]:.4f}) vs nominal {FOOTPRINT}"),
        ("overall height matches nominal within 1 mm",
         abs(dims[2] - expected_height) < TOL,
         f"measured {dims[2]:.4f} vs expected {expected_height:.4f}"),
        ("all 4 storeys present",
         rep["shells"] == N_STOREYS, f"shells={rep['shells']}"),
        ("every level elevation within 1 mm of nominal",
         z_err < TOL, f"max elevation error {z_err * 1000:.6f} mm"),
        ("mm precision retained at 24 m span",
         dims[0] / TOL > 1e4 and abs(dims[0] - FOOTPRINT[0]) < 1e-6,
         f"span/tolerance ratio {dims[0] / TOL:.0f}, "
         f"actual error {abs(dims[0] - FOOTPRINT[0]):.3e} m"),
    ]
