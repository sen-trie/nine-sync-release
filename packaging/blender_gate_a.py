"""Gate A checks, run INSIDE Blender (background) against installed extensions.

    blender -b --factory-startup --python-exit-code 1 --python packaging/blender_gate_a.py -- orders <report.json>
    blender -b --factory-startup --python-exit-code 1 --python packaging/blender_gate_a.py -- prefs-set <report.json>
    blender -b --python-exit-code 1 --python packaging/blender_gate_a.py -- prefs-check <report.json>

The combined extension (ninesync_bundled), standalone Core (ninesync), standalone FX (ninesync_fx) and the
external mmd_tools must all be installed in the throwaway profile. Nothing is enabled beforehand.

orders      S1: all four foreign-copy enable orders fail closed and leave the first copy intact; refusing,
            disabling the refused copy, normal enable/disable, reload_in_place and FX's relink path.
prefs-set   S4: the combined build's one preferences class holds Core's and FX's settings; they are
            writable, the import scale is published, and everything is saved to the profile's userpref.
prefs-check S4, second process (a restart): the saved values come back and Core applies the import scale at
            startup; the published scale also survives File > Open (S8).

Prints "GATE ok|FAIL <name>" lines, writes a JSON report and exits non-zero on any failure.
"""
import importlib
import json
import os
import sys
import tempfile

import addon_utils
import bpy

PKG = "bl_ext.user_default.ninesync_bundled"
CORE = "bl_ext.user_default.ninesync"
FX = "bl_ext.user_default.ninesync_fx"
MMD = "bl_ext.user_default.mmd_tools"
results = []


def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": str(detail)})
    suffix = (" | " + str(detail)) if (detail or not ok) else ""
    print("GATE %s %s%s" % ("ok  " if ok else "FAIL", name, suffix), flush=True)
    return ok


def registry():
    return bpy.app.driver_namespace.get("ninesync_hooks") or {}


def enable(name, default_set=False):
    errors = []
    module = addon_utils.enable(name, default_set=default_set, persistent=default_set, handle_error=lambda e: errors.append(repr(e)))
    return module, errors


def disable(name, default_set=False):
    addon_utils.disable(name, default_set=default_set)


# Everything NineSync has registered, by identity. Two snapshots that are equal mean nothing was replaced,
# removed or re-registered.
def snapshot(identity=True):
    classes = {}
    for name in dir(bpy.types):
        cls = getattr(bpy.types, name, None)
        module = getattr(cls, "__module__", "") or ""
        if "ninesync" in module and isinstance(cls, type):
            classes[name] = (module, id(cls) if identity else 0)
    reg = registry()
    marker = reg.get("core")
    handlers = {}
    for group in ("frame_change_post", "load_post", "depsgraph_update_post", "save_pre"):
        handlers[group] = sorted(
            "%s.%s" % (getattr(h, "__module__", ""), getattr(h, "__qualname__", ""))
            for h in getattr(bpy.app.handlers, group)
            if "ninesync" in (getattr(h, "__module__", "") or "")
        )
    hooks = {}
    for group in ("post_sync", "clean", "report"):
        hooks[group] = {owner: getattr(fn, "__module__", "") for owner, fn in (reg.get(group) or {}).items()}
    return {
        "classes": classes,
        "scene_mmd_bridge": hasattr(bpy.types.Scene, "mmd_bridge"),
        "scene_ninesync_fx": hasattr(bpy.types.Scene, "ninesync_fx"),
        "wm_rigify": hasattr(bpy.types.WindowManager, "ninesync_rigify_free"),
        "object_visible": hasattr(bpy.types.Object, "ninesync_visible"),
        "core_marker": None if marker is None else (marker.get("package"), tuple(marker.get("version") or ())),
        "hooks": hooks,
        "handlers": handlers,
        "api_version": reg.get("api_version"),
    }


def diff(before, after):
    return sorted(k for k in before if before[k] != after.get(k))


def empty(state):
    return (
        not state["classes"]
        and not state["scene_mmd_bridge"]
        and not state["scene_ninesync_fx"]
        and not state["wm_rigify"]
        and not state["object_visible"]
        and state["core_marker"] is None
        and not any(state["hooks"].values())
        and not any(state["handlers"].values())
    )


def sync_operator():
    cls = getattr(bpy.types, "NINESYNC_OT_sync_now", None)
    return cls is not None and hasattr(bpy.ops.ninesync, "sync_now")


