#!/usr/bin/env python3
"""Downloads and verifies an official Blender build (Linux x64) and prints the path of its executable.

    python packaging/fetch_blender.py --version 5.3.0 --dest build/blender

The file must exist under https://download.blender.org/release/BlenderX.Y/ together with its
.sha256 file; if it does not, this fails. It never falls back to another version. Versions below 5.3.0 are refused.
"""
import argparse
import hashlib
import os
import shutil
import sys
import tarfile
import urllib.error
import urllib.request

BASE = "https://download.blender.org/release/Blender%d.%d/"


def get(url, target=None):
    request = urllib.request.Request(url, headers={"User-Agent": "nine-sync-release-build"})
    with urllib.request.urlopen(request, timeout=300) as response:
        if target is None:
            return response.read().decode("utf-8", "replace")
        with open(target, "wb") as out:
            shutil.copyfileobj(response, out)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="5.3.0")
    parser.add_argument("--dest", required=True)
    args = parser.parse_args()

    parts = tuple(int(p) for p in args.version.split("."))
    if len(parts) != 3 or parts < (5, 3, 0):
        sys.exit("refusing Blender %s: NineSync needs 5.3.0 or newer" % args.version)
    os.makedirs(args.dest, exist_ok=True)
    folder = BASE % parts[:2]
    name = "blender-%s-linux-x64.tar.xz" % args.version
    url = folder + name
    try:
        listing = get(folder + "blender-%s.sha256" % args.version)
    except urllib.error.HTTPError as error:
        sys.exit("no official Blender %s at %s (HTTP %s). Not substituting another version." % (args.version, folder, error.code))
    expected = next((l.split()[0] for l in listing.splitlines() if l.strip().endswith(name)), None)
    if not expected:
        sys.exit("%s is not listed in the official checksum file" % name)
    archive = os.path.join(args.dest, "blender.tar.xz")
    get(url, archive)
    actual = sha256_file(archive)
    if actual != expected:
        sys.exit("checksum mismatch for %s: expected %s, got %s" % (url, expected, actual))
    with tarfile.open(archive) as bundle:
        top = bundle.getnames()[0].split("/")[0]
        bundle.extractall(args.dest, filter="data")
    os.remove(archive)
    exe = os.path.join(args.dest, top, "blender")
    if not os.path.isfile(exe):
        sys.exit("blender executable not found after extraction")
    print("official=true", file=sys.stderr)
    print(exe)
    with open(os.path.join(args.dest, "official.txt"), "w") as handle:
        handle.write("true")


if __name__ == "__main__":
    main()
