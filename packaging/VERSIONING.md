# Bundled versioning

The combined NineSync extension, Core and FX have **independent versions**. Builds never require their numbers to match. The component-update PR bumps the Bundled version according to the highest-level change in Core or FX:

| Change | Bundled bump |
| --- | --- |
| Core/FX major release | Major |
| Core/FX minor release | Minor |
| Core/FX patch release | Patch |
| Bundled-only packaging, dependency or integration change | Patch |

Major bumps reset minor and patch to zero; minor bumps reset patch to zero. Bundled-only changes must not trigger major or minor bumps.

Update both `packaging/bundle/blender_manifest.toml` and `BUNDLE_VERSION` in `packaging/bundle/__init__.py`; they must match.
