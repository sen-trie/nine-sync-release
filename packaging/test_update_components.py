"""Offline tests for update_components.py (fake GitHub API) and for the workflow safety policy.

    python -I packaging/test_update_components.py
"""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update_components as uc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLED = "owner/bundled"
CORE, FX = "sen-trie/nine-sync-core", "sen-trie/nine-sync-fx"
HOOKS = b"API_VERSION = 1\n"
BOT = "nine-sync-bot"


def sha(label):
    return (label.encode().hex() * 40)[:40]


class Fake:
    """Just enough of the GitHub REST API for update_components.update()."""

    def __init__(self):
        self.repos = {r: {"releases": [], "tags": {}, "default": set(), "manifest": {}, "hooks": {}} for r in (CORE, FX)}
        self.trees, self.commits, self.refs, self.prs, self.writes = {}, {}, {}, [], []
        self.bundle_manifest = b'version = "0.3.0"\n'
        self.bundled_changelog = b"# Changelog\n\n## [Unreleased]\n\n- Installer fix for the combined extension.\n"
        self.bundled_releases = [{"tag_name": "v0.3.0", "draft": False, "published_at": "2026-11-01T00:00:00Z",
                                  "assets": [{"name": "artifact-manifest.json", "browser_download_url": "https://github.com/x/y/m.json"}]}]
        self.previous_manifest = {"core": {"version": "0.3.0"}, "fx": {"version": "0.3.0"}, "dependencies": {}}
        self.changelogs = {}  # (repo, commit) -> text
        for repo, pfx in ((CORE, "core"), (FX, "fx")):
            self.add_release(repo, "0.3.0", sha(pfx + "0.3.0"))
        self.make_commit("main", None, {"nine-sync-core": sha("core0.3.0"), "nine-sync-fx": sha("fx0.3.0")}, "base", "owner")

    # -- fixtures
    def add_release(self, repo, version, commit, draft=False, prerelease=False, annotated=False, hooks=HOOKS, manifest=None):
        r = self.repos[repo]
        tag = "v" + version
        r["releases"].append({"tag_name": tag, "draft": draft, "prerelease": prerelease, "published_at": None if draft else "2026-11-01T00:00:00Z"})
        r["tags"][tag] = ("tag", sha("annot" + commit)) if annotated else ("commit", commit)
        if annotated:
            r["tags"][sha("annot" + commit)] = ("commit", commit)
        r["default"].add(commit)
        r["manifest"][commit] = ('version = "%s"\n' % (manifest or version)).encode()
        r["hooks"][commit] = hooks

    def make_commit(self, ref, parent, pins, message, login, extra_files=()):
        commit = sha("c%d" % len(self.commits))
        tree = "tree" + commit
        self.trees[tree] = dict(pins)
        self.commits[commit] = {"tree": tree, "parent": parent, "message": message, "login": login, "extra": list(extra_files)}
        self.refs[ref] = commit
        return commit

    def pins_at(self, ref):
        return self.trees[self.commits[self.refs[ref]]["tree"]]

    # -- API
    def get_raw(self, path):
        m = re.match(r"/repos/([^/]+/[^/]+)/contents/(.+)\?ref=(.+)$", path)
        repo, file, ref = m.groups()
        if repo == BUNDLED:
            if file.startswith("CHANGELOG.md"):
                return self.bundled_changelog
            if file.startswith("packaging/dependencies.lock"):
                return b'{"components": {}}'
            return self.bundle_manifest
        if file.startswith("CHANGELOG.md"):
            if (repo, ref) not in self.changelogs:
                raise uc.ApiError(404, path)
            return self.changelogs[(repo, ref)].encode()
        data = self.repos[repo]["manifest" if file == "blender_manifest.toml" else "hooks"].get(ref)
        if data is None:
            raise uc.ApiError(404, path)
        return data

    def get_url(self, url):
        return json.dumps(self.previous_manifest).encode()

    def get_url(self, url):
        return json.dumps(self.previous_manifest).encode()

    def get(self, path):
        m = re.match(r"^/repos/([^/]+/[^/]+)(/.*)?$", path)
        repo, rest = m.group(1), m.group(2) or ""
        if repo != BUNDLED:
            return self.get_component(repo, rest)
        if rest == "":
            return {"default_branch": "main"}
        if rest.startswith("/releases?"):
            return list(self.bundled_releases)
        if rest.startswith("/releases?"):
            return list(self.bundled_releases)
        m = re.match(r"/contents/([^?]+)\?ref=(.+)$", rest)
        if m:
            return {"type": "submodule", "sha": self.pins_at(m.group(2))[m.group(1)]}
        m = re.match(r"/git/ref/heads/(.+)$", rest)
        if m:
            if m.group(1) not in self.refs:
                raise uc.ApiError(404, path)
            return {"object": {"sha": self.refs[m.group(1)]}}
        m = re.match(r"/git/commits/(.+)$", rest)
        if m:
            return {"tree": {"sha": self.commits[m.group(1)]["tree"]}}
        m = re.match(r"/compare/(.+)\.\.\.(.+)$", rest)
        if m:
            base, head = m.groups()
            def ancestry(ref):
                out, cur = [], self.refs[ref]
                while cur:
                    out.append(cur)
                    cur = self.commits[cur]["parent"]
                return out
            main_side = set(ancestry(base))
            chain = [c for c in ancestry(head) if c not in main_side]
            behind = len([c for c in ancestry(base) if c not in set(ancestry(head))])
            files = {p for p, s in self.pins_at(head).items() if s != self.pins_at(base).get(p)}
            for c in chain:
                files.update(self.commits[c]["extra"])
            return {"ahead_by": len(chain), "behind_by": behind, "files": [{"filename": f} for f in sorted(files)],
                    "commits": [{"sha": c, "commit": {"message": self.commits[c]["message"]},
                                 "author": {"login": self.commits[c]["login"]}, "committer": {"login": self.commits[c]["login"]}}
                                for c in chain]}
        if rest.startswith("/pulls"):
            return [p for p in self.prs if p["state"] == "open"]
        raise AssertionError("unhandled GET " + path)

    def get_component(self, repo, rest):
        r = self.repos[repo]
        if rest == "":
            return {"default_branch": "master"}
        if rest.startswith("/releases?"):
            return list(r["releases"]) if "page=1" in rest else []
        m = re.match(r"/releases/tags/(.+)$", rest)
        if m:
            for rel in r["releases"]:
                if rel["tag_name"] == m.group(1):
                    return rel
            raise uc.ApiError(404, rest)
        m = re.match(r"/git/ref/tags/(.+)$", rest)
        if m:
            kind, value = r["tags"][m.group(1)]
            return {"object": {"type": kind, "sha": value}}
        m = re.match(r"/git/tags/(.+)$", rest)
        if m:
            kind, value = r["tags"][m.group(1)]
            return {"object": {"type": kind, "sha": value}}
        m = re.match(r"/compare/master\.\.\.(.+)$", rest)
        if m:
            return {"status": "behind" if m.group(1) in r["default"] else "diverged"}
        raise AssertionError("unhandled component GET " + rest)

    def post(self, path, body):
        self.writes.append(("POST", path))
        if path.endswith("/git/trees"):
            tree = "tree-new%d" % len(self.trees)
            pins = dict(self.trees[body["base_tree"]])
            for e in body["tree"]:
                assert e["mode"] == "160000" and e["type"] == "commit"
                pins[e["path"]] = e["sha"]
            self.trees[tree] = pins
            return {"sha": tree}
        if path.endswith("/git/commits"):
            commit = sha("n%d" % len(self.commits))
            self.commits[commit] = {"tree": body["tree"], "parent": body["parents"][0], "message": body["message"], "login": BOT + "[bot]", "extra": []}
            return {"sha": commit}
        if path.endswith("/git/refs"):
            assert body["ref"] == "refs/heads/" + "automation/update-components"
            self.refs["automation/update-components"] = body["sha"]
            return {}
        if path.endswith("/pulls"):
            pr = dict(body, number=len(self.prs) + 1, state="open")
            self.prs.append(pr)
            return pr
        raise AssertionError("unhandled POST " + path)

    def patch(self, path, body):
        self.writes.append(("PATCH", path))
        if "/git/refs/heads/" in path:
            self.refs[path.split("/git/refs/heads/")[1]] = body["sha"]
            return {}
        pr = self.prs[int(path.rsplit("/", 1)[1]) - 1]
        pr.update(body)
        return pr


