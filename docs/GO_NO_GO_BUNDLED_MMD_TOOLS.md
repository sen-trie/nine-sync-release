# Go / no-go: bundling mmd_tools in the combined NineSync extension

Date: 2026-11-01. Author: Release agent. Decision owner: the project owner.

## Recommendation: CONDITIONAL GO, with a documented fallback

Proceed with the combined extension using conditional registration (design A below), **only on these conditions**:

1. The limitations in "What is not supported" are accepted and shown to users.
2. The conflict/failed states get a visible error in the UI. This is not built yet; it needs a panel in the combined entry point, or in Core, that reads `mmd_manager.mode` and `last_error`.
3. The GUI scenario suite (`poc/run_gui.sh`, `poc/startup_test.sh`) is re-run on every Blender release the extension claims to support, because design A depends on Blender behaviour that is observed, not documented.
4. Nothing is submitted to extensions.blender.org until the open policy question below is settled by a person.

If condition 3 ever fails, or reviewers reject a bundled mmd_tools, fall back to design B (prohibit simultaneous use) instead of adding more repair code.

Packaging automation for the two standalone GitHub ZIPs does not depend on this decision and can proceed now. Packaging automation for the combined ZIP should wait for conditions 1 and 4.

## Designs compared

**A: conditional registration with handover** (implemented in `poc/ext/ninesync_poc/mmd_manager.py`). The bundled mmd_tools registers only if no `Object.mmd_root` property exists. A persistent timer (0.5 s) compares reality with the manager's mode. If a standalone registers later, the manager removes only its own handlers, translations, keymap items and menu entries and treats the standalone as the owner. If the standalone disappears, the bundled copy is registered again; classes that Blender still lists as registered get their own `register` hook re-run instead of being unregistered.

**B: prohibit.** The bundled copy registers only when no standalone is present at startup. If a standalone is enabled afterwards, NineSync reports a conflict and asks for a restart. It is simpler, but it does not avoid the shadowing: the standalone enabled second still replaces same-named classes, so B only removes the repair step, not the need to leave the standalone's state alone.

## Evidence (Blender 5.3.0 beta, real windowed sessions, isolated profiles, real timers)

Raw records are in `poc/results/*.json`. All rows below passed on the final manager.

| Scenario | Standalone type | Result |
| --- | --- | --- |
| Bundled first, then standalone enabled; 4 further round trips | extension 4.5.5 | handed over within 1-3 ticks and back each time; models keep their data; no duplicate handlers or menus |
| Standalone first, then NineSync; standalone disabled and re-enabled | extension 4.5.5 | bundled stays unregistered, takes over when the standalone leaves |
| Same two scenarios plus window cases | legacy-layout add-on (4.5.5 source with a `bl_info` header added to a test copy) | pass |
| Both enabled in saved preferences, both orders, relaunch | extension 4.5.5 | coherent after launch in both orders; takes over and hands back correctly afterwards |
| Standalone listed but unable to register (mmd_tools 4.3.10 on Blender 5.3) | extension 4.3.10 | bundled copy used; stays intact across ticks and when the broken standalone is enabled afterwards |
| Standalone enabled then disabled before any tick | 4.5.5 | broken state visible until the next tick, then repaired |
| NineSync disabled before any tick, standalone active | 4.5.5 | standalone fully functional |
| Quit Blender inside the pre-tick window | 4.5.5 | exit code 0, empty stderr |
| `script.reload`, new file, save/reopen, save with add-on disabled, re-enable | n/a | timer survives, data intact |
| Injected failure during registration | n/a | no classes or properties left behind, no retry loop, recovery on re-enable |
| Quit with bundled copy registered | n/a | exit code 0, empty stderr |
| Extension ZIP: validate, build, install-file, enable, use, disable, remove (`poc/zip_install.sh`) | n/a | pass; install directory unchanged apart from `__pycache__`, directory removed on uninstall |
| Core's `validate_real.py` through the bundled copy only, using the repo's `assets/kagamine.pmm` (1 model, camera, light) (`poc/pmm_sync_bundled.sh`) | n/a | 28 checks passed, none failed: 30 fps, resync, 60 fps, Clean |

`blender --command extension validate` only parses the manifest TOML. It passes, but it says nothing about registration behaviour.

### The pre-tick window (investigated as asked)

Between a standalone registering and the next tick the state is: the standalone owns the operators and properties, both copies' load/save handlers and menu entries are present, and 162 of the 183 bundled classes are no longer the registered ones. Observed in that window: operators run (standalone code), a model was created, and a file was saved and reopened, all without error.

Correctness in the window does not depend on the manager. Core resolves mmd_tools from the registered operator's module path (`MMD_TOOLS_OT_import_vmd.__module__`), so it follows whichever copy owns the registration at that moment. The manager only does cleanup and repair. The one case that matters: disabling the standalone again before the tick leaves nothing registered until the tick repairs it (tested, repaired within 3 ticks).

## What is not supported (limits of design A)

- **It relies on observed Blender behaviour, not documented API:**
  - a later registration replaces same-named classes (Blender logs "has been registered before, unregistering previous");
  - `cls.is_registered` tells which classes are still registered (I did not verify that it is documented);
  - a class's own `register` hook is called outside Blender's registration to recreate properties.

  The earlier approach that parsed exception text and stubbed missing properties has been removed.
- **21 bundled PropertyGroup/preferences classes stay registered** after a session in which the standalone took over, until Blender restarts, even after NineSync and the standalone are both disabled. They are inert and are reused on the next start (tested), but they are stale registrations.
- **The pre-tick window cannot be closed** with supported APIs; there is no add-on-enabled callback.
- **Bundled preferences are not shown.** `MMDToolsAddonPreferences.bl_idname` is the nested package name, which is not an add-on, so mmd_tools falls back to its defaults (shared toon folder, default import options).
- **`compat/action_compat.py` patches `Action.__getattribute__` globally.** The handover leaves the patch to the standalone, and a bundled re-registration applies it again. Core already works around it (`iter_fcurves`).
- **Conflict and failed states have no UI yet.**
- **Version coverage is thin.** Only mmd_tools 4.5.5 loads on Blender 5.3 here. 4.3.10 fails to enable (`ActionFCurves` was removed from `bpy.types`), so a mixed-version case could not be tested. The legacy layout was emulated, not tested with a real legacy install.
- **Not tested:**
  - real PMM models with PMX files (the user's project files were deliberately not used);
  - the combined Core+FX+mmd_tools package itself;
  - FX with the bundled importer;
  - Linux or macOS;
  - Blender versions other than this beta;
  - extensions.blender.org review.

## Open policy question (needs a human)

The platform terms ask for self-contained extensions and for not interfering with other add-ons. A bundled copy of a GPL add-on that registers the same operator ids and properties as the upstream add-on is permitted by licence. Whether reviewers accept it, and whether the handover counts as non-interfering, is not something tests can answer.

## Suitable for production?

Not yet. It is a validated proof of concept on one Blender build and one mmd_tools version. Before a release it needs: UI for the conflict states, the combined package built by automated and tested transformations, the full matrix on the Blender versions claimed, and a decision on the policy question above.
