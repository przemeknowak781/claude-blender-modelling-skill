---
title: Boolean practice
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-03, T-12"
---

# Booleans that work

## Solvers

`solver` accepts exactly three values (verified): `FLOAT`, `EXACT`, `MANIFOLD`.

| Solver | Use |
| --- | --- |
| `EXACT` | default choice for CAD work; handles coplanar and touching input best |
| `MANIFOLD` | fast, requires genuinely manifold input; fails or misbehaves otherwise |
| `FLOAT` | legacy, fastest, least reliable; avoid for dimensional work |

## R-206: the protocol

**Validate both inputs before the operation, not after.**

```python
import cadlib

for candidate in (base, cutter):
    rep = cadlib.diagnose(candidate, check_self_intersect=False)
    assert rep["manifold"], f"{candidate.name}: {rep['non_manifold_edges']} non-manifold edges"
    assert rep["duplicate_verts"] == 0, f"{candidate.name}: merge first"

mod = base.modifiers.new(name="Boolean", type='BOOLEAN')
mod.operation = 'DIFFERENCE'         # or 'UNION', 'INTERSECT'
mod.solver = 'EXACT'
mod.object = cutter
```

**Verify by volume, not by looking:**

```python
after = cadlib.diagnose(base)
assert after["manifold"]
assert after["degenerate_faces"] == 0
assert abs(after["volume"] - expected) / expected < 0.005
```

T-03 asserts exactly this and gets the removed volume right to better than
0.5 percent.

## R-207: coplanar faces

Exactly coplanar faces make the solver's inside/outside classification
ambiguous. The fix is to break the coincidence:

```python
NUDGE = 1e-4            # 0.1 mm: far above float noise, far below tolerance
cutter.location.x -= NUDGE
cutter.location.z += NUDGE
bpy.context.view_layer.update()
```

Choose the nudge one to two orders of magnitude **above** float32 noise (~1e-7)
and at least one order **below** your dimensional tolerance. A through-cut that
must not change size should be nudged along its own axis only, or extended past
both faces rather than offset.

T-03 builds a fixture whose cutter shares two faces exactly with the base and
shows the nudge produces a clean manifold result with the expected volume.

## R-208: many cuts

**One manifold cutter per boolean.** Merging several cutter bodies into a
single mesh gives you a self-intersecting multi-shell solid, and `EXACT` then
produces **nothing at all, silently** — no exception, no cut, an unchanged
model that passes any "did it raise?" check.

This project hit that exact failure while writing T-12. The fix:

```python
for cutter in cutters:                       # separate OBJECTS
    mod = stock.modifiers.new(name=f"Bool_{cutter.name}", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
```

If you genuinely want one cutter, union the pieces **into a real solid first**
(a boolean union on its own object), then use the result.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| nothing happened, no error | cutter non-manifold or self-intersecting | validate inputs (R-206) |
| jagged, torn result | coplanar faces | nudge (R-207) |
| slivers with area < 1e-9 | coincident geometry | `degenerate_faces` check, then merge |
| minutes of hang | million-triangle input | check counts first; decimate the cutter |
| result inside out | cutter normals inverted | recalculate normals on both inputs first |
