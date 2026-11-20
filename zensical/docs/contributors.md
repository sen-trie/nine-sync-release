# Contributors Wanted

NineSync benefits from people who use it in real projects, and from developers and writers who want to improve it. You do not need to be a programmer to help.

## Ways to help

**Testers:** Try realistic `.pmm`, `.x` and `.fx` projects and report what works and what does not ([Reporting and Triage](triage.md)).

**Translators:** Help make the interface and documentation accessible in more languages. Translations are `.po` files you can edit in any PO editor; the [Developer Guide](https://github.com/sen-trie/nine-sync-release/blob/main/DEVELOPER_GUIDE.md#translations) explains where they are and how to test them, and the [Translation Glossary](translations/glossary.md) lists the agreed terms and what stays in English.

**Documentation contributors:** Fix errors, clarify steps, add screenshots, or write an [example](examples/index.md). The documentation is Markdown in `zensical/docs/` of the release repository, and the navigation is in `zensical/zensical.toml`.

**Developers:** Fix bugs or add features in Core or FX. Start with the [Developer Guide](https://github.com/sen-trie/nine-sync-release/blob/main/DEVELOPER_GUIDE.md): repository layout, setup, architecture, tests and the release process.

## Which repository

| Repository | What it holds |
|---|---|
| [nine-sync-release](https://github.com/sen-trie/nine-sync-release) | documentation, packaging scripts, release workflows, issue templates 
| [nine-sync-core](https://github.com/sen-trie/nine-sync-core) | PMM Bridge: PMM parsing, PMM Sync, PMM Create, Rigify Remap
| [nine-sync-fx](https://github.com/sen-trie/nine-sync-fx) | FX Importer: `.x` accessories, MME `.fx` effects to nodes | accessories, effects, nodes, baking 

Core and FX are independent add-ons that share only a [hook registry](manual/core/pmm-sync/how-it-works/accessory-fx-integration.md#the-hook-registry). The release repository includes both as Git submodules.

## Pull request workflow

1. Open an issue first for anything larger than a small fix, so the approach can be agreed.
2. Fork the repository that owns the code, create a branch, and make a focused change.
3. Run the tests for that specific repository that apply.
4. Open a PR against that repository and describe what changed and how you checked it. Say what you could not test.
5. The PR is then reviewed. When it is merged in Core or FX, the release repository updates its submodule pointer later.

## AI coding tools

You may use AI tools such as Claude Code or Codex. You remain responsible for every line.

## Third-party assets

Only submit material you have the right to share. Do not include effect, model, motion or texture files made by others unless their licence or the author allows usage outside of MMD. Screenshots and renders in the documentation should show assets you may publish.
