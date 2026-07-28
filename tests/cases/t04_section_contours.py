"""T-04 - extract closed section contours at 12 heights."""
import bpy
import bmesh
import math
import cadlib

ID = "T-04"
PRIORITY = "P1"
TASK = ("Extract section contours at 12 heights through a solid and confirm "
        "each is a closed loop of the expected length.")
RECIPES = ["R-216", "R-409"]

N_LEVELS = 12
RADIUS = 0.5
HEIGHT = 1.0


def section_loops(obj, z):
    """Bisect a copy of the mesh at plane z and return the resulting loops.

    Returns a list of (vertex_count, total_length) per closed loop.
    """
    bm = cadlib.evaluated_bmesh(obj)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(
        bm, geom=geom, dist=1e-7,
        plane_co=(0.0, 0.0, z), plane_no=(0.0, 0.0, 1.0),
        clear_inner=True, clear_outer=True,
    )
    cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]

    # Walk the cut edges into connected loops.
    remaining = set(cut_edges)
    loops = []
    while remaining:
        edge = remaining.pop()
        comp = [edge]
        stack = [edge]
        while stack:
            e = stack.pop()
            for v in e.verts:
                for ne in v.link_edges:
                    if ne in remaining:
                        remaining.discard(ne)
                        comp.append(ne)
                        stack.append(ne)
        verts = {v for e in comp for v in e.verts}
        length = sum(e.calc_length() for e in comp)
        # A closed loop has as many edges as vertices.
        loops.append((len(comp) == len(verts), length))
    bm.free()
    return loops


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # A 64-sided cylinder: circumference is known analytically.
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=64,
                          radius1=RADIUS, radius2=RADIUS, depth=HEIGHT)
    me = bpy.data.meshes.new("Cyl")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("Cyl", me)
    bpy.context.scene.collection.objects.link(obj)

    # 12 levels strictly inside the cylinder, avoiding the end caps.
    zs = [-HEIGHT / 2 + HEIGHT * (i + 1) / (N_LEVELS + 1) for i in range(N_LEVELS)]
    results = [section_loops(obj, z) for z in zs]

    n_curves = sum(len(r) for r in results)
    all_closed = all(closed for r in results for closed, _ in r)

    # A regular 64-gon inscribed in radius R has perimeter 2*n*R*sin(pi/n).
    expected_len = 2 * 64 * RADIUS * math.sin(math.pi / 64)
    total_len = sum(length for r in results for _, length in r)
    expected_total = expected_len * N_LEVELS
    len_err = abs(total_len - expected_total) / expected_total

    return [
        ("exactly 12 contours produced",
         n_curves == N_LEVELS, f"{n_curves} contours from {N_LEVELS} levels"),
        ("every contour is a closed loop",
         all_closed, f"closed={[c for r in results for c, _ in r]}"),
        ("total length matches independent calculation within 0.1%",
         len_err < 0.001,
         f"expected={expected_total:.6f} actual={total_len:.6f} "
         f"({len_err * 100:.4f}%)"),
    ]
