---
name: blender-cad-mesh-repair
description: Validate and repair imported meshes in Blender 5.2 — use for topology-optimisation and marching-cubes output, 3D scans, or any STL/OBJ/PLY whose geometry is dense, non-manifold, self-intersecting, inverted-normal or stair-stepped; covers manifold checking, hole filling, normal recalculation, remeshing with error control, feature-preserving decimation, volume-preserving smoothing, connected-component extraction, and volume and surface-area measurement.
blender_version: "5.2"
verified_on: "2026-07-28"
license: CC-BY-4.0
---

# Blender CAD — Mesh Repair (P0)

Solver and scan output is the highest-priority path. **Nothing else in this
skill family may run on unvalidated input geometry.**

## SCOPE AND LIMITS

- Repair here is polygonal. It cannot recover analytic surfaces that the
  source solver never had, and it cannot invent a feature tree.
- Stair-stepping from voxel/marching-cubes sources is *aliasing*, not noise.
  Smoothing reduces its visibility while shrinking volume; only remeshing at
  a finer error bound genuinely reduces it.
- "Watertight" and "manifold" are not synonyms. A mesh can be closed and still
  have non-manifold edges shared by three or more faces.
- Self-intersection is not detected by any built-in operator. It is found by
  `bmesh` interrogation or by an `EXACT` boolean self-union — both covered here.
- Volume of a non-closed mesh is meaningless. Always check closure first.

## MCP-FIRST WORKFLOW

inspect → ground → mutate → verify. Repair-specific instrumentation:

- **Inspect:** `get_object_detail_summary` for counts; then run the diagnostic
  script (R-101) for the numbers that matter — non-manifold edges, loose
  geometry, boundary loops, shell count, volume, area.
- **Verify:** re-run R-101 after every mutation and **diff the numbers**. A
  repair that fixes normals while halving volume has failed.
- Render only to confirm topology intuitions; never as evidence.

## DECISION TREE

```
Run R-101 diagnostics first. Then:

non_manifold_edges > 0
  ├─ caused by loose/interior geometry?  → R-102 (delete loose, interior faces)
  ├─ caused by doubled vertices?         → R-103 (Merge by Distance, threshold from tolerance)
  └─ genuine T-junction / bowtie?        → R-110 (voxel remesh — rebuilds topology)
boundary_loops > 0 (mesh is open)
  ├─ small, planar holes                 → R-104 (fill holes)
  └─ large or curved openings            → R-110 (remesh) or accept as an open surface
normals inconsistent or inverted         → R-105 (recalculate; verify by signed volume)
shells > 1                               → R-106 (separate components, keep by volume)
triangle count too high
  ├─ organic / no sharp features         → R-107 (Decimate COLLAPSE)
  ├─ sharp features must survive         → R-108 (Decimate PLANAR, or weighted collapse)
  └─ topology itself is bad              → R-110 (remesh, then decimate)
stair-stepping from voxel source         → R-109 (volume-preserving smoothing) + R-110
self-intersections suspected             → R-111 (detect), R-112 (resolve via EXACT self-boolean)
need volume / area / centre of mass      → R-113
```

## RECIPES

| ID | Title |
| --- | --- |
| R-101 | Full mesh diagnostic report (the measurement harness everything else uses) |
| R-102 | Remove loose vertices, edges and interior faces |
| R-103 | Merge by Distance with a tolerance-derived threshold |
| R-104 | Fill boundary holes without distorting the rim |
| R-105 | Recalculate normals and verify by signed volume |
| R-106 | Split connected components and keep by volume rank |
| R-107 | Decimate by collapse to a target triangle budget, preserving volume |
| R-108 | Feature-preserving reduction on sharp-edged geometry |
| R-109 | Smooth voxel stair-stepping without losing volume |
| R-110 | Voxel and Quad remesh with an explicit error bound |
| R-111 | Detect self-intersections |
| R-112 | Resolve self-intersections with an EXACT self-boolean |
| R-113 | Measure volume, surface area and centre of mass |

*(Recipe bodies follow the mandatory template: Problem / When NOT to use /
Blender path / Alternative / Verified code / Result verification / Common
mistakes / Source.)*

## FAILURE MODES

1. Measuring volume on an open mesh — the number is meaningless. Check
   `boundary_loops == 0` first.
2. Merge by Distance with a threshold larger than the smallest real feature —
   silently destroys detail. Derive the threshold from Phase 0 tolerance.
3. `DECIMATE` `COLLAPSE` on mechanical parts — rounds off the very edges that
   carry the dimensions.
4. Smoothing to fix stair-stepping — shrinks the part. Always re-measure volume.
5. Recalculating normals on a mesh with more than one shell — inside-out shells
   can survive. Separate first, then recalculate.
6. Running Boolean to "clean up" before repairing manifoldness — compounds the
   damage.
7. Treating a closed mesh as manifold. They are different tests.
8. Using `bpy.ops.mesh.*` in Object mode or headless without a mode switch —
   fails or silently no-ops. Use `bmesh` (see `references/bmesh-patterns.md`).

## SAFETY

- Repair is destructive by nature. **Save a versioned file before starting**,
  and keep the untouched import in a separate collection.
- Dense imports (millions of triangles) can exhaust memory; check the count
  from R-101 before any remesh, which can multiply it.
- Never run repair operators over an entire scene blindly; scope to the
  selected object.

## REFERENCE INDEX

| File | Load when |
| --- | --- |
| `references/diagnostics-harness.md` | need the full R-101 measurement code |
| `references/bmesh-patterns.md` | writing repair code without `bpy.ops` |
| `references/remesh-and-decimate.md` | choosing between remesh and decimation strategies |
