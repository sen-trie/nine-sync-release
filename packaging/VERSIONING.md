# Bundled versioning

The Bundled extension (`nine-sync-<version>-blender-extensions.zip`) has its own version, independent of Core and FX.
Core and FX are also versioned independently of each other. No build or update check compares the three numbers.

The Bundled version is raised by hand (`packaging/bundle/blender_manifest.toml` and `BUNDLE_VERSION` in
`packaging/bundle/__init__.py`, which must match) following Core and FX:

- **Major**: raised only when Core or FX raises its major.
- **Minor**: raised only when Core or FX raises its minor.
- **Patch**: Bundled-only changes (packaging, dependencies, integration) and Core/FX patch releases.

A major bump resets minor and patch to 0; a minor bump resets patch to 0. The Bundled version never moves ahead of
what Core and FX did: it is not raised for its own sake on a major or minor.