# What a copy has to show while it is the active one.
def working(which):
    state = snapshot()
    if which in ("core", "bundle"):
        ok = state["scene_mmd_bridge"] and sync_operator() and state["core_marker"] is not None
        if not ok:
            return False, state
    if which in ("fx", "bundle"):
        ok = state["scene_ninesync_fx"] and "ninesync_fx" in state["hooks"]["post_sync"] and state["object_visible"]
        if not ok:
            return False, state
    return True, state


ORDERS = [
    ("standalone Core, then the combined build", CORE, "core", PKG),
    ("the combined build, then standalone Core", PKG, "bundle", CORE),
    ("standalone FX, then the combined build", FX, "fx", PKG),
    ("the combined build, then standalone FX", PKG, "bundle", FX),
]


def run_orders():
    module, errors = enable(MMD)
    check("external mmd_tools enables", module is not None, errors)
    for title, first, kind, second in ORDERS:
        tag = title
        first_module, errors = enable(first)
        ok, before = working(kind)
        check("%s: the first copy enables and works" % tag, first_module is not None and ok, errors or before["core_marker"])
        if not ok:
            disable(first)
            continue
        # Refused: an exception, and not one byte of the active copy touched.
        second_module, errors = enable(second)
        after = snapshot()
        refused = second_module is None and bool(errors)
        check("%s: the second copy is refused" % tag, refused, errors[:1])
        check("%s: refusal changed nothing of the first copy" % tag, diff(before, after) == [], diff(before, after))
        still, _state = working(kind)
        check("%s: the first copy still works after the refusal" % tag, still)
        # Disabling the refused copy, the way Blender does it and the way a half-loaded module would be torn down.
        disable(second)
        after_disable = snapshot()
        check("%s: disabling the refused copy changed nothing" % tag, diff(before, after_disable) == [], diff(before, after_disable))
        # Blender drops a module whose register() raised, but its unregister() can still be called (a stale
        # entry in the add-on list, or the module re-imported), so it is called here on purpose.
        try:
            leftover = sys.modules.get(second) or importlib.import_module(second)
            leftover.unregister()
        except Exception as error:
            check("%s: unregister() of the refused copy is harmless" % tag, False, repr(error))
        else:
            after_unregister = snapshot()
            check("%s: unregister() of the refused copy is harmless" % tag, diff(before, after_unregister) == [], diff(before, after_unregister))
        still, _state = working(kind)
        check("%s: the first copy still works after the refused copy's disable" % tag, still)
        # The first copy goes away cleanly, and the other one can then be used.
        disable(first)
        check("%s: disabling the first copy leaves nothing behind" % tag, empty(snapshot()), snapshot()["classes"].keys())
        second_kind = {PKG: "bundle", CORE: "core", FX: "fx"}[second]
        second_module, errors = enable(second)
        ok, _state = working(second_kind)
        check("%s: the second copy enables once the first is gone" % tag, second_module is not None and ok, errors)
        disable(second)
        check("%s: and disables cleanly" % tag, empty(snapshot()))

    # Standalone Core and standalone FX together stay a supported pair.
    core_module, e1 = enable(CORE)
    fx_module, e2 = enable(FX)
    ok_core, _s = working("core")
    ok_fx, _s = working("fx")
    check("standalone Core and FX enable together", core_module is not None and fx_module is not None and ok_core and ok_fx, e1 + e2)
    # ... and the combined build refuses next to both.
    pair = snapshot()
    module, errors = enable(PKG)
    check("the combined build is refused next to standalone Core and FX", module is None and bool(errors), errors[:1])
    check("... without changing either", diff(pair, snapshot()) == [])
    disable(PKG)
    check("... and disabling it changes nothing", diff(pair, snapshot()) == [])
    disable(FX)
    disable(CORE)
    check("standalone pair disables cleanly", empty(snapshot()))

    # Normal enable / disable / enable and the sanctioned reload_in_place of each copy alone.
    for name, kind in ((PKG, "bundle"), (CORE, "core"), (FX, "fx")):
        label = {PKG: "combined", CORE: "standalone Core", FX: "standalone FX"}[name]
        module, errors = enable(name)
        ok, first = working(kind)
        check("%s: enables" % label, module is not None and ok, errors)
        disable(name)
        check("%s: disables to nothing" % label, empty(snapshot()))
        module, errors = enable(name)
        ok, first = working(kind)
        check("%s: re-enables" % label, module is not None and ok, errors)
        before = snapshot(identity=False)
        try:
            module.reload_in_place()
            error = ""
        except Exception as caught:
            error = repr(caught)
        ok, after = working(kind)
        check("%s: reload_in_place keeps everything registered" % label, not error and ok and diff(before, snapshot(identity=False)) == [], error or diff(before, snapshot(identity=False)))
        again = snapshot(identity=False)
        try:
            module.reload_in_place()
            error = ""
        except Exception as caught:
            error = repr(caught)
        check("%s: reload_in_place twice in a row" % label, not error and diff(again, snapshot(identity=False)) == [], error)
        disable(name)
        check("%s: disables to nothing after reloads" % label, empty(snapshot()))

    # The relink path (a stale settings class) goes through the root package's reload_in_place; in the
    # combined build that is the bundle, which re-registers both components and the preferences class.
    for name, kind, relink_module in (
        (PKG, "bundle", PKG + ".ninesync_fx.ui.relink"),
        (CORE, "core", CORE + ".ui.relink"),
        (FX, "fx", FX + ".ui.relink"),
    ):
        label = {PKG: "combined", CORE: "standalone Core", FX: "standalone FX"}[name]
        module, errors = enable(name)
        if module is None:
            check("%s: relink needs the add-on enabled" % label, False, errors)
            continue
        relink = importlib.import_module(relink_module)
        before = snapshot(identity=False)
        original = relink.settings_outdated
        relink.settings_outdated = lambda scene: True
        try:
            relink.relink_settings()
            error = ""
        except Exception as caught:
            error = repr(caught)
        finally:
            relink.settings_outdated = original
        ok, _state = working(kind)
        check("%s: relink re-registers cleanly" % label, not error and ok and diff(before, snapshot(identity=False)) == [], error or diff(before, snapshot(identity=False)))
        disable(name)
        check("%s: disables to nothing after a relink" % label, empty(snapshot()))
    disable(MMD)


