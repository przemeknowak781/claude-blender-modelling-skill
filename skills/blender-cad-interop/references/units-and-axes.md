---
title: Units and axes on import and export
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-06, T-18, T-19"
---

# Units and axes

Two silent corrupters. Neither is visible in the viewport, and both are caught
only by a round trip.

## R-401: import a mesh with explicit units and axes

```python
before = set(bpy.data.objects.keys())
bpy.ops.wm.stl_import(filepath=path, global_scale=0.001,      # mm source
                      forward_axis='Y', up_axis='Z')
obj = [o for o in bpy.data.objects if o.name not in before][0]
```

Capture the object by **diffing the object set**, not by assuming a name — the
importer names from the file and may deduplicate against existing names.

**When NOT to use:** as a substitute for asking. If nobody stated the source
units, ask (W-000 Phase 0); the difference is a factor of 1000.

**Verify:** apply scale (R-403), then assert the bounding box against the
nominal size and `rep["manifold"]`. Then send it to `blender-cad-mesh-repair` —
imported geometry is unvalidated by definition.

## R-403: reconcile millimetre source data with a metre scene

See "STL global_scale writes to OBJECT SCALE" below: import with
`global_scale=0.001`, then **apply the scale**, then assert. T-06 asserts both
halves — that the importer left `scale = 0.001`, and that it is 1.0 after Apply.

## R-404: set the axis convention deliberately

See "The OBJ defaults do NOT round-trip" below. State both axes on every import
and export call. An unstated default is a decision you did not make.

## Verified operator defaults in 5.2

| Operator | `forward_axis` | `up_axis` | `global_scale` |
| --- | --- | --- | --- |
| `wm.obj_export` | `NEGATIVE_Z` | `Y` | 1.0 |
| `wm.obj_import` | `NEGATIVE_Z` | `Y` | 1.0 |
| `wm.stl_export` | `Y` | `Z` | 1.0 |
| `wm.stl_import` | `Y` | `Z` | 1.0 |

## The OBJ defaults do NOT round-trip

**Verified (T-19).** Export a 0.100 x 0.200 x 0.400 part with the operator
defaults and reimport it with the same defaults, and it comes back as
0.100 x 0.400 x 0.200 — Y and Z swapped. No error, no warning. The dimensions
are a permutation of the original, so it is a rotation rather than a rescale,
which makes it even easier to miss.

The OBJ defaults describe a **Y-up target convention**. They are correct for
writing a file another application will read; they are wrong for a Blender →
Blender round trip.

```python
# Lossless round trip: Blender-native axes on BOTH sides.
bpy.ops.wm.obj_export(filepath=p, forward_axis='Y', up_axis='Z',
                      export_selected_objects=True, global_scale=1.0)
bpy.ops.wm.obj_import(filepath=p, forward_axis='Y', up_axis='Z',
                      global_scale=1.0)

# Writing for a Y-up consumer: state it explicitly, and do NOT expect a naive
# reimport to match.
bpy.ops.wm.obj_export(filepath=p, forward_axis='NEGATIVE_Z', up_axis='Y', ...)
```

**Set the axes explicitly every time.** An unstated default is a decision you
did not make.

## STL global_scale writes to OBJECT SCALE

**Verified (T-06).** `wm.stl_import(global_scale=0.001)` does **not** scale the
mesh. It leaves the mesh holding the raw file numbers and sets
`obj.scale = (0.001, 0.001, 0.001)`.

The object measures correctly in world space, so a casual check passes — and
you are now in antipattern 1, with an unapplied scale that will corrupt every
subsequent Bevel, Solidify, Array and export.

```python
bpy.ops.wm.stl_import(filepath=path, global_scale=0.001)
obj = [o for o in bpy.data.objects if o.name not in before][0]

obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

assert all(abs(s - 1.0) < 1e-6 for s in obj.scale)
```

## STL carries no units at all

An STL file holds bare numbers. `40.0` is forty of *something*, agreed between
sender and receiver out of band. If nobody said, **ask** (W-000 Phase 0) — the
difference between millimetres and metres is a factor of 1000 (T-22).

The common convention is millimetres, because most CAD and slicer software
writes millimetres. It is a convention, not a guarantee.

## Scene unit scale

Keep `scene.unit_settings.scale_length = 1.0` and think in metres. Changing
`length_unit` only changes the display; changing `scale_length` changes the
meaning of every stored number and must then be mirrored in every exporter
call. The combination of a non-1.0 unit scale and an exporter `global_scale` is
the classic 1000x error.
