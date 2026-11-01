# Change request for the NineSync FX agent: call the DirectX importer function directly

From: Release agent. Status: proposal, nothing applied. This repository has not modified `nine-sync-fx`.

## Why
Today FX reaches binary and compressed `.x` files by finding an import *operator* registered by the separate DirectX X Importer add-on (`accessories/mesh.py: import_x_with_addon`, probing `bpy.ops.import_scene` for `x`, `directx`, `directx_x`, `x_file`, `dx`). The combined extension must be self-contained, and bundling that add-on with its operator would register `import_scene.directx_x` a second time next to a user-installed copy. The importer module itself (`io_directx_x` 1.4.0, GPL-3.0-or-later, installed copy inspected) has relative imports only (`.parser`) and a plain function:

```
importer.import_x(context, filepath, use_apply_transform=True, global_scale=1.0, axis_forward="-Z", axis_up="Y",
                  import_normals=True, import_uvs=True, import_materials=True, import_textures=True,
                  import_armature=True, import_weights=True, import_animation=True, use_import_collection=True,
                  anim_fps=0.0, set_frame_range=False, ..., import_type="standard", ..., **_)
```
Calling it needs no operator, panel or menu registration, so the bundled copy cannot collide with a standalone one.

## Requested behaviour
1. One resolver, `x_importer_function()`, returning a callable or `None`, tried in this order:
   1. A bundled importer, if the build provides one. The Release build will put a module `x_importer_bundled.py` (or constant) inside the combined package that exposes `import_x`; FX must treat its absence as normal (standalone FX zip has none).
   2. An installed importer add-on: for each name in `X_IMPORTER_MODULES` found by `addon_loaded`, `importlib.import_module(<full addon module name> + ".importer")` and take `import_x` (use the full enabled module name from `bpy.context.preferences.addons`, not a guess at the prefix, so extension and legacy installs both work).
   3. Fallback: the existing operator probe, kept for importers that do not expose `import_x`.
2. `import_x_with_addon(path)` calls `import_x(bpy.context, filepath=path, <explicit options>)` and keeps the existing "objects before/after" diff to return new objects. Pass options explicitly instead of relying on defaults (at minimum `use_import_collection`, `import_animation`, `use_apply_transform`, `global_scale`) and compare against what the operator path produced today for the same file so results do not change.
3. `x_importer_available()` becomes `x_importer_function() is not None`, so the dependency notice (`accessories/dependencies.py`, `ui/hook_entry.py`) stays accurate for all three setups: standalone FX without importer, standalone FX with importer add-on, combined build.
4. Errors from `import_x` (it can raise) must be caught and reported like the current "operator not found" path, not allowed to abort a sync.

## Constraints from the Release side
- No `sys.modules` injection or `sys.path` edits; the bundled module is imported by its package-relative name.
- The Release build supplies the bundled module and provenance (pinned version, hash, licence text). FX keeps working without it.
- FX must not require Core, and must not import `ninesync`.

## Acceptance tests to add in FX
- Resolver returns bundled function when the stub module is present, the installed add-on's function when only that exists, and `None` when neither does (use a fake module for the first case).
- A binary or compressed `.x` fixture imports through the function path and yields the same object count and material count as through the operator path.
- No `import_scene.directx_x` operator is registered by FX or by the bundled copy.
- With a standalone importer add-on enabled as well as the bundled copy, FX uses the documented priority and registers nothing twice.

## Open questions for FX
- Which `import_x` options does the current operator call rely on implicitly?
- Is the importer's `context` argument used beyond scene access (collection linking)?
