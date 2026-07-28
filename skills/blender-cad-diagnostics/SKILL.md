---
name: blender-cad-diagnostics
description: Diagnose broken CAD-style results in Blender 5.2 — use when a boolean produced garbage or did nothing, a bevel or solidify came out the wrong size, an exported model is 1000 times too large or small, a modifier appears to have no effect, geometry is non-manifold or has flipped normals, a Geometry Nodes graph outputs nothing, a Python snippet raises AttributeError or KeyError on a modifier or node socket, or the user asks for a CAD feature Blender does not have.
blender_version: "5.2"
verified_on: "2026-07-28"
license: CC-BY-4.0
---

# Blender CAD — Diagnostics

Symptom-first entry point. Start from what the user observed.

## SCOPE AND LIMITS

- This skill diagnoses geometry, units and API problems. It does not cover
  rendering, shading or animation issues.
- Some symptoms have no fix because the request is outside Blender's
  capabilities. That case is handled explicitly below — **saying "Blender does
  not do this" is a correct answer**, and a better one than improvising an
  operator that does not exist.

## MCP-FIRST WORKFLOW

Diagnosis is measurement. Before forming any hypothesis:

1. `get_objects_summary` — what actually exists, and what is named what.
2. Run the standard probe (`references/probe.md`): object scale, unit settings,
   modifier stack order, evaluated vs base counts, manifold status.
3. Only then form a hypothesis, and change **one** thing to test it.

Do not repair and re-verify in the same step; you will not know which change
was responsible.

## DECISION TREE

```
SYMPTOM: dimensions wrong (thickness, radius, spacing)
  └─ check obj.scale != (1,1,1)          → D-01, fix: apply scale
SYMPTOM: exported model 1000× off
  └─ check scene.unit_settings vs export → D-02
SYMPTOM: modifier appears to do nothing
  ├─ show_viewport off / stack order     → D-03
  └─ measured base mesh not evaluated    → D-04
SYMPTOM: boolean produced garbage or nothing
  ├─ non-manifold or doubled input       → D-05
  ├─ coplanar faces                      → D-06
  └─ wrong solver for the case           → D-07
SYMPTOM: bevel overlaps or explodes
  └─ amount > available edge length      → D-08
SYMPTOM: shading artefacts, dark patches
  └─ inconsistent normals / n-gons       → D-09
SYMPTOM: Geometry Nodes outputs nothing
  └─ D-10 (graph probe checklist)
SYMPTOM: AttributeError / KeyError on modifier or socket
  └─ D-11 (identifier does not exist in 5.2 — verify, do not guess)
SYMPTOM: bpy.ops fails or no-ops in background mode
  └─ D-12 (context; prefer data API / bmesh)
SYMPTOM: everything is slow or Blender hangs
  └─ D-13 (counts before operations)
SYMPTOM: numbers jitter, geometry shimmers in a big scene
  └─ D-14 (float precision budget)
REQUEST: a CAD feature Blender lacks
  └─ D-99 — answer honestly, offer the nearest real workflow
```

## RECIPES

| ID | Symptom |
| --- | --- |
| D-01 | Dimensions wrong — unapplied scale |
| D-02 | Export off by a factor of 1000 |
| D-03 | Modifier has no visible effect |
| D-04 | Assertions pass but geometry is wrong — measuring the base mesh |
| D-05 | Boolean fails on non-manifold input |
| D-06 | Boolean unstable on coplanar faces |
| D-07 | Wrong boolean solver for the case |
| D-08 | Bevel self-overlap |
| D-09 | Shading artefacts from normals or n-gons |
| D-10 | Geometry Nodes graph outputs empty geometry |
| D-11 | `AttributeError` / `KeyError` on a modifier property or node socket |
| D-12 | `bpy.ops` fails or no-ops headless |
| D-13 | Operation hangs or exhausts memory |
| D-14 | Float precision loss in a large scene |
| D-99 | The request is outside Blender's capabilities |

### D-99: Things Blender 5.2 cannot do

When the request matches this list, **refuse the impossible part explicitly**,
name the limitation, and offer the nearest real workflow. Do not invent an
operator, a modifier, or a node.

| Request | Reality | Nearest real workflow |
| --- | --- | --- |
| Exact B-rep fillet to a stated tolerance | no analytic surfaces; `BEVEL` is a chord approximation | choose segments from a deviation budget (precision-modeling R-205) and state the resulting deviation |
| Native STEP / IGES import or export | not in core | tessellated exchange, or third-party add-on — interop R-410 |
| 2D sketch constraint solver | not in core | numeric entry, snapping, Geometry Nodes, drivers — see core `ecosystem-status.md` |
| Associative feature history with rollback | no history tree | modifier stack + Geometry Nodes + versioned files (W-000) |
| Associative dimensions that update with the model | annotations are not associative | script-driven re-measurement — drawing R-505 |
| Assembly mates and degrees of freedom | no mate solver | parenting and transform constraints |
| Geometric tolerance / GD&T | no tolerance model | document tolerances outside the file |
| G-code or tool paths | not a CAM package | model reachable geometry; export to a CAM tool — interop R-406 |
| Class-A surfacing with G2 continuity | NURBS are a shaping tool only | export to a surfacing package |

## FAILURE MODES

Diagnostic process errors, distinct from the geometry errors above:

1. Changing several things at once, then declaring it fixed — you have learned
   nothing and the bug may still be there.
2. Accepting "no exception" as proof. Measure.
3. Trusting the viewport over a number.
4. Fixing the symptom in a later phase instead of the phase that caused it
   (W-000 gate discipline).
5. Guessing an API name after one fails, instead of introspecting.

## SAFETY

- Diagnosis should be read-only where possible. Save before any repair.
- Never "fix" by deleting geometry the user has not agreed to lose.
- When reproducing a bug, work on a copy of the file.

## REFERENCE INDEX

| File | Load when |
| --- | --- |
| `references/probe.md` | the standard diagnostic probe script |
| `references/api-introspection.md` | an identifier failed; verify it exists in 5.2 |
