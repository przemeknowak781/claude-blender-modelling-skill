# blender-cad

Agent Skills for **precision, dimension-driven CAD-style modelling in Blender
5.2 LTS**: mesh repair for solver and scan output, geometry for fabrication,
parametric variants, interoperability, drawing documentation, and diagnostics.

Every API identifier in these files was introspected from a live Blender 5.2.0
LTS build (`fbe6228777e7`, Python 3.13.13) and is checked on every run by an
automated validator. See [`VERIFICATION.md`](VERIFICATION.md) for what was
executed and — equally important — what was not.

**26/26 acceptance cases pass, 151 numeric assertions. 0 unknown identifiers.**

## What this is for

Dimensioned geometry that has to measure correctly, not merely look correct:
topology-optimisation output, CNC and plywood fabrication, 3D printing,
architecture at millimetre accuracy, parametric variant families, and exchange
with engineering tools.

## What this is not

Blender is a polygon mesh modeller, not a B-rep CAD kernel. There is no
geometric kernel, no analytic surfaces, no tolerance model, no feature history,
no sketch constraint solver, and no native STEP or IGES. The skills say so
explicitly and name the nearest real workflow instead of inventing an operator.
That refusal is itself tested (T-99).

This is deliberately **not** a general Blender skill. It contains nothing about
PBR materials, lighting, animation, rigging, sculpting or game-engine export.

## Skills

| Skill | Use it for |
| --- | --- |
| `blender-cad-core` | router, scope limits, units and precision, and **W-000** — the seven-phase process with gates G1–G4 |
| `blender-cad-mesh-repair` | P0: solver/scan output — manifold checks, repair, remesh, decimation, measurement |
| `blender-cad-precision-modeling` | P1/P2: thickness, fillets, booleans, joints, CNC clearances, building scale |
| `blender-cad-parametric` | P3: Geometry Nodes as a parametric system, drivers, headless variant series |
| `blender-cad-interop` | P4: import/export, units, axes, round-trip verification, STEP reality |
| `blender-cad-drawing` | ortho views, sections, paper scale, linework, dimension annotation |
| `blender-cad-diagnostics` | symptom-first debugging, plus **D-99: things Blender cannot do** |

Each `SKILL.md` is a router under 500 lines with a fixed section order
(`SCOPE AND LIMITS`, `MCP-FIRST WORKFLOW`, `DECISION TREE`, `RECIPES`,
`FAILURE MODES`, `SAFETY`, `REFERENCE INDEX`). Detail lives in `references/`
and loads on demand.

## Installation

**As a plugin** — clone this repository and point your Claude plugin
configuration at it; `.claude-plugin/plugin.json` declares the package.

**As plain skills** — copy the skill directories:

```bash
cp -r skills/blender-cad-* ~/.claude/skills/          # user-wide
cp -r skills/blender-cad-* .claude/skills/            # single project
```

Skills activate on their `description` triggers — dimensions, tolerance,
manifold, offset, fillet, STEP, CNC, 3D printing, unit scale, Geometry Nodes,
and similar.

## Requirements

- **Blender 5.2 LTS.** Not "5.x" — the Geometry Nodes modifier input API broke
  between 5.1 and 5.2 (see `VERIFICATION.md`, finding 2). 4.5 LTS differences
  are marked `COMPAT-4.5` where they appear.
- Python 3.13 (bundled with Blender).
- Optional: the [Blender Lab MCP server](https://projects.blender.org/lab/blender_mcp)
  for direct control. Skills degrade cleanly to emitting `bpy` scripts.

## Running the tests

```bash
python3 tests/run_evals.py                      # all 26 cases
python3 tests/run_evals.py --only T-01 T-99     # selected
python3 tests/run_evals.py --json report.json   # machine-readable
```

Each case runs in its own headless Blender process. Fixtures are generated on
first run; nothing depends on external data. Rendering cases need a GL context
— in a container, install `libegl1` and `libgl1-mesa-dri` (the runner sets
`LIBGL_ALWAYS_SOFTWARE=1` itself).

## Keeping it honest

```bash
# re-introspect the binary
blender --background --factory-startup --python tools/harvest_api.py -- \
    skills/blender-cad-core/references/api_dump.json

# fail on any identifier that does not exist in 5.2
python3 tools/validate_identifiers.py
```

The validator scans every `.md` and `.py` in `skills/`, `tests/` and `tools/`
and checks each node type, operator, modifier type and `bmesh.ops` name against
the dump. Identifiers named *because they do not exist* live in
`tools/known_absent.txt` with a reason, and are asserted to stay absent.

This matters because the dominant failure mode of LLM-written Blender material
is confident, plausible, non-existent API. The harvester also records
`enum_settable` — what a live instance actually accepts — separately from what
`bl_rna` advertises, because the two differ (Compare advertises 24 data types
and accepts 11).

## Safety

The Blender Lab add-on executes generated code under what its own source calls
a "weak sandbox" — quoting `weak_sandbox.py`: *"this isn't really a sandbox,
more guidance that some things should not be done."* There is no protection
against data loss. The skills therefore require saving before destructive
operations, forbid `read_homefile` and `quit_blender` without consent, and
confine file access to the project directory. All verification here ran in a
container on synthetic fixtures.

## Versioning

Semantic, independent of Blender's version. Each Blender release requires a
re-harvest, a validator run and a full suite run, recorded in
`VERIFICATION.md` with the date and build hash. Breaking API changes are
documented in a migration table, never silently patched.

## Licence

CC-BY-4.0.
