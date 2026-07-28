---
name: blender-cad-parametric
description: Drive Blender 5.2 geometry from named parameters — use for Geometry Nodes graphs as a parametric CAD system, exposing modifier inputs, socket identifiers and the Socket_N naming scheme, driver expressions linking one dimension to another, custom properties as a single source of truth, variant families, design tables, and headless batch generation of dimensioned series.
blender_version: "5.2"
verified_on: "2026-07-28"
license: CC-BY-4.0
---

# Blender CAD — Parametric (P3)

Geometry Nodes and drivers as the substitute for a feature tree.

## SCOPE AND LIMITS

- Geometry Nodes is a **directed acyclic graph**, not a constraint solver. It
  computes outputs from inputs; it cannot solve for an input given a desired
  output. "Make this hole land 5 mm from the edge whatever the edge does"
  requires you to express the arithmetic explicitly.
- **There is no Bevel node in Geometry Nodes 5.2** (verified: `ng.nodes.new
  ('GeometryNodeBevel')` raises *"Node type GeometryNodeBevel undefined"*).
  Rounding inside a graph means the `BEVEL` modifier after the `NODES`
  modifier, or `GeometryNodeFilletCurve` for curves only.
- Modifier inputs are addressed by **socket identifier** (`Socket_2`, …), not
  by the label shown in the UI. The mapping is discovered at runtime, never
  guessed — see R-303.
- Node `data_type` enums advertise more values via `bl_rna` than the node
  actually accepts. Trust `enum_settable` in `api_dump.json`, or set-and-catch.
- Graph evaluation is not free. A graph rebuilt per frame across a large array
  can be slower than baked geometry.

## MCP-FIRST WORKFLOW

- **Ground before building.** Node type names and socket identifiers are the
  single largest hallucination surface. Confirm each against
  `../blender-cad-core/references/api_dump.json` or `search_api_docs` before
  writing it. If a node is not in the dump, probe it live before use.
- **Verify:** evaluate through the depsgraph and assert the resulting
  dimensions against the parameter you set. A graph that builds without error
  but ignores your input is the characteristic failure here.

## DECISION TREE

```
Does one dimension depend on another, within a single object?
  └─ driver expression → R-301
Do several objects share a dimension?
  └─ custom property on a CTRL- object + drivers → R-302
Do you need a shape rebuilt from named numeric inputs?
  └─ Geometry Nodes group with a modifier interface → R-303, R-304
Do you need N variants of one design?
  ├─ interactive comparison       → R-305 (duplicate object, per-instance inputs)
  └─ files on disk, unattended    → R-306 (headless batch), R-307 (design table CSV)
Do you need the graph result as real geometry?
  └─ R-308 (realise + apply, keeping the unbaked original)
Is the graph producing nothing?
  └─ R-309 (graph debugging checklist) then blender-cad-diagnostics
```

## RECIPES

| ID | Title |
| --- | --- |
| R-301 | Driver linking one dimension to another |
| R-302 | Control object with custom properties as single source of truth |
| R-303 | Discover modifier socket identifiers at runtime and set them by label |
| R-304 | Build a parametric part graph from scratch in Python |
| R-305 | Per-object variants sharing one node group |
| R-306 | Headless batch generation of a variant series |
| R-307 | Drive a series from a CSV design table |
| R-308 | Bake graph output while preserving the parametric original |
| R-309 | Debug a graph that outputs empty geometry |

## FAILURE MODES

1. Writing `modifier["Thickness"]` instead of the socket identifier →
   `KeyError`, or worse, a silently created custom property that does nothing.
2. Assuming socket identifiers are stable across graph edits — reordering the
   interface changes them. Re-resolve by label each run (R-303).
3. Setting an input without tagging the object for update → stale evaluation.
4. Reading `obj.data` after changing a modifier input — that is the base mesh.
   Use the evaluated depsgraph copy.
5. Instances left unrealised before export → exporter writes nothing or one copy.
6. Using a node type name from memory → `RuntimeError: Node type ... undefined`.
7. Expecting a Bevel node to exist. It does not, in 5.2.
8. Float inputs typed as integers in Python (`1` vs `1.0`) → type mismatch on
   strict sockets.

## SAFETY

- Batch generation writes many files. Confirm the output directory and a
  filename pattern with the user **before** running, and never write outside
  the project directory.
- Applying a `NODES` modifier is irreversible; keep the unbaked object.
- A runaway graph (large Array × Subdivision) can exhaust memory in headless
  runs with no UI to interrupt. Bound the parameters.

## REFERENCE INDEX

| File | Load when |
| --- | --- |
| `references/geometry-nodes-api.md` | building graphs in Python; verified node and socket names |
| `references/drivers.md` | driver expressions, dependency pitfalls |
| `references/batch-generation.md` | headless series, CSV tables, output conventions |
