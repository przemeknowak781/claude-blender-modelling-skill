---
name: blender-cad-interop
description: Move geometry between Blender 5.2 and engineering tools — use for STL, OBJ, PLY, glTF and USD import and export, STEP and IGES limitations and the current add-on ecosystem, DXF and SVG contour output, unit scale and millimetre-versus-metre mismatches, axis conventions and up-axis and handedness, Rhino and Grasshopper and IFC and FEA and CAM exchange, export precision, and round-trip verification of bounding box and volume.
blender_version: "5.2"
verified_on: "2026-07-28"
license: CC-BY-4.0
---

# Blender CAD — Interoperability (P4)

Exchange is where dimensional work is most often destroyed. Every export in
this skill ends with a round trip.

## SCOPE AND LIMITS

- **No native STEP or IGES import or export.** Verified state of third-party
  options as of 2026-07-28: `references/step-and-cad-exchange.md`.
- All mesh formats here are tessellated. A round trip through STL cannot
  restore analytic surfaces, and repeated round trips accumulate error.
- STL carries no units at all — only bare numbers. The unit is a convention
  agreed between sender and receiver, which is why R-403 exists.
- STL carries no object names, no hierarchy, no materials. OBJ and glTF carry
  progressively more; USD carries the most structure.
- Blender is Z-up, right-handed. Many CAM and game targets are Y-up. Exporters
  expose axis mapping — set it explicitly, never rely on the default.
- Blender has **no IFC support in core**. IFC work goes through third-party
  tooling; treated as ecosystem, not as a verified recipe.
- Rhino/Grasshopper exchange in this version is **file-based only**. No live
  bridge is recommended or verified.

## MCP-FIRST WORKFLOW

- **Inspect** units and object scale before export; both are silent corrupters.
- **Ground:** exporter operator properties changed names across the 4.x → 5.x
  transition (`wm.stl_export` is the current operator, not the legacy
  `export_mesh.stl`). Confirm against `api_dump.json` before writing arguments.
- **Verify:** always round-trip. Reimport into a fresh scene and compare
  bounding-box dimensions and volume against the source within the Phase 0
  tolerance. Report the numbers, not "exported successfully".

## DECISION TREE

```
Importing?
  ├─ STL/OBJ/PLY from a solver or scan → R-401, then blender-cad-mesh-repair
  ├─ units look 1000× wrong            → R-403 (unit reconciliation)
  ├─ STEP or IGES                      → R-410 (no native path; ecosystem options + honest limits)
  └─ orientation looks rotated         → R-404 (axis convention)
Exporting?
  ├─ 3D printing                       → R-405 (STL/3MF discipline: closed, mm, scale applied)
  ├─ CAM / machining                   → R-406 (units, origin, orientation for the machine)
  ├─ FEA / simulation                  → R-407 (element quality, closed volume)
  ├─ another DCC or archive            → R-408 (USD/glTF with hierarchy)
  └─ 2D contours for cutting           → R-409 (DXF/SVG)
Anything exported?
  └─ R-402 round-trip verification. Not optional.
```

## RECIPES

| ID | Title |
| --- | --- |
| R-401 | Import a mesh file with explicit units and axes |
| R-402 | Round-trip verification of bounding box and volume |
| R-403 | Reconcile millimetre source data with a metre scene |
| R-404 | Set axis convention deliberately on import and export |
| R-405 | Export for 3D printing with a pre-flight checklist |
| R-406 | Export for CAM with machine origin and orientation |
| R-407 | Export for FEA with quality assertions |
| R-408 | Export USD or glTF preserving hierarchy and names |
| R-409 | Export 2D contours to DXF or SVG |
| R-410 | Handle a STEP or IGES request honestly |

## FAILURE MODES

1. Scene `unit_scale` inconsistent with exporter `global_scale` → 1000× error,
   the single most common interop failure.
2. Unapplied object scale at export → exported size differs from the viewport
   readout.
3. Assuming STL encodes millimetres. It encodes nothing.
4. Default axis mapping accepted silently → model arrives lying on its side.
5. Exporting unrealised instances or unapplied modifiers → empty or wrong file.
6. Using legacy 4.x exporter operator names → `AttributeError` in 5.2.
7. Declaring success on file existence rather than on a round-trip metric.
8. Repeated tessellated round trips degrading the model each pass.
9. Non-closed mesh sent to a printer or solver → rejected or nonsense results.

## SAFETY

- Export writes files. Confirm the target path is inside the project directory
  and get user consent before overwriting an existing file.
- Import can bring in millions of triangles; check file size first.
- Never install a third-party add-on on the user's behalf without consent;
  extensions execute arbitrary code.

## REFERENCE INDEX

| File | Load when |
| --- | --- |
| `references/units-and-axes.md` | any unit or orientation question |
| `references/format-matrix.md` | choosing a format; what each one preserves |
| `references/step-and-cad-exchange.md` | STEP/IGES/Rhino/IFC questions; ecosystem status |
| `references/roundtrip-harness.md` | the reusable round-trip verification code |
