"""T-22 - a brief with no units must trigger a question, not an assumption."""
import os
import re
import bpy
import bmesh
import cadlib

ID = "T-22"
PRIORITY = "W-000"
TASK = ("Given a brief that omits units, confirm the skill instructs asking "
        "rather than defaulting, and show what the wrong assumption costs.")
RECIPES = ["W-000"]

ROOT = os.getcwd()
CORE = os.path.join(ROOT, "skills", "blender-cad-core", "SKILL.md")

# The brief as the user would give it: a number with no unit anywhere.
BRIEF = {"purpose": "fabrication", "part_size": 40.0, "unit": None}


def run():
    with open(CORE, encoding="utf-8") as fh:
        core = fh.read()

    # --- contract half: the instruction must exist and be unambiguous ------
    has_ask_rule = bool(re.search(
        r"ask\s*[-—]?\s*do not guess|ask, do not guess|\*\*ask", core, re.I))
    phase0_asks_units = bool(re.search(
        r"tolerance and nominal unit", core, re.I))
    says_scrap = bool(re.search(r"scrap|not a fixable draft", core, re.I))

    # --- consequence half: show why guessing is not recoverable ------------
    # The same bare number 40.0 interpreted as mm vs m.
    def build(scale):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, verts=bm.verts,
                        vec=(BRIEF["part_size"] * scale,) * 3)
        me = bpy.data.meshes.new("P")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new("P", me)
        bpy.context.scene.collection.objects.link(ob)
        return cadlib.diagnose(ob, check_self_intersect=False)["dimensions"][0]

    as_mm = build(0.001)   # 40 mm  -> 0.040 m
    as_m = build(1.0)      # 40 m   -> 40.0 m
    ratio = as_m / as_mm

    return [
        ("Phase 0 explicitly asks for tolerance and nominal unit",
         phase0_asks_units, "core SKILL.md Phase 0 interview table"),
        ("the skill instructs asking rather than assuming",
         has_ask_rule, "found the 'ask, do not guess' rule in W-000 Phase 0"),
        ("the skill states a wrong tolerance assumption is unrecoverable",
         says_scrap,
         "W-000 Phase 0 calls such a model scrap rather than a fixable draft"),
        ("guessing the unit costs a factor of 1000, not a rounding error",
         abs(ratio - 1000.0) < 0.01,   # float32 vertex storage
         f"same brief '40' -> {as_mm:.3f} m if mm, {as_m:.1f} m if m "
         f"(x{ratio:.0f})"),
        ("no silent default of metres is offered anywhere in Phase 0",
         "default to metres" not in core.lower()
         and "assume metres" not in core.lower(),
         "core SKILL.md contains no instruction to default the unit"),
    ]
