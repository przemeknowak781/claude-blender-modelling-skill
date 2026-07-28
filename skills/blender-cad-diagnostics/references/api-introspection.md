---
title: Verifying an identifier instead of guessing it
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-16, T-99"
---

# When an identifier fails, introspect — never guess again

An `AttributeError`, `KeyError` or `RuntimeError: Node type ... undefined`
means the name does not exist in 5.2. The correct response is to look it up in
the live binary. Guessing a second name is how a plausible-but-wrong API
catalogue gets written.

## Check the dump first

```python
import json
dump = json.load(open("skills/blender-cad-core/references/api_dump.json"))

dump["modifiers"]["SOLIDIFY"]["properties"].keys()
dump["nodes"]["FunctionNodeCompare"]["inputs"]
dump["operators"]["wm.stl_import"]["properties"].keys()
```

## Introspect live when the dump does not cover it

```python
# modifier properties
m = obj.modifiers.new(name="tmp", type='BEVEL')
print([p.identifier for p in m.bl_rna.properties if not p.is_readonly])

# what an enum ACTUALLY accepts
print([i.identifier for i in m.bl_rna.properties['limit_method'].enum_items])

# operator properties
print([p.identifier for p in bpy.ops.wm.stl_export.get_rna_type().properties])

# node sockets
n = ng.nodes.new('GeometryNodeExtrudeMesh')
print([(s.identifier, s.name, s.type) for s in n.inputs])
```

## The trap: `bl_rna` enums are a superset

`bl_rna.properties[x].enum_items` lists what the RNA type *advertises*, which
can be far more than the instance *accepts*. Verified example:

- `FunctionNodeCompare.data_type` advertises **24** values.
- It accepts **11**: `FLOAT`, `INT`, `VECTOR`, `RGBA`, `STRING`, `OBJECT`,
  `IMAGE`, `COLLECTION`, `MATERIAL`, `FONT`, `SOUND`.
- Assigning `BOOLEAN`, `ROTATION`, `MATRIX`, `MENU`, `GEOMETRY` and the rest
  raises `TypeError: enum "X" not found in (...)`.

So `api_dump.json` records **`enum_settable`** alongside `enum`, produced by
attempting each assignment on a live instance. **Quote `enum_settable`.** This
is precisely the mechanism that produces confident, wrong code.

## Sockets vary with the node's mode

Polymorphic nodes change their socket set when `data_type`, `mode` or
`operation` changes. Verified:

- `FunctionNodeCompare`, `operation='EQUAL'` → gains an `Epsilon` input.
- `FunctionNodeRandomValue`, `data_type='BOOLEAN'` → `Min`/`Max` are replaced
  by `Probability`.

`api_dump.json` records these under each node's `sockets_by` key.

## Run the validator

```bash
python3 tools/validate_identifiers.py
```

Scans every `.md` and `.py` in `skills/`, `tests/` and `tools/` and fails on
any node, operator, modifier type or `bmesh.ops` name absent from the dump.
Expected output: `OK: 0 unknown identifiers.`

Names that appear *because they do not exist* (so the skill can say so) live in
`tools/known_absent.txt` with a reason, and the validator asserts they stay
absent — if a future release adds one, the build fails and the docs get fixed.
