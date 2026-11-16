# How PMM Sync Works

- [PMM Reading and Writing](reading-and-writing.md) covers what NineSync reads from and writes to a PMM.
- [Synchronization](synchronization.md) explains how changes are detected and when clips are replaced.
- [Accessories and Effects](fx-integration.md) explains how accessories and their effects are brought in.

## High-level overview of a sync

<!-- prettier-ignore -->
| Step | What happens |
|---|---|
| Read the PMM | NineSync reads the project and adjusts its timing to match your scene's frame rate. |
| Check for changes | NineSync compares the project with the previous sync and decides what needs updating. |
| Import models | Model motion and morphs are imported through mmd_tools. |
| Update the scene | Camera and light are updated, followed by accessories and effects, then audio. |
| Finish | Blender re-evaluates the current frame. |

If a model fails to import, NineSync reports it and continues with the others. You can abort this process with **Esc**. The sync process is one undo step, even when cancelled or failed part-way.