class FakeLayout:
    def __init__(self):
        self.props = []

    def row(self, **_k):
        return self

    def prop(self, _data, name, **_k):
        self.props.append(name)

    def separator(self, **_k):
        pass

    def label(self, **_k):
        pass

    def __getattr__(self, name):
        return lambda *a, **k: self


FX_NAMES = ("cache_dir", "cache_limit_mb", "bake_limit_mb")


def addon_preferences():
    entry = bpy.context.preferences.addons.get(PKG)
    return entry.preferences if entry is not None else None


def run_prefs_set():
    module, errors = enable(PKG, default_set=True)
    check("combined build enables", module is not None, errors)
    prefs = addon_preferences()
    check("one preferences object exists on the bundle id", prefs is not None, [a for a in bpy.context.preferences.addons.keys() if "ninesync" in a])
    if prefs is None:
        return
    names = [p.identifier for p in prefs.bl_rna.properties if p.identifier not in ("rna_type", "bl_idname")]
    check("it holds Core's and FX's properties", all(n in names for n in ("use_import_scale", "import_scale") + FX_NAMES), names)
    classes = [c.__name__ for c in bpy.types.AddonPreferences.__subclasses__() if getattr(c, "bl_idname", "").startswith(PKG) and c.is_registered]
    check("exactly one AddonPreferences class is registered for the package and its components", len(classes) == 1, classes)
    shown = FakeLayout()

    class Proxy:
        layout = shown

        def __getattr__(self, name):
            return getattr(prefs, name)

    try:
        type(prefs).draw(Proxy(), bpy.context)
    except Exception as error:
        check("the preferences panel draws", False, repr(error))
    else:
        check("the panel lists the import scale and FX's settings", all(n in shown.props for n in ("use_import_scale", "import_scale") + FX_NAMES), shown.props)
    core = importlib.import_module(PKG + ".ninesync_core.ui.preferences")
    fx_cache = importlib.import_module(PKG + ".ninesync_fx.runtime.cache_store")
    found = core.addon_preferences()
    check("Core's addon_preferences() resolves the bundle's class", found is not None and found.as_pointer() == prefs.as_pointer(), found)
    check("FX resolves the same object", fx_cache._preferences() is not None and fx_cache._preferences().as_pointer() == prefs.as_pointer())
    check("the Core marker is the bundle's Core component", (registry().get("core") or {}).get("package") == PKG + ".ninesync_core", registry().get("core"))
    check("no preferences class is registered under a component id", all(
        c.bl_idname == PKG for c in bpy.types.AddonPreferences.__subclasses__() if getattr(c, "bl_idname", "").startswith(PKG) and c.is_registered))
    prefs.use_import_scale = True
    prefs.import_scale = 0.07
    prefs.cache_limit_mb = 123
    prefs.bake_limit_mb = 321
    check("import_scale is writable and published to FX as it changes", abs(registry()["shared"].get("import_scale", 0) - 0.07) < 1e-6, registry()["shared"])
    prefs.use_import_scale = False
    check("turning it off withdraws the published value", "import_scale" not in registry()["shared"])
    prefs.use_import_scale = True
    bpy.ops.wm.save_userpref()
    path = bpy.utils.user_resource("CONFIG", path="userpref.blend")
    check("the profile's userpref was written", os.path.isfile(path), path)


