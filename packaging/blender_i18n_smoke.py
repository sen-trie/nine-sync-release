"""Translation smoke test, run INSIDE Blender (background) against installed test extensions.

    blender -b --factory-startup --python-exit-code 1 --python packaging/blender_i18n_smoke.py -- <mode> <report.json>

mode: bundled | core | fx | mixed. The installed ZIPs must carry translations.py files compiled with
`i18n_tool.py compile --include-fuzzy`, so the (fuzzy) pilot locale is present; release builds leave fuzzy out.

Checks, with Translate Interface, Tooltips and Reports on and the language set to ja_JP:
- each expected domain registers under its own package name, and only those domains;
- a label, a tooltip and an operator report from each domain come back in Japanese through Blender's own lookup;
- a message missing from the catalog falls back to English;
- disabling the extension removes its dictionaries (the lookup returns English again);
- mixed: the combined extension refuses to start next to standalone Core, and the refusal is in Japanese.

Prints "I18N ok|FAIL <name>" lines, writes a JSON report and exits non-zero on any failure.
"""
import json
import sys

import addon_utils
import bpy

REPO = "bl_ext.user_default."
results = []
t = bpy.app.translations


def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": str(detail)})
    print("I18N %s %s%s" % ("ok  " if ok else "FAIL", name, (" | " + str(detail)) if detail or not ok else ""), flush=True)
    return ok


def japanese(text):
    return any("぀" <= ch <= "ヿ" or "一" <= ch <= "鿿" for ch in text)


def ja_sample(module, kind):
    """(context, msgid, msgstr) of one compiled ja_JP entry of the given kind that Blender itself does not translate."""
    table = module.translations_dict.get("ja_JP", {})
    for (ctx, msgid), msgstr in sorted(table.items()):
        if kind == "tooltip" and (len(msgid) < 25 or "%" in msgid):
            continue
        if kind == "label" and (len(msgid) > 24 or "%" in msgid or ctx != "*"):
            continue
        if kind == "operator" and ctx != "Operator":
            continue
        t.unregister(module_owner[module])
        builtin = t.pgettext_iface(msgid, ctx) != msgid
        module.register(module_owner[module])
        if not builtin:
            return ctx, msgid, msgstr
    return None


module_owner = {}


