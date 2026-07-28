---
title: Working at building scale
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-13, T-14, T-15"
---

# Architectural scale

The problem here is not complexity, it is dynamic range: millimetre detail
across tens of metres.

## The precision budget

`scene_extent / smallest_detail`. Above roughly 1e6, work in a local frame
(R-003). A 24 m building with 1 mm detail is 2.4e4 — comfortable. A site model
at national-grid coordinates with the same detail is 6e8 — not.

**Verified (T-13):** a 24 m x 13.5 m footprint with 4 storeys at 3.25 m holds
every level elevation within 1 mm, with the actual measured error at the
float32 floor. Building-scale work is fine *provided the geometry sits near the
origin*.

**Verified (T-14):** the same 1 mm feature authored at a 600 km easting comes
back with ~0.03 mm of error. Author at the origin; place with the object
transform, which is double precision.

## R-215: mass from a dimensioned footprint

Enter real numbers. There is no stage at which "roughly this big, fix later"
becomes correct — that is the difference between this and artistic modelling,
and it is the main reason models arrive at fabrication un-dimensionable.

## R-217: structural grid

```python
mod = obj.modifiers.new(name="Array", type='ARRAY')
mod.fit_type = 'FIXED_COUNT'
mod.count = 6
mod.use_relative_offset = False          # <- critical
mod.use_constant_offset = True
mod.constant_offset_displace = (7.200, 0.0, 0.0)
```

**Use constant offset, never relative.** Relative offset is a multiple of the
object's own bounding box, so the grid silently shifts when the column section
changes. Constant offset *is* the grid dimension.

**Verified (T-15):** 6 bays at 7.2 m, every grid line within 0.1 mm, overall
length matching nominal.

## R-216: section cut at an exact elevation

```python
bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                       dist=1e-7,
                       plane_co=(0.0, 0.0, elevation),
                       plane_no=(0.0, 0.0, 1.0),
                       clear_inner=False, clear_outer=True)
```

**Always cut a duplicate.** T-25 asserts the master survives untouched.

`clear_inner` / `clear_outer` select which side is discarded. For a plan cut,
keep the geometry below and discard above.

## Clip range

Set the viewport clip range to the object scale. `clip_start` too small at
building scale causes depth-buffer artefacts; too large hides detail. A useful
rule: `clip_start ≈ smallest_detail * 10`, `clip_end ≈ scene_extent * 10`.

## Storeys and datums

Put storey elevations in one place — custom properties on a `CTRL-Levels`
Empty — and drive slabs from them. An elevation retyped into 40 objects is 40
opportunities for a 10 mm error that nobody finds until the section is drawn.