def event(repo, version, commit, key):
    return {"component": key, "repository": repo, "tag": "v" + version, "commit": commit}


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.api, self.cfg, self.logs = Fake(), uc.load_config(), []

    def run_update(self, ev=None, **kw):
        return uc.update(self.api, self.cfg, BUNDLED, ev, BOT, log=self.logs.append, **kw)

    def release(self, repo, version, **kw):
        commit = sha(("core" if repo == CORE else "fx") + version)
        self.api.add_release(repo, version, commit, **kw)
        return commit

    def pins(self):
        return self.api.pins_at("automation/update-components")

    def test_1_core_release_creates_the_pr(self):
        c = self.release(CORE, "0.3.1")
        self.assertEqual(self.run_update(event(CORE, "0.3.1", c, "core")), "created")
        self.assertEqual(self.pins()["nine-sync-core"], c)
        self.assertEqual(self.pins()["nine-sync-fx"], sha("fx0.3.0"))
        self.assertEqual(len(self.api.prs), 1)
        pr = self.api.prs[0]
        self.assertEqual(pr["title"], "chore: Update NineSync Core and FX")
        self.assertIn("Core: 0.3.0 -> 0.3.1", pr["body"])
        self.assertIn("FX:   0.3.0 (unchanged)", pr["body"])
        self.assertEqual(self.api.pins_at("main")["nine-sync-core"], sha("core0.3.0"), "main must not move")

    def test_2_fx_release_updates_the_same_pr(self):
        c = self.release(CORE, "0.3.1")
        self.run_update(event(CORE, "0.3.1", c, "core"))
        f = self.release(FX, "0.3.1", annotated=True)
        self.assertEqual(self.run_update(event(FX, "0.3.1", f, "fx")), "updated")
        self.assertEqual(len(self.api.prs), 1)
        self.assertEqual((self.pins()["nine-sync-core"], self.pins()["nine-sync-fx"]), (c, f))
        self.assertIn("Core: 0.3.0 -> 0.3.1", self.api.prs[0]["body"])
        self.assertIn("FX:   0.3.0 -> 0.3.1", self.api.prs[0]["body"])

    def test_3_newer_core_updates_the_existing_pr(self):
        self.run_update(event(CORE, "0.3.1", self.release(CORE, "0.3.1"), "core"))
        c2 = self.release(CORE, "0.3.2")
        self.assertEqual(self.run_update(event(CORE, "0.3.2", c2, "core")), "updated")
        self.assertEqual(len(self.api.prs), 1)
        self.assertEqual(self.pins()["nine-sync-core"], c2)
        self.assertIn("Core: 0.3.0 -> 0.3.2", self.api.prs[0]["body"])

    def test_4_duplicate_notification_changes_nothing(self):
        c = self.release(CORE, "0.3.1")
        self.run_update(event(CORE, "0.3.1", c, "core"))
        self.api.writes.clear()
        self.assertEqual(self.run_update(event(CORE, "0.3.1", c, "core")), "branch-current")
        self.assertEqual(self.api.writes, [])
        self.assertEqual(len(self.api.prs), 1)

    def test_5_out_of_order_notification_does_not_downgrade(self):
        old = self.release(CORE, "0.3.1")
        new = self.release(CORE, "0.3.2")
        self.run_update(event(CORE, "0.3.2", new, "core"))
        self.api.writes.clear()
        self.run_update(event(CORE, "0.3.1", old, "core"))
        self.assertEqual(self.pins()["nine-sync-core"], new)
        self.assertEqual(self.api.writes, [])

    def test_5b_older_notification_still_picks_up_the_newest(self):
        old = self.release(CORE, "0.3.1")
        new = self.release(CORE, "0.3.2")
        self.run_update(event(CORE, "0.3.1", old, "core"))  # delivered late, 0.3.2 already exists
        self.assertEqual(self.pins()["nine-sync-core"], new)

    def test_6_prereleases_and_drafts_are_ignored(self):
        self.release(CORE, "0.3.5", prerelease=True)
        self.release(CORE, "0.3.6", draft=True)
        self.assertEqual(self.run_update(), "current")
        self.assertEqual(self.api.prs, [])
        pre = sha("core0.3.5")
        with self.assertRaises(uc.Failure):
            self.run_update(event(CORE, "0.3.5", pre, "core"))
        self.assertEqual(self.api.writes, [])

    def test_notification_is_not_trusted(self):
        c = self.release(CORE, "0.3.1")
        bad = [
            event("evil/nine-sync-core", "0.3.1", c, "core"),   # unapproved repository
            event(FX, "0.3.1", c, "core"),                      # repository does not match component
            event(CORE, "0.3.1", c, "other"),                   # unknown component
            event(CORE, "0.3.1", sha("deadbeef"), "core"),      # tag does not resolve to the reported commit
            event(CORE, "0.3.1-rc1", c, "core"),                # not a stable tag
            event(CORE, "0.3.9", c, "core"),                    # release does not exist
            {"component": "core", "repository": CORE, "tag": "v0.3.1"},  # no commit
            "not an object",
        ]
        for ev in bad:
            with self.assertRaises(uc.Failure, msg=str(ev)):
                self.run_update(ev)
        self.assertEqual(self.api.writes, [])

    def test_tag_commit_must_be_on_default_branch_and_match_manifest(self):
        c = self.release(CORE, "0.3.1")
        self.api.repos[CORE]["default"].discard(c)
        with self.assertRaises(uc.Failure):
            self.run_update(event(CORE, "0.3.1", c, "core"))
        self.api.repos[CORE]["default"].add(c)
        self.api.repos[CORE]["manifest"][c] = b'version = "0.3.0"\n'
        with self.assertRaises(uc.Failure):
            self.run_update()
        self.assertEqual(self.api.writes, [])

    def test_already_current_does_nothing(self):
        self.assertEqual(self.run_update(), "current")
        self.assertEqual(self.api.writes, [])

    def test_incompatible_release_keeps_last_compatible_state(self):
        c = self.release(CORE, "0.3.1")
        self.run_update(event(CORE, "0.3.1", c, "core"))
        self.api.writes.clear()
        self.release(CORE, "0.4.0")      # needs a Bundled/FX 0.4 first
        with self.assertRaises(uc.Failure):
            self.run_update()
        self.assertEqual(self.pins()["nine-sync-core"], c)
        self.assertEqual(self.api.writes, [])

    def test_hooks_mismatch_is_incompatible(self):
        self.release(CORE, "0.3.1", hooks=b"API_VERSION = 1\n# changed\n")
        with self.assertRaises(uc.Failure):
            self.run_update()
        self.assertEqual(self.api.writes, [])

    def test_manual_changes_on_the_branch_are_not_overwritten(self):
        c = self.release(CORE, "0.3.1")
        self.run_update(event(CORE, "0.3.1", c, "core"))
        pins = dict(self.pins())
        manual = self.api.make_commit("automation/update-components", self.api.refs["automation/update-components"], pins,
                                      "tweak readme", "human", extra_files=["README.md"])
        self.release(FX, "0.3.1")
        self.api.writes.clear()
        with self.assertRaises(uc.Failure):
            self.run_update()
        self.assertEqual(self.api.refs["automation/update-components"], manual)
        self.assertEqual(self.api.writes, [])

    def test_branch_behind_main_is_rebuilt_not_duplicated(self):
        c = self.release(CORE, "0.3.1")
        self.run_update(event(CORE, "0.3.1", c, "core"))
        self.api.make_commit("main", self.api.refs["main"], self.api.pins_at("main"), "unrelated main change", "owner")
        self.assertEqual(self.run_update(), "updated")
        self.assertEqual(len(self.api.prs), 1)

    def test_dry_run_writes_nothing(self):
        self.release(CORE, "0.3.1")
        self.assertEqual(self.run_update(dry_run=True), "dry-run")
        self.assertEqual(self.api.writes, [])


