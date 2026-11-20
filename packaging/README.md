# Packaging

Build and release tools for the combined NineSync Blender extension. Scripts use Python's standard library only.

| Files | Purpose |
| --- | --- |
| `build_bundle.py`, `validate_bundle.py` | Build a reproducible ZIP, checksums and manifest; check structure, dependencies, licences and source integrity |
| `validate_in_blender.py`, `blender_smoke.py`, `fetch_blender.py` | Validate installation with an isolated profile and an official Blender 5.3+ build |
| `check_publish_gates.py`, `extension_repo.py` | Check stable release eligibility; assemble and verify the GitHub Pages extension repository |
| `check_experimental.py`, `experimental_notes.py`, `release_gates.json` | Check experimental releases and required acknowledgements |
| `update_components.py`, `components.json` | Prepare Core/FX pin updates as PRs; never merge or release automatically |
| `dependencies.lock`, `test_fixtures.lock`, `VERSIONING.md` | Pinned dependencies, test-only fixtures and Bundled versioning rules |

## Stable releases

`.github/workflows/release.yml` runs when a component pin or Bundled manifest changes on `main`, or by manual dispatch.

1. Build the ZIP from clean, pinned sources; run static checks and installation tests in an official Blender 5.3+.
2. After `release` approval, create a **draft** GitHub Release tagged from `bundle/blender_manifest.toml`. A published tag cannot be reused; an existing unpublished draft may be replaced.
3. After `extension-repository` approval, rebuild the GitHub Pages repository using verified previously published ZIPs plus the new ZIP. Reject prereleases, version downgrades, conflicting IDs and changed ZIPs for existing versions.
4. Deploy to Pages and verify the public `index.json` and ZIP over HTTPS against the validated artifact. A person publishes the draft release.

Published versions remain available. To roll back, publish a corrected newer version; do not overwrite an existing ZIP.

## Experimental releases

`.github/workflows/experimental-release.yml` is **manual only** (for example, `v0.1.0-alpha.1`). It runs the same build and static checks, but **does not test in Blender**.

- Inputs: `release_tag`, `acknowledge=EXPERIMENTAL`, and `publish` (optional).
- Publishing requires `experimental-release` environment approval and creates a GitHub **pre-release** marked as unvalidated in Blender.
- Existing tags are untouched. The prerelease tag does not change the version inside the ZIP.
- Experimental builds never enter the GitHub Pages extension repository; stable releases use `release.yml`.

## Dependencies

- **DirectX `.x` importer:** Bundles `importer.py`, `parser.py` and `LICENSE` from [io_directx_x 1.4.0](https://github.com/SaintBaron/io_directx_x), plus a generated entry point. The archive SHA-256 is pinned in `dependencies.lock`; attribution and licensing appear in generated `THIRD_PARTY_NOTICES.md`.
- **mmd_tools:** Core requires a separately installed mmd_tools **4.5.5+** and checks its APIs. `test_fixtures.lock` pins a test-only copy for isolated Blender validation.
