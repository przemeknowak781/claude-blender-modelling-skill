# blender-cad

**Agent Skills that turn Claude into a competent operator of Blender 5.2 for
dimension-driven, CAD-style modelling.**

Not "Blender for artists, but engineering-flavoured." This is for geometry that
has to *measure* correctly — parts that get cut, printed, simulated, or built.

<p>
<img alt="Blender 5.2.0 LTS" src="https://img.shields.io/badge/Blender-5.2.0%20LTS-orange">
<img alt="Python 3.13" src="https://img.shields.io/badge/Python-3.13-blue">
<img alt="27/27 cases" src="https://img.shields.io/badge/acceptance-27%2F27%20cases-brightgreen">
<img alt="159 assertions" src="https://img.shields.io/badge/assertions-159%20numeric-brightgreen">
<img alt="0 unknown identifiers" src="https://img.shields.io/badge/hallucinated%20API-0-brightgreen">
<img alt="CC-BY-4.0" src="https://img.shields.io/badge/licence-CC--BY--4.0-lightgrey">
</p>

---

## The problem this solves

Ask any LLM how to do something in Blender's Python API and you will get code
that looks right. Often it is right. Sometimes it invokes a property, an enum
value, or a node that has never existed, and you find out at runtime — or
worse, you don't, because the operation completed and quietly did nothing.

Blender makes this especially easy to get wrong:

- A **boolean with a bad cutter returns silently**, no exception, model
  unchanged.
- **Solidify on a tight fold produces a clean, manifold, closed result that is
  138 mm oversize.** Every topology check passes.
- **`wm.stl_import(global_scale=…)` puts the factor in the object scale**, not
  the mesh, so your part measures right and then corrupts every downstream
  bevel and export.
- **OBJ's own documented export/import defaults do not round-trip** — they
  rotate the part, and the dimensions come back as a permutation.

None of those raise an error. All four are verified below, with test IDs.

So this repository is built around one rule:

> **Every API identifier in every file was executed against a live Blender 5.2
> instance. An automated validator fails the build if any name in any `.md` or
> `.py` does not exist in the introspection dump.** Content that sounds
> plausible but was not run is rejected.

