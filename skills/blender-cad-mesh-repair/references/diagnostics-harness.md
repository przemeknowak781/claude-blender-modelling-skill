---
title: R-101 measurement harness
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-01, T-07, T-08, T-09, T-10"
---

# R-101: full mesh diagnostic report

**Problem:** you cannot repair what you have not measured, and you cannot prove
a repair worked without measuring again.
**When NOT to use:** never skip it. Every other recipe in this skill diffs its
output before and after.
**Blender path:** `bmesh` interrogation of the evaluated mesh. No `bpy.ops`, so
it is safe headless and in loops.

The implementation is `tests/cadlib.py` — import it rather than retyping it.

```python
import cadlib
rep = cadlib.diagnose(obj)                       # modifiers included
rep = cadlib.diagnose(obj, evaluated=False)      # base mesh only
rep = cadlib.diagnose(obj, check_self_intersect=False)   # skip the BVH pass
print(cadlib.format_report(rep))
```

## The three topology tests are independent

This is the part most repair advice gets wrong.

| Test | Function | What it misses |
| --- | --- | --- |
| closed | `is_closed` | says nothing about 3-face edges or normals |
| manifold | `is_manifold` | **does not detect flipped normals** |
| normals consistent | `inconsistent_normal_edges` | independent of both above |

Verified in T-01: the marching-cubes fixture reports **0 non-manifold edges**
and `closed=True` while carrying **234 edges with inconsistent winding** from a
flipped patch. A repair script that checks only manifoldness declares this mesh
healthy and exports it inside out.

```python
def inconsistent_normal_edges(bm):
    bad = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        dirs = []
        for f in e.link_faces:
            for loop in f.loops:
                if loop.edge == e:
                    dirs.append(loop.vert == e.verts[0])
                    break
        if len(dirs) == 2 and dirs[0] == dirs[1]:
            bad.append(e)
    return bad
```

Two faces share an edge consistently when they traverse it in **opposite**
directions. Same direction means one of them is flipped.

## Volume

```python
vol = bm.calc_volume(signed=True)
```

- Meaningless unless `is_closed(bm)`. `diagnose` returns `None` rather than a
  wrong number — asserted by T-10.
- **Negative signed volume means the normals point inward.** That is the cheap
  global orientation check.
- On a mesh with interior walls the number is still not what you want: T-07
  shows a welded stack of boxes reporting 0.248 where the sum of the separate
  boxes was 0.073. Both numbers are "correct"; neither is the solid volume
  until the interior faces are gone.

## Self-intersection

No built-in operator reports it. `self_intersecting_face_count` triangulates a
copy, builds a `BVHTree`, and counts overlapping face pairs that do **not**
share a vertex (faces meeting at a shared vertex touch legitimately).

Cost is the dominant term in the probe: about a minute on 1.7M triangles. Pass
`check_self_intersect=False` unless you suspect it.

## Verification of the harness itself

| Test | Assertion it supports |
| --- | --- |
| T-10 | volume and area match analytic prism formulae to < 0.01% |
| T-10 | open mesh returns `volume is None`, not a wrong number |
| T-10 | centre of mass lands on the axis of symmetry |
| T-01 | detects flipped patch, debris shell and loose vertices in one pass |
