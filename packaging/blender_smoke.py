"""Runs INSIDE Blender (background) against an installed combined NineSync extension.

    blender -b --factory-startup --python-exit-code 1 --python packaging/blender_smoke.py -- <report.json>

The extension must already be installed (it is enabled here). Prints "SMOKE ok|FAIL <name>" lines,
writes a JSON report and exits non-zero on any failure.
"""
import importlib
import json
import os
import sys
import tempfile

import addon_utils
import bpy

PKG = "bl_ext.user_default.ninesync_bundled"
results = []


def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": str(detail)})
    suffix = (" | " + str(detail)) if (detail or not ok) else ""
    print("SMOKE %s %s%s" % ("ok  " if ok else "FAIL", name, suffix), flush=True)
    return ok


def registry():
    return bpy.app.driver_namespace.get("ninesync_hooks") or {}


def present():
    return {
        "mmd_root": hasattr(bpy.types.Object, "mmd_root"),
        "mmd_bridge": hasattr(bpy.types.Scene, "mmd_bridge"),
        "ninesync_fx": hasattr(bpy.types.Scene, "ninesync_fx"),
        "core_hook": registry().get("core") is not None,
        "fx_hook": "ninesync_fx" in (registry().get("post_sync") or {}),
    }


def enable():
    errors = []
    module = addon_utils.enable(PKG, default_set=False, persistent=False, handle_error=lambda e: errors.append(repr(e)))
    return module, errors


def disable():
    addon_utils.disable(PKG, default_set=False)


def ops(group):
    if not hasattr(bpy.ops, group):
        return []
    return [n for n in dir(getattr(bpy.ops, group)) if not n.startswith("_")]


check("blender >= 5.3", bpy.app.version >= (5, 3, 0), bpy.app.version_string)
check("nothing registered before enable", not any(present().values()), present())

# Guard: a foreign registration must stop the bundle without leaving anything behind.
bpy.types.Scene.ninesync_fx = bpy.props.IntProperty()
module, errors = enable()
after = present()
check("guard: refuses to start next to a foreign registration", module is None and any("cannot start" in e for e in errors), errors[:1])
check("guard: nothing of the bundle registered", not (after["mmd_root"] or after["mmd_bridge"] or after["core_hook"] or after["fx_hook"]), after)
del bpy.types.Scene.ninesync_fx

# Normal enable.
module, errors = enable()
check("enable", module is not None, errors)
state = present()
check("mmd_tools, Core and FX registered", all(state.values()), state)
reg = registry()
check("hook registry api_version 1", reg.get("api_version") == 1, reg.get("api_version"))
check("Core hook version", bool(reg.get("core")) and tuple(reg["core"]["version"]) == (0, 3, 0), reg.get("core"))
counts = {g: len(ops(g)) for g in ("mmd_tools", "ninesync", "ninesync_fx")}
check("operators: mmd_tools, ninesync, ninesync_fx", all(counts.values()), counts)
vmd = getattr(bpy.types, "MMD_TOOLS_OT_import_vmd", None)
check("mmd_tools resolves to the bundled copy", vmd is not None and vmd.__module__.startswith(PKG + ".third_party.mmd_tools."),
      getattr(vmd, "__module__", None))

link = importlib.import_module(PKG + ".ninesync_core.sync.mmd_tools_link")
check("Core finds bundled mmd_tools", link.mmd_tools_available() and link.mmd_tools_base() == PKG + ".third_party.mmd_tools", link.mmd_tools_base())
core_addon = importlib.import_module(PKG + ".ninesync_core.common.addon")
fx_entry = importlib.import_module(PKG + ".ninesync_fx.ui.hook_entry")
check("Core and FX read their versions", core_addon.addon_version() == (0, 3, 0) and fx_entry.addon_version() == (0, 3, 0),
      (core_addon.addon_version(), fx_entry.addon_version()))

# Bundled .x importer.
mesh = importlib.import_module(PKG + ".ninesync_fx.accessories.mesh")
function = mesh.x_importer_function()
check("FX resolves the bundled .x importer first",
      function is not None and function.__module__ == PKG + ".ninesync_fx.x_importer_bundled.importer", getattr(function, "__module__", None))
check("bundle registers no import_scene operator", mesh.x_importer_operator() is None)
X_TEXT = "xof 0303txt 0032\nMesh Tri {\n 3;\n 0.0;0.0;0.0;,\n 1.0;0.0;0.0;,\n 0.0;1.0;0.0;;\n 1;\n 3;0,1,2;;\n}\n"
with tempfile.TemporaryDirectory() as scratch:
    x_path = os.path.join(scratch, "tri.x")
    with open(x_path, "w", newline="\n") as handle:
        handle.write(X_TEXT)
    try:
        created = mesh.import_x_with_addon(x_path)
        check("bundled importer imports a .x mesh", any(o.type == "MESH" and len(o.data.polygons) == 1 for o in created), [o.name for o in created])
    except Exception as error:
        check("bundled importer imports a .x mesh", False, repr(error))

# mmd_tools works.
before = set(bpy.data.objects)
try:
    bpy.ops.mmd_tools.create_mmd_model_root_object(name_j="smoke", name_e="smoke", scale=0.08)
    check("bundled mmd_tools creates a model", any(o.mmd_type == "ROOT" for o in bpy.data.objects if o not in before))
except Exception as error:
    check("bundled mmd_tools creates a model", False, repr(error))

# Persistent data lives in the extension user folder, not the install folder.
store = importlib.import_module(PKG + ".ninesync_fx.nodes.library_store")
user_folder = store.mme_user_folder()
install = os.path.normcase(os.path.abspath(os.path.dirname(module.__file__))) if module else "?"
user_abs = os.path.normcase(os.path.abspath(user_folder)) if user_folder else ""
check("user library folder is the combined extension's own", bool(user_folder) and os.path.isdir(user_folder)
      and os.path.basename(os.path.normpath(user_folder)) == "ninesync_bundled", os.path.basename(os.path.normpath(user_folder or "")))
check("user library folder is outside the install folder", bool(user_abs) and user_abs != install and not user_abs.startswith(install + os.sep))
check("bundled node library file present", os.path.isfile(store.mme_bundled_path()))

# Disable / re-enable / disable.
disable()
check("disable unregisters everything", not any(present().values()), present())
module, errors = enable()
check("re-enable", module is not None and all(present().values()), errors)
disable()
check("second disable unregisters everything", not any(present().values()), present())

failed = [r for r in results if not r["ok"]]
out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else None
if out:
    build_hash = bpy.app.build_hash
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"blender": bpy.app.version_string, "build_hash": build_hash.decode() if isinstance(build_hash, bytes) else str(build_hash),
                   "passed": len(results) - len(failed), "failed": len(failed), "checks": results}, handle, indent=2)
print("SMOKE summary: %d passed, %d failed" % (len(results) - len(failed), len(failed)), flush=True)
sys.exit(1 if failed else 0)
