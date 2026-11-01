# Packaging

Scripts that build and check the combined NineSync Blender extension. Standard library Python only.

| File | Purpose |
| --- | --- |
| `build_bundle.py` | Builds the deterministic ZIP, `.sha256` and `artifact-manifest.json` from the pinned submodules and `dependencies.lock` |
| `validate_bundle.py` | Static checks (structure, manifest, versions, licences, hooks, syntax, private paths) |
| `validate_in_blender.py`, `blender_smoke.py` | Install into an isolated profile and test inside Blender 5.3+ |
| `fetch_blender.py` | Downloads an official Blender release and verifies its checksum; never substitutes another version |
| `check_publish_gates.py` | Stable release gate check (all owner gates + official-Blender validation) |
| `check_experimental.py`, `experimental_notes.py` | Experimental pre-release checks and notes (no Blender run) |
| `release_gates.json` | Owner confirmations required for stable releases |

## Stable release (`.github/workflows/release.yml`)

Manual dispatch. Builds, validates statically, validates inside an official Blender 5.3 or newer, and on request
creates a **draft** release. Requires every gate in `release_gates.json`, a passing Blender validation of the exact
ZIP, and approval of the `release` environment. Unchanged by the experimental path.

## Experimental release (`.github/workflows/experimental-release.yml`)

For the first bundled prerelease, e.g. `v0.1.0-alpha.1`. Manual dispatch only.

1. Same `build_bundle.py` and `validate_bundle.py` as the stable path. No Blender is run.
2. Still enforced: prerelease tag format, clean pinned sources, dependency hashes, manifest, licence files,
   ZIP/`.sha256`/artifact-manifest agreement, and the website and copyright gates.
3. Not required: Blender install tests, official Blender 5.3 validation, the policy-review and install-test gates.
4. Inputs: `release_tag`, `acknowledge` (must be the word `EXPERIMENTAL`), `publish` (off = build and check only).
5. Publishing runs in the `experimental-release` environment. Configure required reviewers on it in the repository
   settings: that approval is the explicit manual step. The release is created as a **Pre-release** whose notes
   say the extension is not validated in Blender. An existing tag is never touched.
6. The tag is only a label: the extension inside the ZIP keeps the version in `bundle/blender_manifest.toml`
   (currently 0.3.0, matching Core and FX).

Stable releases must not use prerelease tags; promote only through `release.yml`.

## Bundled DirectX `.x` importer

Vendored from io_directx_x 1.4.0 (GPL-3.0-or-later), upstream https://github.com/SaintBaron/io_directx_x, maintainer
SaintBaron. Only `importer.py`, `parser.py` and `LICENSE` are included, plus a generated `__init__.py` exposing
`import_x`. The pin is the SHA-256 of the extensions.blender.org archive in `dependencies.lock`
(`cfb8db604f4e6c0e6569e57110659667d55a0cd37ca03b445028bb6fbc968765`); upstream publishes no tag or commit id in
that archive. The files carry no per-file copyright line, so attribution is the maintainer name, source URL and
the full licence text, all listed in the generated `THIRD_PARTY_NOTICES.md`.

mmd_tools 4.5.5 (GPL-3.0-or-later, with OpenCC under Apache-2.0) is pinned by release-archive SHA-256 and upstream
tag commit in the same file.
