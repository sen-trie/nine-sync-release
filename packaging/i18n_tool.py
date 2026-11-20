#!/usr/bin/env python3
"""NineSync UI translation catalogs: extract, merge, check, compile, report coverage. Standard library only.

Three translation domains, each with its own catalog and its own runtime dictionary (see i18n/domains.json):
release (packaging/bundle), core (nine-sync-core) and fx (nine-sync-fx).

    python packaging/i18n_tool.py extract  [--domain D] [--check]   # source -> <catalog>/ui.pot
    python packaging/i18n_tool.py init     --domain D --locale L    # new <catalog>/locales/L.po
    python packaging/i18n_tool.py merge    [--domain D]             # ui.pot -> every locales/*.po (keeps translations)
    python packaging/i18n_tool.py compile  [--domain D] [--check] [--include-fuzzy --out PATH]
    python packaging/i18n_tool.py check    [--domain D]             # everything CI enforces
    python packaging/i18n_tool.py coverage [--domain D] [--json]
    python packaging/i18n_tool.py audit    [--domain D]             # strings Blender cannot translate as written

The .pot/.po files are the source of truth that translators edit (Poedit or any PO editor). The compiled
translations.py is generated, committed (so `blender extension build` works on each repo alone) and rejected by
`check` when it no longer matches the catalogs. Fuzzy entries are never compiled into a release build.
"""
import argparse
import ast
import difflib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "i18n", "domains.json")
TOOL = "packaging/i18n_tool.py"

DEFAULT_CTX = "*"
OPERATOR_CTX = "Operator"

PROP_FUNCS = {
    "BoolProperty", "BoolVectorProperty", "IntProperty", "IntVectorProperty", "FloatProperty",
    "FloatVectorProperty", "StringProperty", "EnumProperty", "PointerProperty", "CollectionProperty",
}
# UILayout / WindowManager calls whose keyword arguments Blender translates when drawn.
UI_KEYWORDS = {
    "text": "label", "heading": "label", "title": "label", "confirm_text": "label", "message": "label",
}
UI_FUNCS = {
    "label", "prop", "operator", "menu", "popover", "prop_enum", "prop_menu_enum", "prop_search",
    "prop_with_popover", "prop_with_menu", "prop_tabs_enum", "operator_menu_enum", "operator_enum",
    "menu_contents", "row", "column", "column_flow", "grid_flow", "box", "split", "panel", "panel_prop",
    "template_list", "template_ID", "invoke_props_dialog", "invoke_confirm", "invoke_popup",
    "invoke_props_popup", "popup_menu", "popover_menu",
}
# Explicit translation calls: name -> kind. The aliases follow Blender's own convention.
EXPLICIT = {
    "pgettext": "label", "pgettext_iface": "label", "pgettext_tip": "tooltip", "pgettext_rpt": "report",
    "pgettext_data": "data", "pgettext_n": "label",
    "iface_": "label", "tip_": "tooltip", "rpt_": "report", "data_": "data", "n_": "label", "_": "label",
}
KINDS = ("label", "tooltip", "report", "data")

PLACEHOLDER = re.compile(r"%(?:\([A-Za-z_]\w*\))?[-#0 +]*(?:\*|\d+)?(?:\.(?:\*|\d+))?[sdifrxXeEgGcoa]|\{[^{}]*\}")


# --- configuration --------------------------------------------------------------------------------------------


def load_config(path=CONFIG):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def domain_paths(cfg, name):
    dom = cfg["domains"][name]
    catalog = os.path.join(ROOT, dom["catalog_dir"])
    return {
        "source": os.path.join(ROOT, dom["source_root"]),
        "exclude": [e.strip("/") for e in dom.get("exclude", [])],
        "pot": os.path.join(catalog, "ui.pot"),
        "locales": os.path.join(catalog, "locales"),
        "compiled": os.path.join(ROOT, dom["compiled"]),
        "catalog_rel": dom["catalog_dir"],
    }


def selected(cfg, domain):
    names = list(cfg["domains"])
    if domain and domain not in names:
        sys.exit("unknown domain %r (have %s)" % (domain, ", ".join(names)))
    return [domain] if domain else names


# --- extraction -----------------------------------------------------------------------------------------------


