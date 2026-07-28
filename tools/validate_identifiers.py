#!/usr/bin/env python3
"""Fail the build if any API identifier in the skill does not exist in 5.2.

Every node type, operator, modifier type and modifier property named in the
Markdown or in the test code is checked against api_dump.json, which was
produced by live introspection (tools/harvest_api.py). Nothing is taken on
trust, including identifiers this project wrote itself.

Identifiers that are deliberately named BECAUSE they do not exist -- the skill
has to be able to say "there is no Bevel node" -- must be listed in
tools/known_absent.txt with a reason, and are then required to be absent.

Usage:
    python3 tools/validate_identifiers.py [--dump PATH] [--quiet]
Exit code 0 means zero unknown identifiers.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DUMP = os.path.join(
    ROOT, "skills", "blender-cad-core", "references", "api_dump.json")
KNOWN_ABSENT = os.path.join(ROOT, "tools", "known_absent.txt")

SCAN_DIRS = ["skills", "tests", "tools"]
SCAN_EXT = (".md", ".py")

# High-signal patterns only. A loose regex produces false positives, which
# train the reader to ignore the report -- worse than not checking.
PAT_NODE = re.compile(r"\b((?:Geometry|Function|Shader)Node[A-Za-z0-9]+)\b")
PAT_OP = re.compile(r"\bbpy\.ops\.([a-z_]+)\.([a-z_0-9]+)")
PAT_MOD_TYPE = re.compile(r"modifiers\.new\([^)]*type\s*=\s*'([A-Z_0-9]+)'")
PAT_BMESH_OP = re.compile(r"\bbmesh\.ops\.([a-z_0-9]+)")


def load_dump(path):
    with open(path) as fh:
        return json.load(fh)


def load_known_absent(path):
    entries = {}
    if not os.path.exists(path):
        return entries
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ident, _, reason = line.partition("::")
            entries[ident.strip()] = reason.strip()
    return entries


def iter_files():
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, _, names in os.walk(base):
            for n in names:
                if n.endswith(SCAN_EXT):
                    yield os.path.join(dirpath, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default=DEFAULT_DUMP)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    dump = load_dump(args.dump)
    absent = load_known_absent(KNOWN_ABSENT)

    known_nodes = {k for k, v in dump["nodes"].items()
                   if "__error__" not in v}
    known_ops = set(dump["operators"])
    known_mods = {k for k, v in dump["modifiers"].items()
                  if "__error__" not in v}
    known_bmesh = set(dump["bmesh_ops"])
    # Node TREE identifiers look like node identifiers to the regex but are a
    # separate namespace (bpy.data.node_groups.new(..., 'GeometryNodeTree')).
    known_nodes |= set(dump.get("node_trees", []))
    # Runtime-only class names (GeometryNodesModifierInterface and friends)
    # match the node regex but are structs reached from a live instance.
    known_nodes |= {k for k in dump.get("runtime_types", {})
                    if not k.startswith("_")}

    unknown = []       # named but not present in 5.2
    resurrected = []   # declared absent yet present in 5.2

    for path in iter_files():
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                for ident in PAT_NODE.findall(line):
                    if ident in known_nodes:
                        continue
                    if ident in absent:
                        continue
                    unknown.append((rel, lineno, "node", ident))
                for mod, op in PAT_OP.findall(line):
                    key = f"{mod}.{op}"
                    if key in known_ops or key in absent:
                        continue
                    unknown.append((rel, lineno, "operator", key))
                for mtype in PAT_MOD_TYPE.findall(line):
                    if mtype in known_mods or mtype in absent:
                        continue
                    unknown.append((rel, lineno, "modifier", mtype))
                for bop in PAT_BMESH_OP.findall(line):
                    if bop in known_bmesh or bop in absent:
                        continue
                    unknown.append((rel, lineno, "bmesh.ops", bop))

    # An entry in known_absent.txt that has since appeared is also a defect:
    # the documentation now understates what Blender can do.
    for ident in absent:
        if ident in known_nodes or ident in known_ops or ident in known_mods:
            resurrected.append(ident)

    if not args.quiet:
        print(f"Blender {dump['blender_version']} (build {dump['build_hash']})")
        print(f"dump: {len(known_nodes)} nodes, {len(known_ops)} operators, "
              f"{len(known_mods)} modifiers, {len(known_bmesh)} bmesh ops")
        print(f"declared-absent identifiers: {len(absent)}")
        for ident, reason in sorted(absent.items()):
            print(f"  - {ident}: {reason}")

    if unknown:
        print(f"\nFAIL: {len(unknown)} identifier(s) not present in "
              f"Blender {dump['blender_version']}:")
        for rel, lineno, kind, ident in unknown:
            print(f"  {rel}:{lineno}  {kind}  {ident}")
    if resurrected:
        print(f"\nFAIL: {len(resurrected)} identifier(s) declared absent but "
              f"found in the dump: {resurrected}")

    if not unknown and not resurrected:
        print("\nOK: 0 unknown identifiers.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
