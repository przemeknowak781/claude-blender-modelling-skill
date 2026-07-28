---
name: blender-cad-drawing
description: Produce technical drawing output from Blender 5.2 models — use for orthographic projections and elevations, section and plan cuts, hidden-line and Freestyle line rendering, Grease Pencil line extraction, dimension annotation and leader text, drawing sheet layout and title blocks, scale-correct output such as 1:50, and vector export to SVG, PDF or DXF for documentation.
blender_version: "5.2"
verified_on: "2026-07-28"
license: CC-BY-4.0
---

# Blender CAD — Drawing Documentation

Included at the client's explicit request. Read SCOPE AND LIMITS before
promising a drawing deliverable.

## SCOPE AND LIMITS

**Blender has no CAD-class drawing generator.** There is no associative
drafting view that updates with the model, no dimension object that measures
geometry and re-measures when it changes, no standards-compliant title block
or line-type library. What follows composes general-purpose tools into
drawing-like output. Specifically:

- Freestyle produces stylised lines from geometry at render time. It is a
  renderer feature, is **Cycles/EEVEE render-time only**, and can be slow.
- Grease Pencil "Line Art" extracts lines from geometry into editable strokes.
  Those strokes are geometry, not a live drafting view.
- **Dimensions are not associative.** Any dimension annotation produced here is
  a text object or Grease Pencil stroke. If the model changes, it does not
  follow. Drive dimension text from the model with a script (R-505) or accept
  that it goes stale — those are the only two honest options.
- Hidden-line removal is achieved by rendering, not by a vector HLR algorithm;
  quality depends on resolution and settings.
- True paper-space scale (1:50) requires deliberate camera and output-size
  arithmetic (R-503). Blender will not do it for you.

If the user needs standards-compliant production drawings, say plainly that
this is the wrong tool and the correct move is to export geometry and dimension
it in a CAD or drafting package.

## MCP-FIRST WORKFLOW

- **Inspect** the model's bounding box first; camera framing and scale
  arithmetic both derive from it.
- **Ground:** Freestyle and Grease Pencil property names are a hallucination
  hotspot. Confirm against `api_dump.json` or `search_api_docs`.
- **Verify:** measure the output *image*, not the intent — assert that a known
  model edge maps to the expected pixel or millimetre length at the declared
  scale (R-503 includes the assertion).

## DECISION TREE

```
What output is needed?
  ├─ orthographic view (plan/elevation)      → R-501
  ├─ section or cut plane                    → R-502 (Bisect + capped section face)
  ├─ output at a true paper scale            → R-503
  ├─ line drawing, raster                    → R-504 (Freestyle)
  ├─ line drawing, editable/vector           → R-506 (Grease Pencil Line Art) → R-508 (SVG)
  ├─ dimension annotation                    → R-505 (script-driven, non-associative)
  ├─ multi-view sheet with title block       → R-507
  └─ vector file for a drafting package      → R-508, or blender-cad-interop R-409 for DXF
```

## RECIPES

| ID | Title |
| --- | --- |
| R-501 | Orthographic camera for a true plan or elevation |
| R-502 | Section cut with a capped, hatched section face |
| R-503 | Camera and render settings for a declared paper scale |
| R-504 | Freestyle line render with weight by edge type |
| R-505 | Script-driven dimension annotations that re-measure the model |
| R-506 | Grease Pencil Line Art extraction |
| R-507 | Multi-view sheet layout with a title block |
| R-508 | Export drawing linework to SVG or PDF |

## FAILURE MODES

1. Presenting a drawing as dimensionally authoritative when the annotations
   are stale text. Re-run R-505 after every model change, or say so.
2. Perspective camera used for an elevation → converging lines, wrong measure.
3. Scale arithmetic done on the render resolution but not the camera
   `ortho_scale` → output is not at the declared scale.
4. Freestyle enabled per-scene but not per-view-layer → no lines appear.
5. Line Art strokes baked once and never refreshed after the model changes.
6. Section cut applied destructively to the master model — cut a copy.
7. Expecting hidden-line quality from a low-resolution render.

## SAFETY

- Section recipes cut geometry. **Always operate on a duplicate**, never the
  master model (W-000 Phase 6 discipline).
- Freestyle renders can take minutes to hours; bound resolution and samples
  before starting an unattended render.
- Rendering writes image files — confirm the output path.

## REFERENCE INDEX

| File | Load when |
| --- | --- |
| `references/ortho-and-scale.md` | camera setup, paper scale arithmetic |
| `references/linework.md` | Freestyle and Grease Pencil Line Art settings |
| `references/annotation.md` | dimension text, leaders, and the associativity problem |