class Entry:
    __slots__ = ("ctx", "msgid", "msgstr", "refs", "kinds", "flags", "previous", "comments", "obsolete")

    def __init__(self, ctx, msgid, msgstr="", refs=None, kinds=None, flags=None, previous=None, comments=None,
                 obsolete=False):
        self.ctx, self.msgid, self.msgstr = ctx, msgid, msgstr
        self.refs = refs if refs is not None else []
        self.kinds = kinds if kinds is not None else set()
        self.flags = flags if flags is not None else set()
        self.previous = previous
        self.comments = comments if comments is not None else []
        self.obsolete = obsolete

    @property
    def key(self):
        return (self.ctx, self.msgid)

    @property
    def fuzzy(self):
        return "fuzzy" in self.flags

    @property
    def translated(self):
        return bool(self.msgstr) and not self.fuzzy


def literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def call_name(func):
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def kw(call, name):
    for item in call.keywords:
        if item.arg == name:
            return item.value
    return None


def is_dynamic(node):
    """A value Blender would receive already formatted, so no catalog entry can match it."""
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.Add)):
        return not (isinstance(node.left, ast.Call) and call_name(node.left.func) in EXPLICIT)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return not (isinstance(node.func.value, ast.Call) and call_name(node.func.value.func) in EXPLICIT)
    return False


def wrapped(node):
    """An explicit translation call, possibly formatted afterwards: rpt_("...") or rpt_("... %s") % value."""
    if isinstance(node, ast.BinOp):
        node = node.left
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        node = node.func.value
    return isinstance(node, ast.Call) and call_name(node.func) in EXPLICIT


class Extractor(ast.NodeVisitor):
    def __init__(self, rel, tree):
        self.rel = rel
        self.found = []  # (ctx, msgid, kind, line)
        self.dynamic = []  # (line, where)
        self.constants = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                self.constants[node.targets[0].id] = node.value
        self.class_stack = []

    def add(self, ctx, msgid, kind, line):
        if msgid and msgid.strip():
            self.found.append((ctx or DEFAULT_CTX, msgid, kind, line))

    def visit_ClassDef(self, node):
        bases = [call_name(b) or "" for b in node.bases]
        is_operator = any(b.endswith("Operator") for b in bases)
        values = {}
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                values[stmt.targets[0].id] = stmt
        context = literal(values["bl_translation_context"].value) if "bl_translation_context" in values else None
        if "bl_label" in values:
            text = literal(values["bl_label"].value)
            self.add(context or (OPERATOR_CTX if is_operator else DEFAULT_CTX), text, "label", values["bl_label"].lineno)
        if "bl_description" in values:
            self.add(DEFAULT_CTX, literal(values["bl_description"].value), "tooltip", values["bl_description"].lineno)
        self.generic_visit(node)

    def enum_items(self, node, ctx, line):
        if isinstance(node, ast.Name) and node.id in self.constants:
            node = self.constants[node.id]
        if not isinstance(node, (ast.List, ast.Tuple)):
            return
        for item in node.elts:
            if isinstance(item, (ast.Tuple, ast.List)) and len(item.elts) >= 2:
                self.add(ctx, literal(item.elts[1]), "label", getattr(item, "lineno", line))
                if len(item.elts) >= 3:
                    self.add(DEFAULT_CTX, literal(item.elts[2]), "tooltip", getattr(item, "lineno", line))

    def visit_Call(self, node):
        name = call_name(node.func)
        if name in PROP_FUNCS:
            ctx = literal(kw(node, "translation_context")) if kw(node, "translation_context") is not None else None
            if kw(node, "name") is not None:
                self.add(ctx, literal(kw(node, "name")), "label", node.lineno)
            if kw(node, "description") is not None:
                self.add(DEFAULT_CTX, literal(kw(node, "description")), "tooltip", node.lineno)
            if name == "EnumProperty" and kw(node, "items") is not None:
                self.enum_items(kw(node, "items"), ctx, node.lineno)
        elif name in EXPLICIT and node.args:
            ctx = literal(node.args[1]) if len(node.args) > 1 else None
            if kw(node, "msgctxt") is not None:
                ctx = literal(kw(node, "msgctxt"))
            text = literal(node.args[0])
            if text is not None:
                self.add(ctx, text, EXPLICIT[name], node.lineno)
        elif name in UI_FUNCS:
            translate = kw(node, "translate")
            if not (isinstance(translate, ast.Constant) and translate.value is False):
                ctx = literal(kw(node, "text_ctxt")) if kw(node, "text_ctxt") is not None else None
                for key, kind in UI_KEYWORDS.items():
                    value = kw(node, key)
                    if value is None:
                        continue
                    if literal(value) is not None:
                        self.add(ctx, literal(value), kind, node.lineno)
                    elif is_dynamic(value):
                        self.dynamic.append((node.lineno, "%s(%s=...)" % (name, key)))
        elif name == "report" and len(node.args) >= 2:
            value = node.args[1]
            if literal(value) is not None:
                # Blender translates a literal report message itself (verified on 5.3.0); a message formatted
                # before it reaches report() never matches, so those need rpt_("... %s") % value.
                self.add(DEFAULT_CTX, literal(value), "report", node.lineno)
            elif is_dynamic(value):
                self.dynamic.append((node.lineno, "report(...) formatted before translation"))
            elif not wrapped(value):
                self.dynamic.append((node.lineno, "report(<variable>): translate where the text is built"))
        self.generic_visit(node)


