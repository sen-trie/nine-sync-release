> **Superseded (2026-11-01).** The owner decided against bundling mmd_tools: the combined extension now requires the user's own mmd_tools and never registers one. This document is kept as the record of the coexistence POC.

# POC: conditional registration of a bundled mmd_tools

Decision and full result table: [GO_NO_GO_BUNDLED_MMD_TOOLS.md](GO_NO_GO_BUNDLED_MMD_TOOLS.md). This file is the how-to-run and history.

## History
1. **Headless round (background mode).** Showed the core hazard: if a standalone mmd_tools registers after the bundled copy, Blender lets it replace same-named classes, and any cleanup that unregisters the bundled classes deletes properties the standalone now owns. The first handover attempt parsed `AttributeError` text and stubbed missing properties to purge stale classes; it worked but was a workaround.
2. **Current design.** No exception parsing and no stubbed properties. The handover removes only identity-specific hooks. The return path re-runs the `register` hook of classes that are still registered. Standalone presence is judged from registered properties and the bundled classes' state, not from the add-on list (a listed but unloadable mmd_tools 4.3.10 must not suppress the bundled copy; that bug was found by the variant run and fixed).
3. **Real GUI round.** Real timers, windowed Blender 5.3.0 beta, one isolated profile per run. A test-driver bug (its own timer was not persistent and was cleared by a file load) cost two runs and is fixed; it was not a manager defect.

## Layout (`poc/`)
- `ext/ninesync_poc/`: test extension. `mmd_manager.py` is the manager; `third_party/mmd_tools/` is a git-ignored copy of upstream 4.5.5 (`prepare.sh <path>` fills it).
- `ext_standalone/`, `ext_standalone_v4310/`, `legacy/`: git-ignored standalone variants (4.5.5, 4.3.10, 4.5.5 with a `bl_info` header added to this test copy only).
- `run_gui.sh <scenario>` with `STD_VARIANT=ext445|ext4310|legacy445`; scenarios are in `gui_driver.py`: `bundled_first`, `standalone_first`, `persistence`, `failure`, `shutdown`, `window_flip`, `window_disable_poc`, `window_quit`, `broken_standalone`, plus `startup_test.sh "std,poc"` / `"poc,std"` for launch with both enabled.
- `run.sh <scenario>` runs the older background-mode scenarios in `run_scenario.py`.
- `zip_install.sh`: validate, build, install from ZIP, enable, use, check the install directory, remove.
- `pmm_sync_bundled.sh <file.pmm>`: Core's `validate_real.py` with the bundled mmd_tools as the only mmd_tools. Run here only with Core's own `assets/kagamine.pmm`.
- `results/`: result records of the final runs. `.profiles/` (git-ignored) holds the throwaway profiles.

Every run uses `BLENDER_USER_RESOURCES` pointing into `poc/.profiles/`, so the user's Blender profile, preferences, extensions and project files are never touched. The user's own Blender session (a separate process) was never used.

## Still to do before production
See "What is not supported" and "Suitable for production?" in the go/no-go document.
