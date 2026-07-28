---
title: Units, scale and the precision budget
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-06, T-13, T-14, T-15"
---

# Units, scale and precision

Unit and scale errors are the most expensive class of mistake in this domain,
because they are invisible in the viewport and only appear at the machine.

## R-001: Set up scene units

**Problem:** the scene must express real dimensions unambiguously.
**When NOT to use:** never skip it; this is gate G1.

```python
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0      # 1 Blender unit == 1 metre
scene.unit_settings.length_unit = 'METERS'
```

**Verify:**
```python
assert scene.unit_settings.system == 'METRIC'
assert scene.unit_settings.scale_length == 1.0
```

**Common mistakes:** setting `length_unit = 'MILLIMETERS'` and believing the
scene now works in millimetres. It does not — it changes only how numbers are
*displayed*. The stored unit is still the Blender unit, and `scale_length` is
what maps it to metres. Leave `scale_length` at 1.0 and think in metres;
0.018 is 18 mm.

**Source:** [Blender 5.2 Manual — Scene Units](https://docs.blender.org/manual/en/5.2/scene_layout/scene/properties.html#units)

## R-002: Apply scale safely

**Problem:** `obj.scale != 1` corrupts every thickness, radius and array
spacing downstream, and every export.
**When NOT to use:** when the scale is deliberately animated or driven.

```python
for obj in objects:
    if not all(abs(s - 1.0) < 1e-6 for s in obj.scale):
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
```

`transform_apply` is one of the cases where `bpy.ops` is genuinely the right
tool — it has to rewrite mesh data and the object matrix together. Select the
objects first; in a script without a UI, set the active object explicitly.

**Verify:** `all(abs(s - 1.0) < 1e-6 for s in obj.scale)` for every object.

**Common mistakes:** applying scale to an object whose children inherit the
transform, silently moving them. Check parenting first.

## R-003: Work in a local frame in a large scene

**Problem:** millimetre detail at survey-grid coordinates is destroyed by
float32 vertex storage.

**Verified by T-14.** A 1 mm feature authored with vertex coordinates at a
600 km easting comes back with roughly 0.03 mm of error — 3 percent of the
feature. The same feature authored at the origin and *placed* by the object
transform is exact to about 1e-7 m, the float32 storage floor.

```python
# WRONG: geometry authored at grid coordinates
bmesh.ops.translate(bm, verts=bm.verts, vec=(600000.0, 0.0, 0.0))

# RIGHT: author at the origin, place with the object matrix
obj.location.x = 600000.0
```

**The budget:** if `scene_extent / smallest_significant_detail > 1e6`, you must
work locally. At 600 km with 1 mm detail the ratio is 6e8.

**Verify:** measure the feature, not the placement. `cadlib.diagnose(obj)`
reports mesh-local dimensions, which is what precision applies to.

**Common mistakes:** believing the object transform costs precision. It does
not — it is a double-precision 4x4 matrix. Only the *vertex coordinates* are
float32.

## Precision facts worth knowing

- Vertex coordinates are **float32**. Even at the origin, expect ~1e-7 m of
  noise. Do not write assertions tighter than that (T-14 learned this).
- `obj.matrix_world` is double precision, so placement is not the problem.
- Comparisons on stored float properties (`ortho_scale`, `thickness`) need a
  float32-sized tolerance, not `== `. T-24 hit exactly this.

## Test evidence

| Test | What it establishes |
| --- | --- |
| T-06 | mm-authored STL lands at nominal size in a metre scene, scale applied |
| T-13 | mm accuracy holds across a 24 m building, 4 storeys |
| T-14 | the 1e6 precision budget is real and measurable |
| T-15 | 7.2 m structural grid, 6 bays, every line within 0.1 mm |
