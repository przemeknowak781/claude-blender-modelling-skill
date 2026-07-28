---
title: Headless batch generation
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-05"
---

# Batch generation

## R-306: a variant series, unattended

```python
VARIANTS = [
    {"Length": 0.400, "Width": 0.300, "Height": 0.200},
    {"Length": 0.500, "Width": 0.300, "Height": 0.200},
    # ...
]

for i, params in enumerate(VARIANTS):
    for label, value in params.items():
        getattr(mod.properties.inputs, ident[label]).value = value
    obj.update_tag()
    bpy.context.evaluated_depsgraph_get().update()

    dims = cadlib.bbox_world(obj)[2]
    want = (params["Length"], params["Width"], params["Height"])
    err = max(abs(a - b) for a, b in zip(dims, want))
    assert err < 1e-4, f"variant {i}: {err * 1000:.4f} mm off"    # 0.1 mm

    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.abspath(f"{OUTDIR}/variant_{i:02d}.blend"))
```

Run it:
```bash
blender --background --factory-startup --python generate.py
```

**Verified (T-05):** 8 variants spanning 50 mm to 2 m, every dimension within
0.1 mm of its parameter, 8 files written.

**Assert inside the loop, not after.** A variant that silently failed to
update produces a file that looks fine and measures wrong.

## R-307: CSV design table

```python
import csv

with open("variants.csv", newline="") as fh:
    for i, row in enumerate(csv.DictReader(fh)):
        for label in ("Length", "Width", "Height"):
            getattr(mod.properties.inputs, ident[label]).value = float(row[label])
        # ... update, assert, save as above, using row["name"] for the filename
```

Keep the CSV next to the `.blend`. It is the design table, and it belongs under
version control with the model.

## Output discipline

- **Confirm the output directory and filename pattern with the user before
  running.** A batch writes many files; getting it wrong overwrites work.
- Never write outside the project directory.
- `os.makedirs(OUTDIR, exist_ok=True)` before the loop, and use absolute paths
  — `save_as_mainfile` resolves relative paths against Blender's cwd, not
  the script's.
- Bound the parameters. A runaway graph (large `ARRAY` x `SUBSURF`) exhausts
  memory with no UI to interrupt it.

## Exporting the series

To ship meshes rather than `.blend` files, export inside the same loop and
round-trip-check at least the first and last (interop R-402). Per-variant
export without a single round-trip check is how a whole batch ships at the
wrong scale.
