"""Generate synthetic test fixtures. No production data ever enters the suite.

Run:  blender --background --factory-startup --python tests/fixtures/make_fixtures.py -- <outdir>
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def save(path):
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("FIXTURE", path)


def new_mesh_object(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# --- F1: marching-cubes-like dense blob, non-manifold, with debris ---------
def fixture_marching_cubes(outdir):
    reset()
    # A metaball converted to mesh gives a dense, irregular, isosurface-like mesh.
    mb = bpy.data.metaballs.new("MB")
    mb.resolution = 0.06
    mb.render_resolution = 0.06
    ob = bpy.data.objects.new("MB", mb)
    bpy.context.scene.collection.objects.link(ob)
    for pos, rad in [((0, 0, 0), 1.0), ((0.9, 0, 0), 0.7), ((0, 0.8, 0.3), 0.6),
                     ((-0.7, -0.5, 0.2), 0.55)]:
        el = mb.elements.new()
        el.co = Vector(pos)
        el.radius = rad

    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)

    blob = bpy.data.objects.new("Blob", me)
    bpy.context.scene.collection.objects.link(blob)

    # Subdivide to push the triangle count up, mimicking a dense solver export.
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    # Four subdivision passes bring this to ~1.2M triangles, matching the
    # density of a real topology-optimisation export (test T-01).
    for _ in range(4):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])

    # Damage it the way a real solver export is damaged:
    # 1. flip a patch of normals
    for f in bm.faces[:80]:
        f.normal_flip()
    # 2. add an isolated debris shell far from the body
    deb = bmesh.new()
    bmesh.ops.create_cube(deb, size=0.15)
    bmesh.ops.translate(deb, verts=deb.verts, vec=Vector((4.0, 4.0, 4.0)))
    tmp = bpy.data.meshes.new("deb")
    deb.to_mesh(tmp)
    deb.free()
    bm.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)
    # 3. loose vertices
    for i in range(12):
        bm.verts.new(Vector((3.0 + i * 0.1, -3.0, 0.0)))

    bm.to_mesh(me)
    bm.free()
    me.update()
    save(os.path.join(outdir, "marching_cubes_blob.blend"))


# --- F2: open curved surface for Solidify ---------------------------------
def fixture_curved_surface(outdir):
    reset()
    bm = bmesh.new()
    n = 24
    span = 2.0
    verts = {}
    for i in range(n + 1):
        for j in range(n + 1):
            x = -span / 2 + span * i / n
            y = -span / 2 + span * j / n
            z = 0.35 * math.sin(2.2 * x) * math.cos(1.7 * y)
            verts[(i, j)] = bm.verts.new((x, y, z))
    bm.verts.ensure_lookup_table()
    for i in range(n):
        for j in range(n):
            bm.faces.new((verts[(i, j)], verts[(i + 1, j)],
                          verts[(i + 1, j + 1)], verts[(i, j + 1)]))
    new_mesh_object("Surface", bm)
    save(os.path.join(outdir, "curved_surface.blend"))


# --- F3: two solids with genuinely coplanar faces --------------------------
def fixture_coplanar(outdir):
    reset()
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)          # spans -1..1 on every axis
    new_mesh_object("Base", bm)

    bm2 = bmesh.new()
    bmesh.ops.create_cube(bm2, size=1.0)         # spans -0.5..0.5
    # Shift so its -X face sits exactly on the base's -X face at x = -1,
    # and its top face sits exactly on the base's top face at z = 1.
    bmesh.ops.translate(bm2, verts=bm2.verts, vec=Vector((-0.5, 0.0, 0.5)))
    new_mesh_object("Cutter", bm2)
    save(os.path.join(outdir, "coplanar_pair.blend"))


# --- F4: sheet part for contour extraction ---------------------------------
def fixture_sheet_part(outdir):
    reset()
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=Vector((0.600, 0.400, 0.018)))
    ob = new_mesh_object("SheetPart", bm)
    ob.location = (0, 0, 0.009)
    save(os.path.join(outdir, "sheet_part.blend"))


# --- F5: stepped / voxel-aliased solid -------------------------------------
def fixture_stepped(outdir):
    reset()
    bm = bmesh.new()
    step = 0.1
    # A quarter-cylinder approximated by stacked boxes -> hard stair-stepping.
    for k in range(10):
        z = k * step
        r = math.sqrt(max(1.0 - (z + step / 2) ** 2, 1e-6))
        nx = max(int(r / step), 1)
        for i in range(nx):
            sub = bmesh.new()
            bmesh.ops.create_cube(sub, size=1.0)
            bmesh.ops.scale(sub, verts=sub.verts, vec=Vector((step, step, step)))
            bmesh.ops.translate(sub, verts=sub.verts,
                                vec=Vector((i * step + step / 2, 0.0, z + step / 2)))
            tmp = bpy.data.meshes.new("t")
            sub.to_mesh(tmp)
            sub.free()
            bm.from_mesh(tmp)
            bpy.data.meshes.remove(tmp)
    new_mesh_object("Stepped", bm)
    save(os.path.join(outdir, "stepped_solid.blend"))


# --- F6: millimetre-scale STL for unit tests -------------------------------
def fixture_mm_stl(outdir):
    reset()
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    # 40 x 25 x 12 "millimetres", written as bare numbers into STL.
    bmesh.ops.scale(bm, verts=bm.verts, vec=Vector((40.0, 25.0, 12.0)))
    ob = new_mesh_object("MMPart", bm)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.wm.stl_export(filepath=os.path.join(outdir, "part_mm.stl"),
                          export_selected_objects=True, global_scale=1.0)
    print("FIXTURE", os.path.join(outdir, "part_mm.stl"))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    outdir = argv[0] if argv else os.path.dirname(__file__)
    os.makedirs(outdir, exist_ok=True)
    fixture_marching_cubes(outdir)
    fixture_curved_surface(outdir)
    fixture_coplanar(outdir)
    fixture_sheet_part(outdir)
    fixture_stepped(outdir)
    fixture_mm_stl(outdir)
    print("FIXTURES_OK")


main()
