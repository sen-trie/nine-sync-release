import importlib
import re
import traceback

import bpy

# "internal": bundled copy registered by us. "external": a standalone mmd_tools was
# active, so nothing of ours is registered. None: not started.
mode = None
last_error = None
_bundled = None


def _log(*parts):
    print("[ninesync_poc]", *parts, flush=True)


# Standalone mmd_tools is recognised by its registered Object.mmd_root property, which
# holds regardless of the package name it was installed under (extension or legacy).
def external_registered():
    return mode != "internal" and "mmd_root" in bpy.types.Object.bl_rna.properties


def external_module_names():
    return [
        name
        for name in bpy.context.preferences.addons.keys()
        if name.rsplit(".", 1)[-1] in ("mmd_tools", "blender_mmd_tools")
        and not name.startswith(__package__)
    ]


def _import_bundled():
    global _bundled
    if _bundled is None:
        _bundled = importlib.import_module(".third_party.mmd_tools", __package__)
    return _bundled


# Registers the bundled copy and, on any failure, unregisters whatever got registered
# so a retry starts from a clean state.
def _register_bundled():
    module = _import_bundled()
    auto_load = importlib.import_module(".auto_load", module.__package__)
    registered = []
    try:
        for cls in auto_load.ordered_classes:
            bpy.utils.register_class(cls)
            registered.append(cls)
        for sub in auto_load.modules:
            if sub.__name__ == auto_load.__name__:
                continue
            if hasattr(sub, "register"):
                sub.register()
        from_handlers = importlib.import_module(".handlers", module.__package__)
        bpy.app.translations.register(
            module.PACKAGE_NAME, importlib.import_module(".m17n", module.__package__).translations_dict
        )
        from_handlers.MMDHanders.register()
    except Exception:
        _log("bundled registration failed, rolling back")
        traceback.print_exc()
        _rollback(module, auto_load, registered)
        raise


def _rollback(module, auto_load, registered):
    handlers = importlib.import_module(".handlers", module.__package__)
    for step in (
        handlers.MMDHanders.unregister,
        lambda: bpy.app.translations.unregister(module.PACKAGE_NAME),
    ):
        try:
            step()
        except Exception:
            pass
    for sub in reversed(auto_load.modules):
        if sub.__name__ != auto_load.__name__ and hasattr(sub, "unregister"):
            try:
                sub.unregister()
            except Exception:
                pass
    for cls in reversed(registered):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


def _start_watchdog():
    if not bpy.app.timers.is_registered(check):
        bpy.app.timers.register(check, first_interval=1.0, persistent=True)


def start():
    global mode, last_error
    last_error = None
    if external_registered():
        mode = "external"
        _log("standalone mmd_tools active, bundled copy not registered:", external_module_names())
        _start_watchdog()
        return mode
    try:
        _register_bundled()
    except Exception as error:
        mode = None
        last_error = repr(error)
        return mode
    mode = "internal"
    _log("bundled mmd_tools registered")
    _start_watchdog()
    return mode


# Called when a standalone mmd_tools was enabled after the bundled copy registered. Blender
# lets the later registration replace same-named classes, and the property hooks of the
# classes it replaced would delete properties the standalone now owns. So no class or
# property is unregistered here; only identity-specific hooks are removed: handlers,
# translations, keymap items and menu draw functions of our copy. Leaked classes are
# purged before any later re-registration (see _purge_leaked).
def _abandon_bundled():
    module = _import_bundled()
    handlers = importlib.import_module(".handlers", module.__package__)
    fileio = importlib.import_module(".operators.fileio", module.__package__)
    menus = importlib.import_module(".menus", module.__package__)
    steps = [
        handlers.MMDHanders.unregister,
        lambda: bpy.app.translations.unregister(module.PACKAGE_NAME),
        fileio.unregister,
    ]
    for name in dir(menus):
        menu = getattr(menus, name)
        if hasattr(menu, "draw_menu") and hasattr(menu, "unregister"):
            steps.append(menu.unregister)
    for step in steps:
        try:
            step()
        except Exception:
            traceback.print_exc()


# Unregisters one class of ours that a handover left registered. Its property hook may
# delete an attribute the standalone's unregister already removed, which raises before
# Blender drops the class; the missing attribute is stubbed so the hook can finish.
def _unregister_stale(cls):
    stubs = []
    for _ in range(24):
        for owner, name in stubs:
            if not hasattr(owner, name):
                setattr(owner, name, bpy.props.BoolProperty())
        try:
            bpy.utils.unregister_class(cls)
            return True
        except AttributeError as error:
            found = re.search(r"type object '(\w+)' has no attribute '(\w+)'", str(error))
            owner = getattr(bpy.types, found.group(1), None) if found else None
            if owner is None or (owner, found.group(2)) in stubs:
                _log("stale unregister failed:", cls.__name__, error)
                return False
            stubs.append((owner, found.group(2)))
        except Exception as error:
            _log("stale unregister failed:", cls.__name__, type(error).__name__, error)
            return False
    return False


# Before registering the bundled copy again, drops classes of ours that an earlier
# handover left registered.
def _purge_leaked():
    module = _import_bundled()
    auto_load = importlib.import_module(".auto_load", module.__package__)
    failed = []
    for cls in reversed(auto_load.ordered_classes):
        if getattr(cls, "is_registered", False) and not _unregister_stale(cls):
            failed.append(cls.__name__)
    if failed:
        _log("could not purge stale classes:", failed)


# Reconciles our mode with whichever mmd_tools is active. Run from a timer in Blender.
def check():
    global mode
    if mode == "internal" and external_module_names():
        _log("standalone mmd_tools appeared, handing over")
        _abandon_bundled()
        mode = "external"
    elif mode == "external" and not external_module_names() and not external_registered():
        _log("standalone mmd_tools went away, registering bundled copy")
        _purge_leaked()
        start()
    return 1.0


def stop():
    global mode
    if bpy.app.timers.is_registered(check):
        bpy.app.timers.unregister(check)
    if mode == "internal":
        module = _import_bundled()
        module.unregister()
    mode = None
