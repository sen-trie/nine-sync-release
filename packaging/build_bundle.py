#!/usr/bin/env python3
"""Builds the combined NineSync Blender extension ZIP.

Standard library only. Inputs are the pinned Core and FX submodules plus the third-party
archives named in packaging/dependencies.lock (downloaded and checked against their SHA-256).

    python packaging/build_bundle.py [--out dist] [--staging build/staging] [--cache build/downloads]

Fails (non-zero, message on stderr) on: a dirty or unpinned submodule, a hash mismatch, a
missing licence file, or an unexpected archive layout. Output: the ZIP, <zip>.sha256 and
artifact-manifest.json. The ZIP is deterministic: same inputs give the same bytes.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
import urllib.request
import zipfile

BUILD_SCRIPT_VERSION = "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGING = os.path.join(ROOT, "packaging")
CHILDREN = {"core": "nine-sync-core", "fx": "nine-sync-fx"}
# Core and FX stay in their own package namespaces inside the combined extension.
CHILD_DEST = {"core": "ninesync_core", "fx": "ninesync_fx"}


class BuildError(Exception):
    pass


def fail(message):
    raise BuildError(message)


def git(*args, cwd=ROOT):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        fail("git %s failed in %s: %s" % (" ".join(args), os.path.basename(cwd), result.stderr.strip()))
    return result.stdout


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


# --- source state ---------------------------------------------------------------------------------

def check_sources(allow_dirty_parent):
    info = {}
    status = git("status", "--porcelain").splitlines()
    parent_dirty = [line for line in status if line.strip()]
    if parent_dirty and not allow_dirty_parent:
        fail("parent repository has uncommitted changes (commit them or use --allow-dirty-parent for a local test build):\n  "
             + "\n  ".join(parent_dirty))
    info["parent"] = {"commit": git("rev-parse", "HEAD").strip(), "dirty": bool(parent_dirty)}
    for key, folder in CHILDREN.items():
        path = os.path.join(ROOT, folder)
        if not os.path.isdir(path):
            fail("submodule %s is not checked out (git submodule update --init)" % folder)
        head = git("rev-parse", "HEAD", cwd=path).strip()
        pinned = git("ls-tree", "HEAD", folder).split()
        if len(pinned) < 3 or pinned[1] != "commit":
            fail("%s is not registered as a submodule in the parent repository" % folder)
        if pinned[2] != head:
            fail("%s is at %s but the parent pins %s; refusing to build an unpinned state" % (folder, head, pinned[2]))
        dirty = git("status", "--porcelain", cwd=path).splitlines()
        if dirty:
            fail("%s has uncommitted or untracked changes:\n  %s" % (folder, "\n  ".join(dirty)))
        info[key] = {"path": folder, "commit": head, "describe": git("describe", "--tags", "--always", cwd=path).strip()}
    return info


def read_toml(path):
    with open(path, "rb") as handle:
        return tomllib.load(handle)


def child_version(folder):
    """ADDON_VERSION tuple from the child's __init__.py, read without importing it (needs bpy)."""
    with open(os.path.join(ROOT, folder, "__init__.py"), encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("ADDON_VERSION"):
                return tuple(int(part) for part in line.split("=", 1)[1].strip().strip("()").replace(" ", "").split(",") if part)
    fail("no ADDON_VERSION in %s/__init__.py" % folder)


# --- exclusion patterns (same spirit as blender_manifest.toml paths_exclude_pattern) -------------------

def excluded(rel, patterns):
    parts = rel.split("/")
    for pattern in patterns:
        if pattern.endswith("/"):
            name = pattern.strip("/")
            if pattern.startswith("/"):
                if rel.startswith(name + "/"):
                    return True
            elif name in parts[:-1]:
                return True
        elif pattern.startswith("/"):
            name = pattern[1:]
            if rel == name or rel.startswith(name + "/") or fnmatch.fnmatch(rel, name):
                return True
        elif fnmatch.fnmatch(parts[-1], pattern) or fnmatch.fnmatch(rel, pattern):
            return True
    return False


# --- staging --------------------------------------------------------------------------------------

class Stage:
    def __init__(self, root):
        self.root = root
        self.files = {}  # relative path -> origin note

    def put(self, rel, data, origin):
        if rel in self.files:
            fail("duplicate file in the bundle: %s (%s and %s)" % (rel, self.files[rel], origin))
        target = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as handle:
            handle.write(data)
        self.files[rel] = origin


def stage_child(stage, key, folder):
    manifest = read_toml(os.path.join(ROOT, folder, "blender_manifest.toml"))
    patterns = manifest.get("build", {}).get("paths_exclude_pattern", [])
    listed = git("ls-files", "-z", cwd=os.path.join(ROOT, folder)).split("\0")
    count = 0
    for rel in sorted(p for p in listed if p):
        if rel == "blender_manifest.toml" or excluded(rel, patterns):
            continue
        if rel.startswith(".git") or rel == "CLAUDE.md":
            continue
        with open(os.path.join(ROOT, folder, *rel.split("/")), "rb") as handle:
            stage.put("%s/%s" % (CHILD_DEST[key], rel), handle.read(), folder)
        count += 1
    if count == 0:
        fail("nothing staged from %s" % folder)


def download(url, expected, cache):
    os.makedirs(cache, exist_ok=True)
    target = os.path.join(cache, expected + ".zip")
    if not (os.path.isfile(target) and sha256_file(target) == expected):
        request = urllib.request.Request(url, headers={"User-Agent": "nine-sync-release-build"})
        with urllib.request.urlopen(request, timeout=120) as response, open(target + ".part", "wb") as out:
            shutil.copyfileobj(response, out)
        os.replace(target + ".part", target)
    actual = sha256_file(target)
    if actual != expected:
        os.remove(target)
        fail("checksum mismatch for %s: expected %s, got %s" % (url, expected, actual))
    return target


def stage_dependency(stage, name, spec, cache):
    archive = download(spec["source_url"], spec["sha256"], cache)
    prefix = spec["strip_prefix"]
    wanted = set(spec["files"]) if "files" in spec else None
    patterns = spec.get("exclude", [])
    seen = set()
    with zipfile.ZipFile(archive) as bundle:
        for member in sorted(bundle.namelist()):
            if member.endswith("/"):
                continue
            if prefix and not member.startswith(prefix):
                fail("%s: unexpected archive layout (%s does not start with %s)" % (name, member, prefix))
            rel = member[len(prefix):]
            if ".." in rel.split("/") or rel.startswith("/"):
                fail("%s: unsafe path in archive: %s" % (name, member))
            if wanted is not None:
                if rel not in wanted:
                    continue
            elif excluded(rel, patterns):
                continue
            stage.put("%s/%s" % (spec["dest"], rel), bundle.read(member), "%s %s" % (name, spec["version"]))
            seen.add(rel)
    if wanted is not None and wanted != seen:
        fail("%s: archive lacks %s" % (name, sorted(wanted - seen)))
    for rel in spec.get("keep_licences", []):
        if rel not in seen and ("%s/%s" % (spec["dest"], rel)) not in stage.files:
            fail("%s: required licence/notice file missing: %s" % (name, rel))
    if "LICENSE" not in seen:
        fail("%s: no LICENSE in the vendored files" % name)
    return archive


IMPORTER_INIT = '''# DirectX .x importer vendored from io_directx_x %(version)s (%(repo)s), GPL-3.0-or-later.
# Only the import half is included. This module registers nothing, so it cannot collide with a standalone
# DirectX X Importer add-on. NineSync: FX calls import_x(context, filepath, **options).
from .importer import import_x  # noqa: F401

SOURCE_VERSION = "%(version)s"
'''


def notices(lock, child_info):
    lines = [
        "# Third-party notices",
        "",
        "NineSync (combined) is GPL-3.0-or-later. It contains the components below, each under its own licence.",
        "The full licence texts ship next to the code in the listed folders.",
        "",
        "| Component | Version | Licence | Folder in this package | Source |",
        "| --- | --- | --- | --- | --- |",
        "| NineSync: PMM Bridge | %s | GPL-3.0-or-later | ninesync_core/ | https://github.com/sen-trie/nine-sync-core (commit %s) |"
        % (".".join(map(str, child_info["core_version"])), child_info["core"]["commit"]),
        "| NineSync: FX Importer | %s | GPL-3.0-or-later | ninesync_fx/ | https://github.com/sen-trie/nine-sync-fx (commit %s) |"
        % (".".join(map(str, child_info["fx_version"])), child_info["fx"]["commit"]),
    ]
    for name, spec in lock["components"].items():
        lines.append("| %s | %s | %s | %s/ | %s (archive sha256 %s) |" % (
            name, spec["version"], spec["license"], spec["dest"], spec["upstream_repo"], spec["sha256"]))
    lines += [
        "",
        "mmd_tools is NOT part of this package. It is a separate extension the user installs; NineSync only calls it.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


# --- zip ------------------------------------------------------------------------------------------

def write_zip(stage, target, epoch):
    stamp = max(epoch, 315532800)  # ZIP cannot store dates before 1980
    import time
    date_time = time.gmtime(stamp)[:6]
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.exists(target):
        os.remove(target)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for rel in sorted(stage.files):
            with open(os.path.join(stage.root, *rel.split("/")), "rb") as handle:
                data = handle.read()
            entry = zipfile.ZipInfo(rel, date_time)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            entry.create_system = 3
            bundle.writestr(entry, data, compresslevel=9)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=os.path.join(ROOT, "dist"))
    parser.add_argument("--staging", default=os.path.join(ROOT, "build", "staging"))
    parser.add_argument("--cache", default=os.path.join(ROOT, "build", "downloads"))
    parser.add_argument("--allow-dirty-parent", action="store_true",
                        help="local test builds only; recorded as dirty in the artifact manifest")
    args = parser.parse_args(argv)

    info = check_sources(args.allow_dirty_parent)
    lock = json.load(open(os.path.join(PACKAGING, "dependencies.lock"), encoding="utf-8"))
    template = os.path.join(PACKAGING, "bundle")
    bundle_manifest = read_toml(os.path.join(template, "blender_manifest.toml"))
    version = bundle_manifest["version"]
    info["core_version"] = child_version(CHILDREN["core"])
    info["fx_version"] = child_version(CHILDREN["fx"])

    if os.path.isdir(args.staging):
        shutil.rmtree(args.staging)
    os.makedirs(args.staging)
    stage = Stage(args.staging)

    for key, folder in CHILDREN.items():
        stage_child(stage, key, folder)
    archives = {}
    for name, spec in lock["components"].items():
        archives[name] = stage_dependency(stage, name, spec, args.cache)

    spec = lock["components"]["io_directx_x"]
    stage.put(spec["dest"] + "/__init__.py",
              (IMPORTER_INIT % {"version": spec["version"], "repo": spec["upstream_repo"]}).encode("utf-8"), "build script")

    for name in ("blender_manifest.toml", "__init__.py"):
        with open(os.path.join(template, name), "rb") as handle:
            stage.put(name, handle.read(), "packaging/bundle")
    licence = open(os.path.join(ROOT, CHILDREN["core"], "LICENSE"), "rb").read()
    if licence != open(os.path.join(ROOT, CHILDREN["fx"], "LICENSE"), "rb").read():
        fail("Core and FX LICENSE files differ")
    stage.put("LICENSE", licence, "nine-sync-core")
    stage.put("THIRD_PARTY_NOTICES.md", notices(lock, info), "build script")

    epoch = int(git("log", "-1", "--format=%ct").strip())
    zip_name = "nine-sync-%s-blender-extensions.zip" % version
    target = os.path.join(args.out, zip_name)
    write_zip(stage, target, epoch)
    digest = sha256_file(target)
    with open(target + ".sha256", "w", encoding="utf-8", newline="\n") as handle:
        handle.write("%s  %s\n" % (digest, zip_name))

    manifest = {
        "artifact": zip_name,
        "sha256": digest,
        "size": os.path.getsize(target),
        "version": version,
        "extension_id": bundle_manifest["id"],
        "build_script_version": BUILD_SCRIPT_VERSION,
        "parent": info["parent"],
        "core": {**info["core"], "version": ".".join(map(str, info["core_version"]))},
        "fx": {**info["fx"], "version": ".".join(map(str, info["fx_version"]))},
        "dependencies": {name: {k: spec[k] for k in ("version", "license", "source_url", "sha256", "upstream_repo", "upstream_commit", "dest")}
                         for name, spec in lock["components"].items()},
        "file_count": len(stage.files),
        "source_date_epoch": epoch,
    }
    manifest_path = os.path.join(args.out, "artifact-manifest.json")
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("built %s (%d files)\nsha256 %s" % (target, len(stage.files), digest))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BuildError as error:
        print("BUILD FAILED: %s" % error, file=sys.stderr)
        sys.exit(1)
