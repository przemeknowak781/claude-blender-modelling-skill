---
title: Choosing between remesh and decimation
blender_version: "5.2"
verified_on: "2026-07-28"
verified_by: "T-01, T-08, T-09"
---

# Remesh vs decimate

They solve different problems. Choosing wrong is antipattern 10.

| Your problem | Tool | Cost |
| --- | --- | --- |
| too many triangles, topology is fine | `DECIMATE` | detail loss proportional to ratio |
| topology is bad (self-intersecting, multi-shell, junk) | `REMESH` `VOXEL` | volume error bounded by voxel size; count often *rises* |
| sharp mechanical features must survive | `DECIMATE` `DISSOLVE` | none, if the faces are genuinely coplanar |
| need quads for subdivision | `REMESH` `QUAD` | reshapes everything |

## R-107: collapse decimation to a triangle budget

```python
mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
mod.decimate_type = 'COLLAPSE'
mod.ratio = min(1.0, TARGET_TRIS / current_tris)
mod.use_collapse_triangulate = True
```

**Compute the ratio from the count *after* cleanup**, not from the original.
T-01 does this: cleanup drops the debris shell first, then the ratio targets
100k against what actually remains.

**Verified result (T-01):** 1,705,996 → under 110,000 triangles with volume
preserved inside 2 percent, zero non-manifold edges, one shell.

**When NOT to use:** on prismatic parts with sharp edges. Collapse rounds off
the very edges that carry the dimensions.

## R-108: feature-preserving reduction

```python
mod = obj.modifiers.new(name="Planar", type='DECIMATE')
mod.decimate_type = 'DISSOLVE'          # "Planar" in the UI
mod.angle_limit = 0.0872665             # 5 degrees, in RADIANS
```

`angle_limit` is radians. Use `math.radians(5)` rather than a magic number.

**Verified result (T-09)** on a densely tessellated cube: over 10x reduction,
bounding box preserved **exactly**, volume preserved to better than 0.0001
percent, still manifold. Collapse decimation at the same triangle budget loses
measurably more volume — the test asserts the comparison, so the claim is not
rhetorical.

## R-110: voxel remesh with a declared error bound

```python
mod = obj.modifiers.new(name="Remesh", type='REMESH')
mod.mode = 'VOXEL'
mod.voxel_size = 0.02      # metres; this IS your error bound
mod.adaptivity = 0.0
```

Voxel remesh guarantees a single manifold shell. The price is a surface
perturbation of up to about one voxel.

**Verified result (T-08):** 73 shells with 543 self-intersecting faces → 1
shell, manifold, 0 self-intersections, volume error inside a declared 10
percent bound at 20 mm voxels on a ~1 m part.

**Declare the bound before you run it, then assert it.** "Remesh made it clean"
is not a result; "volume moved 4.1 percent against a 10 percent budget" is.

**When NOT to use:** when dimensional accuracy matters more than topology. A
voxel remesh moves every surface. For a part that must fit, repair the topology
locally instead and keep the original surfaces.

## R-109: smoothing stair-stepping

Smoothing reduces the *appearance* of voxel aliasing and **shrinks the part**.
Always re-measure volume afterwards and report the change. If the stepping is
genuinely unacceptable, the real fix is a finer isosurface from the solver, not
post-hoc smoothing.
