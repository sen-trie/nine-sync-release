# Changelog

Changes specific to NineSync Bundled: packaging, installation and integration of the combined extension. Core and
FX keep their own changelogs; Bundled release notes summarise them from their published releases.

Add entries under `[Unreleased]` as they happen. Do not bump the version or add a version section until a release is
authorised; then run `python -I packaging/release_notes.py finalize --version X.Y.Z --date YYYY-MM-DD`.

## [Unreleased]

- The combined extension no longer bundles mmd_tools. It requires the user's own mmd_tools 4.5.5 or newer and reports when it is missing or incompatible.
- Stable releases can add the exact validated build to a Blender extension repository hosted on GitHub Pages, so Blender can install and update NineSync natively.

## [0.1.0-alpha.1]

- Experimental pre-release of the combined extension (Core 0.3.0 and FX 0.3.0), not validated in Blender.
- Includes the vendored DirectX `.x` importer and, at that time, mmd_tools.
- Bundled and standalone NineSync (Core, FX, mmd_tools) must not be enabled at the same time.
