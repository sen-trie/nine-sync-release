#!/usr/bin/env python3
"""Draft release notes for NineSync Bundled, built only from published facts.

    python -I packaging/release_notes.py draft --artifact-manifest dist/artifact-manifest.json --version v0.3.1 --out notes.md
    python -I packaging/release_notes.py finalize --version 0.3.1 --date 2026-12-01      # edits CHANGELOG.md

What goes in, and where it comes from:
  * Core / FX: the entries of every *published* component version after the one in the previous published Bundled
    release, up to the one in this build. They are read from the component's own CHANGELOG.md at the release commit,
    so unreleased entries cannot appear. Each bullet is condensed to its first sentence; nothing is written that is
    not in a changelog. A version without a changelog section is reported as missing, never filled in.
  * Bundled-specific changes (packaging, installation, integration): the `## [Unreleased]` section of this
    repository's CHANGELOG.md, verbatim, plus factual bundled-dependency version changes from the artifact manifests.
  * Baseline: the artifact-manifest.json of the previous published (non-draft) Bundled release. If there is none, or it
    has no manifest, the notes say so instead of guessing.

The result is a DRAFT: the release workflow only creates a draft GitHub release from it, and a person publishes.
`finalize` (run by hand once a release is authorised) moves `[Unreleased]` under the new version and keeps history.

Standard library only.
"""
import argparse
import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update_components as uc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")
HEADING = re.compile(r"^##\s+\[?(Unreleased|v?\d+\.\d+\.\d+[^\]\s]*)\]?(?:\s*[-–(].*)?$", re.I)
BULLET_LIMIT = 220
BODY_LIMIT = 60000


# --- changelog parsing ----------------------------------------------------------------------------------------

def parse_changelog(text):
    """{'unreleased': [bullets], (X, Y, Z): [bullets]}. Bullets keep wrapped lines joined; sub-headings are kept as bullets' group."""
    sections, current, bullet = {}, None, None
    for line in text.splitlines():
        match = HEADING.match(line.strip()) if line.startswith("## ") else None
        if line.startswith("## "):
            bullet = None
            if match:
                name = match.group(1)
                current = "unreleased" if name.lower() == "unreleased" else uc.parse_tag(name)
                if current is not None:
                    sections.setdefault(current, [])
            else:
                current = None
            continue
        if current is None:
            continue
        stripped = line.strip()
        if re.match(r"^[-*]\s+", stripped):
            bullet = re.sub(r"^[-*]\s+", "", stripped)
            sections[current].append(bullet)
            bullet = len(sections[current]) - 1
        elif stripped and bullet is not None and line[:1] in " \t":
            sections[current][bullet] += " " + stripped
        elif not stripped:
            bullet = None
    return sections


def condense(bullet):
    first = re.split(r"(?<=[.!?])\s+(?=[A-Z`])", bullet.strip(), maxsplit=1)[0]
    return first if len(first) <= BULLET_LIMIT else first[:BULLET_LIMIT - 1].rstrip() + "…"


def in_range(sections, old, new):
    """Published versions v with old < v <= new that the changelog covers; sections above `new` are unreleased."""
    return sorted((v for v in sections if v != "unreleased" and old < v <= new), reverse=True)


# --- baseline: previous published Bundled release ---------------------------------------------------------------

def previous_release(api, bundled, exclude_tag=None):
    """(release, artifact-manifest dict) of the newest published non-draft release, or (None, None)."""
    releases = [r for r in api.get("/repos/%s/releases?per_page=30" % bundled)
                if not r.get("draft") and r.get("published_at") and r.get("tag_name") != exclude_tag]
    if not releases:
        return None, None
    release = max(releases, key=lambda r: r["published_at"])
    asset = next((a for a in release.get("assets", []) if a["name"] == "artifact-manifest.json"), None)
    if not asset:
        return release, None
    try:
        return release, json.loads(api.get_url(asset["browser_download_url"]))
    except (uc.ApiError, ValueError):
        return release, None


