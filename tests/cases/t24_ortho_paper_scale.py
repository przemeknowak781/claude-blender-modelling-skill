"""T-24 - orthographic view rendered at a declared paper scale."""
import os
import bpy
import bmesh
import cadlib

ID = "T-24"
PRIORITY = "DRAW"
TASK = ("Set up an orthographic elevation at a true 1:50 paper scale and prove "
        "the rendered image measures correctly.")
RECIPES = ["R-501", "R-503"]

SCALE_DENOM = 50.0        # 1:50
PAPER_W_MM = 297.0        # A4 landscape
DPI = 300.0
BUILDING = (10.000, 4.000, 6.000)
OUTDIR = "tests/output/t24"


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(OUTDIR, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=BUILDING)
    me = bpy.data.meshes.new("Building")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("Building", me)
    scene.collection.objects.link(obj)

    # R-503: the arithmetic that makes the scale true.
    # Paper width in metres -> world width the frame must cover.
    paper_w_m = PAPER_W_MM / 1000.0
    world_w = paper_w_m * SCALE_DENOM          # 0.297 * 50 = 14.85 m
    px_w = int(round(PAPER_W_MM / 25.4 * DPI))

    cam_data = bpy.data.cameras.new("DrawCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = world_w            # ortho_scale spans the LONGER axis
    cam = bpy.data.objects.new("DrawCam", cam_data)
    scene.collection.objects.link(cam)
    # Look along +Y at the building's -Y elevation.
    cam.location = (0.0, -30.0, 0.0)
    cam.rotation_euler = (1.5707963267948966, 0.0, 0.0)
    scene.camera = cam

    scene.render.resolution_x = px_w
    scene.render.resolution_y = int(round(px_w * 210.0 / 297.0))
    scene.render.resolution_percentage = 100
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = os.path.abspath(os.path.join(OUTDIR, "elevation"))
    bpy.ops.render.render(write_still=True)

    png = scene.render.filepath + ".png"
    rendered = os.path.exists(png)

    # Measure the building's silhouette in the rendered image.
    measured_mm = None
    if rendered:
        img = bpy.data.images.load(png)
        w, h = img.size
        px = list(img.pixels)   # RGBA floats
        cols = []
        for x in range(w):
            for y in range(0, h, 8):     # sample every 8th row
                if px[(y * w + x) * 4 + 3] > 0.5:   # alpha
                    cols.append(x)
                    break
        if cols:
            span_px = max(cols) - min(cols) + 1
            mm_per_px = PAPER_W_MM / w
            measured_mm = span_px * mm_per_px
        bpy.data.images.remove(img)

    # A 10 m building at 1:50 must draw 200 mm wide on paper.
    expected_mm = BUILDING[0] / SCALE_DENOM * 1000.0
    err = abs(measured_mm - expected_mm) if measured_mm else float("inf")

    return [
        ("camera is orthographic, not perspective",
         cam_data.type == 'ORTHO', f"type={cam_data.type}"),
        # ortho_scale is stored as float32, so compare with a float32-sized
        # tolerance rather than an exact equality.
        ("ortho_scale derived from paper size and scale denominator",
         abs(cam_data.ortho_scale - world_w) < 1e-5,
         f"ortho_scale={cam_data.ortho_scale} = "
         f"{PAPER_W_MM}mm x {SCALE_DENOM:.0f} / 1000"),
        ("render resolution matches the declared DPI",
         scene.render.resolution_x == px_w,
         f"{scene.render.resolution_x} px = {PAPER_W_MM}mm at {DPI:.0f} dpi"),
        ("image was actually written",
         rendered, png),
        ("the drawn building measures 200 mm on paper within 1 mm",
         err < 1.0,
         f"expected {expected_mm:.2f} mm, measured "
         f"{measured_mm:.2f} mm" if measured_mm else "no silhouette found"),
    ]
