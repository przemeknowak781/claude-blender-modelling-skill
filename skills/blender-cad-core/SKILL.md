---
name: blender-cad-core
description: Router and working discipline for precision, dimension-driven CAD-style modelling in Blender 5.2 — use when the task involves exact dimensions, tolerances, wall thickness, offset, fillet or chamfer, manifold checks, boolean cuts, STEP/STL/DXF exchange, CNC or 3D-print fabrication, unit scale and Apply Scale, parametric variants via Geometry Nodes or modifier stacks, or any request where the model must measure correctly rather than merely look correct.
blender_version: "5.2"
verified_on: "2026-07-28"
license: CC-BY-4.0
---

# Blender CAD — Core

Blender 5.2.0 LTS, Python 3.13. Every API identifier in this skill family was
introspected from a live 5.2 build (hash `fbe6228777e7`). See `VERIFICATION.md`.

## SCOPE AND LIMITS

Read this before promising anything. Most "Blender for CAD" material is
worthless because it pretends Blender is something it is not.

**Blender is a polygon mesh modeller. It is not a B-rep CAD kernel.**

1. Geometry is polygonal. There is no Parasolid / ACIS / OpenCASCADE kernel, no
   analytic surfaces, no geometric tolerance, no feature history tree in the
   SolidWorks or Fusion sense. A "fillet" is a faceted approximation whose
   accuracy is set by segment count, not by a tolerance value.
2. Blender's NURBS curves are a shaping tool. They are not class-A surfacing
   with G2 continuity control.
3. There is **no native STEP or IGES import**. Exchange with CAD goes through
   tessellation (STL, OBJ, PLY, glTF, USD) or third-party converters. For the
   verified state of the STEP add-on ecosystem as of 2026-07-28, see
   `../blender-cad-interop/references/step-and-cad-exchange.md` — do not
   recommend add-ons from memory.
4. There is **no native 2D sketch constraint solver**. What exists is
   community add-ons of varying maintenance health; their current state is
   recorded in `references/ecosystem-status.md`.

When a user asks for something in this list, say so plainly and offer the
nearest real workflow. See `blender-cad-diagnostics` → "Things Blender cannot
do". Inventing an operator is a worse outcome than saying no.

### Translating CAD intent into Blender 5.2

| CAD intent | Blender 5.2 equivalent | What is lost |
| --- | --- | --- |
| Dimensioned, constrained sketch | numeric entry during transforms, snapping, Geometry Nodes graph, driver expressions | no constraint solver; parametrics are explicit, not declarative |
| Feature tree | modifier stack + Geometry Nodes modifier | stack order *is* the history; any `Apply` destroys it |
| Extrude / Revolve / Sweep / Loft | Extrude, `SCREW` modifier, curve + bevel object, Bridge Edge Loops | result is tessellated immediately |
| Fillet / Chamfer | `BEVEL` modifier, bevel weights, Harden Normals | radius is a polygonal approximation; **there is no Bevel node in Geometry Nodes 5.2** (verified) |
| Boolean | `BOOLEAN` modifier, solvers `FLOAT` / `EXACT` / `MANIFOLD` | fragile on non-manifold and coplanar input |
| Pattern / Array / Mirror | `ARRAY`, `MIRROR`, Instance on Points | |
| Assembly mates | parenting, Child Of, Copy Transforms, linked collections | no mate constraints |
| Drawing / dimensioning | Freestyle, Grease Pencil, ortho cameras — see `blender-cad-drawing` | no CAD-class drawing generator |
| Wall-thickness / draft analysis | edit-mode overlays, 3D-Print Toolbox, custom `bmesh` scripts | |
| Units and scale | Scene units, `unit_scale`, mandatory Apply Scale | the single most common source of export errors |

## MCP-FIRST WORKFLOW

If the Blender Lab MCP server is connected, drive Blender directly. If not,
emit a `bpy` script for the user to run with
`blender --background --python script.py`. Both paths obey the same cycle.

**inspect → ground → mutate → verify**

1. **Inspect.** Read scene state before touching it (`get_objects_summary`,
   `get_object_detail_summary`). Never assume object names.
2. **Ground.** Before using non-obvious API, query `search_api_docs` /
   `get_python_api_docs`. The server ships docs versioned with the binary —
   that is its advantage over any static Markdown.
