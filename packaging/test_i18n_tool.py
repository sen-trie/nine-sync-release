#!/usr/bin/env python3
"""Unit tests for i18n_tool.py (no Blender). Run: python -I packaging/test_i18n_tool.py -v"""
import ast
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i18n_tool as t  # noqa: E402

SOURCE = '''
import bpy
from bpy.app.translations import pgettext_iface as iface_, pgettext_rpt as rpt_

MODES = [("A", "Alpha", "First mode"), ("B", "Beta", "")]


class NS_OT_sync(bpy.types.Operator):
    bl_idname = "ns.sync"
    bl_label = "Sync"
    bl_description = "Synchronize the project"
    scale: bpy.props.FloatProperty(name="Scale", description="Import scale")
    mode: bpy.props.EnumProperty(items=MODES, name="Mode")

    def execute(self, context):
        self.report({"INFO"}, "Done")
        self.report({"INFO"}, "%d models" % 3)
        self.report({"INFO"}, rpt_("%d bones") % 3)
        self.report({"INFO"}, status)
        return {"FINISHED"}


class NS_PT_main(bpy.types.Panel):
    bl_label = "Sync"

    def draw(self, context):
        self.layout.label(text="Cache", text_ctxt="NineSync")
        self.layout.label(text=f"{3} items")
        self.layout.label(text=iface_("Pass %s") % "a")
        self.layout.label(text="raw", translate=False)
        self.layout.prop(context.scene, "x", text=obj.name)
'''


def extract_source(text):
    tree = ast.parse(text)
    ex = t.Extractor("m.py", tree)
    ex.visit(tree)
    return ex


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.ex = extract_source(SOURCE)
        self.keys = {(c, m): k for c, m, k, _ in self.ex.found}

    def test_operator_label_uses_operator_context(self):
        self.assertIn(("Operator", "Sync"), self.keys)
        self.assertIn(("*", "Sync"), self.keys)  # the panel

    def test_tooltips(self):
        for msg in ("Synchronize the project", "Import scale", "First mode"):
            self.assertEqual(self.keys[("*", msg)], "tooltip")

    def test_enum_items_through_module_constant(self):
        self.assertIn(("*", "Alpha"), self.keys)
        self.assertIn(("*", "Beta"), self.keys)
        self.assertNotIn(("*", ""), self.keys)

    def test_reports_and_explicit_calls(self):
        self.assertEqual(self.keys[("*", "Done")], "report")
        self.assertEqual(self.keys[("*", "%d bones")], "report")
        self.assertIn(("*", "Pass %s"), self.keys)

    def test_text_ctxt_and_translate_false(self):
        self.assertIn(("NineSync", "Cache"), self.keys)
        self.assertNotIn(("*", "raw"), self.keys)

    def test_dynamic_findings(self):
        kinds = sorted(w for _, w in self.ex.dynamic)
        self.assertIn("label(text=...)", kinds)  # the f-string
        self.assertIn("report(...) formatted before translation", kinds)
        self.assertIn("report(<variable>): translate where the text is built", kinds)
        self.assertEqual(len(self.ex.dynamic), 3)  # obj.name and the wrapped calls are not findings


class PoTests(unittest.TestCase):
    def test_round_trip_with_escapes_context_fuzzy_obsolete(self):
        entries = [
            t.Entry("*", 'Say "hi"\nnow', "「こんにちは」\n今", refs=["a.py:1"], kinds={"label"}),
            t.Entry("Operator", "Sync", "同期", refs=["a.py:2"], kinds={"label"}, flags={"fuzzy"}, previous="Sync!"),
            t.Entry("*", "Gone", "消えた", obsolete=True),
        ]
        text = t.write_po(t.header_text("core", "ja_JP"), entries)
        header, back = t.parse_po(text)
        self.assertIn("Language: ja_JP", header)
        self.assertEqual([(e.ctx, e.msgid, e.msgstr, e.obsolete) for e in back],
                         [(e.ctx, e.msgid, e.msgstr, e.obsolete) for e in entries])
        self.assertTrue(back[1].fuzzy)
        self.assertEqual(back[1].previous, "Sync!")
        self.assertEqual(t.write_po(header, back), text)

    def test_duplicate_key_rejected(self):
        text = 'msgid ""\nmsgstr ""\n\nmsgid "A"\nmsgstr ""\n\nmsgid "A"\nmsgstr ""\n'
        with self.assertRaises(ValueError):
            t.parse_po(text)

    def test_plural_rejected(self):
        with self.assertRaises(ValueError):
            t.parse_po('msgid "a"\nmsgid_plural "as"\nmsgstr[0] ""\n')

    def test_continuation_lines(self):
        _, entries = t.parse_po('msgid ""\nmsgstr ""\n\nmsgid ""\n"ab"\n"cd"\nmsgstr "x"\n')
        self.assertEqual(entries[0].msgid, "abcd")


