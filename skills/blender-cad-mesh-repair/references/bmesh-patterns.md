---
title: Repair without bpy.ops
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-01, T-07"
---

# bmesh patterns

`bpy.ops.mesh.*` requires Edit mode and a context. In background mode and in
loops it fails or silently no-ops (antipattern 6, diagnostics D-12). Every
repair below uses `bmesh` instead.

## The frame

```python
import bmesh, cadlib

bm = cadlib.base_bmesh(obj)          # or evaluated_bmesh(obj) to bake modifiers
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

# ... operations ...

bm.to_mesh(obj.data)
bm.free()
obj.data.update()
```

**Call `ensure_lookup_table()` after anything that adds or removes elements.**
Index-based access on a stale table is undefined behaviour, not an error.

**`v.co` is a view into the bmesh.** Reading it after `bm.free()` gives
garbage. Copy what you need out first — `[(v.co.x, v.co.y) for v in bm.verts]`
— which is a bug this project actually hit in T-12.

**`BMElemSeq` does not support slice steps.** `bm.faces[::4]` raises
`TypeError`. Materialise first: `list(bm.faces)[::4]`. Hit in T-02.

## R-102: remove loose geometry

```python
bmesh.ops.delete(bm, geom=cadlib.loose_verts(bm), context='VERTS')
bm.verts.ensure_lookup_table()
```

## R-103: merge by distance

```python
threshold = tolerance / 10.0        # NOT an arbitrary 0.0001
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=threshold)
```

**Derive the threshold from the Phase 0 tolerance**, and check it is at least
an order of magnitude below the smallest real feature. A threshold approaching
feature size silently eats geometry, and nothing warns you. T-07 asserts this
relationship explicitly.

**Necessary but not sufficient:** welding abutting bodies merges the shells and
leaves the interior walls in place. T-07 proves it — the mesh is still
non-manifold afterwards. Follow with interior-face removal or a remesh (R-110).

## R-105: recalculate normals

```python
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
```

**Verify by signed volume, not by eye:**
```python
assert cadlib.volume(bm, signed=True) > 0        # outward
assert not cadlib.inconsistent_normal_edges(bm)  # and internally consistent
```

Both checks are needed. Recalculation makes normals *consistent*; the signed
volume tells you they are consistent *outward*.

**Do this per shell.** On a multi-shell mesh an entire inside-out shell can
survive a global recalculation. Separate first (R-106).

## R-106: split shells, keep by rank

```python
comps = cadlib.shells(bm)
comps.sort(key=len, reverse=True)
doomed = [f for comp in comps[1:] for f in comp]
bmesh.ops.delete(bm, geom=doomed, context='FACES')
```

Ranking by face count suits solver debris. Rank by `sum(f.calc_area())` or by
per-shell volume when the largest body is not the one with most faces.

## R-104: fill boundary holes

```python
bmesh.ops.holes_fill(bm, edges=cadlib.boundary_edges(bm), sides=0)
```

`sides=0` means "no limit on hole size"; set it to bound how large a hole is
allowed to be filled, so a genuinely open surface is not accidentally capped.

**When NOT to use:** on a surface that is *meant* to be open (T-02's input is
an open surface by design), or on large curved openings, where the flat fill
is worse than the hole. Remesh (R-110) instead.

**Verify:** `cadlib.is_closed(bm)` becomes True and the bounding box does not
change — a fill that moves the bbox has bridged something it should not have.

## R-111 / R-112: self-intersection

**R-111, detect:** `cadlib.self_intersecting_face_count(bm)`.

**R-112, resolve.** A voxel remesh (R-110) is the blunt, reliable instrument —
T-08 takes a fixture with 543 self-intersecting faces to 0 while keeping volume
within the declared bound. The alternative, an `EXACT` self-union, resolves the
crossings without rebuilding the whole surface:

```python
# Self-union: the object booleaned against a copy of itself.
dup = obj.copy()
dup.data = obj.data.copy()
bpy.context.scene.collection.objects.link(dup)
mod = obj.modifiers.new(name="SelfUnion", type='BOOLEAN')
mod.operation = 'UNION'
mod.solver = 'EXACT'
mod.object = dup
```

**When NOT to use:** on meshes with many shells that are *supposed* to stay
separate — the union merges them. Split first (R-106).

**Verify:** `self_intersecting_face_count` drops to 0 **and** volume is
unchanged within tolerance. A self-union that changed the volume has merged
shells you wanted kept.

## R-113: measure volume, area and centre of mass

```python
bm = cadlib.evaluated_bmesh(obj)
closed = cadlib.is_closed(bm)
vol  = cadlib.volume(bm) if closed else None      # None, not a wrong number
area = cadlib.surface_area(bm)
com  = cadlib.centre_of_mass(bm)
bm.free()
```

**When NOT to use:** never report a volume for an open mesh. T-10 asserts the
harness returns `None` rather than the meaningless number `calc_volume` would
happily produce.

**Verify:** against an analytic value where one exists. T-10 checks a 256-gon
prism against the polygon area and perimeter formulae and matches to better
than 0.01 percent, which is what makes the harness itself trustworthy.

Note `centre_of_mass` here is the **area-weighted centroid of the surface**,
not the centre of mass of a solid body of uniform density. For a closed convex
solid they coincide; in general they do not. Say which one you mean.
