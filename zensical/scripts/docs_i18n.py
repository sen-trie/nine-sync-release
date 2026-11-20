#!/usr/bin/env python3
"""Documentation and GitHub Markdown translations: inventory, status and per-locale site builds. Stdlib only.

    python zensical/scripts/docs_i18n.py inventory [--check]     # every docs page has an owner (release/core/fx)
    python zensical/scripts/docs_i18n.py status [--locale L]     # missing / current / stale, per domain and surface
    python zensical/scripts/docs_i18n.py stamp --locale L PAGE   # record which English version a translation matches
    python zensical/scripts/docs_i18n.py build --locale L        # build the locale site into zensical/site/<slug>/

English pages live in zensical/docs/ and keep their URLs. A translated page lives at the same relative path in
zensical/i18n/<locale>/ and starts with front matter `translation_of: <hash>`, the hash of the English page it
translates; when the English page changes, the translation shows as stale. A locale build uses the translated page
where one exists and the English page with a visible notice otherwise, so navigation never breaks.

GitHub Markdown (README.md and the like) is translated next to the English file in the repository that owns it,
e.g. README.ja.md, with `<!-- translation_of: <hash> -->` as its first line.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_ROOT = os.path.dirname(HERE)                       # zensical/
REPO = os.path.dirname(SITE_ROOT)                       # release repo
DOCS = os.path.join(SITE_ROOT, "docs")
I18N = os.path.join(SITE_ROOT, "i18n")
PAGES = os.path.join(SITE_ROOT, "translations", "pages.json")
CONFIG = os.path.join(SITE_ROOT, "zensical.toml")
DOMAINS = os.path.join(REPO, "i18n", "domains.json")

# Blender locale -> URL slug, file suffix for GitHub Markdown, Zensical theme language.
LOCALES = {
    "ja_JP": {"slug": "ja", "suffix": "ja", "theme": "ja", "notice": "このページはまだ翻訳されていません。英語の原文を表示しています。"},
    "zh_HANS": {"slug": "zh-hans", "suffix": "zh-Hans", "theme": "zh", "notice": "本页尚未翻译，以下为英文原文。"},
}
GITHUB = {
    "release": ["README.md", "CONTRIBUTING.md", "DEVELOPER_GUIDE.md"],
    "core": ["nine-sync-core/README.md"],
    "fx": ["nine-sync-fx/README.md"],
}
FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)
MARK = re.compile(r"\A<!-- translation_of: ([0-9a-f]+) -->\n")


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read().replace(b"\r\n", b"\n")).hexdigest()[:16]


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read().replace("\r\n", "\n")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def english_pages():
    found = []
    for dirpath, dirnames, filenames in os.walk(DOCS):
        dirnames.sort()
        for name in sorted(filenames):
            if name.endswith(".md"):
                found.append(os.path.relpath(os.path.join(dirpath, name), DOCS).replace(os.sep, "/"))
    return found


def owners():
    with open(PAGES, encoding="utf-8") as handle:
        data = json.load(handle)
    table = {}
    for rule in data["owners"]:
        table[rule["path"]] = rule["owner"]
    return table


def owner_of(page, table):
    best = None
    for prefix, owner in table.items():
        if prefix == "" or page == prefix or (prefix.endswith("/") and page.startswith(prefix)):
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, owner)
    return best[1] if best else None


def translation_state(source, translated, front=True):
    if not os.path.exists(translated):
        return "missing"
    text = read(translated)
    match = FRONT.match(text) if front else MARK.match(text)
    if not match:
        return "unstamped"
    value = re.search(r"translation_of:\s*([0-9a-f]+)", match.group(0))
    if value is None:
        return "unstamped"
    return "current" if value.group(1) == digest(source) else "stale"


def cmd_inventory(args):
    table = owners()
    pages = english_pages()
    unowned = [p for p in pages if owner_of(p, table) is None]
    unknown = sorted(set(o for o in table.values()) - {"release", "core", "fx"})
    if args.check:
        for page in unowned:
            print("FAIL no owner for zensical/docs/%s in translations/pages.json" % page)
        for owner in unknown:
            print("FAIL unknown owner %r" % owner)
        if not unowned and not unknown:
            print("ok    %d pages, every page has an owner" % len(pages))
        return 1 if unowned or unknown else 0
    counts = {}
    for page in pages:
        counts.setdefault(owner_of(page, table) or "(none)", []).append(page)
    for owner in sorted(counts):
        print("%s: %d pages" % (owner, len(counts[owner])))
        for page in counts[owner]:
            print("    " + page)
    return 0


def cmd_status(args):
    table = owners()
    locales = [args.locale] if args.locale else list(LOCALES)
    rows = []
    for locale in locales:
        for page in english_pages():
            state = translation_state(os.path.join(DOCS, page), os.path.join(I18N, locale, page))
            rows.append((owner_of(page, table), "docs", locale, page, state))
        for owner, files in GITHUB.items():
            for rel in files:
                source = os.path.join(REPO, rel)
                if not os.path.exists(source):
                    continue
                target = source[:-3] + "." + LOCALES[locale]["suffix"] + ".md"
                rows.append((owner, "github", locale, rel, translation_state(source, target, front=False)))
    if args.json:
        print(json.dumps([dict(zip(("owner", "surface", "locale", "page", "state"), r)) for r in rows], indent=2))
        return 0
    summary = {}
    for owner, surface, locale, _, state in rows:
        summary.setdefault((owner, surface, locale), {}).setdefault(state, 0)
        summary[(owner, surface, locale)][state] += 1
    print("| Owner | Surface | Locale | Pages | Current | Stale | Missing |")
    print("| --- | --- | --- | ---: | ---: | ---: | ---: |")
    for key in sorted(summary, key=lambda k: (k[0] or "", k[1], k[2])):
        s = summary[key]
        print("| %s | %s | %s | %d | %d | %d | %d |" % (key[0], key[1], key[2], sum(s.values()), s.get("current", 0),
                                                        s.get("stale", 0) + s.get("unstamped", 0), s.get("missing", 0)))
    stale = [r for r in rows if r[4] in ("stale", "unstamped")]
    for owner, surface, locale, page, state in stale:
        print("%s: %s/%s %s" % (state.upper(), locale, page, "(%s)" % surface))
    return 0


def cmd_stamp(args):
    page = args.page.replace("\\", "/")
    source = os.path.join(DOCS, page)
    target = os.path.join(I18N, args.locale, page)
    if not os.path.exists(source) or not os.path.exists(target):
        sys.exit("need both zensical/docs/%s and zensical/i18n/%s/%s" % (page, args.locale, page))
    text = read(target)
    stamp = "translation_of: %s" % digest(source)
    match = FRONT.match(text)
    if match:
        body = re.sub(r"(?m)^translation_of:.*$\n?", "", match.group(1)).strip()
        front = (body + "\n" if body else "") + stamp
        text = "---\n%s\n---\n" % front + text[match.end():]
    else:
        text = "---\n%s\n---\n" % stamp + text
    write(target, text)
    print("stamped %s/%s" % (args.locale, page))
    return 0


def toml_set(text, table, key, value):
    """Sets `key = value` inside [table] of a TOML text (adds the key when absent)."""
    lines, out, current, done = text.split("\n"), [], None, False
    for i, line in enumerate(lines):
        header = re.match(r"^\[\[?([^\[\]]+)\]\]?\s*$", line.strip())
        if header:
            if current == table and not done:
                out.append("%s = %s" % (key, value))
                done = True
            current = header.group(1).strip()
        elif current == table and re.match(r"^%s\s*=" % re.escape(key), line.strip()) and not done:
            out.append("%s = %s" % (key, value))
            done = True
            continue
        out.append(line)
    if not done:
        if current == table:
            out.append("%s = %s" % (key, value))
        else:
            out += ["", "[%s]" % table, "%s = %s" % (key, value)]
    return "\n".join(out)


def cmd_build(args):
    info = LOCALES[args.locale]
    stage = os.path.join(SITE_ROOT, ".build", args.locale)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.copytree(DOCS, os.path.join(stage, "docs"))
    translated = fallback = 0
    for page in english_pages():
        target = os.path.join(stage, "docs", page)
        source = os.path.join(I18N, args.locale, page)
        if os.path.exists(source):
            text = read(source)
            match = FRONT.match(text)
            if match:
                rest = re.sub(r"(?m)^translation_of:.*$\n?", "", match.group(1)).strip()
                text = ("---\n%s\n---\n" % rest if rest else "") + text[match.end():]
            write(target, text)
            translated += 1
        else:
            text = read(target)
            match = FRONT.match(text)
            head, body = (text[:match.end()], text[match.end():]) if match else ("", text)
            lines = body.split("\n")
            at = next((i + 1 for i, l in enumerate(lines) if l.startswith("# ")), 0)
            notice = ['', '!!! note "%s"' % info["notice"], '    [English](/%s)' % page[:-3].replace("index", ""), '']
            write(target, head + "\n".join(lines[:at] + notice + lines[at:]))
            fallback += 1
    config = read(CONFIG)
    config = toml_set(config, "project", "docs_dir", '"docs"')
    out = os.path.abspath(args.out or os.path.join(SITE_ROOT, "site", info["slug"]))
    config = toml_set(config, "project", "site_dir", '"site"')  # Zensical wants it inside the project; copied to `out`
    url = re.search(r'(?m)^site_url\s*=\s*"([^"]*)"', config)
    if url:
        config = toml_set(config, "project", "site_url", '"%s%s/"' % (url.group(1).rstrip("/") + "/", info["slug"]))
    config = toml_set(config, "project.theme", "language", '"%s"' % info["theme"])
    cfg_path = os.path.join(stage, "zensical.toml")
    write(cfg_path, config)
    for name in ("overrides",):
        if os.path.isdir(os.path.join(SITE_ROOT, name)):
            shutil.copytree(os.path.join(SITE_ROOT, name), os.path.join(stage, name))
    print("%s: %d translated, %d English fallback pages" % (args.locale, translated, fallback))
    if args.stage_only:
        print("staged in", os.path.relpath(stage, REPO))
        return 0
    code = subprocess.call([sys.executable, "-m", "zensical", "build", "-f", cfg_path], cwd=stage)
    if code == 0:
        shutil.rmtree(out, ignore_errors=True)
        shutil.copytree(os.path.join(stage, "site"), out)
        print("built", out)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("inventory")
    p.add_argument("--check", action="store_true")
    p = sub.add_parser("status")
    p.add_argument("--locale", choices=sorted(LOCALES))
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("stamp")
    p.add_argument("--locale", required=True, choices=sorted(LOCALES))
    p.add_argument("page")
    p = sub.add_parser("build")
    p.add_argument("--locale", required=True, choices=sorted(LOCALES))
    p.add_argument("--out")
    p.add_argument("--stage-only", action="store_true")
    args = parser.parse_args(argv)
    return globals()["cmd_" + args.command](args)


if __name__ == "__main__":
    sys.exit(main())
