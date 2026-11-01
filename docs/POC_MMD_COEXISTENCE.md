# POC: conditional registration of a bundled mmd_tools

Status: **headless proof of concept passed; not yet validated in a live GUI session or against Core/FX.** No Blender Extensions compliance is claimed.

## Setup
- Blender 5.3.0 Beta (build 2026-10-25), `--background --factory-startup`, a fresh `BLENDER_USER_RESOURCES` per scenario (`poc/run.sh <scenario>`).
- mmd_tools 4.5.5 (extensions.blender.org copy, GPL-3.0-or-later). Bundled as `ninesync_poc.third_party.mmd_tools` (unmodified; its imports are all relative) and, separately, as a standalone extension in the same profile.
- Manager: `poc/ext/ninesync_poc/mmd_manager.py`. Extensions were installed by copying into the `user_default` repo folder, not from a ZIP.

## Design
1. `start()`: if `Object.mmd_root` is already registered (standalone active) do nothing and report `external`; else import the bundled copy lazily and register it (`internal`). A failed registration is rolled back (handlers, translations, keymaps, modules, classes).
2. `check()` (meant for a persistent timer) reconciles later changes:
   - standalone enabled while `internal`: Blender lets the later registration replace same-named classes, so the manager removes only identity-specific hooks of the bundled copy (handlers, translations, keymap items, menu draw functions) and unregisters **no** class or property.
   - standalone disabled while `external`: stale bundled classes are purged (stubbing attributes that their `unregister` hooks would otherwise fail to `del`), then the bundled copy registers again.

## Results (all runs recorded in a real Blender 5.3 beta, background mode)
| Scenario | Result |
| --- | --- |
| Bundled only: enable, make model, 3x disable/enable | pass: 113 operators and 5 Object properties appear and disappear cleanly; handlers and menus return to baseline; model data (`mmd_root.comment_text`) survives each cycle |
| Disable add-on, save .blend, reopen, enable | pass: data intact |
| Standalone enabled first, then NineSync | pass: `external`, nothing of ours registered; toggling NineSync leaves the standalone untouched |
| Standalone disabled while NineSync is `external` | pass after `check()`: bundled copy takes over, new model creation works |
| NineSync first, then standalone enabled | pass after `check()`: standalone fully functional (model created), menus not duplicated; then standalone disabled and `check()`: bundled returns, both existing models keep their data, final disable clean |
| NineSync first, then standalone, **without** `check()` | **fails**: standalone's registration shadows the bundled classes; disabling either add-on afterwards raises (`Object.hide` missing) and leaves stale state |
| Injected failure in a module `register()` | pass: full rollback (0 operators, 0 properties), retry succeeds |
| `script.reload` | pass |

## Open items / risks
- `check()` has not been run from a real timer or in a GUI session; headless mode does not fire timers. Until then the window between enabling the standalone and the next tick is unproven, and the "without check()" row shows what happens if the tick never runs.
- The stale-class purge relies on parsing `AttributeError` text and stubbing properties; it is a workaround, not a supported API.
- Bundled `MMDToolsAddonPreferences` has `bl_idname = __package__` (the nested package), so its preferences are not shown under the extension; code falls back to defaults. Not yet examined for functional impact.
- `compat/action_compat.py` patches `bpy.types.Action.__getattribute__` globally; the handover deliberately leaves it to the standalone.
- Core's own `mmd_tools_base()` lookup does not know about the bundled copy; a packaging-time adapter is needed and untested.
- Not tested: ZIP install, `blender --command extension validate`, other mmd_tools versions, a legacy (non-extension) standalone install, Windows file-permission/read-only installs, real PMM sync.
