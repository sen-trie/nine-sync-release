"""Runs INSIDE Blender (background) against an installed combined NineSync extension.

    blender -b --factory-startup --python-exit-code 1 --python packaging/blender_smoke.py -- <report.json>

The combined extension AND the separately installed mmd_tools extension (the external dependency) must
already be installed in the profile; both are enabled here. Prints "SMOKE ok|FAIL <name>" lines,
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
MMD = "bl_ext.user_default.mmd_tools"
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
        "mmd_bridge": hasattr(bpy.types.Scene, "mmd_bridge"),
        "ninesync_fx": hasattr(bpy.types.Scene, "ninesync_fx"),
        "core_hook": registry().get("core") is not None,
        "fx_hook": "ninesync_fx" in (registry().get("post_sync") or {}),
    }


def mmd_registered():
    return hasattr(bpy.types.Object, "mmd_root") and hasattr(bpy.types, "MMD_TOOLS_OT_import_vmd")


def ops(group):
    if not hasattr(bpy.ops, group):
        return []
    return [n for n in dir(getattr(bpy.ops, group)) if not n.startswith("_")]


# Identity of mmd_tools' registered classes and properties; must not change when NineSync is enabled or disabled.
def mmd_fingerprint():
    names = sorted(n for n in dir(bpy.types) if getattr(getattr(bpy.types, n, None), "__module__", "").startswith(MMD + "."))
    return (
        tuple((n, id(getattr(bpy.types, n))) for n in names),
        len(ops("mmd_tools")),
        tuple(hasattr(bpy.types.Object, a) for a in ("mmd_root", "mmd_type", "mmd_rigid", "mmd_joint", "mmd_camera")),
        hasattr(bpy.types.PoseBone, "mmd_bone"),
        hasattr(bpy.types.Material, "mmd_material"),
        tuple(sorted(h.__qualname__ for h in bpy.app.handlers.load_post if getattr(h, "__module__", "").startswith(MMD + "."))),
        tuple(sorted(h.__qualname__ for h in bpy.app.handlers.save_pre if getattr(h, "__module__", "").startswith(MMD + "."))),
    )


def enable(name=PKG):
    errors = []
    module = addon_utils.enable(name, default_set=False, persistent=False, handle_error=lambda e: errors.append(repr(e)))
    return module, errors


def disable(name=PKG):
    addon_utils.disable(name, default_set=False)


check("blender >= 5.3", bpy.app.version >= (5, 3, 0), bpy.app.version_string)
check("nothing registered before enable", not any(present().values()) and not mmd_registered(), present())

# Guard: standalone NineSync registrations still stop the bundle without leaving anything behind.
bpy.types.Scene.ninesync_fx = bpy.props.IntProperty()
module, errors = enable()
after = present()
check("guard: refuses to start next to standalone FX", module is None and any("cannot start" in e for e in errors), errors[:1])
check("guard: nothing of the bundle registered", not (after["mmd_bridge"] or after["core_hook"] or after["fx_hook"]), after)
del bpy.types.Scene.ninesync_fx

# Missing dependency: the bundle still starts; Core reports mmd_tools as missing and offers no sync.
module, errors = enable()
check("enable without mmd_tools", module is not None and present()["mmd_bridge"] and present()["ninesync_fx"], errors)
link = importlib.import_module(PKG + ".ninesync_core.sync.mmd_tools_link")
state, detail = link.mmd_tools_status()
check("missing: Core reports 'missing' with a message", state == "missing" and "mmd_tools" in detail, (state, detail))
check("missing: mmd_tools_available is False", not link.mmd_tools_available())
check("missing: panel notice lists mmd_tools", [m[0] for m in link.missing_dependencies()] == ["mmd_tools"])
check("missing: the bundle registered no mmd_tools", not mmd_registered() and not ops("mmd_tools"))

# The external mmd_tools is enabled afterwards (extension enable order is not controlled by NineSync).
mmd_module_, errors = enable(MMD)
check("external mmd_tools enables", mmd_module_ is not None and mmd_registered(), errors)
before_mmd = mmd_fingerprint()
state, detail = link.mmd_tools_status()
check("Core sees the external mmd_tools as ok", state == "ok" and link.mmd_tools_available(), (state, detail))
check("Core resolves the external package", link.mmd_tools_base() == MMD, link.mmd_tools_base())
version = link.mmd_tools_version_tuple()
check("mmd_tools version is read and meets the minimum", version is not None and version >= link.MMD_TOOLS_MIN_VERSION, version)
vmd = getattr(bpy.types, "MMD_TOOLS_OT_import_vmd", None)
check("operator belongs to the external package, not NineSync",
      vmd is not None and vmd.__module__.startswith(MMD + ".") and "ninesync" not in vmd.__module__, getattr(vmd, "__module__", None))
check("no mmd_tools files inside the combined package", not os.path.exists(os.path.join(os.path.dirname(module.__file__), "third_party")))

# Incompatible: a higher minimum or a missing API is reported, not crashed on; nothing of mmd_tools changes.
saved_min, saved_api = link.MMD_TOOLS_MIN_VERSION, link.REQUIRED_API
link.MMD_TOOLS_MIN_VERSION = (99, 0, 0)
link._status_cache.clear()
state, detail = link.mmd_tools_status()
check("incompatible: version below the minimum is reported",
      state == "incompatible" and "too old" in detail and not link.mmd_tools_available(), (state, detail))
link.MMD_TOOLS_MIN_VERSION = saved_min
link.REQUIRED_API = (("core.model", ("NoSuchApi",)),)
link._status_cache.clear()
state, detail = link.mmd_tools_status()
check("incompatible: missing API is reported", state == "incompatible" and "NoSuchApi" in detail, (state, detail))
link.REQUIRED_API = saved_api
link._status_cache.clear()
check("compatible again after restoring the checks", link.mmd_tools_status()[0] == "ok")
check("the checks did not touch mmd_tools", mmd_fingerprint() == before_mmd)

# Normal state.
state = present()
check("Core and FX registered", all(state.values()), state)
reg = registry()
check("hook registry api_version 1", reg.get("api_version") == 1, reg.get("api_version"))
counts = {g: len(ops(g)) for g in ("mmd_tools", "ninesync", "ninesync_fx")}
check("operators: mmd_tools, ninesync, ninesync_fx", all(counts.values()), counts)

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

# The external mmd_tools works.
before = set(bpy.data.objects)
try:
    bpy.ops.mmd_tools.create_mmd_model_root_object(name_j="smoke", name_e="smoke", scale=0.08)
    check("external mmd_tools creates a model", any(o.mmd_type == "ROOT" for o in bpy.data.objects if o not in before))
except Exception as error:
    check("external mmd_tools creates a model", False, repr(error))

# Persistent data lives in the extension user folder, not the install folder.
store = importlib.import_module(PKG + ".ninesync_fx.nodes.library_store")
user_folder = store.mme_user_folder()
install = os.path.normcase(os.path.abspath(os.path.dirname(module.__file__))) if module else "?"
user_abs = os.path.normcase(os.path.abspath(user_folder)) if user_folder else ""
check("user library folder is the combined extension's own", bool(user_folder) and os.path.isdir(user_folder)
      and os.path.basename(os.path.normpath(user_folder)) == "ninesync_bundled", os.path.basename(os.path.normpath(user_folder or "")))
check("user library folder is outside the install folder", bool(user_abs) and user_abs != install and not user_abs.startswith(install + os.sep))
check("bundled node library file present", os.path.isfile(store.mme_bundled_path()))

# Disable / re-enable / disable NineSync: mmd_tools must be exactly as before.
disable()
check("disable unregisters NineSync", not any(present().values()), present())
check("disabling NineSync leaves mmd_tools untouched", mmd_registered() and mmd_fingerprint() == before_mmd)
module, errors = enable()
check("re-enable", module is not None and all(present().values()), errors)
check("re-enabling NineSync leaves mmd_tools untouched", mmd_fingerprint() == before_mmd)

# Disabling mmd_tools while NineSync is enabled: NineSync stays up and reports it; re-enabling recovers.
disable(MMD)
link = importlib.import_module(PKG + ".ninesync_core.sync.mmd_tools_link")
state = link.mmd_tools_status()
check("mmd_tools disabled: NineSync stays registered and reports 'missing'", all(present().values()) and state[0] == "missing", state)
mmd_module_, errors = enable(MMD)
check("mmd_tools re-enabled: Core is ok again", mmd_registered() and link.mmd_tools_status()[0] == "ok", errors)

disable()
check("second disable unregisters NineSync", not any(present().values()), present())
check("mmd_tools still registered after NineSync is gone", mmd_registered())
disable(MMD)

failed = [r for r in results if not r["ok"]]
out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else None
if out:
    build_hash = bpy.app.build_hash
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"blender": bpy.app.version_string, "build_hash": build_hash.decode() if isinstance(build_hash, bytes) else str(build_hash),
                   "mmd_tools_version": ".".join(map(str, version)) if version else None,
                   "passed": len(results) - len(failed), "failed": len(failed), "checks": results}, handle, indent=2)
print("SMOKE summary: %d passed, %d failed" % (len(results) - len(failed), len(failed)), flush=True)
sys.exit(1 if failed else 0)