def run_prefs_check():
    prefs = addon_preferences()
    check("after a restart the bundle is enabled from the saved preferences", PKG in bpy.context.preferences.addons.keys(), list(bpy.context.preferences.addons.keys())[:6])
    if prefs is None:
        check("after a restart the bundle's preferences exist", False)
        return
    check("saved Core import scale is back", prefs.use_import_scale and abs(prefs.import_scale - 0.07) < 1e-6, (prefs.use_import_scale, prefs.import_scale))
    check("saved FX values are back (names and id unchanged)", prefs.cache_limit_mb == 123 and prefs.bake_limit_mb == 321, (prefs.cache_limit_mb, prefs.bake_limit_mb))
    core = importlib.import_module(PKG + ".ninesync_core")
    mmd_loaded, errors = enable(MMD)
    core.startup_check()
    shared = registry().get("shared") or {}
    check("the import scale is published at startup", abs(shared.get("import_scale", 0) - 0.07) < 1e-6, shared)
    wm = bpy.context.window_manager
    props = None
    try:
        props = wm.operator_properties_last("mmd_tools.import_model")
    except Exception:
        pass
    check("the scale is applied to mmd_tools' importer defaults", props is not None and abs(getattr(props, "scale", 0) - 0.07) < 1e-6, getattr(props, "scale", None))
    # S8 on the shipping package: opening another file empties driver_namespace; Core republishes.
    scratch = tempfile.mkdtemp(prefix="ninesync_gate_")
    other = os.path.join(scratch, "other.blend")
    bpy.ops.wm.save_as_mainfile(filepath=other, copy=True)
    registry()["shared"]["marker_key"] = 1
    bpy.ops.wm.open_mainfile(filepath=other)
    shared = registry().get("shared") or {}
    check("File > Open: the registry was rebuilt (a stray key is gone)", "marker_key" not in shared, shared)
    check("File > Open: the import scale is published again", abs(shared.get("import_scale", 0) - 0.07) < 1e-6, shared)
    check("File > Open: Core and FX are both back in the registry", registry().get("core") is not None and "ninesync_fx" in (registry().get("post_sync") or {}))
    bpy.ops.wm.open_mainfile(filepath=other)
    check("a second File > Open keeps it", abs((registry().get("shared") or {}).get("import_scale", 0) - 0.07) < 1e-6)
    prefs = addon_preferences()
    prefs.use_import_scale = False
    check("Set Import Scale off withdraws it", "import_scale" not in registry()["shared"])
    disable(PKG)
    check("the bundle disables to nothing", empty(snapshot()))


MODES = {"orders": run_orders, "prefs-set": run_prefs_set, "prefs-check": run_prefs_check}

if "--" in sys.argv:
    mode, out = sys.argv[sys.argv.index("--") + 1 : sys.argv.index("--") + 3]
else:
    raise SystemExit("usage: -- <orders|prefs-set|prefs-check> <report.json>")
check("blender >= 5.3", bpy.app.version >= (5, 3, 0), bpy.app.version_string)
try:
    MODES[mode]()
except Exception as error:
    import traceback

    check("%s ran to the end" % mode, False, traceback.format_exc())
failed = [r for r in results if not r["ok"]]
with open(out, "w", encoding="utf-8") as handle:
    json.dump({"mode": mode, "blender": bpy.app.version_string, "passed": len(results) - len(failed), "failed": len(failed), "checks": results}, handle, indent=2)
print("GATE summary %s: %d passed, %d failed" % (mode, len(results) - len(failed), len(failed)), flush=True)
sys.exit(1 if failed else 0)
