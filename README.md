# NineSync release repository

Packaging, dependency integration, validation and release tooling for NineSync, which brings MikuMikuDance projects, accessories and MME effects into Blender 5.3 or newer. The two add-ons are developed in their own repositories and pinned here as submodules:

- [NineSync: PMM Bridge (Core)](https://github.com/sen-trie/nine-sync-core)
- [NineSync: FX Importer (FX)](https://github.com/sen-trie/nine-sync-fx)

No release has been published yet.

### Installation Compatibility

NineSync supports two configurations:

1. **Standalone:** NineSync Core and FX enabled separately, with their required dependencies.
2. **Bundled:** The combined NineSync release enabled with its bundled dependencies.

Both configurations may be installed together, but **simultaneous activation is unsupported** and may cause conflicts or unexpected behavior.

Disable one configuration before enabling the other. Restarting Blender when switching is recommended.

## Building the bundled extension

Local (needs a clean tree, network for the pinned dependency archives):

```
python -I packaging/build_bundle.py
python -I packaging/validate_bundle.py dist/nine-sync-<version>-blender-extensions.zip
python -I packaging/validate_in_blender.py --blender <blender 5.3+> --zip dist/<zip> --report dist/blender-validation.json
```

CI: Actions > "Bundled release" > Run workflow. It builds, validates statically, validates inside an official Blender 5.3 or newer, and only on request creates a **draft** release once every owner gate in `packaging/release_gates.json` is true. Nothing is published automatically.

## Licence

NineSync is GPL-3.0-or-later. Bundled third-party components keep their own licences; see the dependency and licence audit once it exists.
