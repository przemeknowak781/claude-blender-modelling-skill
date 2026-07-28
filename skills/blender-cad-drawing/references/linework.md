---
title: Freestyle and Grease Pencil Line Art
blender_version: "5.2"
verified_on: "2026-07-28"
verification_status: "settings from live introspection; full render output NOT visually verified"
---

# Linework

Two routes, with different outputs.

| | Freestyle | Grease Pencil Line Art |
| --- | --- | --- |
| Output | raster, at render time | editable strokes (geometry) |
| Engine | EEVEE or Cycles only | any |
| Editable after | no | yes |
| Vector export | no (raster only) | yes, via SVG |
| Speed | slow on complex scenes | moderate, but strokes are baked |

## R-504: Freestyle

```python
scene.render.engine = 'BLENDER_EEVEE'          # or 'CYCLES'
scene.render.use_freestyle = True

view_layer = bpy.context.view_layer
view_layer.use_freestyle = True                # <- per VIEW LAYER, easily missed
settings = view_layer.freestyle_settings
lineset = settings.linesets.new("Outlines")
lineset.select_silhouette = True
lineset.select_border = True
lineset.select_crease = True
lineset.select_edge_mark = False
```

**The commonest failure is enabling Freestyle on the scene but not on the view
layer.** Both flags are required; with only the scene flag set, no lines appear
and nothing warns you.

`BLENDER_WORKBENCH` does **not** support Freestyle. If you want measured
geometry (R-503) and Freestyle lines, render twice and compose, or accept
EEVEE.

## R-506: Grease Pencil Line Art

Line Art extracts strokes from geometry into an editable Grease Pencil object.
Because the strokes are geometry, they are **baked at the moment you generate
them**: change the model and the strokes are stale until regenerated. Same
associativity problem as dimensions (`annotation.md`).

Use it when you need the linework as vectors — for SVG export (R-508) or for
manual cleanup. Use Freestyle when a raster render is the deliverable.

## R-508: vector export

Grease Pencil strokes can be written to SVG. Contours from geometry can also go
out as DXF or SVG via the interop path (R-409), which is usually the better
route for anything that must be dimensionally exact, because it comes from the
mesh rather than from a render.

## Engine identifiers in 5.2

Verified by assignment on a live 5.2 instance:

| Identifier | Result |
| --- | --- |
| `BLENDER_EEVEE` | accepted |
| `BLENDER_WORKBENCH` | accepted |
| `CYCLES` | accepted |
| `BLENDER_EEVEE_NEXT` | **`TypeError`** |

`BLENDER_EEVEE_NEXT` was the 4.2-era name and **does not exist in 5.2**. This
is a live trap for anything written against 4.x material.

Note also that `render.bl_rna.properties['engine'].enum_items` reports only
`BLENDER_EEVEE` at factory startup, because the other engines register
dynamically. The advertised enum understates what is settable here — the
mirror image of the Compare-node case, and another reason to test assignment
rather than read the enum.

## Honest limits

- Hidden-line removal here is achieved by *rendering*, not by a vector HLR
  algorithm. Quality depends on resolution and settings.
- There is no line-type library, no standards-compliant weights, no title-block
  generator. Compose those yourself (R-507) or in a drafting package.
- Freestyle renders can take minutes to hours. Bound resolution and samples
  before starting an unattended render.
