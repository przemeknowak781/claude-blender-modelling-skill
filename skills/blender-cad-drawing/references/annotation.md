---
title: Dimension annotation and the associativity problem
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-25"
---

# Annotation

## The limitation, stated first

**Blender has no associative dimensions.** There is no dimension object that
measures geometry and re-measures when the geometry changes. Anything you
produce is a text object or a Grease Pencil stroke holding a *string*.

You have exactly two honest options:

1. **Generate the text by measuring** (R-505) and **re-run the generator after
   every model change**.
2. **Say the drawing is a snapshot** and date it.

There is no third option. A drawing whose numbers were typed by hand, or
measured once and never refreshed, is a drawing that will eventually lie.

**Verified (T-25):** the annotation is generated from the geometry, then the
model is made 300 mm taller. The text does not change. The test asserts this
staleness explicitly, and then asserts that re-running the generator produces
the corrected value.

## R-505: measure, never retype

```python
def annotate(obj, label):
    _, _, dims = cadlib.bbox_world(obj)
    text = f"{label} {dims[0] * 1000:.0f} x {dims[2] * 1000:.0f}"

    tdata = bpy.data.curves.new(f"DIM-{label}", type='FONT')
    tdata.body = text
    tob = bpy.data.objects.new(f"DIM-{label}", tdata)
    bpy.context.scene.collection.objects.link(tob)
    return tob
```

The number comes from `cadlib.bbox_world`, which measures the **evaluated**
object. Never build a dimension string from the parameter you *set* — build it
from what the geometry *is*. Those differ whenever a modifier changed
something, and the whole point of a dimension is to report reality.

## Refreshing every annotation

```python
def refresh_annotations():
    for tob in bpy.data.objects:
        if not tob.name.startswith("DIM-"):
            continue
        source = bpy.data.objects.get(tob.name[4:])
        if source is None:
            continue
        _, _, dims = cadlib.bbox_world(source)
        tob.data.body = f"{dims[0] * 1000:.0f} x {dims[2] * 1000:.0f}"
```

Run it as the last step before any drawing output, always. Put it in the same
script that renders, so it cannot be forgotten.

## R-502: sections

**Cut a duplicate, never the master.**

```python
cut = source.copy()
cut.data = source.data.copy()        # copy the DATA too
cut.name = f"{source.name}_section"
bpy.context.scene.collection.objects.link(cut)

bm = bmesh.new()
bm.from_mesh(cut.data)
bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                       dist=1e-7, plane_co=(0.0, 0.0, elevation),
                       plane_no=(0.0, 0.0, 1.0),
                       clear_inner=False, clear_outer=True)
bm.to_mesh(cut.data)
bm.free()
cut.data.update()
```

T-25 asserts the master's volume is unchanged afterwards and that the section
lands at the requested elevation to within 1e-6 m.

## R-507: sheet layout

There is no title-block generator. Build one from text objects and a rectangle
in a dedicated collection, position it in camera space, and drive the fields
(project, date, scale, revision) from custom properties on a `CTRL-Sheet`
Empty so they are edited in one place.

State the scale on the sheet **and** verify it (R-503). A drawing labelled
1:50 that is not 1:50 is worse than an unlabelled one.
