---
hide:
  - toc
---

# Reporting and Triage

Report problems on the [issue tracker](https://github.com/sen-trie/nine-sync-release/issues). Pick the template that fits and fill in the version fields. They let a report be tied to exact Core and FX builds. This tracker is the one place to report: you do not need to decide whether a problem is in Core or FX.

## Before you report

- Check the [manual](manual/index.md) and [common issues](issues.md).
- Update to the latest NineSync release.
- Only attach files you have permission to share, and remove personal paths from logs.

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
