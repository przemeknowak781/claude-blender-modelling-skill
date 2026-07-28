"""T-99 - the skill must be able to say "Blender does not do this"."""
import json
import os
import re
import subprocess

ID = "T-99"
PRIORITY = "NEG"
TASK = ("Confirm the skill refuses impossible CAD requests by name instead of "
        "inventing an operator, and that no identifier anywhere is fabricated.")
RECIPES = ["D-99"]

ROOT = os.getcwd()
DIAG = os.path.join(ROOT, "skills", "blender-cad-diagnostics", "SKILL.md")
CORE = os.path.join(ROOT, "skills", "blender-cad-core", "SKILL.md")
DUMP = os.path.join(ROOT, "skills", "blender-cad-core", "references",
                    "api_dump.json")

# Each impossible request, and a phrase that must appear near it.
IMPOSSIBLE = [
    ("B-rep fillet", r"B-rep fillet"),
    ("native STEP/IGES", r"STEP\s*/\s*IGES"),
    ("sketch constraint solver", r"constraint solver"),
    ("feature history with rollback", r"feature history"),
    ("associative dimensions", r"[Aa]ssociative dimensions"),
    ("assembly mates", r"[Aa]ssembly mates"),
    ("GD&T tolerances", r"GD&T|[Gg]eometric tolerance"),
    ("G-code / tool paths", r"G-code|tool paths"),
    ("class-A G2 surfacing", r"[Cc]lass-A"),
]


def run():
    with open(DIAG, encoding="utf-8") as fh:
        diag = fh.read()
    with open(CORE, encoding="utf-8") as fh:
        core = fh.read()

    out = []

    missing = [name for name, pat in IMPOSSIBLE
               if not re.search(pat, diag)]
    out.append(("D-99 names every impossible request explicitly",
                not missing,
                f"missing from D-99: {missing}" if missing
                else f"all {len(IMPOSSIBLE)} listed"))

    # Each row must offer a real alternative, not just a refusal.
    d99 = diag.split("### D-99")[-1] if "### D-99" in diag else ""
    rows = [ln for ln in d99.splitlines()
            if ln.strip().startswith("|") and ln.count("|") >= 4]
    body = [r for r in rows if "---" not in r and "Request" not in r]
    with_alternative = [r for r in body if r.rstrip().rstrip("|").split("|")[-1].strip()]
    out.append(("every refusal offers a concrete alternative workflow",
                len(body) >= len(IMPOSSIBLE) and len(with_alternative) == len(body),
                f"{len(with_alternative)}/{len(body)} rows carry a workaround"))

    # The specific trap: a Bevel node that does not exist in 5.2.
    with open(DUMP, encoding="utf-8") as fh:
        dump = json.load(fh)
    bevel_absent = "__error__" in dump["nodes"].get("GeometryNodeBevel", {})
    documented = "no Bevel node in Geometry Nodes 5.2" in core
    out.append(("the absent Bevel node is proven absent AND documented",
                bevel_absent and documented,
                f"dump records: "
                f"{dump['nodes'].get('GeometryNodeBevel', {}).get('__error__')!r}"))

    # The hallucination control: zero unknown identifiers across the repo.
    proc = subprocess.run(
        ["python3", os.path.join(ROOT, "tools", "validate_identifiers.py")],
        capture_output=True, text=True, cwd=ROOT)
    out.append(("identifier validator reports zero unknown identifiers",
                proc.returncode == 0 and "OK: 0 unknown identifiers" in proc.stdout,
                proc.stdout.strip().splitlines()[-1] if proc.stdout else "no output"))

    # A refusal must not be softened into a fake capability.
    forbidden = re.findall(r"bpy\.ops\.\w+\.(?:fillet|step_import|iges_import|"
                           r"constraint_solve|dimension_add)\b", diag + core)
    out.append(("no invented operator is offered as a workaround",
                not forbidden, f"found {forbidden}" if forbidden else "none"))

    return out