3. **Mutate.** Make the smallest change that advances the task.
4. **Verify.** Check a **number**: face count, volume, bounding-box dimensions,
   non-manifold edge count. **Absence of an exception is not success.** For
   suspect geometry add `render_viewport_to_path`.

The 20 tools this server actually exposes are listed in
`references/mcp-workflow.md`, read from the add-on source, not from a README.

## DECISION TREE

```
Geometry came from outside (solver, scan, CAD, marching cubes)?
  └─ YES → blender-cad-mesh-repair FIRST. Never model on unvalidated input.
Need exact dimensions, thickness, holes, joints, fabrication output?
  └─ blender-cad-precision-modeling
Need a family of variants driven by parameters, or headless batch generation?
  └─ blender-cad-parametric
Importing or exporting, units or axes look wrong?
  └─ blender-cad-interop
Drawings, sections, ortho views, dimension annotation?
  └─ blender-cad-drawing
Something is broken and you do not know why?
  └─ blender-cad-diagnostics
Starting a model from scratch?
  └─ W-000 below. Do not skip it.
```

## RECIPES

### W-000: The modelling process (master recipe)

R-recipes answer "how do I do X". W-000 answers "in what order, and when to
stop". Blender does not enforce this discipline; CAD enforces it through
architecture. Run W-000 at the start of every modelling session.

Full text with gate scripts: `references/w000-process.md`.

**Phase 0 — Interview (do not touch Blender).** Record five answers at the top
of the script or in the file's decision log:

| Question | Why it determines everything after |
| --- | --- |
| Purpose: fabrication, simulation, visualisation, documentation? | sets required topology and permissible simplification |
| Dimensional tolerance and nominal unit? | sets segment counts, Merge-by-Distance threshold, export precision |
| Which dimensions will change later? | decides what must stay parametric and what may be baked |
| Is geometry external input or built from zero? | external input **always** starts at mesh repair |
| Who or what consumes the output file? | sets axis convention, units, format |

If an answer is missing and cannot be safely assumed, **ask — do not guess**. A
model built on a wrong tolerance assumption is scrap, not a fixable draft.

**Phase 1 — Scene setup. Gate G1:** units set, `unit_scale` intentional, all
objects at scale 1.0, file saved under a versioned name. Precision budget: if
scene extent ÷ smallest significant detail exceeds ~1e6, work in a local
offset frame, not world space.

**Phase 2 — Decomposition.** For every feature, declare *up front* whether it
is destructive.

> Anything derived from a parameter that may change stays unbaked (modifier or
> Geometry Nodes). Everything else may be baked immediately. The destructive
> boundary is declared in advance, not discovered later.

| Situation | Tool |
| --- | --- |
| One-off shape, dimensions fixed | mesh edit with numeric entry |
| Repetition, symmetry, thickness, rounding | modifier stack |
| Variant family, coupled parameters, batch output | Geometry Nodes |
| Subtracting solids, pockets, holes | Boolean — but only after manifold validation of both inputs |
| Solver or scan output | mesh-repair path first, nothing else |
| A dimension derived from another dimension | driver or graph input, never a retyped number |

**Phase 3 — Dimensional blockout. Gate G2:** measured bounding boxes match the
nominal dimension table within tolerance. Enter real numbers now. Eyeballing
"to fix later" is the difference between a CAD process and an artistic one,
and is the main cause of models that can never be brought to dimension.
All driving dimensions live in **one** place: custom properties on a control
object (convention `CTRL-<name>`) or Geometry Nodes modifier inputs.

**Phase 4 — Parametric core.** Canonical stack order. **Default, not sacred** —
verify empirically on unusual geometry:

1. Topology generators — `MIRROR`, `ARRAY`, `SCREW` (they define the whole solid)
2. `BOOLEAN` (needs valid input; before bevelling so new edges get bevelled)
3. `SOLIDIFY` (thickness on a settled shape)
4. Cleanup — `WELD`, degenerate removal
5. `BEVEL` (second-to-last shape step)
6. `SUBSURF` or `REMESH`, if at all
7. Export only — `TRIANGULATE`, `DECIMATE`
8. `WEIGHTED_NORMAL` last; it only affects shading

Rules worth memorising: Mirror before Bevel, or the bevel runs through the
mirror plane. Boolean before Bevel, or cut edges stay sharp.

