# Reporting and Triage

Report problems on the [issue tracker](https://github.com/sen-trie/nine-sync-release/issues). Pick the template that fits and fill in the version fields. They let a report be tied to exact Core and FX builds.

## Before you report

- Check the [FAQ](faq.md) and the [manual](manual/index.md).
- Update to the latest NineSync release.
- Do not enable the combined extension and a standalone Core or FX copy at the same time. This is unsupported.
- Only attach files you have permission to share, and remove personal paths from logs.

## What belongs where

| Problem | Where it goes |
| --- | --- |
| NineSync bug, any component | This tracker |
| Install, update or conflict problem | This tracker |
| PMX/VMD import or mmd_tools UI | [mmd_tools](https://github.com/MMD-Blender/blender_mmd_tools/issues) |
| DirectX `.x` importer bug | The `.x` importer project |

## How reports are handled

1. **New:** reports start with `needs-triage`.
2. **Triaged:** the report is labelled `core`, `fx` or `packaging`, and asked for missing details if needed.
3. **Reproduced:** the cause is confirmed. Component bugs are tracked in Core or FX and linked back here as `needs-upstream`.
4. **Fixed:** the fix lands in Core or FX and is marked `fixed-in-submodule`.
5. **Released:** the issue closes when a NineSync release includes the fix.
