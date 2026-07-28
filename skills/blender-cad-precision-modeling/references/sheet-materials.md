---
title: Sheet materials, joints and CNC clearances
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-12, T-04"
---

# Sheet material work

## R-209: one source of truth for material thickness

Plywood is not its nominal thickness. Measure the sheet, put the measured
number in one place, and drive everything from it.

```python
ctrl = bpy.data.objects.new("CTRL-Sheet", None)
bpy.context.scene.collection.objects.link(ctrl)
ctrl["thickness"] = 0.0177      # MEASURED, not the 18 mm on the label
ctrl["kerf"] = 0.0032           # measured cutter width
ctrl["fit_clearance"] = 0.0002  # per joint face
```

Every slot width, tab length and pocket depth reads from these (R-301/R-302).
When the next sheet measures 17.4 mm, you change one number.

## R-212: dogbone relief for internal corners

**Problem:** a round cutter cannot produce a sharp internal corner. Without
relief, the mating tab does not seat and the joint is loose or will not close.
**When NOT to use:** laser or waterjet cutting, where the kerf is effectively a
point; and on outside corners, which need no relief.

The relief is a bore of the tool radius at each corner, pulled diagonally
inward so its edge reaches the nominal corner point:

```python
import math
offset = tool_r / math.sqrt(2.0)        # diagonal pull-in
centre = (hx - offset, hy - offset)     # per corner, signs per quadrant
```

**Verified (T-12):** with a 6 mm cutter, the relieved pocket grows by
`2 * (r - r/sqrt(2))` on each axis, matched to better than 0.05 mm, and the
result stays manifold. The plain pocket matches nominal exactly, so the growth
is attributable to the relief and nothing else.

T-bone relief (the bore pushed along one axis into the wall rather than
diagonally) is the alternative when the corner must stay visually square on one
face. Same radius arithmetic, different offset direction.

## Joints

**R-210 finger joints.** Finger width should be 1.5–3x material thickness.
Generate as an `ARRAY` of cutter tabs with constant offset, so the count and
pitch stay parametric. Add `fit_clearance` to the slot, not to the tab — it is
easier to sand a tab than to widen a slot.

**R-211 mortise and tenon.** The mortise gets the clearance. Both dimensions
derive from `ctrl["thickness"]`; never type the mating dimension twice.

## R-213: nesting

Space parts by at least `kerf + 2 * fit_clearance`, plus a margin for cutter
runout. Use `ARRAY` with constant offset for repeated parts so the pitch stays
a single editable number.

## R-214: flat contours

Sheet parts must be flat and axis-aligned before contour extraction. Section
them at mid-thickness (R-216 / T-04's `bisect_plane` approach) and export the
resulting closed loops via `blender-cad-interop` R-409.

**Verify** the loops are closed and their total length matches an independent
calculation — T-04 does this against the analytic perimeter of a 64-gon and
matches to better than 0.001 percent.

## Checklist before cutting

- [ ] `obj.scale == (1,1,1)` on every part (antipattern 1)
- [ ] thickness reads from `CTRL-Sheet`, nowhere else
- [ ] every internal corner has relief sized to the actual cutter
- [ ] parts are flat, on the XY plane, at Z = 0
- [ ] contours are closed loops
- [ ] round trip through the export format checked (interop R-402)
