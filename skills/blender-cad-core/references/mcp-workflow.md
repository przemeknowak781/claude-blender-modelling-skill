---
title: Blender Lab MCP server — verified tool list and working cycle
blender_version: "5.2"
verified_on: "2026-07-28"
source: "projects.blender.org/lab/blender_mcp @ 98b0e49d (2026-05-05)"
verification_status: "tool names read from add-on source; live socket session NOT exercised"
---

# MCP workflow

## Provenance

The tool names below were read from the add-on's own source tree
(`mcp/blmcp/tools/*.py`) at commit `98b0e49d`, **not** copied from any README
or from another MCP project. Anything this project did not exercise is marked.

- Upstream: <https://projects.blender.org/lab/blender_mcp>
- Product page: <https://www.blender.org/lab/mcp-server/>
- Add-on manifest declares `blender_version_min = "5.1.0"`. **The manifest does
  not state an upper bound**, and this project did not run the add-on against
  5.2 in a live session (see `VERIFICATION.md` → Environment for why).
  Treat 5.2 compatibility as *expected but unverified*, and confirm it in your
  own environment before relying on it.

## Architecture

Two processes over a TCP socket: a Blender add-on that executes requests inside
a running Blender, and an MCP server process launched by the MCP client. Both
must be running; the add-on must be installed **and enabled** or every tool
fails.

## The 20 tools

| Tool | Use in a CAD workflow |
| --- | --- |
| `execute_blender_code` | the workhorse; runs Python inside the live session |
| `get_objects_summary` | collection hierarchy and objects — **always the first call** |
| `get_object_detail_summary` | one object's detail; use before mutating it |
| `get_blendfile_summary_datablocks` | data-block counts, workspace, render engine |
| `get_blendfile_summary_path_info` | path, save status, age, backups |
| `get_blendfile_summary_missing_files` | broken external references |
| `get_blendfile_summary_of_linked_libraries` | linked library tree |
| `get_blendfile_summary_usage_guess` | scored guess at the file's purpose |
| `search_api_docs` | **ground API names here before writing them** |
| `get_python_api_docs` | full API page for a symbol |
| `search_manual_docs` | user-manual search |
| `get_screenshot_of_window_as_image` | whole-window PNG |
| `get_screenshot_of_area_as_image` | single-area PNG |
| `get_screenshot_of_window_as_json` | window layout, active object, selection |
| `render_viewport_to_path` | render with current settings |
| `render_thumbnail_to_path` | fast low-quality check |
| `jump_to_tab_by_name` | switch workspace by name |
| `jump_to_tab_by_space_type` | switch workspace by editor type |
| `jump_to_view3d_object_by_name` | focus the viewport on an object |
| `jump_to_view3d_object_data_by_name` | focus by data-block name |

Note what is **absent**: there is no modelling tool, no "add cube", no
"boolean". Every geometric operation goes through `execute_blender_code`. This
skill's recipes are what you send through it.

## The cycle: inspect → ground → mutate → verify

```python
# 1. INSPECT — never assume a name exists
#    get_objects_summary()  ->  {"Collection": ["Blob", "CTRL-Tray", ...]}

# 2. GROUND — confirm the API before writing it
#    search_api_docs("solidify modifier thickness")

# 3. MUTATE — smallest change that advances the task
mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
mod.solidify_mode = 'NON_MANIFOLD'
mod.thickness = 0.018

# 4. VERIFY — a number, not the absence of an exception
import cadlib
rep = cadlib.diagnose(obj)
assert rep["manifold"], rep
assert rep["self_intersecting_faces"] == 0, rep
```

**Do not report success because nothing raised.** Antipattern 8. The failure
modes that matter here — wrong thickness, wrong units, self-intersection,
a modifier silently doing nothing — all complete without an exception.

## Degradation: no MCP server

Emit a standalone script and give the user the command:

```bash
blender --background --factory-startup --python part.py
```

Every recipe in this skill is written to work this way. Scripts must not depend
on GUI state, must not call `time.sleep`, and must not loop on `bpy.ops`.
Anything that renders additionally needs a GL context; in a headless container
set `LIBGL_ALWAYS_SOFTWARE=1` and install `libegl1` and `libgl1-mesa-dri`
(this is how test T-24 renders here).

## Safety

The add-on's own `weak_sandbox.py` says:

> Weak sandbox for LLM-generated code execution. Note that this isn't really a
> sandbox, more guidance that some things should not be done. […] If the LLM
> (or its user) is motivated these can be worked around.

So: it blocks `sys.exit()` and similar accidents. It does **not** stop file
deletion, network access, or overwriting the user's work. Treat
`execute_blender_code` as a shell with the user's privileges:

- Save the file before anything destructive.
- Never call `bpy.ops.wm.read_homefile` or `bpy.ops.wm.quit_blender` without
  explicit consent.
- Never touch paths outside the project directory.
- Do verification runs in a container on synthetic files.