That validator scans this project's own writing too. It has already caught one
defect in itself — see [Keeping it honest](#keeping-it-honest).

---

## What you get

| | |
| --- | --- |
| **7 skills** | routers under 500 lines each, fixed section order, progressive disclosure |
| **64 recipes** | every advertised ID has a body — problem, when *not* to use, code, verification, common mistakes |
| **26 reference files** | loaded on demand, not up front |
| **27 acceptance cases** | 159 numeric assertions, isolated headless Blender per case |
| **3.7 MB API dump** | live introspection: 27 modifiers, 62 node types, 60 operators, 83 `bmesh.ops` |
| **[`VERIFICATION.md`](VERIFICATION.md)** | what was executed, what was **not**, and a 4.x→5.2 migration table |

### The skills

| Skill | Reach for it when |
| --- | --- |
| **`blender-cad-core`** | starting anything. Scope limits, units, precision budget, and **W-000** — the seven-phase process with gates G1–G4 |
| **`blender-cad-mesh-repair`** | geometry came from a solver, scan, or marching cubes. Manifold checks, repair, remesh, decimation, measurement |
| **`blender-cad-precision-modeling`** | thickness, fillets, booleans, joints, CNC clearances, buildings at millimetre accuracy |
| **`blender-cad-parametric`** | Geometry Nodes as a parametric system, drivers, headless variant series |
| **`blender-cad-interop`** | import/export, units, axes, round-trip verification, and the truth about STEP |
| **`blender-cad-drawing`** | ortho views, sections, true paper scale, linework, dimension annotation |
| **`blender-cad-diagnostics`** | something broke and you don't know why — plus **D-99: things Blender cannot do** |

---

## W-000: the part that matters most

CAD packages enforce discipline through architecture — you cannot dimension a
feature that doesn't exist, and the history tree makes order visible. **Blender
enforces nothing.** You can scale an object non-uniformly, bevel it, export it,
and never learn that the radius you typed is not the radius you got.

W-000 supplies the discipline the software omits. Recipes answer *how do I do
X*; W-000 answers *in what order, and when to stop*.

```
Phase 0  Interview — 5 questions, answered BEFORE touching Blender
                     (missing units? ask. guessing costs a factor of 1000)
Phase 1  Scene setup ──────────────────────────────► G1  units, scale, saved
Phase 2  Decomposition — declare the destructive boundary up front
Phase 3  Dimensional blockout ─────────────────────► G2  bboxes match nominal
Phase 4  Parametric core — canonical stack order
Phase 5  Detail & validation ──────────────────────► G3  manifold, clean
Phase 6  Bake & export ────────────────────────────► G4  round trip in tolerance
```

The gates are **runnable code**, not advice — `tests/gates.py`, exercised end to
end by T-20, which passes all four with numeric evidence.

**Never skip a gate.** If one fails, return to the phase that caused it rather
than masking it in the next. A masked dimensional error surfaces at the CNC.

**Stopping criterion:** the model is done when G4 passes and the Phase 0 brief
is met — not when it looks good.

---

## What Blender is not

The skills state this up front, because most "Blender for CAD" material is
worthless for pretending otherwise.

Blender is a **polygon mesh modeller**. There is no Parasolid/ACIS/OpenCASCADE
kernel, no analytic surfaces, no geometric tolerance, no feature history, no
sketch constraint solver, and no native STEP or IGES.

| You want | Reality | What you actually do |
| --- | --- | --- |
| Exact B-rep fillet to a tolerance | `BEVEL` is a chord approximation | derive segment count from a deviation budget (R-205) and **state the resulting deviation** |
| Native STEP / IGES | not in core | tessellated exchange, or a third-party add-on — with its limits stated (R-410) |
| Sketch constraint solver | not in core | numeric entry, snapping, Geometry Nodes, drivers |
| Feature history with rollback | no history tree | modifier stack + Geometry Nodes + versioned files (W-000) |
| Associative dimensions | annotations are dead text | script-driven re-measurement (R-505) — or say it's a dated snapshot |
| G-code / tool paths | not a CAM package | model reachable geometry, export to CAM (R-406) |

**A skill that cannot say "Blender doesn't do this" is worse than no skill.**
That refusal is itself a test: **T-99** asserts every impossible request is
named explicitly, that each carries a concrete alternative, and that no
invented operator is offered as a workaround.

---

## Install

**As a plugin** — clone and point your Claude plugin configuration here;
`.claude-plugin/plugin.json` declares the package.

**As plain skills:**

```bash
cp -r skills/blender-cad-* ~/.claude/skills/     # user-wide
cp -r skills/blender-cad-* .claude/skills/       # this project only
```

Skills activate on their `description` triggers: dimensions, tolerance,
manifold, offset, fillet, STEP, CNC, 3D printing, unit scale, Geometry Nodes,
and similar.

**Requires Blender 5.2 LTS** — not "5.x". The Geometry Nodes modifier input API
broke between 5.1 and 5.2 (see below). Python 3.13 ships with Blender. The
[Blender Lab MCP server](https://projects.blender.org/lab/blender_mcp) is
optional; the skills degrade cleanly to emitting `bpy` scripts.

---

## Run the tests

```bash
python3 tests/run_evals.py                      # all 27 cases
python3 tests/run_evals.py --only T-01 T-99     # selected
python3 tests/run_evals.py --json report.json   # machine-readable
```

Each case runs in **its own headless Blender process**, so one crash cannot
mask or contaminate another. Fixtures — including a 1.7-million-triangle
marching-cubes blob with deliberately flipped normals, debris shells and loose
vertices — are generated deterministically on first run. Nothing depends on
external data, and no production file is ever opened.

Coverage: P0 ×5, P1 ×6, P2 ×3, P3 ×3, P4 ×3, W-000 process ×4, drawing ×2,
negative ×1.

> Rendering cases need a GL context. In a container:
> `apt-get install libegl1 libgl1-mesa-dri` — the runner sets
> `LIBGL_ALWAYS_SOFTWARE=1` itself.

---

## Keeping it honest

```bash
# re-introspect the binary
blender --background --factory-startup --python tools/harvest_api.py -- \
    skills/blender-cad-core/references/api_dump.json

# fail on any identifier that does not exist in 5.2
python3 tools/validate_identifiers.py
```

The validator checks every node type, operator, modifier type and `bmesh.ops`
name in every `.md` and `.py` under `skills/`, `tests/` and `tools/`.

Two details that make it more than a spell-checker:

**Names used *because* they don't exist** live in `tools/known_absent.txt` with
a reason, and are asserted to *stay* absent. The skill needs to be able to say
"there is no Bevel node" — and if a future release adds one, the build fails
and the docs get corrected instead of quietly becoming wrong in the other
direction.

**The harvester records `enum_settable` separately from `enum`** — what a live
instance *accepts* versus what `bl_rna` *advertises*. These differ, and the gap
is exactly where confident-but-wrong code comes from:

```python
FunctionNodeCompare.data_type   # advertises 24 values
                                # accepts 11
                                # 'BOOLEAN', 'ROTATION', 'MATRIX' → TypeError
```

The engine enum fails the *opposite* way: it advertises only `BLENDER_EEVEE`,
yet `CYCLES` and `BLENDER_WORKBENCH` assign fine. **Test assignment, don't read
the enum.**

### It caught a defect in itself

The validator originally treated an operator whose harvest had *failed* as
known — it keyed on the dictionary entry existing, not on it succeeding. That
let a misspelled `wm.gpencil_import_svg` (real name:
`wm.grease_pencil_import_svg`) validate cleanly while not existing.

Fixed, and written up in `VERIFICATION.md` rather than quietly patched. **A
validator that can be fooled is worse than none — it manufactures confidence.**

---

## Fifteen things that are not what you'd assume

All verified on Blender 5.2.0 LTS, build `fbe6228777e7`. Full table with
evidence in [`VERIFICATION.md`](VERIFICATION.md).

**The one most likely to bite you:**

```python
# Blender 4.x — ALL THREE raise TypeError in 5.2
mod["Socket_2"]                              # read
mod["Socket_2"] = 0.5                        # write
mod.keys()                                   # enumerate

# Blender 5.2
getattr(mod.properties.inputs, "Socket_1").value = 0.5
```

Socket identifiers also shift when the interface is reordered, so resolve them
from labels at runtime rather than hard-coding. T-16 asserts all three legacy
forms raise, so the claim is re-checked on every run.

**The rest, briefly:**

- **No Bevel node exists in Geometry Nodes 5.2.** `nodes.new('GeometryNodeBevel')`
  raises.
- **A too-tight Solidify doesn't self-intersect — it spikes.** 15° fold + 18 mm
  wall = 138 mm of overshoot, still closed and manifold. Topology gates pass it.
  *(T-26 — and this one disproved a claim in an earlier draft of these skills.)*
- **Manifoldness does not detect flipped normals.** The T-01 fixture reports 0
  non-manifold edges *and* 234 inconsistently-wound ones. Three independent
  tests: closed, manifold, normals-consistent.
- **Merge by Distance is necessary, not sufficient** — it leaves interior walls,
  and the volume reading changes meaning (T-07).
- **A multi-shell self-intersecting cutter makes `EXACT` boolean output
  nothing, silently.** One manifold cutter per boolean.
- **Vertex coordinates are float32.** Precision floor ~1e-7 m at the origin;
  ~0.03 mm on a 1 mm feature at a 600 km easting (T-14).
- **`BMElemSeq` doesn't support slice steps** — `bm.faces[::4]` raises.
- **Changing a custom property doesn't invalidate its drivers** — tag the owner
  or read a stale value with no error (T-17).
- **No DXF operator exists in core 5.2 at all.** Vector out goes through
  `wm.grease_pencil_export_svg`/`_pdf`.
- **`bpy.ops.export_mesh` survives as an empty namespace** — so `hasattr` says
  `True` while `export_mesh.stl` raises. Feature detection lies here.

Two premises in the original brief **did not reproduce** and are documented as
such rather than repeated: Compare/Random Value socket identifiers did *not*
change in 5.2, and there is no new Bevel node.

---

## Safety

The Blender Lab add-on executes generated code under what its own source calls
a weak sandbox — quoting `weak_sandbox.py`:

> *"Note that this isn't really a sandbox, more guidance that some things
> should not be done. […] If the LLM (or its user) is motivated these can be
> worked around."*

It blocks `sys.exit()`. It does not stop file deletion, network access, or
overwriting your work. Treat `execute_blender_code` as a shell with your
privileges. The skills therefore require saving before destructive operations,
forbid `read_homefile` and `quit_blender` without consent, and confine file
access to the project directory. All verification here ran in a container on
synthetic fixtures.

---

## What is *not* verified

Stated plainly, because a verification document that only lists successes isn't
one:

- **No live MCP session.** Tool names were read from the add-on source at
  commit `98b0e49d`; the manifest declares `blender_version_min = "5.1.0"` with
  no upper bound. 5.2 compatibility is *expected but unconfirmed*.
- **No CAD add-on installed or executed.** The ecosystem page records vendor
  listing metadata gathered 2026-07-28. Re-check before relying on it.
- **DXF/SVG file *writing*.** Contour extraction is verified against an
  analytic perimeter (T-04); the writers are not exercised.
- **No GPU render path**, no interactive GUI, no Rhino/Grasshopper/IFC/FEA/CAM
  software present.

---

## Maintenance

Semantic versioning, independent of Blender's. Every Blender release requires a
re-harvest, a validator run, and a full suite run, recorded in
`VERIFICATION.md` with the date and build hash. Breaking API changes go in the
migration table — never a silent edit.

## Licence

CC-BY-4.0.
