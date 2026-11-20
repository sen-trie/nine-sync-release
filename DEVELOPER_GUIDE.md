# NineSync Developer Guide

## Project Scope

NineSync brings MikuMikuDance (MMD) projects into Blender, including PMM synchronization and supported MME effects.

| Component | Repository | Responsibility |
| --- | --- | --- |
| **Core** | [nine-sync-core](https://github.com/sen-trie/nine-sync-core) | PMM read/write, motion and model sync, Rigify remap, camera, light, audio |
| **FX** | [nine-sync-fx](https://github.com/sen-trie/nine-sync-fx) | `.x` accessories, `.fx` translation, Geometry Nodes, shader nodes, caches and bakes |
| **Release** | [nine-sync-release](https://github.com/sen-trie/nine-sync-release) | Combined extension, packaging, CI, releases, documentation and translation tooling |

## Development Setup

Clone the release repository with its pinned Core and FX submodules:

```sh
git clone --recurse-submodules https://github.com/sen-trie/nine-sync-release.git
cd nine-sync-release
git submodule status
```

Install Blender 5.3.0+ and mmd_tools 4.5.5+. Build the extension you want to test:

```sh
# Combined extension (requires clean source trees)
python -I packaging/build_bundle.py --out dist --staging build/staging --cache build/downloads

# Standalone Core / FX (from their respective directories)
blender --command extension build --output-dir ../dist
```

Install the resulting ZIP from **Blender > Preferences > Get Extensions > Install from Disk**. Restart Blender after failed registration or when testing changes that do not reload cleanly. Logs appear in the Blender text block `NineSyncLog` and in the console.

## Project Structure

```text
nine-sync-release/
├── nine-sync-core/     # Core submodule
├── nine-sync-fx/       # FX submodule
├── packaging/          # Build, checks, releases, translations
│   └── bundle/         # Bundled extension wrapper
├── i18n/               # Release translation catalog and configuration
├── zensical/           # Documentation site
└── .github/            # CI and contribution templates
```

Make changes in the repository that owns the feature. Core and FX communicate through the versioned `ninesync_hooks` API, **not** direct imports. Coordinate changes to `hooks.py` across both repositories. The release repo pins component commits instead of copying their source manually.

## Coding Standards

- Preserve operator IDs (`ninesync.*`, `ninesync_fx.*`), saved properties, node-group identifiers and other serialized names. UI labels may change; saved-data identifiers must not.
- Use Blender-safe registration, cleanup and user-writable storage. Do not modify another installed add-on or inject global `sys.path` entries.
- Provide descriptions/tooltips for user-facing controls. Translate messages before formatting, leave internal logs and generated node trees in English.
- Keep source and third-party licensing compatible with GPL-3.0-or-later.

## Tests

Run the tests relevant to the repository and feature. Common entry points:

```sh
python -I packaging/test_i18n_tool.py
python -I packaging/i18n_tool.py check
python nine-sync-core/tests/check_static.py
blender -b --factory-startup --python nine-sync-core/tests/t_registration.py
```

Core and FX have additional tests in their `tests/` folders. Some Blender/FX integration tests require locally supplied fixtures. Use an isolated Blender profile for testing. For performance changes, measure an animated scene and record Blender version, hardware and test conditions.

## Translations

There are **three independent UI dictionaries**, owned by Release, Core and FX. Translators edit gettext `.po` files; generated `translations.py` files are compiled and committed. Use a PO editor such as [Poedit](https://poedit.net/).

```sh
# Replace core with fx or release as needed
python packaging/i18n_tool.py extract --domain core
python packaging/i18n_tool.py merge --domain core
python packaging/i18n_tool.py compile --domain core
python packaging/i18n_tool.py check
```

Keep placeholders unchanged, review fuzzy entries, and test labels, tooltips and reports in Blender. Do not translate identifiers, effect parameters, file extensions or user data. UI changes should update the relevant catalog, tooltip and manual page. Translation terminology is documented in the [glossary](zensical/docs/translations/glossary.md).

Documentation lives in `zensical/`. Translated pages are maintained separately from UI catalogs. Preview the docs with `cd zensical && zensical serve` after installing `requirements-docs.txt`.

## Release Process

1. Changes land in Core or FX and pass their tests. The release repository then updates its pinned submodule commits.
2. Release CI builds and validates the combined ZIP, including a Blender smoke test.
3. A draft GitHub Release is prepared, publishing and extension-repository approval are handled by maintainers.
4. Core and FX publish their standalone builds independently. The documentation site is deployed to match the released version.

See [packaging/README.md](packaging/README.md) for the full release checklist.

## Contributing

Open issues in the [release issue tracker](https://github.com/sen-trie/nine-sync-release/issues), but submit code changes to the owning repository. Keep PRs scoped, document reproduction steps and tests, and add user-visible changes to the owning `CHANGELOG.md`.

AI-assisted contributions are allowed, but the submitter must understand and review the result and verify all claimed tests.
