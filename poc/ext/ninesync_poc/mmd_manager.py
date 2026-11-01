import importlib
import traceback

import bpy

# "internal": bundled copy registered by us. "external": a standalone mmd_tools owns the
# registration. "conflict"/"failed": the bundled copy is NOT registered and last_error says
# why. None: not started.
mode = None
last_error = None
CHECK_INTERVAL = 0.5
ticks = 0
_bundled = None


def _log(*parts):
    print("[ninesync_poc]", *parts, flush=True)


# Only for log messages. Whether a standalone really owns the registration is decided
# from the registered properties and the bundled classes' state, not from this list: an
# add-on that is listed but failed to register (e.g. an mmd_tools too old for this
# Blender) must not suppress the bundled copy.
def external_module_names():
    return [
        name
        for name in bpy.context.preferences.addons.keys()
        if name.rsplit(".", 1)[-1] in ("mmd_tools", "blender_mmd_tools")
        and not name.startswith(__package__)
    ]


def _props_registered():
    return "mmd_root" in bpy.types.Object.bl_rna.properties


def _import_bundled():
    global _bundled
    if _bundled is None:
        _bundled = importlib.import_module(".third_party.mmd_tools", __package__)
    return _bundled


def _parts():
    module = _import_bundled()
    auto_load = importlib.import_module(".auto_load", module.__package__)
    handlers = importlib.import_module(".handlers", module.__package__)
    m17n = importlib.import_module(".m17n", module.__package__)
    return module, auto_load, handlers, m17n


# True while every bundled class is still the registered one. A standalone registering
# later replaces same-named classes, so this turns False at once without relying on the
# add-on list.
def bundled_intact():
    _module, auto_load, _handlers, _m17n = _parts()
    return _props_registered() and all(getattr(c, "is_registered", False) for c in auto_load.ordered_classes)


# Registers the bundled copy. Classes that a handover left registered are not
# unregistered (their property hooks would delete properties); their own register hook
# is re-run instead, which recreates the properties and menu entries the standalone
# removed. A failure rolls back what this call registered.
def _register_bundled():
    module, auto_load, handlers, m17n = _parts()
    fresh = []
    rehooked = []
    try:
        for cls in auto_load.ordered_classes:
            if getattr(cls, "is_registered", False):
                if hasattr(cls, "register"):
                    cls.register()
                rehooked.append(cls)
            else:
                bpy.utils.register_class(cls)
                fresh.append(cls)
        for sub in auto_load.modules:
            if sub.__name__ != auto_load.__name__ and hasattr(sub, "register"):
                sub.register()
        bpy.app.translations.register(module.PACKAGE_NAME, m17n.translations_dict)
        handlers.MMDHanders.register()
    except Exception:
        _log("bundled registration failed, rolling back")
        traceback.print_exc()
        _rollback(fresh)
        raise


def _rollback(fresh):
    module, auto_load, handlers, _m17n = _parts()
    for step in (handlers.MMDHanders.unregister, lambda: bpy.app.translations.unregister(module.PACKAGE_NAME)):
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
    for cls in reversed(fresh):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


# Removes only what is identity-specific to the bundled copy after a standalone has
# replaced the shared registrations: handlers, translations, keymap items, menu entries.
# No class or property is unregistered.
def _abandon_bundled():
    module, _auto_load, handlers, _m17n = _parts()
    fileio = importlib.import_module(".operators.fileio", module.__package__)
    menus = importlib.import_module(".menus", module.__package__)
    steps = [handlers.MMDHanders.unregister, lambda: bpy.app.translations.unregister(module.PACKAGE_NAME), fileio.unregister]
    for name in dir(menus):
        menu = getattr(menus, name)
        if hasattr(menu, "draw_menu") and hasattr(menu, "unregister"):
            steps.append(menu.unregister)
    for step in steps:
        try:
            step()
        except Exception:
            traceback.print_exc()


def start():
    global mode, last_error
    last_error = None
    if _props_registered():
        mode = "external"
        _log("standalone mmd_tools present, bundled copy not registered:", external_module_names())
    else:
        try:
            _register_bundled()
            mode = "internal"
            _log("bundled mmd_tools registered")
        except Exception as error:
            mode = "failed"
            last_error = "bundled mmd_tools failed to register: %r" % (error,)
    _start_watchdog()
    return mode


# Reconciles the mode with reality. Cheap; also called before every NineSync operation so
# correctness does not depend on the timer having ticked.
def check():
    global mode, last_error, ticks
    ticks += 1
    if mode == "internal" and not bundled_intact():
        _log("registration was taken over or broken, handing over")
        _abandon_bundled()
        mode = "external"
    if mode == "external" and not _props_registered():
        _log("no standalone mmd_tools left, registering bundled copy")
        try:
            _register_bundled()
            if not bundled_intact():
                raise RuntimeError("bundled registration incomplete")
            mode = "internal"
        except Exception as error:
            mode = "conflict"
            last_error = "could not take over from standalone mmd_tools: %r" % (error,)
    return CHECK_INTERVAL


def _start_watchdog():
    if not bpy.app.timers.is_registered(check):
        bpy.app.timers.register(check, first_interval=CHECK_INTERVAL, persistent=True)


def stop():
    global mode
    if bpy.app.timers.is_registered(check):
        bpy.app.timers.unregister(check)
    if mode == "internal" and bundled_intact():
        _import_bundled().unregister()
    elif mode in ("internal", "conflict"):
        _abandon_bundled()
    mode = None
