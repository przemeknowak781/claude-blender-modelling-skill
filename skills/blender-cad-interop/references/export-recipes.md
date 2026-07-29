---
title: Export recipes by destination
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-18, T-20 (STL/OBJ paths); DXF/SVG writing NOT exercised"
---

# Export recipes

Every one of these ends with R-402, the round trip. Without it you have a file,
not a verified export.

## R-405: export for 3D printing

**Pre-flight, all of which must pass before writing the file:**

```python
rep = cadlib.diagnose(obj)
assert rep["closed"],           "printer needs a closed volume"
assert rep["manifold"],         rep["non_manifold_edges"]
assert rep["self_intersecting_faces"] == 0
assert rep["inconsistent_normal_edges"] == 0
assert rep["normals_inward"] is False, "normals point inward"
assert rep["scale_applied"],    rep["object_scale"]
assert rep["degenerate_faces"] == 0
```

```python
bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                      global_scale=1000.0,        # metres -> millimetres
                      apply_modifiers=True,
                      forward_axis='Y', up_axis='Z')
```

Most slicers assume millimetres. `global_scale=1000.0` converts a metre scene
on the way out; confirm the convention with the recipient rather than assuming.

**When NOT to use:** on an open surface. Give it thickness first (R-201).

**Verify:** R-402 with `global_scale=0.001` on the way back in.

## R-406: export for CAM

Same closed/manifold pre-flight as R-405, plus:

- **Origin.** Set the object origin to the machine datum — usually a corner of
  the stock or the centre of a fixture — before exporting. The CAM package
  reads the file's origin as the work-coordinate zero.
- **Orientation.** The cut face should face +Z. State `forward_axis` and
  `up_axis` explicitly.
- **Reachability.** Internal corners need relief for the actual cutter
  (precision-modeling R-212), or the part will not assemble.

Blender produces **no tool paths**. This is geometry preparation only.

## R-407: export for FEA

Element quality matters more than triangle count:

```python
rep = cadlib.diagnose(obj)
assert rep["closed"] and rep["manifold"]
assert rep["degenerate_faces"] == 0      # zero-area elements break solvers
assert rep["self_intersecting_faces"] == 0
```

Prefer an even element distribution — a voxel remesh (R-110) at a declared size
usually beats decimated solver output, because element *size* is controlled
rather than merely element *count*.

## R-408: export USD or glTF preserving hierarchy

```python
bpy.ops.wm.usd_export(filepath=path, selected_objects_only=True)
```

USD and glTF keep names, hierarchy and units, which STL and OBJ do not. Use
them when the recipient needs structure rather than a single solid. Both treat
scene units as metres.

**Verify:** R-402 plus an assertion that the object names survived — that is
the reason you chose these formats.

## R-409: export 2D contours to DXF or SVG

**Status: contour extraction is verified (T-04, against an analytic perimeter);
the DXF/SVG file writing is NOT exercised by this project.** Treat the writing
step as unverified and check the output in the receiving application.

Extract the contours first (precision-modeling R-214 / R-216), convert the
resulting loops to curve objects, then export. Core Blender has no DXF writer;
SVG export is available for Grease Pencil strokes, and DXF requires an add-on.

**What core 5.2 actually provides, verified by introspection:**

| Operator | Direction |
| --- | --- |
| `wm.grease_pencil_export_svg` | SVG out, Grease Pencil strokes only |
| `wm.grease_pencil_export_pdf` | PDF out, Grease Pencil strokes only |
| `wm.grease_pencil_import_svg` | SVG in |
| `import_curve.svg` | SVG in, as curves |

**There is no DXF operator in core Blender 5.2 at all** — not for import, not
for export. DXF requires a third-party add-on, which this project has not
tested. Do not promise DXF output without checking the user's installation.

Vector *export* therefore runs through Grease Pencil: convert the contours to
Grease Pencil strokes (drawing skill R-506), then
`wm.grease_pencil_export_svg`.

**Verify:** reimport the vector file into the cutting software and measure a
known dimension. For anything dimensionally critical, prefer exporting the 3D
contour and flattening downstream.
