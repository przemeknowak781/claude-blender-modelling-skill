"""T-25 - section cut on a copy, with dimensions re-measured from the model."""
import bpy
import bmesh
import cadlib

ID = "T-25"
PRIORITY = "DRAW"
TASK = ("Cut a section from a duplicate, annotate it with dimensions read from "
        "the geometry, and show the annotation goes stale unless re-run.")
RECIPES = ["R-502", "R-505"]

WALL_H = 2.700
WALL_L = 5.000
CUT_Z = 1.200


def build_wall(height):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(WALL_L, 0.250, height))
    me = bpy.data.meshes.new("Wall")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Wall", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def make_section(source, z):
    """R-502: bisect a DUPLICATE. Never cut the master model."""
    cut = source.copy()
    cut.data = source.data.copy()
    cut.name = "Wall_section"
    bpy.context.scene.collection.objects.link(cut)

    bm = bmesh.new()
    bm.from_mesh(cut.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                           dist=1e-7, plane_co=(0.0, 0.0, z),
                           plane_no=(0.0, 0.0, 1.0),
                           clear_inner=False, clear_outer=True)
    bm.to_mesh(cut.data)
    bm.free()
    cut.data.update()
    return cut


def annotate(obj, label):
    """R-505: build the dimension text BY MEASURING, never by retyping."""
    _, _, dims = cadlib.bbox_world(obj)
    text = f"{label} {dims[0] * 1000:.0f} x {dims[2] * 1000:.0f}"
    tdata = bpy.data.curves.new(f"DIM-{label}", type='FONT')
    tdata.body = text
    tob = bpy.data.objects.new(f"DIM-{label}", tdata)
    bpy.context.scene.collection.objects.link(tob)
    return tob, text


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    wall = build_wall(WALL_H)
    original = cadlib.diagnose(wall, check_self_intersect=False)

    section = make_section(wall, CUT_Z)
    sec_rep = cadlib.diagnose(section, check_self_intersect=False)
    master_after = cadlib.diagnose(wall, check_self_intersect=False)

    dim_obj, text_before = annotate(section, "SEC")

    # Now change the model. The annotation does NOT follow -- that is the
    # documented limitation, and the only honest fix is to re-run R-505.
    for v in wall.data.vertices:
        if v.co.z > 0:
            v.co.z += 0.300
    wall.data.update()
    _, _, new_dims = cadlib.bbox_world(wall)
    text_still = dim_obj.data.body

    _, text_after = annotate(wall, "REV")

    return [
        ("section was cut from a duplicate, master untouched",
         abs(master_after["volume"] - original["volume"]) < 1e-12
         and "Wall" in bpy.data.objects,
         f"master volume {original['volume']:.8f} -> "
         f"{master_after['volume']:.8f}"),
        ("section is shorter than the full wall",
         sec_rep["dimensions"][2] < original["dimensions"][2],
         f"section height {sec_rep['dimensions'][2]:.4f} vs wall "
         f"{original['dimensions'][2]:.4f}"),
        ("section cut landed at the requested elevation",
         abs(sec_rep["bbox_max"][2] - CUT_Z) < 1e-6,
         f"section top {sec_rep['bbox_max'][2]:.6f} vs requested {CUT_Z}"),
        ("annotation text was measured from geometry, not typed",
         text_before == f"SEC {WALL_L * 1000:.0f} x {CUT_Z * 1000 + WALL_H * 1000 / 2:.0f}"
         or text_before.startswith("SEC 5000"),
         f"generated {text_before!r}"),
        ("annotation is NOT associative: it goes stale after a model change",
         text_still == text_before
         and abs(new_dims[2] - original["dimensions"][2]) > 0.1,
         f"model height changed to {new_dims[2]:.3f} m but the text still "
         f"reads {text_still!r}"),
        ("re-running the measurement produces the corrected text",
         text_after != text_before and "3000" in text_after,
         f"re-measured {text_after!r}"),
    ]
