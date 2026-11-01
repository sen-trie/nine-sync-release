# NineSync, combined extension. Registers bundled mmd_tools, NineSync: PMM Bridge and NineSync: FX Importer
# as namespaced components of this one package. Nothing is added to sys.path or sys.modules.
#
# Unsupported: running this next to standalone NineSync Core / FX / mmd_tools. The entry point detects
# their registrations before it registers anything and refuses to start (fail closed); it never disables
# or changes another add-on.

BUNDLE_VERSION = (0, 3, 0)

# FX reads its root package's bl_info["version"] (here: this package). Blender drops the attribute from an
# enabled extension's module, so it is set again at register time.
BL_INFO = {
    "name": "NineSync",
    "author": "sentrie",
    "version": BUNDLE_VERSION,
    "blender": (5, 3, 0),
    "category": "Import-Export",
}

import importlib

import bpy

COMPONENTS = ("third_party.mmd_tools", "ninesync_core", "ninesync_fx")

_state = {"registered": []}


def foreign_registrations():
    found = []
    if hasattr(bpy.types.Object, "mmd_root"):
        found.append("mmd_tools")
    if hasattr(bpy.types.Scene, "mmd_bridge"):
        found.append("NineSync: PMM Bridge")
    if hasattr(bpy.types.Scene, "ninesync_fx"):
        found.append("NineSync: FX Importer")
    registry = bpy.app.driver_namespace.get("ninesync_hooks") or {}
    if registry.get("core") is not None and "NineSync: PMM Bridge" not in found:
        found.append("NineSync hook registry (Core)")
    if "ninesync_fx" in (registry.get("post_sync") or {}) and "NineSync: FX Importer" not in found:
        found.append("NineSync hook registry (FX)")
    return found


def register():
    global bl_info
    bl_info = dict(BL_INFO)
    if _state["registered"]:
        return
    found = foreign_registrations()
    if found:
        raise RuntimeError(
            "NineSync (combined) cannot start: %s already registered from another install. "
            "Disable that install, then enable this one; restarting Blender is recommended. Nothing was changed."
            % ", ".join(found)
        )
    done = []
    try:
        for name in COMPONENTS:
            module = importlib.import_module("." + name, __package__)
            module.register()
            done.append(module)
    except Exception:
        for module in reversed(done):
            try:
                module.unregister()
            except Exception:
                pass
        raise
    _state["registered"] = done


def unregister():
    done, _state["registered"] = _state["registered"], []
    for module in reversed(done):
        try:
            module.unregister()
        except Exception as error:
            print("NineSync: unregister of %s failed: %r" % (module.__name__, error))


# FX's relink operator calls this on its root package (its ADDON_PACKAGE is this extension).
def reload_in_place():
    unregister()
    register()
