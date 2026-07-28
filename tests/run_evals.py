#!/usr/bin/env python3
"""Acceptance suite for the blender-cad skill.

Each case runs in its own headless Blender process so one crash cannot mask or
contaminate another. Every assertion is numeric; no case passes on "no
exception was raised".

Usage:
    python3 tests/run_evals.py                 # all cases
    python3 tests/run_evals.py --only T-01 T-03
    python3 tests/run_evals.py --blender /path/to/blender
    python3 tests/run_evals.py --json report.json
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES_DIR = os.path.join(HERE, "cases")
FIXTURES = os.path.join(HERE, "fixtures")

GREEN, RED, YELLOW, DIM, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
)


def find_blender(explicit=None):
    cand = explicit or os.environ.get("BLENDER") or shutil.which("blender")
    if not cand:
        sys.exit("Blender not found. Pass --blender or set $BLENDER.")
    return cand


def blender_version(blender):
    out = subprocess.run([blender, "--version"], capture_output=True, text=True).stdout
    first = out.strip().splitlines()[0] if out.strip() else "unknown"
    hashline = next((l.strip() for l in out.splitlines() if "build hash" in l), "")
    return first, hashline


def ensure_fixtures(blender):
    marker = os.path.join(FIXTURES, "marching_cubes_blob.blend")
    if os.path.exists(marker):
        return
    print("Generating fixtures (first run only)...")
    subprocess.run(
        [blender, "--background", "--factory-startup", "--python",
         os.path.join(FIXTURES, "make_fixtures.py"), "--", FIXTURES],
        check=True, capture_output=True,
    )


def run_case(blender, case_path, tmpdir, verbose=False):
    out_json = os.path.join(tmpdir, os.path.basename(case_path) + ".json")
    cmd = [blender, "--background", "--factory-startup", "--python",
           os.path.join(HERE, "_run_case.py"), "--", case_path, out_json]
    started = time.time()
    # Cases that render need a GL context. In a headless container there is no
    # GPU, so force Mesa's software path; harmless when a GPU is present.
    env = dict(os.environ)
    env.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT,
                          env=env)
    elapsed = time.time() - started

    if not os.path.exists(out_json):
        return {
            "id": os.path.basename(case_path).split("_")[0].upper(),
            "file": os.path.basename(case_path),
            "task": "", "priority": "", "assertions": [],
            "error": f"case produced no output (exit {proc.returncode})\n"
                     f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}",
            "seconds": elapsed,
        }
    with open(out_json) as fh:
        result = json.load(fh)
    result["seconds"] = elapsed
    if verbose:
        result["stdout"] = proc.stdout[-4000:]
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender")
    ap.add_argument("--only", nargs="*", default=None,
                    help="case IDs to run, e.g. T-01 T-99")
    ap.add_argument("--json", help="write the full report here")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    blender = find_blender(args.blender)
    version, build = blender_version(blender)
    print(f"Blender: {version}  {build}")
    ensure_fixtures(blender)

    cases = sorted(
        os.path.join(CASES_DIR, f)
        for f in os.listdir(CASES_DIR)
        if f.endswith(".py") and not f.startswith("_")
    )
    if args.only:
        wanted = {w.upper().replace("_", "-") for w in args.only}
        cases = [
            c for c in cases
            if os.path.basename(c).split("_")[0].upper().replace("T", "T-", 1) in wanted
            or os.path.basename(c).split("_")[0].upper() in wanted
        ]
    if not cases:
        sys.exit("No cases matched.")

    results = []
    tmpdir = tempfile.mkdtemp(prefix="blender-cad-evals-")
    try:
        for path in cases:
            res = run_case(blender, path, tmpdir, args.verbose)
            results.append(res)

            n_pass = sum(1 for a in res["assertions"] if a["passed"])
            n_all = len(res["assertions"])
            ok = res["error"] is None and n_all > 0 and n_pass == n_all
            tag = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
            print(f"{tag} {res['id']:<6} {res['priority']:<3} "
                  f"{n_pass}/{n_all:<3} {res['seconds']:6.1f}s  {res['task'][:64]}")
            for a in res["assertions"]:
                if not a["passed"]:
                    print(f"       {RED}x{RESET} {a['name']}: {a['detail']}")
            if res["error"]:
                print(f"       {RED}ERROR{RESET}\n{DIM}{res['error'][-1500:]}{RESET}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    total = len(results)
    passed = sum(
        1 for r in results
        if r["error"] is None and r["assertions"]
        and all(a["passed"] for a in r["assertions"])
    )
    n_assert = sum(len(r["assertions"]) for r in results)
    print(f"\n{'-' * 72}\n{passed}/{total} cases passed "
          f"({n_assert} assertions total)")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"blender": version, "build": build,
                       "cases": results, "passed": passed, "total": total},
                      fh, indent=1)
        print(f"Report: {args.json}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
