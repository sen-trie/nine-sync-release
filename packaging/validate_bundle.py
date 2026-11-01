#!/usr/bin/env python3
"""Static validation of the combined NineSync ZIP (no Blender needed).

    python packaging/validate_bundle.py dist/nine-sync-<version>-blender-extensions.zip [--report report.json]

Checks structure, manifest, version consistency, licence files, pinned dependencies, hooks identity,
syntax, nesting-safe imports, duplicate Blender identifiers and leaked private data.
Env NINESYNC_PRIVATE_TERMS (comma separated) adds local strings that must not appear (kept out of the repo).
"""
import argparse
import ast
import collections
import fnmatch
import hashlib
import io
import json
import os
import re
import sys
import tomllib
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN_PARTS = {".git", "__pycache__", "tests", "docs", "debug-src", ".github", ".vscode", ".venv", "src_private"}
FORBIDDEN_NAMES = ("CLAUDE.md", ".gitignore", ".env", "*.pyc", "*.pem", "*.key", "id_rsa*", "credentials*", "*.pmm.bak")
# 'src' is excluded for Core only; the combined package must not contain Core's src folder.
FORBIDDEN_PREFIXES = ("ninesync_core/src/",)
PRIVATE_PATTERNS = [
    re.compile(rb"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"']+", re.I),
    re.compile(rb"/home/[a-z][a-z0-9_-]+/"),
    re.compile(rb"/Users/[A-Za-z][A-Za-z0-9_.-]+/"),
    re.compile(rb"[A-Za-z]:[\\/]+Projects-D", re.I),
]
# Generic placeholders that are fine inside third-party code and docs.
PRIVATE_ALLOW = (b"C:\\Users\\Public", b"/Users/name/", b"/Users/username/", b"/home/user/", b"/home/username/", b"/home/name/",
                 b"C:\\Users\\username", b"C:\\Users\\user\\", b"C:\\Users\\name\\", b"C:/Users/username", b"C:\\Users\\<")
TEXT_SUFFIXES = (".py", ".toml", ".md", ".txt", ".json", ".yml", ".yaml", ".cfg", ".lock")


def is_text(name):
    return name.endswith(TEXT_SUFFIXES) or name.rsplit("/", 1)[-1] in ("LICENSE", "NOTICE")


class Report:
    def __init__(self):
        self.results = []

    def check(self, name, ok, detail=""):
        self.results.append({"check": name, "ok": bool(ok), "detail": detail})
        print("%s  %s%s" % ("PASS" if ok else "FAIL", name, (" -- " + detail) if detail and not ok else ""))
        return ok

    @property
    def failed(self):
        return [r for r in self.results if not r["ok"]]


def tuple_from(source, name):
    match = re.search(r"^%s\s*=\s*\(([^)]*)\)" % name, source, re.M)
    return tuple(int(p) for p in match.group(1).replace(" ", "").split(",") if p) if match else None


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("zip")
    parser.add_argument("--report")
    parser.add_argument("--lock", default=os.path.join(ROOT, "packaging", "dependencies.lock"))
    args = parser.parse_args(argv)
    rep = Report()

    path = os.path.abspath(args.zip)
    bundle = zipfile.ZipFile(path)
    names = sorted(n for n in bundle.namelist() if not n.endswith("/"))
    data = {n: bundle.read(n) for n in names}
    lock = json.load(open(args.lock, encoding="utf-8"))

    rep.check("zip integrity", bundle.testzip() is None)
    rep.check("manifest at ZIP root", "blender_manifest.toml" in data and "__init__.py" in data)
    manifest = tomllib.loads(data["blender_manifest.toml"].decode("utf-8")) if "blender_manifest.toml" in data else {}

    # --- manifest
    rep.check("manifest: required fields", all(manifest.get(k) for k in
              ("schema_version", "id", "version", "name", "tagline", "maintainer", "type", "blender_version_min", "license", "website")),
              str(sorted(manifest)))
    rep.check("manifest: id is ninesync_bundled", manifest.get("id") == "ninesync_bundled")
    rep.check("manifest: blender_version_min >= 5.3.0",
              tuple(int(p) for p in str(manifest.get("blender_version_min", "0")).split(".")) >= (5, 3, 0))
    rep.check("manifest: SPDX GPL-3.0-or-later", manifest.get("license") == ["SPDX:GPL-3.0-or-later"])
    rep.check("manifest: permissions explain files", bool(manifest.get("permissions", {}).get("files")))
    rep.check("manifest: no network permission claimed", "network" not in manifest.get("permissions", {}))
    rep.check("manifest: copyright present", bool(manifest.get("copyright")))
    rep.check("manifest: tagline <= 64 chars", len(manifest.get("tagline", "")) <= 64 and not manifest.get("tagline", "").endswith("."))
    rep.check("manifest: permission reasons <= 64 chars, no trailing period",
              all(len(v) <= 64 and not v.endswith(".") for v in manifest.get("permissions", {}).values()))
    rep.check("manifest: no build section leaked", "build" not in manifest)

    # --- layout
    top = {n.split("/")[0] for n in names}
    rep.check("top-level layout", top <= {"blender_manifest.toml", "__init__.py", "LICENSE", "THIRD_PARTY_NOTICES.md",
                                          "ninesync_core", "ninesync_fx"}, str(sorted(top)))
    bad = [n for n in names if (set(n.split("/")[:-1]) & FORBIDDEN_PARTS) or n.startswith(FORBIDDEN_PREFIXES)
           or any(fnmatch.fnmatch(n.split("/")[-1], p) for p in FORBIDDEN_NAMES)]
    rep.check("no developer-only, cache or credential files", not bad, str(bad[:10]))
    rep.check("no nested blender_manifest.toml", [n for n in names if n.endswith("blender_manifest.toml") and n != "blender_manifest.toml"] == [])
    rep.check("mmd_tools is not bundled (external dependency)",
              not [n for n in names if n.startswith("third_party/") or "/mmd_tools/" in "/" + n or n.startswith("mmd_tools/")], "")
    core_link = data.get("ninesync_core/sync/mmd_tools_link.py", b"").decode("utf-8")
    rep.check("Core validates the external mmd_tools (version and API)",
              "MMD_TOOLS_MIN_VERSION" in core_link and "REQUIRED_API" in core_link and "def mmd_tools_status" in core_link)
    rep.check("bundle entry point does not register mmd_tools",
              b"mmd_tools" not in re.sub(rb"(?m)^\s*#.*$", b"", data.get("__init__.py", b"")))
    rep.check("no duplicate paths", len(names) == len(set(names)))

    # --- versions
    core_v = tuple_from(data.get("ninesync_core/__init__.py", b"").decode("utf-8"), "ADDON_VERSION")
    fx_v = tuple_from(data.get("ninesync_fx/__init__.py", b"").decode("utf-8"), "ADDON_VERSION")
    bundle_v = tuple_from(data.get("__init__.py", b"").decode("utf-8"), "BUNDLE_VERSION")
    rep.check("bundle bl_info is set at register time", b"bl_info = dict(BL_INFO)" in data.get("__init__.py", b""))
    man_v = tuple(int(p) for p in str(manifest.get("version", "0")).split(".")) if manifest.get("version") else None
    rep.check("versions: Core, FX and bundle found", None not in (core_v, fx_v, bundle_v, man_v), str((core_v, fx_v, bundle_v, man_v)))
    if None not in (core_v, fx_v, bundle_v, man_v):
        rep.check("versions: manifest == BUNDLE_VERSION", man_v == bundle_v)
        rep.check("versions: Core and FX share major.minor with the bundle", core_v[:2] == fx_v[:2] == man_v[:2], str((core_v, fx_v, man_v)))
    rep.check("versions: bl_info follows ADDON_VERSION in components",
              all(re.search(r'"version":\s*ADDON_VERSION', data.get(p, b"").decode("utf-8")) for p in
                  ("ninesync_core/__init__.py", "ninesync_fx/__init__.py")))
    expected_name = "nine-sync-%s-blender-extensions.zip" % manifest.get("version")
    rep.check("file name matches version", os.path.basename(path) == expected_name, os.path.basename(path))

    # --- checksum + artifact manifest next to the zip
    sidecar = path + ".sha256"
    actual = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if os.path.isfile(sidecar):
        rep.check("checksum file matches", open(sidecar, encoding="utf-8").read().split()[0] == actual)
    else:
        rep.check("checksum file exists", False, sidecar)
    amf = os.path.join(os.path.dirname(path), "artifact-manifest.json")
    if os.path.isfile(amf):
        am = json.load(open(amf, encoding="utf-8"))
        rep.check("artifact manifest: sha256 and version", am.get("sha256") == actual and am.get("version") == manifest.get("version"))
        rep.check("artifact manifest: clean pinned commits",
                  all(len(am.get(k, {}).get("commit", "")) == 40 for k in ("core", "fx")) and not am.get("parent", {}).get("dirty"),
                  "parent dirty" if am.get("parent", {}).get("dirty") else "")
        rep.check("artifact manifest: dependencies equal the lock",
                  all(am.get("dependencies", {}).get(n, {}).get("sha256") == s["sha256"] and am["dependencies"][n]["version"] == s["version"]
                      for n, s in lock["components"].items()))
    else:
        rep.check("artifact manifest exists", False, amf)

    # --- licences and dependencies
    for required in ("LICENSE", "THIRD_PARTY_NOTICES.md", "ninesync_core/LICENSE", "ninesync_fx/LICENSE",
                     "ninesync_fx/x_importer_bundled/LICENSE"):
        rep.check("licence file: " + required, required in data and len(data[required]) > 500 or required.endswith("NOTICE.txt") and required in data)
    rep.check("GPL text in root LICENSE", b"GNU GENERAL PUBLIC LICENSE" in data.get("LICENSE", b"") and b"Version 3" in data.get("LICENSE", b""))
    rep.check("dependency lock lists only the .x importer", sorted(lock["components"]) == ["io_directx_x"], str(sorted(lock["components"])))
    iox = lock["components"]["io_directx_x"]
    importer_files = sorted(n for n in names if n.startswith("ninesync_fx/x_importer_bundled/"))
    rep.check("x importer: exact file set", [n.rsplit("/", 1)[1] for n in importer_files] == sorted(["__init__.py"] + iox["files"]),
              str(importer_files))
    importer_src = data.get("ninesync_fx/x_importer_bundled/importer.py", b"").decode("utf-8")
    try:
        tree = ast.parse(importer_src)
        has_import_x = any(isinstance(n, ast.FunctionDef) and n.name == "import_x" for n in tree.body)
        args_ok = has_import_x and [a.arg for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "import_x" for a in n.args.args][:2] == ["context", "filepath"]
    except SyntaxError:
        has_import_x = args_ok = False
    rep.check("x importer: import_x(context, filepath, ...) contract", has_import_x and args_ok)
    init_src = data.get("ninesync_fx/x_importer_bundled/__init__.py", b"").decode("utf-8")
    rep.check("x importer: registers nothing", "register" not in init_src.replace("registers nothing", "") and "bpy" not in init_src)

    # --- hooks identity
    core_hooks, fx_hooks = data.get("ninesync_core/hooks.py"), data.get("ninesync_fx/hooks.py")
    rep.check("hooks.py identical in Core and FX", core_hooks is not None and core_hooks == fx_hooks)
    rep.check("hooks API_VERSION == 1", b"API_VERSION = 1" in (core_hooks or b""))

    # --- syntax, imports, identifiers
    syntax_errors, absolute_imports = [], []
    idnames = collections.defaultdict(list)
    for name in names:
        if not name.endswith(".py"):
            continue
        try:
            tree = ast.parse(data[name], filename=name)
        except SyntaxError as error:
            syntax_errors.append("%s: %s" % (name, error))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots = [node.module.split(".")[0]]
            else:
                roots = []
            if any(r in ("mmd_tools", "ninesync", "ninesync_fx", "ninesync_core", "x_importer_bundled", "io_directx_x") for r in roots):
                absolute_imports.append("%s:%d" % (name, node.lineno))
            if isinstance(node, ast.ClassDef):
                for stmt in node.body:
                    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)
                            and stmt.targets[0].id == "bl_idname" and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)):
                        kind = next((b.attr if isinstance(b, ast.Attribute) else getattr(b, "id", "") for b in node.bases), "")
                        idnames[(stmt.value.value, "Operator" if kind in ("Operator", "OperatorType") else "other" if kind not in ("Panel", "Menu", "Header") else kind)].append(name)
    rep.check("all Python files parse", not syntax_errors, "; ".join(syntax_errors[:3]))
    rep.check("no absolute imports of moved packages (nesting-safe)", not absolute_imports, str(absolute_imports[:5]))
    dupes = {k: v for k, v in idnames.items() if len(v) > 1}
    rep.check("no duplicate bl_idname per kind", not dupes, str({k: v for k, v in list(dupes.items())[:5]}))
    rep.check("no sys.path / sys.modules injection in NineSync code", not [
        n for n in names if n.endswith(".py") and n.split("/")[0] in ("ninesync_core", "ninesync_fx") and not n.endswith("__init__.py")
        and re.search(rb"sys\.path\.(append|insert)|sys\.modules\[[^\]]+\]\s*=", data[n])], "")

    # --- private data
    terms = [t.strip().lower().encode() for t in os.environ.get("NINESYNC_PRIVATE_TERMS", "").split(",") if t.strip()]
    leaks = []
    for name in names:
        if not is_text(name):
            continue
        blob = data[name]
        for pattern in PRIVATE_PATTERNS:
            for match in pattern.finditer(blob):
                if not any(a in match.group(0) or match.group(0) in a for a in PRIVATE_ALLOW):
                    leaks.append("%s: %r" % (name, match.group(0)[:60]))
        low = blob.lower()
        leaks += ["%s: private term" % name for t in terms if t in low]
    rep.check("no absolute local paths or private terms in text files", not leaks, "; ".join(leaks[:5]))
    binaries = [n for n in names if not is_text(n)]
    rep.check("binary files are expected types", all(n.endswith((".bmp", ".blend", ".pmm", ".png", ".dat")) for n in binaries), str([n for n in binaries][:10]))

    summary = {"zip": os.path.basename(path), "sha256": actual, "passed": len(rep.results) - len(rep.failed),
               "failed": len(rep.failed), "checks": rep.results}
    if args.report:
        with open(args.report, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(summary, handle, indent=2)
            handle.write("\n")
    print("\n%d passed, %d failed" % (summary["passed"], summary["failed"]))
    return 1 if rep.failed else 0


if __name__ == "__main__":
    sys.exit(main())
