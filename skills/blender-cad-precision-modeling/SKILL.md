---
name: blender-cad-precision-modeling
description: Build dimension-accurate geometry in Blender 5.2 for fabrication and architecture — use for exact wall thickness and offset, fillets and chamfers via Bevel, boolean pockets and holes, plywood and sheet-material parts, CNC 2.5D and 3-axis clearances, tool-radius compensation, finger and mortise joints, layer nesting, flat unfolding, building masses, sections and construction details at millimetre accuracy across tens of metres.
blender_version: "5.2"
verified_on: "2026-07-28"
license: CC-BY-4.0
---

# Blender CAD — Precision Modelling (P1, P2)

Dimensioned geometry for fabrication (P1) and controlled-dimension
architecture (P2). Assumes W-000 Phase 1 has passed gate G1.

## SCOPE AND LIMITS

- A `BEVEL` radius is a chord approximation. Segment count sets deviation; the
  formula and a segment-count table are in `references/bevel-and-chamfer.md`.
- `SOLIDIFY` cannot produce a valid offset where the surface folds more
  tightly than the thickness. **Verified (T-26): it does not self-intersect —
  it spikes.** The offset apex overshoots by `t / tan(theta/2)`, so a 15-degree
  fold given an 18 mm wall grows 138 mm, while the result stays closed,
  manifold and self-intersection-free. Every topology check passes. Detect it
  before the modifier with R-202; a G3-style topology gate will not catch it.
- Boolean results are only as good as their inputs. Coplanar faces and
  non-manifold cutters produce unstable output regardless of solver.
- Blender has no tool-path generation. Tool-radius compensation here means
  modelling the *geometry* a given cutter can reach — dogbones, minimum
  internal radii — not producing G-code.
- Flat unfolding of doubly-curved surfaces is approximate and introduces
  strain. Only developable surfaces unfold exactly.
- At building scale, watch the precision budget from W-000 Phase 1.

## MCP-FIRST WORKFLOW

inspect → ground → mutate → verify, with dimensional assertions:

- **Inspect:** confirm `obj.scale == (1,1,1)` before *any* thickness, radius or
  array operation. This single check prevents the most common class of error.
- **Mutate:** set modifier properties through the data API
  (`obj.modifiers.new(...)`), not `bpy.ops.object.modifier_add`.
- **Verify:** measure the evaluated mesh, not the base mesh — via
  `depsgraph.id_eval_get(obj).to_mesh()`. Assert bounding-box dimensions and
  thickness against the nominal table.

## DECISION TREE

```
Need thickness on a surface?
  ├─ closed/clean surface, uniform t     → R-201 (SOLIDIFY, NON_MANIFOLD mode)
  ├─ any concave fold tighter than t     → R-202 (detect FIRST; then redesign or reduce t)
  └─ must stay parametric in a graph     → parametric skill, Extrude Mesh + Flip Faces
Need a rounded or chamfered edge?
  ├─ uniform, all edges                  → R-203 (BEVEL, angle limit)
  ├─ selected edges only                 → R-204 (bevel weights / edge weight limit)
  └─ deviation matters                   → R-205 (segment count from tolerance)
Need to cut material away?
  ├─ inputs validated manifold?          → R-206 (BOOLEAN, EXACT or MANIFOLD solver)
  ├─ faces coplanar with the cutter      → R-207 (off-plane nudge)
  └─ many identical cuts                 → R-208 (single joined cutter, one boolean)
Sheet-material part?
  ├─ thickness discipline                → R-209 (material thickness as one source of truth)
  ├─ joints and tabs                     → R-210 (finger joints), R-211 (mortise and tenon)
  ├─ CNC internal corners                → R-212 (dogbone / T-bone relief for tool radius)
  ├─ nesting on a sheet                  → R-213
  └─ flat output                         → R-214 (contour extraction), interop skill for DXF/SVG
Architectural?
  ├─ mass from footprint + height        → R-215
  ├─ section cut                         → R-216 (Bisect), drawing skill for presentation
  └─ repeated structural bay             → R-217 (ARRAY with exact offset)
```

## RECIPES

| ID | Title |
| --- | --- |
| R-201 | Constant-thickness offset on an open surface |
| R-202 | Detect concave radii too tight for the requested thickness |
| R-203 | Uniform edge rounding by angle limit |
| R-204 | Bevel only selected edges via bevel weight |
| R-205 | Derive bevel segment count from a deviation tolerance |
| R-206 | Boolean difference with validated manifold inputs |
| R-207 | Break coplanarity before a boolean |
| R-208 | Batch many holes as one joined cutter |
| R-209 | Single-source material thickness driving a whole part |
| R-210 | Parametric finger joints along an edge |
| R-211 | Mortise and tenon with fit clearance |
| R-212 | Dogbone and T-bone relief for CNC internal corners |
| R-213 | Nest flat parts on a stock sheet with kerf spacing |
| R-214 | Extract flat contours from sheet parts |
| R-215 | Building mass from a dimensioned footprint |
| R-216 | Section cut at an exact elevation |
| R-217 | Structural bay array with exact spacing |

## FAILURE MODES

1. Unapplied scale → thickness and radius silently wrong. Assert scale first.
2. Bevel amount exceeding available edge length → overlapping geometry.
   Clamp with `use_clamp_overlap`.
3. Bevel before Boolean → cut edges left sharp. Follow the W-000 stack order.
4. Mirror after Bevel → bevel crosses the mirror plane. Mirror first.
5. Solidify on a tightly folded surface → a spike, not a self-intersection.
   The part is grossly oversize yet passes manifold, closed and
   self-intersection checks, so only a *dimensional* check catches it. Run
   R-202 before the modifier (T-26).
6. Measuring the base mesh instead of the evaluated mesh → modifiers invisible
   to your assertions, which then pass falsely.
7. Modelling internal corners a round cutter cannot reach → part does not fit.
   Use R-212.
8. Millimetre detail at 1e5 coordinates → float noise. Local frame.

## SAFETY

- Save before every boolean; `EXACT` can produce large, hard-to-undo results.
- Boolean on million-triangle input can hang for minutes — check counts first.
- Keep an unbaked copy before applying any modifier (W-000 Phase 6).

## REFERENCE INDEX

| File | Load when |
| --- | --- |
| `references/solidify-and-offset.md` | thickness, offset, feasibility of an offset |
| `references/bevel-and-chamfer.md` | radius, segments, deviation, weights, harden normals |
| `references/boolean-practice.md` | solver choice, coplanarity, validation protocol |
| `references/sheet-materials.md` | plywood, joints, kerf, nesting, CNC clearances |
| `references/architectural-scale.md` | large-scene precision, storeys, sections |