# --- notes ----------------------------------------------------------------------------------------------------------

def component_section(api, cfg, key, old, new, commit):
    comp = cfg["components"][key]
    label, repo = comp["label"], comp["repository"]
    if old is None:
        return ["### %s" % label, "", "Baseline unknown: changes are not enumerated. Included version: %s." % uc.fmt(new), ""]
    if new == old:
        return ["### %s" % label, "", "Unchanged (%s)." % uc.fmt(new), ""]
    if new < old:
        return ["### %s" % label, "", "**Warning:** version goes from %s to %s (a downgrade); review before publishing." % (uc.fmt(old), uc.fmt(new)), ""]
    out = ["### %s %s → %s" % (label, uc.fmt(old), uc.fmt(new)), ""]
    releases = {uc.parse_tag(r["tag_name"]): r for r in uc.eligible_releases(api, repo)}
    versions = sorted((v for v in releases if old < v <= new), reverse=True)
    if versions:
        out += ["GitHub Releases: " + ", ".join("[%s](%s)" % (releases[v]["tag_name"], releases[v].get("html_url") or
                "https://github.com/%s/releases/tag/%s" % (repo, releases[v]["tag_name"])) for v in versions), ""]
    try:
        sections = parse_changelog(api.get_raw("/repos/%s/contents/CHANGELOG.md?ref=%s" % (repo, commit)).decode("utf-8"))
    except uc.ApiError:
        return out + ["No CHANGELOG.md was found at the release commit; see the releases above.", ""]
    covered = in_range(sections, old, new)
    wanted = sorted((v for v in set(versions) | set(covered)), reverse=True)
    for version in wanted:
        bullets = sections.get(version)
        out.append("**%s**" % uc.fmt(version))
        out.append("")
        out += ["- " + condense(b) for b in bullets] if bullets else ["- (no changelog entry was published for this version)"]
        out.append("")
    if not wanted:
        out += ["No changelog entries were published for this range.", ""]
    return out


def dependency_changes(previous, current):
    out = []
    for name in sorted(set(previous) | set(current)):
        before, after = (previous.get(name) or {}).get("version"), (current.get(name) or {}).get("version")
        if before != after:
            out.append("- Bundled dependency `%s`: %s" % (name, "added %s" % after if before is None else
                       "removed (was %s)" % before if after is None else "%s → %s" % (before, after)))
    return out


def draft_notes(api, cfg, bundled, current, current_deps, unreleased, label, exclude_tag=None):
    """current: {'core': {'version': tuple, 'commit': sha}, 'fx': {...}}; current_deps: {name: {'version': str}}."""
    release, manifest = previous_release(api, bundled, exclude_tag)
    old = {}
    for key in cfg["components"]:
        try:
            old[key] = uc.parse_tag(manifest[key]["version"]) if manifest else None
        except (KeyError, TypeError):
            old[key] = None
    lines = ["## NineSync %s (draft)" % label, "",
             "> Draft generated from the published Core and FX changelogs and this repository's changelog. "
             "Review and edit it, then publish the release by hand.", ""]
    if release is None:
        lines += ["No earlier Bundled release was found, so there is no baseline to compare against.", ""]
    elif manifest is None:
        lines += ["The previous release (%s) has no readable artifact-manifest.json, so component changes are not enumerated." % release["tag_name"], ""]
    else:
        lines += ["Changes since [%s](%s)." % (release["tag_name"], release.get("html_url") or
                  "https://github.com/%s/releases/tag/%s" % (bundled, release["tag_name"])), ""]
    lines += ["### Components", "", "| Component | Previous | This release |", "| --- | --- | --- |"]
    for key, comp in cfg["components"].items():
        lines.append("| %s | %s | %s |" % (comp["label"], uc.fmt(old[key]) if old[key] else "unknown", uc.fmt(current[key]["version"])))
    lines.append("")
    lines += ["## User-facing changes", ""]
    for key in cfg["components"]:
        lines += component_section(api, cfg, key, old[key], current[key]["version"], current[key]["commit"])
    lines += ["## Bundled packaging, installation and integration", ""]
    bundled_lines = ["- " + b if not b.startswith("- ") else b for b in unreleased]
    deps = dependency_changes((manifest or {}).get("dependencies", {}), current_deps) if manifest else []
    if bundled_lines or deps:
        lines += bundled_lines + deps + [""]
    else:
        lines += ["No Bundled-specific changes were recorded.", ""]
    text = "\n".join(lines).rstrip() + "\n"
    return text if len(text) <= BODY_LIMIT else text[:BODY_LIMIT].rsplit("\n", 1)[0] + "\n\n(truncated)\n"


