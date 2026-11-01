#!/usr/bin/env python3
"""Fail-closed check run before the (draft) release is created.

    python packaging/check_publish_gates.py --dist dist --validation dist/blender-validation.json --static dist/static-validation.json

Passes only if: every owner gate in packaging/release_gates.json is true, static validation and the Blender
validation both passed on an official Blender >= 5.3 release build against this exact ZIP, and the artifact
manifest is clean and matches the ZIP checksum.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", required=True)
    parser.add_argument("--validation", required=True)
    parser.add_argument("--static", required=True)
    args = parser.parse_args()
    problems = []

    gates = json.load(open(os.path.join(ROOT, "packaging", "release_gates.json"), encoding="utf-8"))
    problems += ["owner gate not confirmed: %s" % k for k, v in gates.items() if not k.startswith("_") and v is not True]

    zips = glob.glob(os.path.join(args.dist, "nine-sync-*-blender-extensions.zip"))
    missing = [p for p in (os.path.join(args.dist, "artifact-manifest.json"), args.validation, args.static) if not os.path.isfile(p)]
    if len(zips) != 1:
        problems.append("expected exactly one bundled ZIP in %s, found %d" % (args.dist, len(zips)))
    elif missing:
        problems.append("missing required reports: %s" % ", ".join(missing))
    else:
        digest = hashlib.sha256(open(zips[0], "rb").read()).hexdigest()
        manifest = json.load(open(os.path.join(args.dist, "artifact-manifest.json"), encoding="utf-8"))
        if manifest["sha256"] != digest:
            problems.append("artifact manifest checksum does not match the ZIP")
        if manifest["parent"]["dirty"]:
            problems.append("build came from a dirty parent tree")
        static = json.load(open(args.static, encoding="utf-8"))
        if static.get("failed") != 0 or static.get("sha256") != digest:
            problems.append("static validation failed or was run against a different ZIP")
        blender = json.load(open(args.validation, encoding="utf-8"))
        if not blender.get("passed") or blender.get("zip_sha256") != digest:
            problems.append("Blender validation failed or was run against a different ZIP")
        if not blender.get("blender_official_release"):
            problems.append("Blender validation did not use an official release build")
        found = re.match(r"Blender (\d+)\.(\d+)", blender.get("blender_version", ""))
        if not found or (int(found.group(1)), int(found.group(2))) < (5, 3):
            problems.append("validated Blender version is not 5.3 or newer: %r" % blender.get("blender_version"))
    if problems:
        print("PUBLICATION REFUSED:\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 1
    print("all publication gates satisfied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