def iter_sources(paths):
    source, exclude = paths["source"], paths["exclude"]
    for dirpath, dirnames, filenames in os.walk(source):
        rel_dir = os.path.relpath(dirpath, source).replace(os.sep, "/")
        dirnames[:] = sorted(
            d for d in dirnames
            if not d.startswith((".", "__"))
            and not any(fnmatch_dir((rel_dir + "/" + d).lstrip("./"), e) for e in exclude)
        )
        for filename in sorted(filenames):
            if filename.endswith(".py") and filename != "translations.py":
                rel = (rel_dir + "/" + filename).lstrip("./") if rel_dir != "." else filename
                yield os.path.join(dirpath, filename), rel


def fnmatch_dir(rel, pattern):
    return rel == pattern or rel.startswith(pattern + "/")


def extract(paths):
    """Returns (entries in a stable order, dynamic findings)."""
    entries, dynamic = {}, []
    for path, rel in iter_sources(paths):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as error:
            sys.exit("cannot parse %s: %s" % (rel, error))
        ex = Extractor(rel, tree)
        ex.visit(tree)
        for ctx, msgid, kind, line in ex.found:
            entry = entries.setdefault((ctx, msgid), Entry(ctx, msgid))
            ref = "%s:%d" % (rel, line)
            if ref not in entry.refs:
                entry.refs.append(ref)
            entry.kinds.add(kind)
        dynamic += [(rel, line, where) for line, where in ex.dynamic]

    def order(entry):
        path, line = entry.refs[0].rsplit(":", 1)
        return (path, int(line), entry.ctx, entry.msgid)

    return sorted(entries.values(), key=order), dynamic


# --- PO reading and writing -----------------------------------------------------------------------------------


def escape(text):
    return (text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
            .replace("\r", "\\r"))


_UNESCAPE = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}


