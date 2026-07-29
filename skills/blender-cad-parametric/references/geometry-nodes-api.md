---
title: Geometry Nodes from Python in 5.2
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-05, T-16, T-21"
---

# Geometry Nodes in Python — Blender 5.2

## The breaking change you must know about

**The 4.x dict-style modifier input access is gone in 5.2.** All three of these
raise `TypeError: bpy_struct: this type doesn't support IDProperties`:

```python
value = mod["Socket_2"]        # TypeError
mod["Socket_2"] = 0.5          # TypeError
mod.keys()                     # TypeError
```

This is the single most likely thing to be reproduced from memory and the most
likely to fail. Test **T-16** asserts all three raise, so the claim is checked
on every run rather than asserted once in prose.

**The 5.2 form** is attribute access on `mod.properties.inputs`, keyed by
socket **identifier**, then `.value`:

```python
getattr(mod.properties.inputs, "Socket_1").value = 0.75
current = getattr(mod.properties.inputs, "Socket_1").value
```

`mod.properties` is a `GeometryNodesModifierInterface` exposing `inputs`,
`outputs` and `panels`. Each socket accessor carries `name`, `value`, `type`
and `attribute_name`. Note `mod.properties.inputs` is **not** iterable and has
no `len()` — its RNA properties *are* the socket identifiers.

## R-303: resolve identifiers from labels at runtime

Identifiers (`Socket_0`, `Socket_1`, …) are assigned in interface creation
order and **change when the interface is reordered**. Never hard-code them;
resolve from the label every run:

```python
ident = {i.name: i.identifier
         for i in node_group.interface.items_tree
         if i.item_type == 'SOCKET' and i.in_out == 'INPUT'}

getattr(mod.properties.inputs, ident["Length"]).value = 0.750
```

## R-304: build a parametric graph from scratch

```python
ng = bpy.data.node_groups.new("Part", 'GeometryNodeTree')

out_sock = ng.interface.new_socket(name="Geometry", in_out='OUTPUT',
                                   socket_type='NodeSocketGeometry')
s = ng.interface.new_socket(name="Length", in_out='INPUT',
                            socket_type='NodeSocketFloat')
s.default_value = 0.400
s.min_value = 0.001

gi = ng.nodes.new('NodeGroupInput')
go = ng.nodes.new('NodeGroupOutput')
cube = ng.nodes.new('GeometryNodeMeshCube')
combine = ng.nodes.new('ShaderNodeCombineXYZ')

ng.links.new(gi.outputs[ident["Length"]], combine.inputs['X'])
ng.links.new(combine.outputs['Vector'], cube.inputs['Size'])
ng.links.new(cube.outputs['Mesh'], go.inputs[out_sock.identifier])

mod = obj.modifiers.new(name="GN", type='NODES')
mod.node_group = ng
```

Node **inputs/outputs** are indexed by socket name (`cube.inputs['Size']`);
**group** input/output sockets are indexed by identifier. They are different
namespaces — mixing them is a common `KeyError`.

## Forcing re-evaluation

Setting an input does not by itself refresh the evaluated mesh:

```python
obj.update_tag()
bpy.context.evaluated_depsgraph_get().update()
dims = cadlib.bbox_world(obj)[2]     # now current
```

For drivers, tag the **property owner too** — T-17 found that tagging only the
driven object leaves the driver reading a stale value with no error.

## Verify that the parameter actually drives geometry

```python
for value in (0.5, 2.0, 3.25):
    getattr(mod.properties.inputs, ident["Length"]).value = value
    obj.update_tag()
    bpy.context.evaluated_depsgraph_get().update()
    assert abs(cadlib.bbox_world(obj)[2][0] - value) < 1e-6
```

A graph that builds without error but ignores your input is the characteristic
failure here, and it raises nothing.

## R-305: per-object variants sharing one node group

```python
for name, length in (("PartA", 0.4), ("PartB", 0.6)):
    obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new(name="GN", type='NODES')
    mod.node_group = shared_group          # ONE group, many objects
    getattr(mod.properties.inputs, ident["Length"]).value = length
```

Modifier input values live on the **modifier**, not on the node group, so one
group can drive any number of differently-dimensioned objects. Editing the
group changes all of them; editing a modifier input changes one.

**When NOT to use:** when variants differ *structurally* rather than
numerically — then they need different graphs, not different inputs.

**Verify:** evaluate each object and assert its own dimensions (R-306's loop).

## R-308: bake graph output, keeping the parametric original

```python
unbaked = obj.copy()
unbaked.data = obj.data.copy()
unbaked.name = f"{obj.name}_unbaked"
bpy.context.scene.collection.objects.link(unbaked)

with bpy.context.temp_override(object=obj):
    bpy.ops.object.modifier_apply(modifier="GN")
```

`modifier_apply` is context-sensitive, so it needs the override in a script.
This is one of the few places `bpy.ops` is unavoidable.

**When NOT to use:** before gate G4. Keep the graph until the round trip
passes; applying early throws away the only thing that can regenerate the part.

**Verify:** the baked object's dimensions and volume match the evaluated
pre-bake values, and `f"{obj.name}_unbaked"` exists.

**Common mistakes:** `obj.copy()` without `obj.data.copy()` — both objects then
share one mesh and applying to one wrecks the other.

## R-309: debug a graph that outputs nothing

Work down this list; each step is a single change with a single check.

1. **Is the group linked?** `mod.node_group is not None`.
2. **Is the output socket connected?** An unconnected Group Output produces
   empty geometry with no error.
3. **Read `mod.node_warnings`** — the modifier exposes the warnings the UI
   shows in its panel.
4. **Is the input value what you think?**
   `getattr(mod.properties.inputs, ident[label]).value` — a value silently left
   at its default is the commonest cause.
5. **Did you force evaluation?** `obj.update_tag()` then
   `bpy.context.evaluated_depsgraph_get().update()`.
6. **Are you measuring the evaluated object?** `obj.data` is the base mesh and
   is legitimately empty for a graph-generated part (T-21 asserts exactly that:
   0 base vertices, full evaluated geometry).
7. **Are instances realised?** Instanced geometry needs
   `GeometryNodeRealizeInstances` before most exporters see it.

## Enum traps

`bl_rna` enum lists are a **superset** of what a node accepts.
`FunctionNodeCompare.data_type` advertises 24 values and accepts 11. Read
`enum_settable` in `api_dump.json`, or set-and-catch.

Sockets also change with mode: `FunctionNodeCompare` with `operation='EQUAL'`
gains an `Epsilon` input; `FunctionNodeRandomValue` with `data_type='BOOLEAN'`
replaces `Min`/`Max` with `Probability`.

## No Bevel node

`ng.nodes.new('GeometryNodeBevel')` raises `Node type GeometryNodeBevel
undefined`. There is no Bevel node in 5.2. Use the `BEVEL` modifier after the
`NODES` modifier, or `GeometryNodeFilletCurve` for curves.