**Phase 5 — Detail and validation. Gate G3:** zero non-manifold edges, zero
doubles above threshold, consistent normals, no self-intersections introduced
by Solidify or Bevel, volume and area in range. Verification is **numeric and
scripted**. A viewport render supplements it; it never proves it.

**Phase 6 — Bake and export. Gate G4:** an unbaked copy is preserved in a
separate collection before any `Apply`; export with explicit units and axes;
then **round-trip** — reimport and compare bounding box and volume against the
original, within the Phase 0 tolerance.

**Accompanying rules.** Save before every gate, incrementing the name — the
file is the only undo that survives a session. Keep a decision log in a text
data-block inside the `.blend` so the model explains itself months later.
**Never skip a gate:** if one fails, return to the phase that caused it rather
than masking it in the next. A masked dimensional error surfaces at the CNC.
**Stopping criterion:** the model is done when G4 passes and the Phase 0 brief
is met — not when it looks good.

### Operational recipes in this skill

| ID | Title | Reference |
| --- | --- | --- |
| R-001 | Set up scene units and precision budget | `references/units-and-precision.md` |
| R-002 | Apply scale safely across a hierarchy | `references/units-and-precision.md` |
| R-003 | Work in a local offset frame in a large scene | `references/units-and-precision.md` |
| R-004 | Establish a `CTRL-` control object and drivers | `references/scene-hygiene.md` |
| R-005 | Write and read the in-file decision log | `references/scene-hygiene.md` |
| R-006 | Preserve an unbaked copy before Apply | `references/scene-hygiene.md` |
| R-007 | Gate scripts G1–G4 as reusable functions | `references/w000-process.md` |

## FAILURE MODES

The ten antipatterns below are the recurring causes of wrong CAD output in
Blender. Full symptom/repair detail: `../blender-cad-diagnostics/SKILL.md`.

1. Unapplied object scale before Bevel, Solidify, Array or export → radii and
   thicknesses differ from what you typed.
2. Scene unit scale inconsistent with export units → model 1000× off.
3. Boolean on non-manifold input or doubled vertices → garbage or silent
   no-op. Merge by Distance and validate **before**, not after.
4. Coplanar faces in Boolean → unstable result. Nudge the cutter off-plane.
5. N-gons feeding Subdivision or Bevel → shading and geometry artefacts.
6. `bpy.ops` in a loop over objects → quadratic cost and context dependence.
   Use `bmesh` or the data API.
7. Float precision loss in wide scenes (1e5 coordinates, 1e-3 detail) → work
   in a local frame.
8. Judging success by "no exception raised" instead of a geometric metric.
9. Premature `Apply` destroying the modifier stack → keep an unbaked copy.
10. `DECIMATE` in `COLLAPSE` mode on sharp-featured geometry → use `PLANAR`
    or weight the collapse.

## SAFETY

The Blender Lab add-on executes LLM-generated code with what its own source
calls a "weak sandbox" — quoting `weak_sandbox.py`: *"Note that this isn't
really a sandbox, more guidance that some things should not be done."* There is
no protection against data loss or exfiltration. Therefore:

- **Save the file before any destructive operation.** Blender's undo does not
  survive the session; the saved file is the only real checkpoint.
- **Never** call `bpy.ops.wm.read_homefile` or `bpy.ops.wm.quit_blender`
  without explicit user consent — both discard unsaved work irrecoverably.
- **Never** read or write paths outside the project directory.
- Do all verification in a container or VM on synthetic files, never on
  production projects.
- Prefer headless (`blender --background --python`) for validation; use an
  interactive session only for visual inspection.
- Treat `execute_blender_code` as an unsandboxed shell with the user's
  filesystem privileges. Scope it accordingly.

## REFERENCE INDEX

| File | Load when |
| --- | --- |
| `references/w000-process.md` | starting any model; need gate scripts G1–G4 |
| `references/units-and-precision.md` | units, scale, tolerance, large-scene precision |
| `references/scene-hygiene.md` | naming, collections, control objects, decision log |
| `references/mcp-workflow.md` | MCP server is connected, or you need its tool list |
| `references/ecosystem-status.md` | asked about STEP import or constraint-solver add-ons |
| `references/api_dump.json` | need to confirm any identifier exists in 5.2 |

Sibling skills: `blender-cad-mesh-repair`, `blender-cad-precision-modeling`,
`blender-cad-parametric`, `blender-cad-interop`, `blender-cad-drawing`,
`blender-cad-diagnostics`.