def unescape(text, where):
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            if i + 1 >= len(text) or text[i + 1] not in _UNESCAPE:
                raise ValueError("%s: bad escape in %r" % (where, text))
            out.append(_UNESCAPE[text[i + 1]])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def parse_po(text, name="<po>"):
    """Returns (header msgstr, [Entry]). Raises ValueError on malformed input or duplicate keys."""
    header, entries, seen = None, [], set()
    cur, field = None, None

    def finish():
        nonlocal header, cur
        if cur is None:
            return
        if cur.get("msgid") is None:
            raise ValueError("%s: entry without msgid near line %d" % (name, cur["line"]))
        if cur.get("plural"):
            raise ValueError("%s:%d: plural forms are not supported" % (name, cur["line"]))
        ctx = cur.get("msgctxt")
        if cur["msgid"] == "" and ctx is None and not cur["obsolete"]:
            header = cur.get("msgstr", "")
        else:
            entry = Entry(ctx if ctx is not None else DEFAULT_CTX, cur["msgid"], cur.get("msgstr", ""),
                          refs=cur["refs"], kinds=cur["kinds"], flags=cur["flags"], previous=cur.get("previous"),
                          comments=cur["comments"], obsolete=cur["obsolete"])
            if not entry.obsolete:
                if entry.key in seen:
                    raise ValueError("%s:%d: duplicate msgctxt/msgid %r" % (name, cur["line"], entry.key))
                seen.add(entry.key)
            entries.append(entry)
        cur = None

    def new(line):
        return {"line": line, "refs": [], "kinds": set(), "flags": set(), "comments": [], "obsolete": False}

    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            finish()
            field = None
            continue
        obsolete = line.startswith("#~")
        if obsolete:
            line = line[2:].strip()
            if line.startswith("|"):
                continue
        if line.startswith("#") and not obsolete:
            if cur is not None and cur.get("msgid") is not None:
                finish()
            cur = cur or new(number)
            if line.startswith("#:"):
                cur["refs"] += line[2:].split()
            elif line.startswith("#."):
                body = line[2:].strip()
                if body.startswith("kind:"):
                    cur["kinds"] |= {k.strip() for k in body[5:].split(",") if k.strip()}
            elif line.startswith("#,"):
                cur["flags"] |= {f.strip() for f in line[2:].split(",") if f.strip()}
            elif line.startswith("#|"):
                match = re.match(r'msgid\s+"(.*)"$', line[2:].strip())
                if match:
                    cur["previous"] = unescape(match.group(1), "%s:%d" % (name, number))
            else:
                cur["comments"].append(line[1:].lstrip() if len(line) > 1 else "")
            continue
        match = re.match(r'(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+"(.*)"$', line)
        if match:
            keyword, value = match.group(1), unescape(match.group(2), "%s:%d" % (name, number))
            if keyword == "msgctxt" or (keyword == "msgid" and cur is not None and cur.get("msgid") is not None):
                if cur is not None and cur.get("msgid") is not None:
                    finish()
            cur = cur or new(number)
            cur["obsolete"] = cur["obsolete"] or obsolete
            if keyword == "msgid_plural" or keyword.startswith("msgstr["):
                cur["plural"] = True
                keyword = "msgstr" if keyword.startswith("msgstr[") else "plural"
            cur[keyword] = value
            field = keyword
            continue
        match = re.match(r'"(.*)"$', line)
        if match and cur is not None and field:
            cur[field] = cur.get(field, "") + unescape(match.group(1), "%s:%d" % (name, number))
            continue
        raise ValueError("%s:%d: cannot parse %r" % (name, number, raw))
    finish()
    return header, entries


def header_text(domain, locale=None, existing=None):
    if existing is not None:
        return existing
    fields = [
        ("Project-Id-Version", "NineSync %s" % domain),
        ("Report-Msgid-Bugs-To", "https://github.com/sen-trie/nine-sync-release/issues"),
        ("Language", locale or ""),
        ("MIME-Version", "1.0"),
        ("Content-Type", "text/plain; charset=UTF-8"),
        ("Content-Transfer-Encoding", "8bit"),
        ("X-NineSync-Domain", domain),
    ]
    if locale:
        fields.insert(2, ("Language-Team", "NineSync %s translators" % locale))
    return "".join("%s: %s\n" % f for f in fields)


def write_po(header, entries, with_strings=True):
    out = ["# NineSync UI catalog. Generated layout: edit msgstr values only; see DEVELOPER_GUIDE.md#translations.",
           'msgid ""', 'msgstr ""']
    out += ['"%s"' % escape(line + "\n") for line in header.splitlines()]
    for entry in entries:
        if entry.obsolete:
            continue
        out.append("")
        out += ["# " + c if c else "#" for c in entry.comments]
        if entry.kinds:
            out.append("#. kind: " + ", ".join(sorted(entry.kinds)))
        if entry.refs:
            out.append("#: " + " ".join(entry.refs))
        if entry.flags:
            out.append("#, " + ", ".join(sorted(entry.flags)))
        if entry.previous is not None and entry.fuzzy:
            out.append('#| msgid "%s"' % escape(entry.previous))
        if entry.ctx != DEFAULT_CTX:
            out.append('msgctxt "%s"' % escape(entry.ctx))
        out.append('msgid "%s"' % escape(entry.msgid))
        out.append('msgstr "%s"' % escape(entry.msgstr if with_strings else ""))
    for entry in sorted((e for e in entries if e.obsolete), key=lambda e: e.key):
        out.append("")
        if entry.ctx != DEFAULT_CTX:
            out.append('#~ msgctxt "%s"' % escape(entry.ctx))
        out.append('#~ msgid "%s"' % escape(entry.msgid))
        out.append('#~ msgstr "%s"' % escape(entry.msgstr))
    return "\n".join(out) + "\n"


