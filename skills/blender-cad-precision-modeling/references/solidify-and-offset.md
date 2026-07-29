---
title: Wall thickness and offset
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-02, T-26"
---

# Solidify and offset

## R-201: constant-thickness offset on an open surface

**Problem:** the user has a surface with no thickness and needs a solid of a
given thickness t.

**When NOT to use:** when the surface has concave folds tighter than t. Run
R-202 first — the result will be dimensionally wrong in a way that passes every
topology check.

**Blender path:** `SOLIDIFY` modifier, `NON_MANIFOLD` mode, even thickness.

**Alternative:** Geometry Nodes `GeometryNodeExtrudeMesh` + `GeometryNodeFlipFaces`
when the thickness must be a graph parameter.

**Code (verified 5.2, 2026-07-28, T-02):**

```python
mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
mod.solidify_mode = 'NON_MANIFOLD'    # settable: 'EXTRUDE', 'NON_MANIFOLD'
mod.thickness = 0.018                 # 18 mm
mod.offset = -1.0                     # all thickness on one side
mod.use_even_offset = True
```

`offset` runs -1.0 to 1.0: -1.0 puts the material entirely behind the original
surface, 0.0 centres it, +1.0 puts it entirely in front. For sheet material,
which face of the model is the datum determines the sign.

**Result verification:**

```python
rep = cadlib.diagnose(obj)
assert rep["closed"], rep["boundary_edges"]
assert rep["manifold"], rep["non_manifold_edges"]
assert rep["self_intersecting_faces"] == 0
# shell volume should approach (one-sided area) x thickness
assert abs(rep["volume"] - area_before * 0.018) / (area_before * 0.018) < 0.05
```

Measure the thickness itself by ray-casting from the **original** surface, not
from the solidified result — the result's rim strips are faces too, and a ray
cast from one rim hits the opposite rim a fraction of a millimetre away. Cast
from a point outside along −normal, take the first hit (outer skin) and then
the second (inner skin); the gap between them is the wall. T-02 measures 10
points this way and requires every one inside 17.5–18.5 mm.

**Common mistakes:** an unapplied object scale gives a thickness different from
the one you typed (antipattern 1) — assert `rep["scale_applied"]` first. Using
`EXTRUDE` mode on an open surface with curvature gives uneven thickness at the
folds; `NON_MANIFOLD` is the mode that keeps it even.

**Source:** [Blender 5.2 Manual — Solidify Modifier](https://docs.blender.org/manual/en/5.2/modeling/modifiers/generate/solidify.html)

---

## R-202: detect concave folds too tight for the thickness

**Problem:** an inward offset cannot survive a fold sharper than the offset
distance, and Blender does not warn you.

**When NOT to use:** on closed solids being thickened outward, where the
constraint is reversed (convex folds become the problem).

**Blender path:** none — this is computed, not queried. `cadlib.concave_offset_conflicts`.

**The geometry.** Offsetting both faces of a concave fold inward by t makes
them meet at

```
reach = t / tan(theta / 2)
```

from the shared edge, where theta is the **interior** angle. If either face
does not extend that far from the edge, the offset surface runs past it.

**Code (verified 5.2, 2026-07-28, T-26):**

```python
import math

def concave_offset_conflicts(obj, thickness):
    bm = cadlib.evaluated_bmesh(obj)
    bm.normal_update()
    out = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        signed = e.calc_face_angle_signed(0.0)
        if signed >= 0:                      # convex or flat: no conflict
            continue
        interior = math.pi - abs(signed)
        reach = thickness / math.tan(interior / 2.0)
        origin = e.verts[0].co
        along = (e.verts[1].co - origin).normalized()
        for f in e.link_faces:
            far = max((v.co - origin - along * ((v.co - origin).dot(along))).length
                      for v in f.verts)
            if far < reach:
                out.append((e.index, math.degrees(interior), reach, far))
                break
    bm.free()
    return out
```

**The sign convention matters.** `calc_face_angle_signed` returns the
**deviation from flat**, not the interior angle, and **negative means
concave**. A 15-degree V-groove reports −165 degrees. Interior angle is
`pi - abs(signed)`. Getting this backwards silently inverts the whole test —
it then reports zero conflicts on everything, which looks like success.

**Result verification:**

```python
conflicts = cadlib.concave_offset_conflicts(obj, 0.018)
assert not conflicts, conflicts    # run BEFORE adding the modifier
```

**What actually goes wrong — verified, and not what you would guess.**

Running Solidify on a 15-degree fold with an 18 mm wall does **not**
self-intersect. T-26 measures the result:

| Check | Result |
| --- | --- |
| closed | True |
| manifold | True |
| self-intersecting faces | **0** |
| Z extent | **0.1875 m**, from a 0.05 m tall input |

The offset apex overshoots the original apex by 0.1379 m — within 1 percent of
the 0.1367 m `reach` the formula predicts. The part grew 138 mm because it was
given an 18 mm wall.

So the damage is a **spike**, a gross dimensional error, and **every topology
check passes**. A gate that tests only manifoldness and self-intersection —
which is what most repair advice checks — waves this through to the exporter.
That is precisely why R-202 runs *before* the modifier and why gate G2
(dimensions) exists separately from gate G3 (topology).

**Common mistakes:** running the check on the base mesh when earlier modifiers
in the stack created the tight fold — use the evaluated mesh, as the code
above does. Also: a fold that is fine at 0.5 mm is not fine at 18 mm, so
re-run the check whenever the thickness parameter changes.
