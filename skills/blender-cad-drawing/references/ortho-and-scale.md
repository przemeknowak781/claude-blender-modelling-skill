---
title: Orthographic views and true paper scale
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-24"
---

# Orthographic views at a declared scale

## R-501: orthographic camera for a plan or elevation

```python
cam_data = bpy.data.cameras.new("DrawCam")
cam_data.type = 'ORTHO'
cam = bpy.data.objects.new("DrawCam", cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

# Elevation looking along +Y at the -Y face:
cam.location = (0.0, -30.0, 0.0)
cam.rotation_euler = (math.radians(90), 0.0, 0.0)

# Plan looking down:
# cam.location = (0.0, 0.0, 50.0);  cam.rotation_euler = (0.0, 0.0, 0.0)
```

A perspective camera gives converging lines and no consistent measure. For a
drawing it is always `ORTHO`.

The camera's *distance* does not affect an orthographic image's scale — only
`ortho_scale` does. Place it clear of the geometry and forget about it.

## R-503: true paper scale

`ortho_scale` is the world-space width the frame spans, along the **longer**
sensor axis. For scale 1:D on paper of width `W_mm`:

```
world_width = (W_mm / 1000) * D
```

```python
SCALE_DENOM = 50.0        # 1:50
PAPER_W_MM = 297.0        # A4 landscape
DPI = 300.0

cam_data.ortho_scale = (PAPER_W_MM / 1000.0) * SCALE_DENOM      # 14.85 m
px_w = int(round(PAPER_W_MM / 25.4 * DPI))                      # 3508 px
scene.render.resolution_x = px_w
scene.render.resolution_y = int(round(px_w * 210.0 / 297.0))
scene.render.resolution_percentage = 100
```

**Verify by measuring the image, not the intent:**

```python
mm_per_px = PAPER_W_MM / scene.render.resolution_x
# ... find the silhouette's pixel span in the rendered PNG ...
measured_mm = span_px * mm_per_px
assert abs(measured_mm - (model_width / SCALE_DENOM * 1000)) < 1.0
```

**Verified (T-24):** a 10 m building at 1:50 on A4 at 300 dpi draws 200 mm wide
in the rendered image, within 1 mm. The test renders with
`BLENDER_WORKBENCH`, reads the alpha channel of the PNG, and measures the
silhouette. It is a measurement, not an assumption.

## Render settings for line output

```python
scene.render.engine = 'BLENDER_WORKBENCH'    # fast, deterministic, no lighting
scene.render.film_transparent = True          # alpha, so the silhouette is measurable
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
```

`BLENDER_WORKBENCH` is the right engine for measured drawings: it is fast and
has no lighting to argue about. Freestyle linework needs EEVEE or Cycles
(`linework.md`).

## Headless rendering

Rendering needs a GL context even in `--background`. In a container:

```bash
apt-get install -y libegl1 libgl1 libgl1-mesa-dri libglx-mesa0
LIBGL_ALWAYS_SOFTWARE=1 blender --background --python draw.py
```

Without this, Blender aborts with `Couldn't open libEGL.so.1`. `tests/run_evals.py`
sets `LIBGL_ALWAYS_SOFTWARE=1` for exactly this reason.

## Float32

`ortho_scale` is stored as float32. Compare with a tolerance (`< 1e-5`), never
with `==` — 14.85 reads back as 14.850000381469727.
