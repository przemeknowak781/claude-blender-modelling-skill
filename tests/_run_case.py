"""Inner runner: executed inside Blender, runs one case module, writes JSON.

Not called directly — see tests/run_evals.py.
Usage: blender --background --factory-startup --python tests/_run_case.py -- <case.py> <out.json>
"""
import importlib.util
import json
import os
import sys
import traceback

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    case_path, out_path = argv[0], argv[1]

    spec = importlib.util.spec_from_file_location("case_mod", case_path)
    mod = importlib.util.module_from_spec(spec)

    result = {
        "id": os.path.basename(case_path).split("_")[0].upper(),
        "file": os.path.basename(case_path),
        "task": "",
        "priority": "",
        "assertions": [],
        "error": None,
    }
    try:
        spec.loader.exec_module(mod)
        result["id"] = getattr(mod, "ID", result["id"])
        result["task"] = getattr(mod, "TASK", "")
        result["priority"] = getattr(mod, "PRIORITY", "")
        result["recipes"] = getattr(mod, "RECIPES", [])
        for name, passed, detail in mod.run():
            result["assertions"].append(
                {"name": name, "passed": bool(passed), "detail": str(detail)}
            )
    except Exception:
        result["error"] = traceback.format_exc()

    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=1)


main()
