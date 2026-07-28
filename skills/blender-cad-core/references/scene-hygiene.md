---
title: Scene hygiene — naming, control objects, decision log
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-17, T-20"
---

# Scene hygiene

## Naming convention

| Prefix | Meaning |
| --- | --- |
| `CTRL-` | control object; holds driving dimensions, no geometry |
| `CUT-` | boolean cutter, not part of the delivered model |
| `REF-` | reference or imported geometry, never edited |
| `<name>_unbaked` | preserved pre-Apply copy |

Collections: `01_model`, `02_cutters`, `03_reference`, `04_export`,
`99_unbaked`. Anything not in `01_model` is excluded from export.

## R-004: Control object as the single source of truth

**Problem:** the same dimension retyped in three places drifts.
**When NOT to use:** a genuinely one-off shape with no repeated dimension.

```python
ctrl = bpy.data.objects.new("CTRL-Cabinet", None)   # Empty: no geometry
bpy.context.scene.collection.objects.link(ctrl)
ctrl["depth"] = 0.600
ctrl["wall"] = 0.018
```

Then drive geometry from it (R-301), never by retyping the number.

**Verify:** `"depth" in ctrl.keys()` and the driven object measures correctly.

**Common mistakes:** putting the control properties on a mesh object that later
gets its scale applied or gets deleted in cleanup. Use an Empty.

## R-005: Decision log inside the .blend

**Problem:** in six months, nobody remembers why the wall is 18 mm.

```python
NAME = "DECISIONS"
text = bpy.data.texts.get(NAME) or bpy.data.texts.new(NAME)
text.write(
    "2026-07-28 wall=18mm: stock plywood thickness, not a design choice\n"
    "2026-07-28 tolerance=0.5mm: CNC router repeatability\n"
)
```

**Verify:** `bpy.data.texts["DECISIONS"].as_string()` returns the entries.

**Common mistakes:** keeping the log in a separate file that gets separated
from the `.blend`. The point is that it travels with the model.

## R-006: Preserve an unbaked copy before Apply

**Problem:** `Apply` destroys the modifier stack, which is the only feature
history Blender has. Undo does not survive the session.
**When NOT to use:** never skip it before a destructive Apply.

```python
unbaked = obj.copy()
unbaked.data = obj.data.copy()        # copy the DATA too, or they share a mesh
unbaked.name = f"{obj.name}_unbaked"
bpy.context.scene.collection.objects.link(unbaked)
```

**Verify:** `f"{obj.name}_unbaked" in bpy.data.objects` — asserted by T-20.

**Common mistakes:** `obj.copy()` alone. Without copying `.data`, both objects
share one mesh and editing either edits both.