class PolicyTests(unittest.TestCase):
    """Merging a component PR must never publish; the release path stays manual."""

    def workflow(self, name):
        with open(os.path.join(ROOT, ".github", "workflows", name), encoding="utf-8") as handle:
            return handle.read()

    def test_release_workflows_are_manual_only(self):
        for name in ("release.yml", "experimental-release.yml"):
            text = self.workflow(name)
            on_block = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
            self.assertEqual(re.findall(r"^  (\w+):", on_block, re.M), ["workflow_dispatch"], name)

    def test_automation_workflows_cannot_publish_or_merge(self):
        for name in ("update-components.yml", "pr-validation.yml"):
            text = self.workflow(name)
            for forbidden in ("gh release", "deploy-pages", "upload-pages-artifact", "pulls/merge", "enable-auto-merge",
                              "gh pr merge", "git tag", "contents: write\n    steps"):
                self.assertNotIn(forbidden, text, "%s: %s" % (name, forbidden))
            self.assertNotRegex(text, r"(?m)^on:\n(?:.*\n)*?\s+push:", name)

    def test_script_never_merges_or_tags(self):
        with open(os.path.join(ROOT, "packaging", "update_components.py"), encoding="utf-8") as handle:
            source = handle.read()
        for forbidden in ("/merge", "auto_merge", "/releases\", {", "refs/tags", "git/tags\","):
            self.assertNotIn(forbidden, source)

    def test_pr_validation_uses_no_secrets(self):
        self.assertNotIn("secrets.", self.workflow("pr-validation.yml"))

    def test_config_is_approved_repositories_only(self):
        cfg = uc.load_config()
        self.assertEqual({c["repository"] for c in cfg["components"].values()}, {CORE, FX})
        self.assertEqual(cfg["branch"], "automation/update-components")


if __name__ == "__main__":
    unittest.main()
