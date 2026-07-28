---
title: STEP, IGES, Rhino, IFC — the honest position
blender_version: "5.2"
verified_on: "2026-07-28"
verification_status: "add-on metadata web-sourced; nothing installed or executed here"
---

# CAD exchange

## R-410: handling a STEP or IGES request honestly

Blender 5.2 has **no native STEP or IGES import or export**. There is no
operator to find. Say so, then give the real options:

1. **A third-party importer.** Maintained options exist on the official
   extensions platform — see `../../blender-cad-core/references/ecosystem-status.md`
   for the versions and dates found on 2026-07-28. Installing one runs
   third-party code; that is the user's decision, and this project has not
   tested any of them.
2. **Convert upstream.** If the sender has CAD, ask for STL/OBJ/STEP→STL at a
   stated tessellation quality. This puts the approximation decision with the
   person who has the exact geometry.
3. **FreeCAD as a converter.** Scriptable and free; converts STEP to mesh
   outside Blender.

**The limitation that survives every option:** you receive a *tessellation*.
Analytic surfaces and the feature tree are not recoverable at any quality
setting — higher quality means more triangles, not more exactness. Anything
arriving this way goes through `blender-cad-mesh-repair` before modelling.

What to say when asked to "export STEP from Blender": Blender has no B-rep to
export. Even with a perfect exporter there is no analytic geometry to write —
only a mesh. If the downstream tool needs a solid model, it has to be built in
a CAD package.

## Rhino and Grasshopper

**File-based exchange only** in this version of the skill. No live bridge is
recommended or verified.

- Rhino reads and writes OBJ, STL, PLY and glTF; use them with explicit units
  and axes (R-401/R-404) and round-trip-check (R-402).
- Rhino is Z-up like Blender, which removes the commonest orientation problem —
  but state the axes explicitly anyway.
- Grasshopper definitions do not transfer. What transfers is *baked* geometry.
  If the parametric behaviour must survive, rebuild it as a Geometry Nodes
  graph (`blender-cad-parametric`), and treat the two as separate models with
  one source of truth for the dimensions.

## IFC

Not supported in core Blender. IFC work goes through third-party tooling
(BlenderBIM / Bonsai and successors), which this project has not verified.
Treat it as ecosystem, not as a recipe: if the user needs IFC, say that it
requires an add-on, that its state should be checked, and that this skill has
no verified path.

## FEA and CAM

Blender generates no tool paths and runs no analysis. What this skill can do is
prepare geometry that is **valid input**: closed, manifold, correctly scaled,
correctly oriented, free of degenerate faces, at a controlled element density.
That is R-406 and R-407. G-code belongs to a CAM package.