def unreleased_of(text):
    return parse_changelog(text).get("unreleased", [])


def pr_section(api, cfg, bundled, ref, targets):
    """Draft notes for the rolling PR (targets as built by update_components.select_targets)."""
    current = {k: {"version": t["version"], "commit": t["commit"]} for k, t in targets.items()}
    try:
        changelog = api.get_raw("/repos/%s/contents/CHANGELOG.md?ref=%s" % (bundled, ref)).decode("utf-8")
    except uc.ApiError:
        changelog = ""
    try:
        lock = json.loads(api.get_raw("/repos/%s/contents/packaging/dependencies.lock?ref=%s" % (bundled, ref)))["components"]
    except (uc.ApiError, ValueError, KeyError):
        lock = {}
    return draft_notes(api, cfg, bundled, current, lock, unreleased_of(changelog), "(next release)")


# --- command line -------------------------------------------------------------------------------------------------------

def finalize(path, version, date):
    """Move [Unreleased] under `## version - date`, keeping everything else (history) byte for byte."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    lines = text.splitlines(keepends=True)
    start = next((i for i, l in enumerate(lines) if re.match(r"^##\s+\[?unreleased\]?\s*$", l.strip(), re.I)), None)
    if start is None:
        raise uc.Failure("CHANGELOG.md has no [Unreleased] section")
    if re.search(r"^##\s+\[?v?%s\]?\b" % re.escape(version.lstrip("v")), text, re.M):
        raise uc.Failure("CHANGELOG.md already has a section for %s" % version)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    body = "".join(lines[start + 1:end]).strip("\n")
    if not body.strip():
        raise uc.Failure("[Unreleased] is empty; nothing to finalize")
    new = lines[:start] + ["## [Unreleased]\n", "\n", "## [%s] - %s\n" % (version.lstrip("v"), date), "\n", body + "\n", "\n"] + lines[end:]
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(new))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    dp = sub.add_parser("draft")
    dp.add_argument("--artifact-manifest", required=True)
    dp.add_argument("--version", required=True, help="label for the release, e.g. the tag")
    dp.add_argument("--out", required=True)
    fp = sub.add_parser("finalize")
    fp.add_argument("--version", required=True)
    fp.add_argument("--date", required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "finalize":
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
                raise uc.Failure("--date must be YYYY-MM-DD")
            finalize(CHANGELOG, args.version, args.date)
            print("CHANGELOG.md finalized for", args.version)
            return 0
        cfg = uc.load_config()
        api = uc.GitHub(os.environ.get("GH_TOKEN", ""))
        with open(args.artifact_manifest, encoding="utf-8") as handle:
            built = json.load(handle)
        current = {k: {"version": uc.parse_tag(built[k]["version"]), "commit": built[k]["commit"]} for k in cfg["components"]}
        if any(v["version"] is None for v in current.values()):
            raise uc.Failure("artifact manifest has no X.Y.Z component versions")
        with open(CHANGELOG, encoding="utf-8") as handle:
            unreleased = unreleased_of(handle.read())
        text = draft_notes(api, cfg, os.environ["GITHUB_REPOSITORY"], current, built.get("dependencies", {}), unreleased,
                           args.version, exclude_tag=args.version)
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print("wrote", args.out)
        return 0
    except (uc.Failure, uc.ApiError, KeyError, OSError) as exc:
        print("::error title=Release notes::%s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
