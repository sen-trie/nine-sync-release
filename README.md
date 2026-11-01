# NineSync release repository

Packaging, dependency integration, validation and release tooling for NineSync, which brings MikuMikuDance projects, accessories and MME effects into Blender 5.3 or newer. The two add-ons are developed in their own repositories and pinned here as submodules:

- [NineSync: PMM Bridge (Core)](https://github.com/sen-trie/nine-sync-core)
- [NineSync: FX Importer (FX)](https://github.com/sen-trie/nine-sync-fx)

No release has been published yet.

## Installing and updating in Blender

NineSync is distributed as a self-hosted Blender extension repository on GitHub Pages, generated with Blender's own `extension server-generate`. Once a stable release has been deployed:

1. Blender 5.3 or newer: Preferences > Get Extensions > Repositories (the dropdown at the top right) > **Add Remote Repository**.
2. URL: `https://sen-trie.github.io/nine-sync-release/index.json`. Keep "Check for Updates on Startup" on if you want update notices.
3. Install **NineSync** from that repository. Updates appear through Blender's normal extension update flow.

From a terminal: `blender --command extension repo-add --name nine_sync --url https://sen-trie.github.io/nine-sync-release/index.json`, then `blender --command extension install --enable ninesync_bundled`.

The same ZIPs are attached to GitHub Releases (with `.sha256`, `artifact-manifest.json` and validation reports) and can be installed with "Install from Disk". The repository only ever lists stable releases that passed every release gate; experimental pre-releases are GitHub pre-releases only. Until the first deployment the URL above returns 404.

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

CI: Actions > "Bundled release" > Run workflow. It builds, validates statically, validates inside an official Blender 5.3 or newer, and only on request creates a **draft** release and/or adds the build to the GitHub Pages extension repository, once every owner gate in `packaging/release_gates.json` is true and a reviewer approves the matching environment. Nothing is published automatically.

## Licence

NineSync is GPL-3.0-or-later. Bundled third-party components keep their own licences; see the dependency and licence audit once it exists.
