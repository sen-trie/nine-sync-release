#!/usr/bin/env python3
"""Checks for the MANUAL EXPERIMENTAL release path only. Stable releases use check_publish_gates.py,
which is unchanged and still requires every owner gate and an official-Blender validation.

    python packaging/check_experimental.py --dist dist --static dist/static-validation.json --tag v0.1.0-alpha.1

Requires: a prerelease tag (alpha/beta/rc), exactly one ZIP whose checksum matches the sidecar and the artifact
manifest, a clean parent tree, pinned 40-char commits, a passing static validation of this exact ZIP, and the
website and copyright gates. It does NOT require any Blender run.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG = re.compile(r"^v\d+\.\d+\.\d+-(alpha|beta|rc)\.\d+$")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", required=True)
    parser.add_argument("--static", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    problems = []
    if not TAG.match(args.tag):
        problems.append("tag %r is not a prerelease tag like v0.1.0-alpha.1" % args.tag)
    with open(os.path.join(ROOT, "packaging", "release_gates.json"), encoding="utf-8") as handle:
        gates = json.load(handle)
    for key in ("website_confirmed", "copyright_holder_confirmed"):
        if gates.get(key) is not True:
            problems.append("owner gate not confirmed: " + key)
    zips = glob.glob(os.path.join(args.dist, "nine-sync-*-blender-extensions.zip"))
    if len(zips) != 1:
        problems.append("expected exactly one bundled ZIP, found %d" % len(zips))
    else:
        with open(zips[0], "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        with open(zips[0] + ".sha256", encoding="utf-8") as handle:
            sidecar = handle.read().split()[0]
        with open(os.path.join(args.dist, "artifact-manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        with open(args.static, encoding="utf-8") as handle:
            static = json.load(handle)
        if sidecar != digest or manifest["sha256"] != digest:
            problems.append("checksum mismatch between ZIP, .sha256 and artifact manifest")
        if manifest["parent"]["dirty"]:
            problems.append("build came from a dirty parent tree")
        if not all(len(manifest[k]["commit"]) == 40 for k in ("core", "fx")):
            problems.append("Core/FX commits are not pinned")
        if static.get("failed") != 0 or static.get("sha256") != digest:
            problems.append("static validation failed or was run against a different ZIP")
    if problems:
        print("EXPERIMENTAL RELEASE REFUSED:\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 1
    print("experimental release checks passed (no Blender validation was required or run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
