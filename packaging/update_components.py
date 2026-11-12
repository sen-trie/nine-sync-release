#!/usr/bin/env python3
"""Rolling dependency-update PR for the pinned NineSync Core and FX submodules.

    python -I packaging/update_components.py update [--event-json JSON] [--dry-run]
    python -I packaging/update_components.py verify-pins --base origin/main

`update` (run by .github/workflows/update-components.yml) never trusts the notification payload. It re-resolves the
latest eligible *stable* release of both components from the approved repositories (packaging/components.json),
checks that the tag resolves to a commit on the component's default branch and that the commit's manifest version
equals the tag, checks Core/FX compatibility, and then maintains ONE branch and ONE pull request.

It only talks to the GitHub API (no submodule code is fetched or run). It changes nothing but the submodule
pointers, never downgrades, never merges, never tags, never releases and never deploys.

`verify-pins` (run by PR validation on the automation branch) re-checks, from the checked-out tree, that every
pin changed by the PR is a stable release commit and not a downgrade.

Standard library only.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# `python -I` (used by the workflow) leaves the script directory off sys.path, but `update` imports release_notes.
if HERE not in sys.path:
    sys.path.insert(0, HERE)
STABLE_TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA = re.compile(r"^[0-9a-f]{40}$")
SEP = "\n\n---\n\n"


class Failure(Exception):
    """A condition that must stop the run without changing anything."""


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__("GitHub API %s: %s" % (status, message))
        self.status = status


# --- GitHub API ---------------------------------------------------------------------------------------------

class GitHub:
    def __init__(self, token, base="https://api.github.com"):
        self.token, self.base = token, base

    def request(self, method, path, body=None, raw=False):
        headers = {
            "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nine-sync-update-components",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read()
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code, "%s %s" % (method, path)) from None
        return payload if raw else json.loads(payload or b"null")

    def get(self, path):
        return self.request("GET", path)

    def get_raw(self, path):
        return self.request("GET", path, raw=True)

    def get_url(self, url):
        """Public release-asset download; deliberately sent without the token (it redirects to another host)."""
        if not url.startswith("https://github.com/"):
            raise ApiError(400, "refusing to fetch " + url)
        req = urllib.request.Request(url, headers={"User-Agent": "nine-sync-update-components"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read(5_000_000)
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code, url) from None

    def post(self, path, body):
        return self.request("POST", path, body)

    def patch(self, path, body):
        return self.request("PATCH", path, body)


# --- versions and release resolution ------------------------------------------------------------------------

def parse_tag(tag):
    match = STABLE_TAG.match(tag or "")
    return tuple(int(p) for p in match.groups()) if match else None


def fmt(version):
    return ".".join(str(p) for p in version)


def load_config():
    with open(os.path.join(HERE, "components.json"), encoding="utf-8") as handle:
        cfg = json.load(handle)
    for comp in cfg["components"].values():
        if not REPO_NAME.match(comp["repository"]):
            raise Failure("bad repository in components.json: %r" % comp["repository"])
    return cfg


def default_branch(api, repo):
    return api.get("/repos/%s" % repo)["default_branch"]


def tag_commit(api, repo, tag):
    """Resolve a tag (lightweight or annotated) to its commit sha."""
    ref = api.get("/repos/%s/git/ref/tags/%s" % (repo, tag))["object"]
    for _ in range(5):
        if ref["type"] == "commit":
            return ref["sha"]
        if ref["type"] != "tag":
            break
        ref = api.get("/repos/%s/git/tags/%s" % (repo, ref["sha"]))["object"]
    raise Failure("%s tag %s does not resolve to a commit" % (repo, tag))


def manifest_version(api, repo, sha):
    raw = api.get_raw("/repos/%s/contents/blender_manifest.toml?ref=%s" % (repo, sha))
    version = parse_tag(str(tomllib.loads(raw.decode("utf-8")).get("version", "")))
    if version is None:
        raise Failure("%s@%s: blender_manifest.toml has no X.Y.Z version" % (repo, sha[:12]))
    return version


def release_info(api, repo, release):
    """Verify one release and return {version, tag, commit}. Raises Failure when it is not eligible."""
    tag = release.get("tag_name")
    version = parse_tag(tag)
    if version is None:
        raise Failure("%s release %r is not a stable X.Y.Z tag" % (repo, tag))
    if release.get("draft") or release.get("prerelease") or not release.get("published_at"):
        raise Failure("%s release %s is a draft, a prerelease or unpublished" % (repo, tag))
    commit = tag_commit(api, repo, tag)
    status = api.get("/repos/%s/compare/%s...%s" % (repo, default_branch(api, repo), commit)).get("status")
    if status not in ("behind", "identical"):
        raise Failure("%s release %s commit %s is not on the default branch" % (repo, tag, commit[:12]))
    if manifest_version(api, repo, commit) != version:
        raise Failure("%s release %s: manifest version at %s differs from the tag" % (repo, tag, commit[:12]))
    return {"version": version, "tag": tag, "commit": commit}


def eligible_releases(api, repo):
    found = []
    for page in range(1, 6):
        batch = api.get("/repos/%s/releases?per_page=100&page=%d" % (repo, page))
        for rel in batch:
            if not rel.get("draft") and not rel.get("prerelease") and rel.get("published_at") and parse_tag(rel.get("tag_name")):
                found.append(rel)
        if len(batch) < 100:
            break
    return found


def latest_release(api, repo):
    releases = eligible_releases(api, repo)
    if not releases:
        return None
    return release_info(api, repo, max(releases, key=lambda r: parse_tag(r["tag_name"])))


def verify_event(api, cfg, payload):
    """Check a repository_dispatch payload against the approved repositories and the real release."""
    if not isinstance(payload, dict):
        raise Failure("notification payload is not an object")
    key, repo, tag, commit = (payload.get(k) for k in ("component", "repository", "tag", "commit"))
    if key not in cfg["components"]:
        raise Failure("notification names an unknown component: %r" % (key,))
    comp = cfg["components"][key]
    if repo != comp["repository"]:
        raise Failure("notification repository %r is not the approved %s repository" % (repo, key))
    if parse_tag(tag) is None:
        raise Failure("notification tag %r is not a stable X.Y.Z tag" % (tag,))
    if not isinstance(commit, str) or not SHA.match(commit):
        raise Failure("notification has no full commit sha")
    try:
        release = api.get("/repos/%s/releases/tags/%s" % (repo, tag))
    except ApiError as exc:
        raise Failure("reported release %s %s was not found (%s)" % (repo, tag, exc))
    info = release_info(api, repo, release)
    if info["commit"] != commit:
        raise Failure("tag %s resolves to %s, not the reported %s" % (tag, info["commit"][:12], commit[:12]))
    return key, info


# --- compatibility ------------------------------------------------------------------------------------------

def api_version_of(hooks):
    match = re.search(rb"^API_VERSION\s*=\s*(\d+)\s*$", hooks, re.M)
    return int(match.group(1)) if match else None


def check_compat(api, cfg, targets, bundle_version):
    """Same rules validate_bundle.py enforces: identical hooks.py and API version. Versions are independent (see VERSIONING.md)."""
    problems = []
    hooks = {}
    for key, tgt in targets.items():
        try:
            hooks[key] = api.get_raw("/repos/%s/contents/hooks.py?ref=%s" % (cfg["components"][key]["repository"], tgt["commit"]))
        except ApiError:
            problems.append("%s has no hooks.py at %s" % (key, tgt["commit"][:12]))
    if len(hooks) == 2:
        if hooks["core"] != hooks["fx"]:
            problems.append("hooks.py differs between Core and FX")
        if api_version_of(hooks["core"]) != 1:
            problems.append("hooks API_VERSION is not 1")
    return problems


# --- repository state ---------------------------------------------------------------------------------------

def gitlink(api, repo, path, ref):
    entry = api.get("/repos/%s/contents/%s?ref=%s" % (repo, path, ref))
    if not isinstance(entry, dict) or entry.get("type") != "submodule":
        raise Failure("%s is not a submodule at %s" % (path, ref))
    return entry["sha"]


def read_pins(api, cfg, bundled, ref):
    pins = {}
    for key, comp in cfg["components"].items():
        sha = gitlink(api, bundled, comp["path"], ref)
        pins[key] = {"commit": sha, "version": manifest_version(api, comp["repository"], sha)}
    return pins


def bundle_version(api, cfg, bundled, ref):
    raw = api.get_raw("/repos/%s/contents/%s?ref=%s" % (bundled, cfg["bundle_manifest"], ref))
    version = parse_tag(str(tomllib.loads(raw.decode("utf-8")).get("version", "")))
    if version is None:
        raise Failure("Bundled manifest has no X.Y.Z version")
    return version


def select_targets(base_pins, latest):
    """Newest eligible release per component; never lower than what the base branch already pins."""
    targets = {}
    for key, pin in base_pins.items():
        rel = latest.get(key)
        if rel and rel["version"] > pin["version"]:
            targets[key] = {"commit": rel["commit"], "version": rel["version"], "tag": rel["tag"]}
        else:
            targets[key] = {"commit": pin["commit"], "version": pin["version"], "tag": None}
    return targets


def describe(cfg, base_pins, targets):
    lines = []
    for key, comp in cfg["components"].items():
        before, after = base_pins[key]["version"], targets[key]["version"]
        label = (comp["label"] + ":").ljust(5)
        lines.append("%s %s -> %s" % (label, fmt(before), fmt(after)) if after != before
                     else "%s %s (unchanged)" % (label, fmt(before)))
    return lines


def pr_body(cfg, base_pins, targets):
    lines = ["Update NineSync components", ""] + ["    " + l for l in describe(cfg, base_pins, targets)] + [""]
    for key, comp in cfg["components"].items():
        t = targets[key]
        if t["tag"]:
            lines.append("- %s `%s` at `%s`: https://github.com/%s/releases/tag/%s"
                         % (comp["label"], t["tag"], t["commit"][:12], comp["repository"], t["tag"]))
    lines += [
        "",
        "Only the pinned submodule references change. Merging does **not** change the Bundled version, create a tag,",
        "publish a release, deploy GitHub Pages or touch the public extension repository: those stay with the",
        "manually dispatched, separately approved `release.yml`.",
        "",
        "This PR is maintained by `update-components.yml` and is never merged automatically. Further stable Core or FX",
        "releases update it in place. If you push your own commits to the branch the automation stops and reports a conflict.",
    ]
    return "\n".join(lines)


def commit_message(cfg, base_pins, targets):
    return "\n".join([cfg["title"], ""] + describe(cfg, base_pins, targets) + ["", cfg["marker"]])


def branch_state(api, cfg, bundled, base, app_slug):
    """None when the branch is absent; else {sha, pins, ahead, behind}. Raises Failure if it was modified by hand."""
    branch = cfg["branch"]
    try:
        sha = api.get("/repos/%s/git/ref/heads/%s" % (bundled, branch))["object"]["sha"]
    except ApiError as exc:
        if exc.status == 404:
            return None
        raise
    cmp = api.get("/repos/%s/compare/%s...%s" % (bundled, base, branch))
    allowed = {c["path"] for c in cfg["components"].values()}
    bot = (app_slug + "[bot]") if app_slug else None
    problems = []
    for commit in cmp.get("commits", []):
        msg = commit["commit"]["message"]
        author = (commit.get("author") or {}).get("login")
        committer = (commit.get("committer") or {}).get("login")
        if cfg["marker"] not in msg:
            problems.append("commit %s was not made by the automation" % commit["sha"][:12])
        elif bot and bot not in (author, committer):
            problems.append("commit %s was made by %s" % (commit["sha"][:12], author or committer))
    for entry in cmp.get("files", []):
        if entry["filename"] not in allowed:
            problems.append("file %s was changed on the branch" % entry["filename"])
    if problems:
        raise Failure("the rolling branch %s has manual changes; not overwriting it: %s" % (branch, "; ".join(problems)))
    return {"sha": sha, "pins": read_pins(api, cfg, bundled, branch), "behind": cmp.get("behind_by", 0)}


def open_pr(api, cfg, bundled, base):
    owner = bundled.split("/")[0]
    prs = api.get("/repos/%s/pulls?state=open&head=%s:%s&base=%s&per_page=10" % (bundled, owner, cfg["branch"], base))
    return prs[0] if prs else None


def update(api, cfg, bundled, event=None, app_slug=None, dry_run=False, log=print):
    """Returns a status string. Raises Failure/ApiError when nothing may be changed."""
    notice = None
    if event is not None:
        key, info = verify_event(api, cfg, event)
        log("notification verified: %s %s (%s)" % (key, info["tag"], info["commit"][:12]))
    base = default_branch(api, bundled)
    base_pins = read_pins(api, cfg, bundled, base)
    if event is not None and info["version"] <= base_pins[key]["version"]:
        notice = "%s %s is not newer than the selected %s" % (key, info["tag"], fmt(base_pins[key]["version"]))
        log(notice)
    latest = {k: latest_release(api, c["repository"]) for k, c in cfg["components"].items()}
    targets = select_targets(base_pins, latest)
    for line in describe(cfg, base_pins, targets):
        log("  " + line)
    changed = {k: t for k, t in targets.items() if t["commit"] != base_pins[k]["commit"]}
    if not changed:
        log("selected versions are already current; nothing to do")
        return "current"
    problems = check_compat(api, cfg, targets, bundle_version(api, cfg, bundled, base))
    if problems:
        raise Failure("incompatible Core/FX combination; the last compatible state is kept: " + "; ".join(problems))
    state = branch_state(api, cfg, bundled, base, app_slug)
    pr = open_pr(api, cfg, bundled, base)
    wanted = {k: t["commit"] for k, t in targets.items()}
    if state and not state["behind"] and {k: p["commit"] for k, p in state["pins"].items()} == wanted:
        log("rolling branch is already up to date")
        status = "branch-current"
    elif dry_run:
        log("dry run: would %s %s" % ("update" if state else "create", cfg["branch"]))
        return "dry-run"
    else:
        base_commit = api.get("/repos/%s/git/ref/heads/%s" % (bundled, base))["object"]["sha"]
        tree = api.get("/repos/%s/git/commits/%s" % (bundled, base_commit))["tree"]["sha"]
        entries = [{"path": cfg["components"][k]["path"], "mode": "160000", "type": "commit", "sha": t["commit"]}
                   for k, t in changed.items()]
        new_tree = api.post("/repos/%s/git/trees" % bundled, {"base_tree": tree, "tree": entries})["sha"]
        new_commit = api.post("/repos/%s/git/commits" % bundled, {
            "message": commit_message(cfg, base_pins, targets), "tree": new_tree, "parents": [base_commit]})["sha"]
        if state:
            # The branch is derived entirely from the base plus pins, so re-deriving it loses nothing; still, refuse
            # if somebody pushed since it was inspected.
            now = api.get("/repos/%s/git/ref/heads/%s" % (bundled, cfg["branch"]))["object"]["sha"]
            if now != state["sha"]:
                raise Failure("the rolling branch changed while updating; not overwriting it")
            api.patch("/repos/%s/git/refs/heads/%s" % (bundled, cfg["branch"]), {"sha": new_commit, "force": True})
            status = "updated"
        else:
            api.post("/repos/%s/git/refs" % bundled, {"ref": "refs/heads/" + cfg["branch"], "sha": new_commit})
            status = "created"
        log("branch %s: %s at %s" % (cfg["branch"], status, new_commit[:12]))
    body = pr_body(cfg, base_pins, targets)
    try:
        import release_notes  # lazy: release_notes imports this module
        body += SEP + release_notes.pr_section(api, cfg, bundled, base, targets)
    except (Failure, ApiError) as exc:
        body += SEP + "Draft release notes could not be generated: %s" % exc
    if pr is None:
        pr = api.post("/repos/%s/pulls" % bundled, {"title": cfg["title"], "head": cfg["branch"], "base": base,
                                                     "body": body, "maintainer_can_modify": False})
        log("opened PR #%s" % pr["number"])
        status = "created" if status == "branch-current" else status
    elif pr.get("title") != cfg["title"] or pr.get("body") != body:
        api.patch("/repos/%s/pulls/%s" % (bundled, pr["number"]), {"title": cfg["title"], "body": body})
        log("refreshed PR #%s" % pr["number"])
    return status


# --- CI check on the PR ---------------------------------------------------------------------------------------

def local_pins(api, cfg, ref):
    pins = {}
    for key, comp in cfg["components"].items():
        out = subprocess.run(["git", "ls-tree", ref, comp["path"]], cwd=ROOT, check=True, capture_output=True, text=True).stdout
        parts = out.split()
        if len(parts) < 3 or parts[0] != "160000":
            raise Failure("%s is not a submodule at %s" % (comp["path"], ref))
        pins[key] = {"commit": parts[2], "version": manifest_version(api, comp["repository"], parts[2])}
    return pins


def verify_pins(api, cfg, base):
    base_pins, head_pins = local_pins(api, cfg, base), local_pins(api, cfg, "HEAD")
    problems = []
    for key, pin in head_pins.items():
        repo = cfg["components"][key]["repository"]
        if pin["version"] < base_pins[key]["version"]:
            problems.append("%s is downgraded: %s -> %s" % (key, fmt(base_pins[key]["version"]), fmt(pin["version"])))
        elif pin["commit"] != base_pins[key]["commit"]:
            rel = next((r for r in eligible_releases(api, repo) if parse_tag(r["tag_name"]) == pin["version"]), None)
            if rel is None:
                problems.append("%s %s has no stable published release" % (key, fmt(pin["version"])))
                continue
            try:
                info = release_info(api, repo, rel)
            except Failure as exc:
                problems.append(str(exc))
                continue
            if info["commit"] != pin["commit"]:
                problems.append("%s pin %s is not the commit of release %s" % (key, pin["commit"][:12], info["tag"]))
    with open(os.path.join(ROOT, cfg["bundle_manifest"]), "rb") as handle:
        bundle = parse_tag(str(tomllib.load(handle).get("version", "")))
    problems += check_compat(api, cfg, {k: {"commit": p["commit"], "version": p["version"]} for k, p in head_pins.items()}, bundle)
    return problems


# --- command line -----------------------------------------------------------------------------------------------

def summary(text):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("update")
    up.add_argument("--event-json", default="", help="client_payload of the repository_dispatch event (verified, not trusted)")
    up.add_argument("--dry-run", action="store_true")
    vp = sub.add_parser("verify-pins")
    vp.add_argument("--base", required=True)
    args = parser.parse_args(argv)
    api = GitHub(os.environ.get("GH_TOKEN", ""))
    try:
        cfg = load_config()
        if args.cmd == "update":
            bundled = os.environ["GITHUB_REPOSITORY"]
            event = None
            if args.event_json.strip():
                try:
                    event = json.loads(args.event_json)
                except ValueError:
                    raise Failure("notification payload is not valid JSON")
            status = update(api, cfg, bundled, event, os.environ.get("APP_SLUG") or None, args.dry_run)
            summary("### Component update: %s" % status)
        else:
            problems = verify_pins(api, cfg, args.base)
            if problems:
                raise Failure("; ".join(problems))
            print("pins verified")
    except (Failure, ApiError) as exc:
        print("::error title=Component update::%s" % exc)
        summary("### Component update failed\n\n%s" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
