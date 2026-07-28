"""T-23 - detect and correct a Bevel-before-Boolean stack, and show why."""
import bpy
import bmesh
import cadlib
import gates

ID = "T-23"
PRIORITY = "W-000"
TASK = ("Given a stack with Bevel before Boolean, detect the violation, "
        "correct it, and demonstrate that the order genuinely changes the "
        "result rather than being a style preference.")
RECIPES = ["W-000", "R-206", "R-203"]


def build(bevel_first):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=0.100)
    me = bpy.data.meshes.new("Block")
    bm.to_mesh(me)
    bm.free()
    block = bpy.data.objects.new("Block", me)
    bpy.context.scene.collection.objects.link(block)

    cb = bmesh.new()
    bmesh.ops.create_cone(cb, cap_ends=True, cap_tris=False, segments=48,
                          radius1=0.020, radius2=0.020, depth=0.200)
    cm = bpy.data.meshes.new("Cutter")
    cb.to_mesh(cm)
    cb.free()
    cutter = bpy.data.objects.new("Cutter", cm)
    bpy.context.scene.collection.objects.link(cutter)

    def add_bevel():
        b = block.modifiers.new(name="Bevel", type='BEVEL')
        b.width = 0.003
        b.segments = 4
        b.limit_method = 'ANGLE'
        b.use_clamp_overlap = True
        return b

    def add_boolean():
        m = block.modifiers.new(name="Boolean", type='BOOLEAN')
        m.operation = 'DIFFERENCE'
        m.solver = 'EXACT'
        m.object = cutter
        return m

    if bevel_first:
        add_bevel()
        add_boolean()
    else:
        add_boolean()
        add_bevel()
    return block


def sharp_edge_count(obj, threshold_deg=80.0):
    """Edges sharper than *threshold_deg*: a proxy for unbevelled cut edges."""
    import math
    bm = cadlib.evaluated_bmesh(obj)
    limit = math.radians(threshold_deg)
    n = sum(1 for e in bm.edges
            if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > limit)
    bm.free()
    return n


def run():
    # The wrong order, as briefed.
    wrong = build(bevel_first=True)
    wrong_ok, wrong_report = gates.check_stack_order(wrong)
    wrong_sharp = sharp_edge_count(wrong)

    # Correct it in place, preserving every modifier's settings.
    corrected_stack = gates.reorder_to_canonical(wrong)
    fixed_ok, fixed_report = gates.check_stack_order(wrong)
    fixed_sharp = sharp_edge_count(wrong)

    # An independently built correct stack, to confirm the reorder matches.
    right = build(bevel_first=False)
    right_sharp = sharp_edge_count(right)

    return [
        ("the briefed stack is detected as a hard violation",
         not wrong_ok and wrong_report["hard_violations"],
         f"stack={wrong_report['stack']} "
         f"violation={wrong_report['hard_violations'][0]['found'] if wrong_report['hard_violations'] else None}"),
        ("the violation is reported with a reason, not just a flag",
         bool(wrong_report["hard_violations"]
              and wrong_report["hard_violations"][0]["why"]),
         wrong_report["hard_violations"][0]["why"]
         if wrong_report["hard_violations"] else "no reason given"),
        ("reordering fixes the violation",
         fixed_ok and not fixed_report["hard_violations"],
         f"corrected stack={corrected_stack}"),
        ("Boolean now precedes Bevel",
         corrected_stack.index('BOOLEAN') < corrected_stack.index('BEVEL'),
         f"{corrected_stack}"),
        ("order genuinely changes the geometry (cut edges left sharp)",
         wrong_sharp != fixed_sharp,
         f"sharp edges: bevel-first={wrong_sharp}, boolean-first={fixed_sharp}"),
        ("the corrected stack matches an independently built correct one",
         fixed_sharp == right_sharp,
         f"corrected={fixed_sharp} independent={right_sharp}"),
    ]
