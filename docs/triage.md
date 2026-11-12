# Reporting and Triage

Report problems on the [issue tracker](https://github.com/sen-trie/nine-sync-release/issues). Pick the template that fits and fill in the version fields. They let a report be tied to exact Core and FX builds.

## Before you report

- Check the [manual](manual/index.md).
- Update to the latest NineSync release.
- Only attach files you have permission to share, and remove personal paths from logs.

## What belongs where

| Problem                             | Where it goes                                                        |
| ----------------------------------- | -------------------------------------------------------------------- |
| NineSync bug, any component         | This tracker                                                         |
| Install, update or conflict problem | This tracker                                                         |
| PMX/VMD import or mmd_tools UI      | [mmd_tools](https://github.com/MMD-Blender/blender_mmd_tools/issues) |

## How reports are handled

`New`
: Every report is labelled `needs-triage` automatically, even if it skipped the template.

`Triaged`
: The report is labelled `core`, `fx` or `packaging`, and asked for missing details if needed.

`Reproduced`

: The cause is confirmed. Component bugs are tracked in Core or FX and linked back here as `needs-upstream`.

`Fixed`
: The fix lands in Core or FX and is marked `fixed-in-submodule`.

`Released`
: The issue closes when a NineSync release includes the fix.
