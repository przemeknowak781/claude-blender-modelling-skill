---
title: Drivers
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-17"
---

# Drivers

Use a driver when one dimension is a function of another **within the same
file**, and the relationship is arithmetic rather than geometric.

## R-301: dimension derived from another dimension

```python
fcurve = shelf.driver_add("scale", 1)        # index 1 == Y
drv = fcurve.driver
drv.type = 'SCRIPTED'

for name, path in (("d", '["depth"]'), ("w", '["wall"]')):
    var = drv.variables.new()
    var.name = name
    var.type = 'SINGLE_PROP'
    var.targets[0].id = ctrl                 # the CTRL- Empty
    var.targets[0].data_path = path

drv.expression = "d - w"
```

**Verified (T-17):** the shelf depth resolves to `depth - wall` on first
evaluation, and changing `ctrl["depth"]` propagates automatically with no other
edit and no movement in the other two axes.

## The update trap

Changing a custom property does **not** by itself invalidate the driver. Tag
the owner as well as the driven object:

```python
ctrl.update_tag()          # <- easily forgotten; the driver silently stales
shelf.update_tag()
bpy.context.evaluated_depsgraph_get().update()
```

Without `ctrl.update_tag()` the driver returns the previous value and raises
nothing. T-17 failed on exactly this before the tag was added.

## Driver or graph input?

| Situation | Use |
| --- | --- |
| one scalar depends on another scalar | driver |
| a shape is rebuilt from named numbers | Geometry Nodes input |
| many objects share one dimension | `CTRL-` custom property + drivers |
| you need a variant series in files | Geometry Nodes + batch (R-306) |

## Rules

- **Never retype a derived number.** If it is `depth - wall`, express it.
- Drivers on `scale` require the object's base geometry to be at unit size, or
  the meaning of the number changes. Prefer driving a Geometry Nodes input.
- Circular dependencies fail quietly to zero rather than raising. If a driven
  value is unexpectedly 0.0, look for a cycle.
- `expression` runs in a restricted namespace. `math` is not available by
  default; write plain arithmetic.