class MergeTests(unittest.TestCase):
    def test_keeps_translations_fuzzes_changes_retires_removed(self):
        old = [t.Entry("*", "Import scale", "スケール"), t.Entry("*", "Removed thing", "削除")]
        template = [t.Entry("*", "Import scale", refs=["x:1"]), t.Entry("*", "Removed things", refs=["x:2"]),
                    t.Entry("*", "Brand new", refs=["x:3"])]
        out = t.merge(template, old)
        live = [e for e in out if not e.obsolete]
        self.assertEqual([e.msgid for e in live], ["Import scale", "Removed things", "Brand new"])
        self.assertEqual(live[0].msgstr, "スケール")
        self.assertFalse(live[0].fuzzy)
        self.assertTrue(live[1].fuzzy)
        self.assertEqual(live[1].previous, "Removed thing")
        self.assertEqual(live[2].msgstr, "")
        self.assertEqual([e for e in out if e.obsolete], [])  # the donor was reused, nothing left to retire

    def test_removed_translation_becomes_obsolete(self):
        out = t.merge([t.Entry("*", "Totally different")], [t.Entry("*", "Old", "古い")])
        self.assertEqual([(e.msgid, e.obsolete) for e in out], [("Totally different", False), ("Old", True)])


class CheckTests(unittest.TestCase):
    def test_placeholders(self):
        good = t.Entry("*", "%d of %(total)s {name}", "%(total)s 中 %d {name}")
        bad = t.Entry("*", "%d models", "モデル")
        self.assertEqual(t.entry_problems(good, "f"), [])
        self.assertTrue(t.entry_problems(bad, "f"))
        self.assertEqual(t.entry_problems(t.Entry("*", "100%% done", "100%% 完了"), "f"), [])

    def test_newlines(self):
        self.assertTrue(t.entry_problems(t.Entry("*", "a\nb", "ab"), "f"))


class CompileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.paths = {"locales": os.path.join(self.dir, "locales"), "catalog_rel": "x/i18n"}
        os.makedirs(self.paths["locales"])
        entries = [t.Entry("*", "B", "ビー"), t.Entry("*", "A", "エー"), t.Entry("Operator", "Sync", "同期"),
                   t.Entry("*", "Fuzzy", "曖昧", flags={"fuzzy"}), t.Entry("*", "Empty", "")]
        t.write_text(os.path.join(self.paths["locales"], "ja_JP.po"), t.write_po(t.header_text("x", "ja_JP"), entries))
        t.write_text(os.path.join(self.paths["locales"], "zh_HANS.po"),
                     t.write_po(t.header_text("x", "zh_HANS"), [t.Entry("*", "A", "")]))

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_excludes_fuzzy_empty_and_empty_locales(self):
        data = t.compiled_dict(self.paths)
        self.assertEqual(data, {"ja_JP": {("*", "A"): "エー", ("*", "B"): "ビー", ("Operator", "Sync"): "同期"}})
        self.assertIn(("*", "Fuzzy"), t.compiled_dict(self.paths, include_fuzzy=True)["ja_JP"])

    def test_output_is_deterministic_and_valid_python(self):
        one = t.render_compiled("x", self.paths)
        self.assertEqual(one, t.render_compiled("x", self.paths))
        tree = ast.parse(one)
        names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        self.assertEqual(names, {"register", "unregister"})
        self.assertLess(one.index("('*', 'A')"), one.index("('*', 'B')"))


class RepositoryTests(unittest.TestCase):
    """The committed catalogs of every configured domain whose source is checked out."""

    def test_release_domain_is_current(self):
        cfg = t.load_config()
        self.assertEqual(t.cmd_check(cfg, type("A", (), {"domain": "release"})()), 0)


if __name__ == "__main__":
    unittest.main()
