---
title: Bevel — radius, segments, deviation
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-11, T-23"
---

# Bevel and chamfer

A Blender bevel is **not** a fillet. It is a chord approximation of an arc, and
its accuracy is set by segment count. There is no tolerance parameter, so you
must supply the arithmetic yourself.

## R-205: derive segment count from a deviation budget

**Problem:** "how many segments?" answered by guessing.
**Blender path:** `BEVEL` modifier, `segments` computed from the budget.

An *n*-segment bevel across a 90-degree edge approximates the quarter arc with
*n* chords. The sagitta (maximum deviation) of one chord is:

```
theta   = (pi/2) / n
sagitta = r * (1 - cos(theta/2))
```

```python
import math

def segments_for_deviation(radius, tolerance):
    n = 1
    while n < 512:
        theta = (math.pi / 2.0) / n
        sagitta = radius * (1.0 - math.cos(theta / 2.0))
        if sagitta <= tolerance:
            return n, sagitta
        n += 1
    raise ValueError("tolerance unreachable")
```

**Verified (T-11):** a 6 mm fillet to a 0.02 mm budget. The derived segment
count keeps the measured radial deviation from the true arc inside the budget;
a 1-segment chamfer misses it by orders of magnitude. The test measures the
actual vertex positions against the analytic arc, so this is not just the
formula checking itself.

| radius | budget | segments |
| --- | --- | --- |
| 6 mm | 0.02 mm | 4 |
| 6 mm | 0.005 mm | 7 |
| 3 mm | 0.02 mm | 3 |
| 20 mm | 0.05 mm | 7 |

Recompute rather than trusting the table — it exists to show the shape of the
relationship, not to be copied.

## R-203: uniform rounding by angle limit

```python
mod = obj.modifiers.new(name="Bevel", type='BEVEL')
mod.affect = 'EDGES'
mod.offset_type = 'OFFSET'          # 'OFFSET' == the distance you mean
mod.width = 0.006
mod.segments = n_seg
mod.limit_method = 'ANGLE'
mod.angle_limit = math.radians(30.0)
mod.use_clamp_overlap = True
```

`offset_type` alternatives (`WIDTH`, `DEPTH`, `PERCENT`, `ABSOLUTE`) all mean
different distances. `OFFSET` is the one that matches "I want a 6 mm radius".

`use_clamp_overlap = True` prevents the bevel exceeding available edge length
and self-intersecting. Leave it on unless you have a specific reason.

## R-204: bevel only selected edges

```python
obj.data.edges[i].bevel_weight = 1.0     # per-edge weight
mod.limit_method = 'WEIGHT'
```

## Verification

```python
rep = cadlib.diagnose(obj)
assert rep["manifold"]
assert rep["self_intersecting_faces"] == 0
assert all(abs(d - nominal) < 1e-6 for d, nominal in zip(rep["dimensions"], NOM))
```

**Outer dimensions must not change.** Bevelling a 100 mm cube leaves it 100 mm.
If they moved, `offset_type` is not what you assumed.

## Ordering

- **Mirror before Bevel**, or the bevel crosses the mirror plane.
- **Boolean before Bevel**, or the cut edges stay sharp. T-23 counts sharp
  edges in both orders and gets different numbers, so this is a geometric fact,
  not a convention.
- **Solidify before Bevel**, or you bevel a surface with no thickness yet.

## Limits worth stating to the user

There is **no Bevel node in Geometry Nodes 5.2** — verified: `ng.nodes.new
('GeometryNodeBevel')` raises `Node type GeometryNodeBevel undefined`. For
rounding inside a parametric setup, put the `BEVEL` modifier after the `NODES`
modifier. `GeometryNodeFilletCurve` exists but works on curves only.
