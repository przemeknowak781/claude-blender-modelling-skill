---
title: R-402 round-trip verification
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-18, T-20"
---

# R-402: round-trip verification

**Problem:** an export that "succeeded" can be the wrong size, the wrong
orientation, or empty.
**When NOT to use:** never skip it. This is gate G4.

The implementation is `gates.gate_g4`.

```python
import gates

ok, report = gates.gate_g4(obj, "out/part.stl", tolerance=0.0005,
                           importer='stl', global_scale=1.0)
assert ok, report
```

It exports nothing itself — you export, then it reimports into a **fresh
scene**, applies scale if the importer left it un-applied, and compares:

- `max_dimension_error` against your Phase 0 tolerance
- `volume_error_fraction`
- `reimported_manifold`

## Full pattern

```python
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
path = os.path.abspath("out/part.stl")

bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                      global_scale=1.0, apply_modifiers=True)

ok, report = gates.gate_g4(obj, path, tolerance=0.0005,
                           importer='stl', global_scale=1.0)
print(f"round trip: {report['original_dimensions']} -> "
      f"{report['reimported_dimensions']}, "
      f"error {report['max_dimension_error'] * 1000:.4f} mm")
assert ok
```

## Report the numbers

Not "exported successfully" — say:

> Exported `part.stl`. Round trip: 0.300 x 0.300 x 0.240 m in, same out, max
> dimension error 0.0000 mm against a 0.5 mm tolerance, manifold. Volume
> 0.01696 m3, unchanged to 6 significant figures.

That is a verification. The first phrasing is a claim.

## Because gate_g4 resets the scene

`gate_g4` opens a factory-default file to do the reimport, which discards
unsaved work. **Save before calling it**, and call it last. T-20 does exactly
this: preserve the unbaked copy, save, export, then gate.