def read_text(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read().replace("\r\n", "\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def locale_files(paths):
    if not os.path.isdir(paths["locales"]):
        return []
    return sorted(
        (name[:-3], os.path.join(paths["locales"], name))
        for name in os.listdir(paths["locales"]) if name.endswith(".po")
    )


# --- merge ------------------------------------------------------------------------------------------------------


def merge(template, old_entries):
    """New entry list in template order. Existing translations are kept; a changed source string gets the closest
    old translation marked fuzzy; strings that disappeared stay at the end as obsolete (#~)."""
    old = {e.key: e for e in old_entries if not e.obsolete}
    retired = {e.key: e for e in old_entries if e.obsolete}
    used, result = set(), []
    for tpl in template:
        entry = Entry(tpl.ctx, tpl.msgid, refs=list(tpl.refs), kinds=set(tpl.kinds))
        prior = old.get(tpl.key) or retired.get(tpl.key)
        if prior is not None:
            entry.msgstr, entry.flags, entry.comments = prior.msgstr, set(prior.flags), list(prior.comments)
            entry.previous = prior.previous
            used.add(tpl.key)
        else:
            pool = [k for k in old if k[0] == tpl.ctx and k not in used and k not in {t.key for t in template}]
            close = difflib.get_close_matches(tpl.msgid, [k[1] for k in pool], n=1, cutoff=0.8)
            if close and old[(tpl.ctx, close[0])].msgstr:
                donor = old[(tpl.ctx, close[0])]
                entry.msgstr, entry.flags = donor.msgstr, {"fuzzy"}
                entry.previous, entry.comments = donor.msgid, list(donor.comments)
                used.add(donor.key)
        if not entry.fuzzy:
            entry.previous = None
        if "python-format" in entry.flags:
            entry.flags.discard("python-format")
        result.append(entry)
    live = {t.key for t in template}
    for key, entry in sorted(old.items()):
        if key not in live and key not in used and entry.msgstr:
            result.append(Entry(entry.ctx, entry.msgid, entry.msgstr, obsolete=True))
    for key, entry in sorted(retired.items()):
        if key not in live and key not in used and key not in old:
            result.append(entry)
    return result


# --- checks -----------------------------------------------------------------------------------------------------


def placeholders(text):
    return sorted(PLACEHOLDER.findall(text.replace("%%", "")))


def entry_problems(entry, where):
    problems = []
    if not entry.msgstr:
        return problems
    if placeholders(entry.msgid) != placeholders(entry.msgstr):
        problems.append("%s: placeholders differ in %r: %s vs %s"
                        % (where, entry.msgid, placeholders(entry.msgid), placeholders(entry.msgstr)))
    if entry.msgid.count("\n") != entry.msgstr.count("\n"):
        problems.append("%s: line breaks differ in %r" % (where, entry.msgid))
    if entry.msgid.endswith((" ", ":")) and not entry.msgstr.endswith((entry.msgid[-1], "：")):
        problems.append("%s: trailing %r dropped in %r" % (where, entry.msgid[-1], entry.msgid))
    return problems


# --- compile ----------------------------------------------------------------------------------------------------

COMPILED_TEMPLATE = '''\
# SPDX-License-Identifier: GPL-3.0-or-later
# Generated by %(tool)s from %(catalog)s/locales/*.po. Do not edit: change the .po file and run
#     python %(tool)s compile --domain %(domain)s
# Untranslated and fuzzy entries are left out, so Blender shows the English text for them.
import bpy

translations_dict = %(body)s


# Adds this domain's dictionary under `owner`, the registering package's __name__, so the standalone and the
# bundled copy of a component never share a registration.
def register(owner):
    if not translations_dict:
        return
    try:
        bpy.app.translations.register(owner, translations_dict)
    except ValueError:
        # Left registered by an earlier enable that did not unregister (e.g. a failed reload).
        bpy.app.translations.unregister(owner)
        bpy.app.translations.register(owner, translations_dict)


def unregister(owner):
    if not translations_dict:
        return
    try:
        bpy.app.translations.unregister(owner)
    except ValueError:
        pass
'''


def compiled_dict(paths, include_fuzzy=False):
    result = {}
    for locale, path in locale_files(paths):
        _, entries = parse_po(read_text(path), path)
        table = {}
        for entry in entries:
            if entry.obsolete or not entry.msgstr or (entry.fuzzy and not include_fuzzy):
                continue
            table[(entry.ctx, entry.msgid)] = entry.msgstr
        if table:
            result[locale] = table
    return result


def fuzzy_counts(paths):
    counts = {}
    for locale, path in locale_files(paths):
        _, entries = parse_po(read_text(path), path)
        counts[locale] = sum(1 for e in entries if not e.obsolete and e.fuzzy and e.msgstr)
    return counts


def render_compiled(domain, paths, include_fuzzy=False):
    data = compiled_dict(paths, include_fuzzy)
    if not data:
        body = "{}"
    else:
        lines = ["{"]
        for locale in sorted(data):
            lines.append("    %r: {" % locale)
            for key in sorted(data[locale]):
                lines.append("        (%r, %r): %r," % (key[0], key[1], data[locale][key]))
            lines.append("    },")
        lines.append("}")
        body = "\n".join(lines)
    return COMPILED_TEMPLATE % {"tool": TOOL, "catalog": paths["catalog_rel"], "domain": domain, "body": body}


# --- commands ---------------------------------------------------------------------------------------------------


def cmd_extract(cfg, args):
    failed = False
    for name in selected(cfg, args.domain):
        paths = domain_paths(cfg, name)
        entries, _ = extract(paths)
        text = write_po(header_text(name), entries, with_strings=False)
        current = read_text(paths["pot"]) if os.path.exists(paths["pot"]) else None
        if args.check:
            if current != text:
                print("STALE %s: %s does not match the source; run extract" % (name, rel(paths["pot"])))
                failed = True
            else:
                print("ok    %s: %s (%d strings)" % (name, rel(paths["pot"]), len(entries)))
        else:
            write_text(paths["pot"], text)
            print("%s: %d strings -> %s" % (name, len(entries), rel(paths["pot"])))
    return 1 if failed else 0


def cmd_init(cfg, args):
    paths = domain_paths(cfg, args.domain)
    target = os.path.join(paths["locales"], args.locale + ".po")
    if os.path.exists(target):
        sys.exit("%s exists; use merge" % rel(target))
    _, template = parse_po(read_text(paths["pot"]), paths["pot"])
    write_text(target, write_po(header_text(args.domain, args.locale), merge(template, [])))
    print("created", rel(target))
    return 0


def cmd_merge(cfg, args):
    for name in selected(cfg, args.domain):
        paths = domain_paths(cfg, name)
        _, template = parse_po(read_text(paths["pot"]), paths["pot"])
        for locale, path in locale_files(paths):
            header, entries = parse_po(read_text(path), path)
            merged = merge(template, entries)
            write_text(path, write_po(header_text(name, locale, header), merged))
            fuzzy = sum(1 for e in merged if e.fuzzy and not e.obsolete)
            print("%s/%s: %d strings, %d fuzzy" % (name, locale, len(template), fuzzy))
    return 0


def cmd_compile(cfg, args):
    failed = False
    names = selected(cfg, args.domain)
    if args.out and len(names) != 1:
        sys.exit("--out needs --domain")
    for name in names:
        paths = domain_paths(cfg, name)
        text = render_compiled(name, paths, include_fuzzy=args.include_fuzzy)
        target = args.out or paths["compiled"]
        if args.check:
            current = read_text(target) if os.path.exists(target) else None
            if current != text:
                print("STALE %s: %s does not match its .po files; run compile" % (name, rel(target)))
                failed = True
            else:
                print("ok    %s: %s" % (name, rel(target)))
        else:
            if args.include_fuzzy and not args.out:
                sys.exit("--include-fuzzy writes test builds only: pass --out")
            write_text(target, text)
            left_out = fuzzy_counts(paths) if not args.include_fuzzy else {}
            note = ", ".join("%s: %d fuzzy left out" % kv for kv in sorted(left_out.items()) if kv[1])
            print("%s -> %s%s" % (name, rel(target), " (%s)" % note if note else ""))
    return 1 if failed else 0


def cmd_check(cfg, args):
    problems = []
    for name in selected(cfg, args.domain):
        paths = domain_paths(cfg, name)
        if not os.path.exists(paths["pot"]):
            problems.append("%s: no %s; run extract" % (name, rel(paths["pot"])))
            continue
        entries, _ = extract(paths)
        if read_text(paths["pot"]) != write_po(header_text(name), entries, with_strings=False):
            problems.append("%s: %s is stale; run extract then merge" % (name, rel(paths["pot"])))
        _, template = parse_po(read_text(paths["pot"]), paths["pot"])
        keys = [e.key for e in template]
        for locale, path in locale_files(paths):
            try:
                text = read_text(path)
                _, po = parse_po(text, path)
            except (ValueError, UnicodeDecodeError) as error:
                problems.append(str(error))
                continue
            if [e.key for e in po if not e.obsolete] != keys:
                problems.append("%s: not merged with ui.pot; run merge" % rel(path))
            for entry in po:
                if not entry.obsolete:
                    problems += entry_problems(entry, rel(path))
        target = paths["compiled"]
        if not os.path.exists(target) or read_text(target) != render_compiled(name, paths):
            problems.append("%s: %s is stale; run compile" % (name, rel(target)))
    for problem in problems:
        print("FAIL", problem)
    if not problems:
        print("i18n check passed (%s)" % ", ".join(selected(cfg, args.domain)))
    return 1 if problems else 0


def coverage_rows(cfg, domain=None):
    rows = []
    for name in selected(cfg, domain):
        paths = domain_paths(cfg, name)
        if not os.path.exists(paths["pot"]):
            continue
        _, template = parse_po(read_text(paths["pot"]), paths["pot"])
        tooltips = sum(1 for e in template if "tooltip" in e.kinds)
        base = {"domain": name, "total": len(template), "tooltips": tooltips,
                "by_kind": {k: sum(1 for e in template if k in e.kinds) for k in KINDS}}
        locales = locale_files(paths)
        if not locales:
            rows.append(dict(base, locale=None, translated=0, fuzzy=0, missing=len(template), tooltips_translated=0))
        for locale, path in locales:
            _, po = parse_po(read_text(path), path)
            live = [e for e in po if not e.obsolete]
            rows.append(dict(
                base, locale=locale,
                translated=sum(1 for e in live if e.translated),
                fuzzy=sum(1 for e in live if e.fuzzy and e.msgstr),
                missing=sum(1 for e in live if not e.msgstr),
                tooltips_translated=sum(1 for e in live if e.translated and "tooltip" in e.kinds),
            ))
    return rows


def cmd_coverage(cfg, args):
    rows = coverage_rows(cfg, args.domain)
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    print("| Domain | Locale | Strings | Tooltips | Translated | Tooltips translated | Fuzzy | Missing |")
    print("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in rows:
        print("| %s | %s | %d | %d | %d | %d | %d | %d |" % (
            r["domain"], r["locale"] or "-", r["total"], r["tooltips"], r["translated"], r["tooltips_translated"],
            r["fuzzy"], r["missing"]))
    return 0


def cmd_audit(cfg, args):
    count = 0
    for name in selected(cfg, args.domain):
        _, dynamic = extract(domain_paths(cfg, name))
        for path, line, where in dynamic:
            print("%s: %s:%d: %s" % (name, path, line, where))
            count += 1
    print("%d call sites need an explicit translation call" % count)
    return 0


def rel(path):
    try:
        return os.path.relpath(path, ROOT).replace(os.sep, "/")
    except ValueError:  # another drive on Windows
        return os.path.abspath(path).replace(os.sep, "/")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("extract", "init", "merge", "compile", "check", "coverage", "audit"):
        p = sub.add_parser(command)
        p.add_argument("--domain", required=command == "init")
        p.add_argument("--config", default=CONFIG)
        if command in ("extract", "compile"):
            p.add_argument("--check", action="store_true")
        if command == "init":
            p.add_argument("--locale", required=True)
        if command == "compile":
            p.add_argument("--include-fuzzy", action="store_true")
            p.add_argument("--out")
        if command == "coverage":
            p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    return globals()["cmd_" + args.command](cfg, args)


if __name__ == "__main__":
    sys.exit(main())
