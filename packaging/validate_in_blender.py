#!/usr/bin/env python3
"""Installs the combined ZIP into an isolated Blender profile and runs the smoke test.

    python packaging/validate_in_blender.py --blender <path> --zip dist/<zip> --report dist/blender-validation.json [--official]

--official records that this Blender came from download.blender.org/release (the workflow sets it).
Steps: refuse Blender < 5.3; `extension validate`; install-file into a throwaway profile; smoke test
inside Blender; check the install folder was not changed by use; `extension remove`; check it is gone.
The profile is a temp folder passed as BLENDER_USER_RESOURCES, never the user's own.
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
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ID = "ninesync_bundled"
MMD_ID = "mmd_tools"
ROOT = os.path.dirname(HERE)


# The external mmd_tools extension the combined build requires, fetched from the pinned test fixture and
# checked against its SHA-256. It is installed into the throwaway profile only; it is never part of the ZIP.
def fetch_mmd_tools(cache):
    with open(os.path.join(HERE, "test_fixtures.lock"), encoding="utf-8") as handle:
        spec = json.load(handle)["mmd_tools"]
    os.makedirs(cache, exist_ok=True)
    target = os.path.join(cache, spec["sha256"] + ".zip")
    digest = lambda path: hashlib.sha256(open(path, "rb").read()).hexdigest()
    if not (os.path.isfile(target) and digest(target) == spec["sha256"]):
        request = urllib.request.Request(spec["source_url"], headers={"User-Agent": "nine-sync-release-build"})
        with urllib.request.urlopen(request, timeout=120) as response, open(target + ".part", "wb") as out:
            shutil.copyfileobj(response, out)
        os.replace(target + ".part", target)
    if digest(target) != spec["sha256"]:
        os.remove(target)
        raise SystemExit("checksum mismatch for mmd_tools test fixture")
    return target, spec["version"]


def run(cmd, env, timeout=900):
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout, errors="replace")
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def tree_hash(folder):
    digest = hashlib.sha256()
    for base, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            path = os.path.join(base, name)
            digest.update(os.path.relpath(path, folder).replace(os.sep, "/").encode())
            with open(path, "rb") as handle:
                digest.update(hashlib.sha256(handle.read()).digest())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender", required=True)
    parser.add_argument("--zip", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--mmd-tools-zip", help="mmd_tools extension ZIP to install as the external dependency (default: the pinned test fixture)")
    parser.add_argument("--cache", default=os.path.join(ROOT, "build", "downloads"))
    args = parser.parse_args()
    zip_path = os.path.abspath(args.zip)
    steps = []

    def step(name, ok, detail=""):
        steps.append({"step": name, "ok": bool(ok), "detail": detail})
        print("%s  %s%s" % ("PASS" if ok else "FAIL", name, (" -- " + detail) if detail and not ok else ""), flush=True)
        return ok

    profile = tempfile.mkdtemp(prefix="ninesync_profile_")
    env = dict(os.environ, BLENDER_USER_RESOURCES=profile)
    for name in ("BLENDER_USER_CONFIG", "BLENDER_USER_SCRIPTS", "BLENDER_USER_EXTENSIONS", "BLENDER_USER_DATAFILES"):
        env.pop(name, None)
    base = [args.blender, "-b", "--factory-startup"]
    with open(zip_path, "rb") as handle:
        zip_sha = hashlib.sha256(handle.read()).hexdigest()
    if args.mmd_tools_zip:
        mmd_zip, mmd_version = os.path.abspath(args.mmd_tools_zip), "custom"
    else:
        mmd_zip, mmd_version = fetch_mmd_tools(args.cache)
    report = {"mmd_tools_fixture_version": mmd_version, "zip": os.path.basename(zip_path), "zip_sha256": zip_sha, "steps": steps}
    exit_code = 1
    try:
        code, out = run([args.blender, "--version"], env)
        match = re.search(r"Blender (\d+)\.(\d+)\.(\d+)[^\n]*", out)
        version = tuple(int(x) for x in match.groups()) if match else (0, 0, 0)
        report["blender_version"] = match.group(0).strip() if match else out.strip()[:80]
        hash_match = re.search(r"build hash: (\w+)", out)
        report["blender_build_hash"] = hash_match.group(1) if hash_match else ""
        report["blender_official_release"] = bool(args.official)
        if step("Blender >= 5.3.0 (%s)" % report["blender_version"], version >= (5, 3, 0)):
            code, out = run(base + ["--command", "extension", "validate", zip_path], env)
            step("blender extension validate", code == 0 and "Error" not in out, out.strip()[-400:])
            code, out = run(base + ["--command", "extension", "install-file", "-r", "user_default", zip_path], env)
            install = os.path.join(profile, "extensions", "user_default", PKG_ID)
            step("extension install-file", code == 0 and os.path.isdir(install), out.strip()[-400:])
            code, out = run(base + ["--command", "extension", "install-file", "-r", "user_default", mmd_zip], env)
            mmd_install = os.path.join(profile, "extensions", "user_default", MMD_ID)
            step("external mmd_tools installs (test fixture, not part of the ZIP)", code == 0 and os.path.isdir(mmd_install), out.strip()[-400:])
            if os.path.isdir(install) and os.path.isdir(mmd_install):
                before = tree_hash(install)
                mmd_before = tree_hash(mmd_install)
                smoke = os.path.join(profile, "smoke.json")
                code, out = run(base + ["--python-exit-code", "1", "--python", os.path.join(HERE, "blender_smoke.py"), "--", smoke], env)
                lines = [l for l in out.splitlines() if l.startswith("SMOKE")]
                print("\n".join(lines))
                failing = "\n".join(l for l in lines if " FAIL " in l)
                step("smoke test inside Blender", code == 0 and os.path.isfile(smoke), failing or out.strip()[-600:])
                if os.path.isfile(smoke):
                    with open(smoke, encoding="utf-8") as handle:
                        report["smoke"] = json.load(handle)
                step("install folder unchanged by use (ignoring __pycache__)", tree_hash(install) == before)
                step("mmd_tools install folder unchanged by NineSync", tree_hash(mmd_install) == mmd_before)
                code, out = run(base + ["--command", "extension", "remove", PKG_ID], env)
                step("extension remove deletes the install folder", code == 0 and not os.path.isdir(install), out.strip()[-300:])
                step("removing NineSync leaves mmd_tools installed and unchanged", os.path.isdir(mmd_install) and tree_hash(mmd_install) == mmd_before)
        report["passed"] = bool(steps) and all(s["ok"] for s in steps)
        exit_code = 0 if report["passed"] else 1
    finally:
        shutil.rmtree(profile, ignore_errors=True)
        report.setdefault("passed", False)
        with open(args.report, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
