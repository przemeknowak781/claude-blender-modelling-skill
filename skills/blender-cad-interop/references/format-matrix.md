---
title: What each exchange format preserves
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-18"
---

# Format matrix

| Format | Units | Hierarchy | Names | Materials | Good for |
| --- | --- | --- | --- | --- | --- |
| STL | none | no | no | no | 3D print, single solid, CAM input |
| OBJ | none | flat groups | yes | basic | quick mesh exchange |
| PLY | none | no | no | vertex colours | scan data, point attributes |
| glTF | metres | yes | yes | PBR | archive, web, DCC exchange |
| USD | metres | yes | yes | yes | large scenes, pipeline interchange |
| DXF/SVG | 2D | layers | yes | no | cutting contours, drafting |
| STEP/IGES | — | — | — | — | **not native — see step-and-cad-exchange.md** |

## Choosing

- **3D printing** → STL, closed manifold mesh, millimetre convention, scale
  applied.
- **CAM** → STL or OBJ, with the machine's origin and orientation set
  deliberately, not defaulted.
- **FEA** → whatever the solver reads, but the mesh must be closed and free of
  degenerate faces; element quality matters more than triangle count.
- **Another DCC or an archive** → USD or glTF, which keep names and hierarchy.
- **Cutting** → DXF or SVG contours (R-409).

## Verified round-trip behaviour (T-18)

A 48-segment truncated cone exported and reimported:

- **STL** with `global_scale=1.0` both ways: bounding box and volume survive to
  better than 1e-5 m and 1e-4 respectively; still manifold.
- **OBJ** with `forward_axis='Y', up_axis='Z'` both ways: same.
- **OBJ** with operator defaults both ways: **orientation is permuted** (T-19).

## Rules

1. **Always round-trip (R-402).** Reimport into a fresh scene and compare
   bounding box and volume. File existence is not verification.
2. **Realise instances and apply modifiers** before export, or the exporter
   writes one copy or nothing. `apply_modifiers=True` on the export operator
   handles the modifier half.
3. **Tessellated round trips accumulate error.** Each pass through a mesh
   format re-approximates. Do not use the exported file as your working master.
4. **A non-closed mesh** sent to a printer or solver is rejected or produces
   nonsense. Check `cadlib.diagnose(obj)["closed"]` first.