def domain_checks(label, package, module_path):
    module = sys.modules.get(module_path)
    if not check("%s: compiled module loaded" % label, module is not None, module_path):
        return None
    module_owner[module] = package
    check("%s: pilot locale compiled in" % label, bool(module.translations_dict.get("ja_JP")),
          "%d entries" % len(module.translations_dict.get("ja_JP", {})))
    for kind, lookup in (("label", t.pgettext_iface), ("tooltip", t.pgettext_tip), ("operator", t.pgettext_iface)):
        sample = ja_sample(module, kind)
        if sample is None:
            if kind == "operator" and label == "release":
                continue  # Release has no operators
            check("%s: a %s entry Blender does not translate itself" % (label, kind), label == "release", "none found")
            continue
        ctx, msgid, msgstr = sample
        got = lookup(msgid, ctx)
        check("%s: %s translated" % (label, kind), got == msgstr and japanese(got), "%r -> %r" % (msgid[:40], got[:40]))
    return module


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    mode, out = argv[0], argv[1]
    tooltips = json.load(open(argv[2], encoding="utf-8")) if len(argv) > 2 else {}
    view = bpy.context.preferences.view
    view.language = "ja_JP"
    view.use_translate_interface = view.use_translate_tooltips = view.use_translate_reports = True
    check("language is ja_JP", t.locale == "ja_JP", t.locale)
    check("missing message falls back to English", t.pgettext_iface("NineSync smoke: no such message") ==
          "NineSync smoke: no such message")

    if mode == "mixed":
        core, _ = enable(REPO + "ninesync")
        check("standalone Core enabled", core is not None)
        errors = []
        addon_utils.enable(REPO + "ninesync_bundled", default_set=False, handle_error=lambda e: errors.append(str(e)))
        text = " ".join(errors)
        check("combined refuses next to standalone Core", "NineSync" in text and bool(errors), text[:160])
        check("the refusal is in Japanese", japanese(text), text[:160])
        check("the combined extension left nothing registered",
              "bl_ext.user_default.ninesync_bundled" not in {m.__name__ for m in addon_utils.modules() if addon_utils.check(m.__name__)[1]})
        finish(out)
        return

    targets = {
        "bundled": [("release", REPO + "ninesync_bundled", REPO + "ninesync_bundled.translations"),
                    ("core", REPO + "ninesync_bundled.ninesync_core", REPO + "ninesync_bundled.ninesync_core.i18n.translations"),
                    ("fx", REPO + "ninesync_bundled.ninesync_fx", REPO + "ninesync_bundled.ninesync_fx.i18n.translations")],
        "core": [("core", REPO + "ninesync", REPO + "ninesync.i18n.translations")],
        "fx": [("fx", REPO + "ninesync_fx", REPO + "ninesync_fx.i18n.translations")],
    }[mode]
    extension = {"bundled": "ninesync_bundled", "core": "ninesync", "fx": "ninesync_fx"}[mode]
    module, errors = enable(REPO + extension)
    if not check("%s enabled" % extension, module is not None and not errors, errors):
        finish(out)
        return
    samples = []
    for label, package, path in targets:
        compiled = domain_checks(label, package, path)
        if compiled is not None:
            sample = ja_sample(compiled, "tooltip") or ja_sample(compiled, "label")
            if sample:
                samples.append((label, sample))
        try:
            t.register(package, {"ja_JP": {("*", "probe"): "probe"}})
            check("%s: registered under its own package name" % label, False, "owner %s was free" % package)
            t.unregister(package)
        except ValueError:
            check("%s: registered under its own package name" % label, True, package)

    # Real tooltips: catalog entries of kind "tooltip" that are the description of a property or operator this
    # extension registered, looked up the way Blender draws a tooltip.
    descriptions = registered_descriptions()
    for label, _, _ in targets:
        for ctx, msgid, msgstr in tooltips.get(label, []):
            if msgid not in descriptions:
                continue
            got = t.pgettext_tip(msgid, ctx)
            check("%s: tooltip of %s translated" % (label, descriptions[msgid]), got == msgstr and japanese(got),
                  "%r -> %r" % (msgid[:40], got[:40]))
            break
        else:
            check("%s: a registered tooltip found to test" % label, label == "release", "none of the samples is registered")

    # A report through Blender's report path: an operator's literal message, translated by Blender itself.
    if samples:
        label, (ctx, msgid, msgstr) = samples[0]

        class NINESYNC_OT_i18n_probe(bpy.types.Operator):
            bl_idname = "ninesync_i18n.probe"
            bl_label = "probe"

            def execute(self, context):
                self.report({"ERROR"}, msgid)
                return {"CANCELLED"}

        bpy.utils.register_class(NINESYNC_OT_i18n_probe)
        try:
            bpy.ops.ninesync_i18n.probe()
            text = ""
        except RuntimeError as error:
            text = str(error)
        bpy.utils.unregister_class(NINESYNC_OT_i18n_probe)
        check("report text is translated (%s)" % label, msgstr in text, text[:120])

    addon_utils.disable(REPO + extension, default_set=False)
    for label, (ctx, msgid, msgstr) in samples:
        check("%s: dictionary removed on disable" % label, t.pgettext_tip(msgid, ctx) == msgid, t.pgettext_tip(msgid, ctx)[:60])
    module, errors = enable(REPO + extension)
    check("re-enable works", module is not None and not errors, errors)
    for label, (ctx, msgid, msgstr) in samples:
        check("%s: translated again after re-enable" % label, t.pgettext_tip(msgid, ctx) == msgstr)
    addon_utils.disable(REPO + extension, default_set=False)
    finish(out)


def registered_descriptions():
    """{description: 'Type.property'} for every registered RNA struct, property and enum item description."""
    found = {}
    for name in dir(bpy.types):
        cls = getattr(bpy.types, name, None)
        rna = getattr(cls, "bl_rna", None)
        if rna is None:
            continue
        if rna.description:
            found.setdefault(rna.description, name)
        for prop in rna.properties:
            if prop.description:
                found.setdefault(prop.description, "%s.%s" % (name, prop.identifier))
            for item in getattr(prop, "enum_items", ()):
                if item.description:
                    found.setdefault(item.description, "%s.%s[%s]" % (name, prop.identifier, item.identifier))
    return found


def enable(name):
    errors = []
    module = addon_utils.enable(name, default_set=False, handle_error=lambda e: errors.append(repr(e)))
    return module, errors


def finish(out):
    failed = [r for r in results if not r["ok"]]
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"results": results, "failed": len(failed), "blender": bpy.app.version_string,
                   "build_hash": bpy.app.build_hash.decode()}, handle, indent=2, ensure_ascii=False)
    print("I18N %d checks, %d failed" % (len(results), len(failed)), flush=True)
    if failed:
        sys.exit(1)


main()
