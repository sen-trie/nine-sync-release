#!/usr/bin/env python3
"""Builds pilot-locale test ZIPs and runs blender_i18n_smoke.py against them in throwaway profiles.

    python -I packaging/run_i18n_smoke.py --blender <path> --zip dist/nine-sync-<v>-blender-extensions.zip [--out build/i18n-smoke]

Test ZIPs are copies of the combined release ZIP and of standalone Core/FX built from their committed HEADs, with
each translations.py recompiled with --include-fuzzy so the unreviewed pilot locale is present. They are written
under --out and are never release artifacts. Modes: bundled, core, fx, mixed (combined next to standalone Core).
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import i18n_tool  # noqa: E402
import validate_in_blender as vib  # noqa: E402

COMPILED_IN_BUNDLE = {"release": "translations.py", "core": "ninesync_core/i18n/translations.py",
                      "fx": "ninesync_fx/i18n/translations.py"}


def fuzzy_module(domain):
    cfg = i18n_tool.load_config()
    return i18n_tool.render_compiled(domain, i18n_tool.domain_paths(cfg, domain), include_fuzzy=True).encode("utf-8")


def tooltip_samples():
    """Per domain, the ja_JP entries the catalog marks as tooltips (property, operator and enum item descriptions)."""
    cfg = i18n_tool.load_config()
    found = {}
    for domain in cfg["domains"]:
        paths = i18n_tool.domain_paths(cfg, domain)
        po = os.path.join(paths["locales"], "ja_JP.po")
        if not os.path.exists(po):
            continue
        _, entries = i18n_tool.parse_po(i18n_tool.read_text(po), po)
        found[domain] = [[e.ctx, e.msgid, e.msgstr] for e in entries
                         if not e.obsolete and e.msgstr and "tooltip" in e.kinds and "%" not in e.msgid]
    return found


def bundle_test_zip(source, target):
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as dst:
        replaced = {path: fuzzy_module(domain) for domain, path in COMPILED_IN_BUNDLE.items()}
        for info in src.infolist():
            data = replaced.get(info.filename, src.read(info.filename))
            dst.writestr(info, data)


def standalone_test_zip(blender, repo, domain, out, env):
    work = tempfile.mkdtemp(prefix="i18n-%s-" % domain, dir=out)
    archive = subprocess.run(["git", "-C", os.path.join(ROOT, repo), "archive", "HEAD"], capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(work, filter="data")
    with open(os.path.join(work, "i18n", "translations.py"), "wb") as handle:
        handle.write(fuzzy_module(domain))
    built = os.path.join(out, "zips-" + domain)
    os.makedirs(built, exist_ok=True)
    code, text = vib.run([blender, "--factory-startup", "--command", "extension", "build", "--source-dir", work,
                          "--output-dir", built], env)
    zips = [f for f in os.listdir(built) if f.endswith(".zip")]
    if code != 0 or len(zips) != 1:
        raise SystemExit("standalone %s build failed:\n%s" % (domain, text[-800:]))
    return os.path.join(built, zips[0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender", required=True)
    parser.add_argument("--zip", required=True)
    parser.add_argument("--out", default=os.path.join(ROOT, "build", "i18n-smoke"))
    parser.add_argument("--cache", default=os.path.join(ROOT, "build", "downloads"))
    args = parser.parse_args()
    out = os.path.abspath(args.out)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    base_env = dict(os.environ, BLENDER_USER_RESOURCES=os.path.join(out, "profile-build"))
    bundle = os.path.join(out, "bundle-pilot.zip")
    bundle_test_zip(os.path.abspath(args.zip), bundle)
    core = standalone_test_zip(args.blender, "nine-sync-core", "core", out, base_env)
    fx = standalone_test_zip(args.blender, "nine-sync-fx", "fx", out, base_env)
    samples_path = os.path.join(out, "tooltip-samples.json")
    with open(samples_path, "w", encoding="utf-8") as handle:
        json.dump(tooltip_samples(), handle, ensure_ascii=False, indent=2)
    mmd_zip, _ = vib.fetch_mmd_tools(args.cache)
    installs = {"bundled": [bundle], "core": [core], "fx": [fx], "mixed": [bundle, core]}
    summary = {}
    for mode, zips in installs.items():
        env = dict(os.environ, BLENDER_USER_RESOURCES=os.path.join(out, "profile-" + mode))
        for path in [mmd_zip] + zips:
            code, text = vib.run([args.blender, "--factory-startup", "--command", "extension", "install-file", "-r",
                                  "user_default", path], env)
            if code != 0:
                raise SystemExit("install of %s failed:\n%s" % (path, text[-800:]))
        report = os.path.join(out, "report-%s.json" % mode)
        code, text = vib.run([args.blender, "-b", "--factory-startup", "--python-exit-code", "1", "--python",
                              os.path.join(HERE, "blender_i18n_smoke.py"), "--", mode, report, samples_path], env, timeout=600)
        print("\n".join(l for l in text.splitlines() if l.startswith("I18N")))
        summary[mode] = {"exit": code, "report": os.path.relpath(report, ROOT)}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps(summary, indent=2))
    return 0 if all(v["exit"] == 0 for v in summary.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
