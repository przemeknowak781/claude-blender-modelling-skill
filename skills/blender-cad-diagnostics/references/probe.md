---
title: The standard diagnostic probe
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-01 through T-25 (every case uses it)"
---

# The standard probe

Before forming any hypothesis, run this. It is the same harness the whole test
suite asserts on (`tests/cadlib.py`).

```python
import cadlib

rep = cadlib.diagnose(obj)          # evaluated by default: modifiers included
print(cadlib.format_report(rep))
```

## What each field tells you

| Field | Reading it |
| --- | --- |
| `scale_applied` | `False` explains almost every wrong-dimension report (D-01) |
| `non_manifold_edges` | > 0 makes booleans and 3D printing unreliable |
| `boundary_edges` | > 0 means the mesh is open; `volume` will be `None` |
| `inconsistent_normal_edges` | flipped patches; **manifoldness does not catch these** |
| `duplicate_verts` | what Merge by Distance would remove at the threshold |
| `shells` | > 1 means separate bodies — often solver debris |
| `self_intersecting_faces` | computed via BVH overlap; no operator reports this |
| `degenerate_faces` | zero-area faces, usually boolean residue |
| `volume` / `area` | `None` volume is correct behaviour on an open mesh |
| `dimensions` | mesh-local; use `cadlib.bbox_world` for world space |

## The three rules of diagnosis

1. **Measure the evaluated mesh.** `cadlib.diagnose(obj)` does this. Measuring
   `obj.data` is D-04: your assertions pass while the geometry is wrong.
2. **Change one thing.** Then re-probe and diff the numbers. A repair that
   fixes normals while halving volume has failed.
3. **A number, not an absence of exceptions.** Antipattern 8.

## Diffing two probes

```python
before = cadlib.diagnose(obj)
# ... one change ...
after = cadlib.diagnose(obj)
for k in ("verts", "faces", "shells", "non_manifold_edges", "volume"):
    if before[k] != after[k]:
        print(f"{k}: {before[k]} -> {after[k]}")
```

## Cost

`self_intersecting_face_count` builds a BVH and tests every overlapping pair;
on a 1.7M-triangle mesh the full probe takes about a minute. Pass
`check_self_intersect=False` for the hot path and enable it when you actually
suspect self-intersection.
