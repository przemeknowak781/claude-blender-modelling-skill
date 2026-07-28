---
title: W-000 process reference and gate scripts
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-20, T-21, T-22, T-23"
---

# W-000 — the modelling process, with runnable gates

`SKILL.md` carries the summary. This file carries the gate code and the
reasoning you need when a gate fails.

The four gates are implemented in `tests/gates.py` and exercised end to end by
test **T-20**, which passes all four with numeric evidence.

## Why a process at all

CAD packages enforce order through architecture: you cannot dimension a
feature that does not exist, and the history tree makes the order visible.
Blender enforces nothing. You can scale an object non-uniformly, bevel it,
export it and never learn that the bevel radius you typed is not the radius you
got. W-000 supplies the discipline the software omits.

R-recipes answer *how do I do X*. W-000 answers *in what order, and when to
stop*.

## Phase 0 — Interview

Answer these five before opening Blender. Record them in the script header or
in the file's decision log (R-005).

| Question | Determines |
| --- | --- |
| Purpose: fabrication, simulation, visualisation, documentation? | required topology, permissible simplification |
| Dimensional tolerance and nominal unit? | segment counts, merge threshold, export precision |
| Which dimensions will change later? | what stays parametric, what may be baked |
| External input or built from zero? | external input always starts at mesh repair |
| Who consumes the output? | axis convention, units, format |

**If an answer is missing and cannot be safely assumed, ask.** Test T-22
demonstrates the cost of guessing: the bare number `40` is either 0.040 m or
40 m — a factor of 1000, discovered at the machine, not in the viewport.

## Gate G1 — scene setup

```python
import gates
ok, report = gates.gate_g1(expect_unit_scale=1.0, expect_system='METRIC')
```

Checks metric system, `unit_scale`, that every mesh object has scale 1.0, and
that the file has been saved. Failing `objects_with_unapplied_scale` is the
single highest-value catch in the whole process — see antipattern 1.

**Precision budget.** If scene extent ÷ smallest significant detail exceeds
roughly 1e6, work in a local frame. Test T-14 measures this: a 1 mm feature
authored at a 600 km easting comes back with ~0.03 mm of error, while the same
feature authored at the origin and *placed* by the object transform is exact to
the float32 storage floor.

## Gate G2 — dimensional blockout

```python
ok, report = gates.gate_g2({"Tray": (0.400, 0.300, 0.060)}, tolerance=0.0005)
```

Compares measured world-space bounding boxes against the nominal table. It
measures the **evaluated** object, so modifiers are included.

## Phase 4 — canonical stack order

```python
ok, report = gates.check_stack_order(obj)
new_order = gates.reorder_to_canonical(obj)   # preserves every setting
```

Default order, with the reason for each position:

| # | Modifier | Why here |
| --- | --- | --- |
| 1 | `MIRROR`, `ARRAY`, `SCREW` | topology generators define the whole solid |
| 2 | `BOOLEAN` | needs valid input; before bevelling so cut edges get bevelled |
| 3 | `SOLIDIFY` | thickness on a settled shape |
| 4 | `WELD` | cleanup before rounding |
| 5 | `BEVEL` | second-to-last shape step |
| 6 | `SUBSURF`, `REMESH` | if at all |
| 7 | `TRIANGULATE`, `DECIMATE` | export only |
| 8 | `WEIGHTED_NORMAL` | shading only, always last |

The order is a **default, not a law**. Unusual geometry can justify departing
from it — but the three pairs in `gates.HARD_RULES` each have a specific broken
outcome, so they are reported separately:

- **Boolean → Bevel.** Inverted, the cut edges stay sharp. Test T-23 proves
  this is not a style question: it counts sharp edges in both orders and gets
  different numbers.
- **Mirror → Bevel.** Inverted, the bevel runs through the mirror plane.
- **Solidify → Bevel.** Inverted, the bevel is applied before the thickness
  exists.

## Gate G3 — geometric validation

```python
ok, report = gates.gate_g3([obj], merge_threshold=1e-5)
```

Fails on non-manifold edges, unexpected boundary edges, duplicate vertices,
inconsistent normals, self-intersections or degenerate faces.

**Manifold and closed are different tests.** A mesh can be watertight and still
have an edge shared by three faces. **Consistent normals is a third, separate
test**: a flipped patch leaves every edge shared by exactly two faces, so
manifoldness does not see it. `cadlib.inconsistent_normal_edges` is the check
that does — in test T-01 it finds 234 such edges in an input that reports zero
non-manifold edges.

## Gate G4 — export round trip

```python
ok, report = gates.gate_g4(obj, "out/part.stl", tolerance=0.0005,
                           importer='stl', global_scale=1.0)
```

Exports, reimports into a fresh scene, applies scale if the importer left it
un-applied, and compares bounding box and volume. This is the only gate that
catches unit and axis errors, which are invisible in the viewport.

**A verified 5.2 trap:** `wm.stl_import(global_scale=...)` writes the factor
into **object scale**, not into the mesh, so the imported object arrives with
`scale = 0.001` — antipattern 1, by default. `gate_g4` applies it; your import
recipe must too. Test T-06 asserts both halves.

## Accompanying rules

- **Checkpoints.** Save before every gate with an incrementing name. Blender
  has no history tree; outside the session the file is the only undo.
- **Decision log.** Keep the parametric decisions in a text data-block inside
  the `.blend` (R-005) so the model explains itself months later.
- **Never skip a gate.** If one fails, return to the phase that caused it. A
  masked dimensional error surfaces at the CNC.
- **Stopping criterion.** Done means G4 passes and the Phase 0 brief is met —
  not that it looks right.
