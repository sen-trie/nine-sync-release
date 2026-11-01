#!/usr/bin/env python3
"""Assembles and verifies the self-hosted Blender extension repository (GitHub Pages).

    python packaging/extension_repo.py assemble --zip dist/nine-sync-X-blender-extensions.zip \
        --artifact-manifest dist/artifact-manifest.json --base-url https://<owner>.github.io/<repo>/ \
        --blender <official blender 5.3+> --out site
    python packaging/extension_repo.py verify --zip dist/nine-sync-X-blender-extensions.zip --base-url <same url>

assemble: downloads every version already served at BASE/index.json (each checked against the hash the index
advertises), adds the new ZIP, and lets Blender's own `extension server-generate` write index.json (and the
html listing). It refuses pre-release versions, a changed ZIP under an existing version, and a version that is not
newer than the newest one already served. Nothing is uploaded; the workflow publishes the `--out` directory.

verify: fetches the PUBLIC index.json and ZIP over HTTPS and checks that they list and serve exactly the local ZIP.
Standard library only (Python 3.11+ for tomllib).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import zipfile

AGENT = {"User-Agent": "nine-sync-release-build"}
VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


class RepoError(Exception):
    pass


def fail(message):
    raise RepoError(message)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url, allow_missing=False):
    if not url.startswith("https://"):
        fail("refusing non-HTTPS URL: %s" % url)
    request = urllib.request.Request(url, headers=AGENT)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if allow_missing and error.code == 404:
            return None
        fail("GET %s failed: HTTP %d" % (url, error.code))
    except urllib.error.URLError as error:
        fail("GET %s failed: %s" % (url, error.reason))


def normalise_base(url):
    if not url.startswith("https://") or "<" in url or "example" in url:
        fail("base URL must be a real https:// URL, got %r" % url)
    return url if url.endswith("/") else url + "/"


def version_tuple(text):
    found = VERSION.match(text)
    if not found:
        fail("version %r is not a plain MAJOR.MINOR.PATCH release version (pre-releases never enter the stable repository)" % text)
    return tuple(int(part) for part in found.groups())


def zip_manifest(path):
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n == "blender_manifest.toml"]
        if not names:
            fail("%s has no blender_manifest.toml at its root" % path)
        return tomllib.loads(archive.read("blender_manifest.toml").decode("utf-8"))


def read_index(base):
    raw = fetch(base + "index.json", allow_missing=True)
    if raw is None:
        return []
    try:
        data = json.loads(raw.decode("utf-8"))["data"]
    except (ValueError, KeyError) as error:
        fail("existing index.json at %s is not a valid repository index: %s" % (base, error))
    return data


def assemble(args):
    base = normalise_base(args.base_url)
    new_zip = os.path.abspath(args.zip)
    manifest = zip_manifest(new_zip)
    ext_id, version = manifest["id"], manifest["version"]
    new_version = version_tuple(version)
    digest = sha256_file(new_zip)

    if args.artifact_manifest:
        recorded = json.load(open(args.artifact_manifest, encoding="utf-8"))
        if recorded["sha256"] != digest or recorded["version"] != version or recorded["extension_id"] != ext_id:
            fail("artifact manifest does not describe %s" % new_zip)

    out = os.path.abspath(args.out)
    if os.path.exists(out):
        fail("output directory %s already exists" % out)
    os.makedirs(out)

    kept = []
    for entry in read_index(base):
        if entry.get("id") != ext_id:
            fail("existing repository serves a different extension id %r; refusing to mix" % entry.get("id"))
        name = os.path.basename(urllib.parse.urlparse(entry["archive_url"]).path)
        data = fetch(urllib.parse.urljoin(base, entry["archive_url"]))
        if "sha256:" + sha256_bytes(data) != entry["archive_hash"] or len(data) != entry["archive_size"]:
            fail("served %s does not match the hash its own index advertises; refusing to republish it" % name)
        old = version_tuple(entry["version"])
        if old == new_version:
            if sha256_bytes(data) != digest:
                fail("version %s is already published with different content; bump the version instead" % version)
            continue  # identical re-deploy
        if old > new_version:
            fail("version %s is older than the already published %s" % (version, entry["version"]))
        with open(os.path.join(out, name), "wb") as handle:
            handle.write(data)
        kept.append(entry["version"])

    target = os.path.join(out, os.path.basename(new_zip))
    shutil.copyfile(new_zip, target)
    open(os.path.join(out, ".nojekyll"), "w").close()

    profile = tempfile.mkdtemp(prefix="nine-sync-repo-profile-")
    env = dict(os.environ, BLENDER_USER_RESOURCES=profile)
    try:
        result = subprocess.run([args.blender, "--factory-startup", "--background", "--command", "extension",
                                 "server-generate", "--repo-dir", out, "--html"],
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    print(result.stdout.strip()[-1500:])
    if result.returncode != 0 or not os.path.isfile(os.path.join(out, "index.json")):
        fail("blender extension server-generate failed (exit %d)" % result.returncode)

    index = json.load(open(os.path.join(out, "index.json"), encoding="utf-8"))["data"]
    versions = sorted(e["version"] for e in index)
    expected = sorted(kept + [version])
    if versions != expected:
        fail("generated index lists %s, expected %s" % (versions, expected))
    for entry in index:
        path = os.path.join(out, os.path.basename(entry["archive_url"]))
        if not os.path.isfile(path) or entry["archive_hash"] != "sha256:" + sha256_file(path):
            fail("generated index entry %s does not match its file" % entry["version"])
    print("assembled %s: versions %s" % (out, ", ".join(expected)))
    return 0


def verify(args):
    base = normalise_base(args.base_url)
    manifest = zip_manifest(args.zip)
    digest = sha256_file(args.zip)
    problem = "no attempt made"
    for attempt in range(1, args.attempts + 1):
        try:
            entries = [e for e in read_index(base) if e.get("id") == manifest["id"] and e.get("version") == manifest["version"]]
            if len(entries) != 1:
                fail("public index.json does not list %s %s exactly once" % (manifest["id"], manifest["version"]))
            entry = entries[0]
            if entry["archive_hash"] != "sha256:" + digest:
                fail("public index advertises a different hash than the release ZIP")
            url = urllib.parse.urljoin(base, entry["archive_url"])
            data = fetch(url)
            if sha256_bytes(data) != digest:
                fail("public ZIP %s differs from the release ZIP" % url)
            print("verified %s\n  index  %sindex.json\n  zip    %s\n  sha256 %s" % (manifest["version"], base, url, digest))
            return 0
        except RepoError as error:
            problem = str(error)
            print("attempt %d/%d: %s" % (attempt, args.attempts, problem), file=sys.stderr)
            if attempt < args.attempts:
                time.sleep(args.delay)
    fail("public repository verification failed: %s" % problem)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("assemble")
    a.add_argument("--zip", required=True)
    a.add_argument("--artifact-manifest")
    a.add_argument("--base-url", required=True)
    a.add_argument("--blender", required=True)
    a.add_argument("--out", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--zip", required=True)
    v.add_argument("--base-url", required=True)
    v.add_argument("--attempts", type=int, default=12)
    v.add_argument("--delay", type=int, default=15)
    args = parser.parse_args()
    return assemble(args) if args.command == "assemble" else verify(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RepoError as error:
        print("EXTENSION REPOSITORY: %s" % error, file=sys.stderr)
        sys.exit(1)
