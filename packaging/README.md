# Packaging

Scripts that build and check the combined NineSync Blender extension. Standard library Python only.

| File | Purpose |
| --- | --- |
| `build_bundle.py` | Builds the deterministic ZIP, `.sha256` and `artifact-manifest.json` from the pinned submodules and `dependencies.lock` |
| `validate_bundle.py` | Static checks (structure, manifest, versions, licences, hooks, syntax, private paths) |
| `validate_in_blender.py`, `blender_smoke.py` | Install into an isolated profile and test inside Blender 5.3+ |
| `fetch_blender.py` | Downloads an official Blender release and verifies its checksum; never substitutes another version |
| `VERSIONING.md` | How the Bundled version relates to Core and FX versions |
| `check_publish_gates.py` | Stable release check (static + official-Blender validation of the exact ZIP, clean manifest) |
| `check_experimental.py`, `experimental_notes.py` | Experimental pre-release checks and notes (no Blender run) |
| `extension_repo.py` | Assembles the GitHub Pages extension repository (Blender `extension server-generate`) and verifies the public index and ZIP |
| `release_gates.json` | Website and copyright confirmations, read by the experimental path only |
| `update_components.py`, `components.json`, `COMPONENT_UPDATES.md` | Rolling Core + FX dependency PR (never merges or releases); see `COMPONENT_UPDATES.md` |

## Stable release (`.github/workflows/release.yml`)

Manual dispatch. Builds, validates statically, validates inside an official Blender 5.3 or newer, and on request
creates a **draft** release. Requires a passing Blender validation of the exact
ZIP and approval of the `release` environment. Unchanged by the experimental path.

### Extension repository on GitHub Pages

Input `deploy_extension_repository` (independent of `create_draft_release`; both may be set in one run). Jobs:

1. `assemble-repository` (environment `extension-repository`, the manual approval): re-runs `check_publish_gates.py`, fetches an
   official Blender, then `extension_repo.py assemble` downloads every version already served at the Pages URL (each checked
   against the hash its own index advertises), adds the new ZIP, and runs Blender's `extension server-generate --html`.
   It refuses pre-release versions, a changed ZIP under an already published version, an older version, and a different
   extension id. The result is uploaded as the Pages artifact.
2. `deploy-repository` (environment `github-pages`): `actions/deploy-pages`.
3. `verify-repository`: fetches the public `index.json` and ZIP over HTTPS and compares them with the release ZIP
   (retries while Pages propagates). The run is only green if the public files match.

The Pages site is rebuilt from the previously served versions plus the new one, so no content branch is kept. The base
URL is `https://<owner>.github.io/<repo>/`, derived from the repository, or the `EXTENSION_REPO_URL` repository variable
(custom domain). Rolling back means deploying a corrected newer version; the workflow never deletes a published version.

## Experimental release (`.github/workflows/experimental-release.yml`)

For the first bundled prerelease, e.g. `v0.1.0-alpha.1`. Manual dispatch only.

1. Same `build_bundle.py` and `validate_bundle.py` as the stable path. No Blender is run.
2. Still enforced: prerelease tag format, clean pinned sources, dependency hashes, manifest, licence files,
   ZIP/`.sha256`/artifact-manifest agreement, and the website and copyright gates.
3. Not required: Blender install tests, official Blender 5.3 validation, the install-test gate.
4. Inputs: `release_tag`, `acknowledge` (must be the word `EXPERIMENTAL`), `publish` (off = build and check only).
5. Publishing runs in the `experimental-release` environment. Configure required reviewers on it in the repository
   settings: that approval is the explicit manual step. The release is created as a **Pre-release** whose notes
   say the extension is not validated in Blender. An existing tag is never touched.
6. The tag is only a label: the extension inside the ZIP keeps the version in `bundle/blender_manifest.toml`
   (currently 0.1.0; see `VERSIONING.md`).

Stable releases must not use prerelease tags; promote only through `release.yml`. Experimental builds never enter the
GitHub Pages extension repository: this workflow has no deployment job and `extension_repo.py` rejects non-`X.Y.Z` versions.

## Bundled DirectX `.x` importer

Vendored from io_directx_x 1.4.0 (GPL-3.0-or-later), upstream https://github.com/SaintBaron/io_directx_x, maintainer
SaintBaron. Only `importer.py`, `parser.py` and `LICENSE` are included, plus a generated `__init__.py` exposing
`import_x`. The pin is the SHA-256 of the extensions.blender.org archive in `dependencies.lock`
(`cfb8db604f4e6c0e6569e57110659667d55a0cd37ca03b445028bb6fbc968765`); upstream publishes no tag or commit id in
that archive. The files carry no per-file copyright line, so attribution is the maintainer name, source URL and
the full licence text, all listed in the generated `THIRD_PARTY_NOTICES.md`.

## mmd_tools is external

The combined ZIP contains no mmd_tools. Core finds the user's installed mmd_tools through its registered operators and
checks its version (>= 4.5.5, `MMD_TOOLS_MIN_VERSION` in Core's `sync/mmd_tools_link.py`) and the API Core calls
(`REQUIRED_API`). `validate_bundle.py` fails the build if any mmd_tools file is present or the entry point mentions
mmd_tools. `test_fixtures.lock` pins the mmd_tools 4.5.5 release archive (SHA-256) that `validate_in_blender.py` installs
into its isolated profile; it is test-only.
