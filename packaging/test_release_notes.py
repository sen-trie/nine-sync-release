"""Offline tests for release_notes.py.

    python -I packaging/test_release_notes.py
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_notes as rn  # noqa: E402
import test_update_components as base  # noqa: E402
import update_components as uc  # noqa: E402


class NotesTests(unittest.TestCase):
    def setUp(self):
        self.api, self.cfg = base.Fake(), uc.load_config()

    def test_pr_body_collects_every_release_since_the_previous_bundled_release(self):
        for v in ("0.3.1", "0.3.2"):
            c = base.sha("core" + v)
            self.api.add_release(base.CORE, v, c)
            self.api.changelogs[(base.CORE, c)] = (
                "# Changelog\n\n## Unreleased\n\n- Not shipped yet.\n\n"
                "## 0.3.2\n\n- Beta feature\n  wrapped line.\n\n"
                "## 0.3.1\n\n- Alpha fix. Second sentence is dropped.\n\n"
                "## 0.3.0\n\n- Old.\n")
        status = uc.update(self.api, self.cfg, base.BUNDLED, None, base.BOT, log=lambda *_: None)
        self.assertEqual(status, "created")
        body = self.api.prs[0]["body"]
        self.assertIn("**0.3.2**", body)
        self.assertIn("**0.3.1**", body)                  # intermediate release is included
        self.assertIn("- Alpha fix.", body)
        self.assertNotIn("Second sentence", body)         # condensed to the first sentence
        self.assertIn("Beta feature wrapped line.", body)
        self.assertNotIn("Not shipped yet", body)         # unreleased never appears
        self.assertNotIn("- Old.", body)                  # already in the previous Bundled release
        self.assertIn("Installer fix for the combined extension.", body)
        self.assertIn("Changes since [v0.3.0]", body)
        self.assertIn("releases/tag/v0.3.1", body)        # links to the GitHub Releases

    def test_missing_changelog_entry_is_reported_not_invented(self):
        c = base.sha("core0.3.1")
        self.api.add_release(base.CORE, "0.3.1", c)
        self.api.changelogs[(base.CORE, c)] = "# Changelog\n\n## 0.3.0\n\n- Old.\n"
        uc.update(self.api, self.cfg, base.BUNDLED, None, base.BOT, log=lambda *_: None)
        self.assertIn("no changelog entry was published for this version", self.api.prs[0]["body"])

    def test_no_baseline_is_stated(self):
        cur = {"core": {"version": (0, 3, 0), "commit": "a"}, "fx": {"version": (0, 3, 0), "commit": "b"}}
        self.api.bundled_releases = []
        text = rn.draft_notes(self.api, self.cfg, base.BUNDLED, cur, {}, [], "v1")
        self.assertIn("no baseline", text)
        self.assertIn("Baseline unknown", text)
        self.api.bundled_releases = [{"tag_name": "v0", "draft": False, "published_at": "2026-01-01T00:00:00Z", "assets": []}]
        self.assertIn("no readable artifact-manifest.json", rn.draft_notes(self.api, self.cfg, base.BUNDLED, cur, {}, [], "v1"))

    def test_drafts_are_never_the_baseline(self):
        self.api.bundled_releases.append({"tag_name": "v9", "draft": True, "published_at": None, "assets": []})
        release, _ = rn.previous_release(self.api, base.BUNDLED)
        self.assertEqual(release["tag_name"], "v0.3.0")

    def test_dependency_changes_are_factual(self):
        out = rn.dependency_changes({"a": {"version": "1"}, "b": {"version": "2"}}, {"a": {"version": "2"}, "c": {"version": "3"}})
        self.assertEqual(len(out), 3)
        self.assertEqual(rn.dependency_changes({"a": {"version": "1"}}, {"a": {"version": "1"}}), [])

    def test_finalize_keeps_history_and_refuses_misuse(self):
        text = "# Changelog\n\n## [Unreleased]\n\n- New thing.\n\n## [0.1.0]\n\n- Old thing.\n"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "CHANGELOG.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            rn.finalize(path, "v0.2.0", "2026-12-01")
            with open(path, encoding="utf-8") as handle:
                out = handle.read()
            self.assertIn("## [Unreleased]\n\n## [0.2.0] - 2026-12-01\n\n- New thing.", out)
            self.assertTrue(out.endswith("## [0.1.0]\n\n- Old thing.\n"))
            with self.assertRaises(uc.Failure):
                rn.finalize(path, "0.2.0", "2026-12-02")      # version already present
            with self.assertRaises(uc.Failure):
                rn.finalize(path, "0.3.0", "2026-12-02")      # [Unreleased] is empty

    def test_release_workflow_uses_draft_notes_and_stays_a_draft(self):
        with open(os.path.join(base.ROOT, ".github", "workflows", "release.yml"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("release_notes.py draft", text)
        self.assertIn("--draft", text)


if __name__ == "__main__":
    unittest.main()
