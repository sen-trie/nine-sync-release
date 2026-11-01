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

## Licence

NineSync is GPL-3.0-or-later. Bundled third-party components keep their own licences; see the dependency and licence audit once it exists.
