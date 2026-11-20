#!/usr/bin/env python3
# Generates zensical/docs/changelog.md from the changelogs of the release repo, Core and FX, so the manual never keeps a copy that can
# drift. Run it from anywhere: python packaging/build_changelog.py [--check]
# A version is "released" when its component has a v<version> tag or it is not newer than the version the latest bundled
# release includes; anything else is shown as upcoming. Dates come from the tag, or from the commit that added the version
# heading to the component's CHANGELOG.md.

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "zensical" / "docs" / "changelog.md"
SCRIPT_VERSION = 1
COMPONENTS = (
    ("core", "Core", ROOT / "nine-sync-core"),
    ("fx", "FX", ROOT / "nine-sync-fx"),
)
CATEGORIES = ("Features", "Improvements", "Compatibility", "Fixes")
RULES = (
    (
        "Fixes",
        re.compile(r"^(fix|fixes|fixed|repair|correct)\b|\b(no longer|bug)\b", re.I),
    ),
    (
        "Compatibility",
        re.compile(
            r"^(support|compatib|require|minimum|rigify|blender 5)|\bcompatib", re.I
        ),
    ),
    (
        "Improvements",
        re.compile(
            r"^(faster|speed|lower|less|reduce|keep|cut|skip|share|incremental|build memory|clean up|rearrange)",
            re.I,
        ),
    ),
)


def git(path, *args):
    try:
        done = subprocess.run(
            ("git", "-C", str(path)) + args, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return done.stdout.strip()


def version_key(text):
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def parse(path):
    entries, current = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        heading = re.match(
            r"^##\s+\[?(\d+\.\d+\.\d+)\]?\s*(?:[-–]\s*(\d{4}-\d{2}-\d{2}))?\s*$", raw
        )
        if heading:
            current = {
                "version": heading.group(1),
                "date": heading.group(2),
                "lines": [],
            }
            entries.append(current)
        elif current is not None and raw.strip():
            current["lines"].append(raw.rstrip())
    return entries


def bundled_pins(entries):
    pins = {}
    if not entries:
        return pins
    for line in entries[0]["lines"]:
        found = re.search(r"\((Core|FX)\)\s*\[(\d+\.\d+\.\d+)\]", line)
        if found:
            pins[found.group(1).lower()] = found.group(2)
    return pins


def date_of(repo, version):
    tag = "v" + version
    if git(repo, "tag", "-l", tag):
        stamp = git(repo, "log", "-1", "--format=%as", tag)
        if stamp:
            return stamp, True
    stamp = git(
        repo, "log", "-S## " + version, "--format=%as", "--", "CHANGELOG.md"
    ).splitlines()
    return (stamp[-1] if stamp else ""), False


def categorise(text):
    for name, rule in RULES:
        if rule.search(text):
            return name
    return "Features"


def bullets(lines):
    items = []
    for line in lines:
        if re.match(r"^\s*[-*]\s+", line):
            items.append(
                [re.sub(r"^\s*[-*]\s+", "", line), len(line) - len(line.lstrip())]
            )
        elif items:
            items[-1][0] += " " + line.strip()
    return items


def shown(version):
    return version[:-2] if version.endswith(".0") else version


def date_line(entry):
    return "[%s]" % (entry["date"] or "Unreleased")


def render_entry(kind, label, entry, released, dated, bundled_in, repo_url):
    title = "%s %s" % (label, shown(entry["version"]))
    out = ['## %s {.cl-h data-comp="%s"}' % (title, kind), ""]
    groups = {name: [] for name in CATEGORIES}
    for text, indent in bullets(entry["lines"]):
        name = categorise(text) if indent == 0 else None
        if name is None:
            groups[last].append("    " * 1 + "- " + text)
            continue
        last = name
        groups[name].append("- " + text)
    for name in CATEGORIES:
        if groups[name]:
            out += ["**%s**" % name, ""] + groups[name] + [""]
    return out


def main(check=False):
    root_entries = parse(ROOT / "CHANGELOG.md")
    pins = bundled_pins(root_entries)
    records = []
    for entry in root_entries:
        stamp = git(
            ROOT,
            "log",
            "-S## [%s]" % entry["version"],
            "--format=%as",
            "--",
            "CHANGELOG.md",
        ).splitlines()
        tag = "v" + entry["version"]
        tagged = git(ROOT, "log", "-1", "--format=%as", tag) if git(ROOT, "tag", "-l", tag) else ""
        entry["date"] = entry["date"] or tagged or (stamp[-1] if stamp else "")
        records.append(("bundle", "Bundled release", entry, True, ""))
    for kind, label, repo in COMPONENTS:
        pinned = pins.get(kind)
        bundled_by = {}
        for release in root_entries:
            for line in release["lines"]:
                found = re.search(r"\((Core|FX)\)\s*\[(\d+\.\d+\.\d+)\]", line)
                if found and found.group(1).lower() == kind:
                    bundled_by.setdefault(found.group(2), release["version"])
        for entry in parse(repo / "CHANGELOG.md"):
            stamp, tagged = date_of(repo, entry["version"])
            entry["date"] = entry["date"] or stamp
            released = tagged or bool(
                pinned and version_key(entry["version"]) <= version_key(pinned)
            )
            records.append(
                (kind, label, entry, released, bundled_by.get(entry["version"], ""))
            )
    records.sort(
        key=lambda r: (
            r[2]["date"] or "9999",
            r[0] == "bundle",
            version_key(r[2]["version"]),
        ),
        reverse=True,
    )
    lines = [
        "<!-- Generated by packaging/build_changelog.py (v%d). Do not edit by hand. -->"
        % SCRIPT_VERSION,
        "",
        "# Changelog",
        '<div class="cl-filter" id="cl-filter"></div>',
        "",
    ]
    for kind, label, entry, released, bundled_in in records:
        if kind == "bundle":
            lines += render_bundle(entry)
        else:
            lines += render_entry(kind, label, entry, released, True, bundled_in, "")
    text = "\n".join(lines).rstrip() + "\n"
    if check:
        return (
            0 if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") == text else 1
        )
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s (%d entries)" % (OUTPUT.relative_to(ROOT), len(records)))
    return 0


def render_bundle(entry):
    out = ['## Bundled %s {.cl-h data-comp="bundle"}' % shown(entry["version"]), ""]
    for line in entry["lines"]:
        if line.startswith("###"):
            out += ["", "**%s**" % line.lstrip("# ").strip(), ""]
        else:
            out.append(re.sub(r"\[(\d+\.\d+)\.0\]", r"[\g<1>]", line))
    out.append("")
    return out


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
