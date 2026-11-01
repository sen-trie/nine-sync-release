# Runs one scenario inside a real (windowed) Blender session. Steps are generator
# yields so every wait is a real timer interval. Results print as "R|<json>" lines.
import json
import os
import sys
import time

import faulthandler
import addon_utils
import bpy

REPO = "bl_ext.user_default."
POC = REPO + "ninesync_poc"
STD = os.environ.get("POC_STD", REPO + "mmd_tools")
SCEN = os.environ["POC_SCENARIO"]
OUT = os.environ["POC_OUT"]
BLEND = os.path.join(os.environ["POC_TMP"], "gui.blend")
faulthandler.dump_traceback_later(int(os.environ.get("POC_HANG", "90")), exit=True)
records = []
failures = []


def mgr():
    return sys.modules.get(POC + ".mmd_manager")


def snap():
    m = mgr()
    ops = [n for n in dir(bpy.ops.mmd_tools) if not n.startswith("_")] if hasattr(bpy.ops, "mmd_tools") else []
    reg = None
    if m:
        al = sys.modules.get(POC + ".third_party.mmd_tools.auto_load")
        if al is not None:
            reg = sum(1 for c in al.ordered_classes if getattr(c, "is_registered", False))
    return {
        "mode": getattr(m, "mode", None),
        "ticks": getattr(m, "ticks", None),
        "ops": len(ops),
        "props": sum(1 for n in ("mmd_root", "mmd_type", "mmd_camera", "mmd_rigid", "mmd_joint") if n in bpy.types.Object.bl_rna.properties),
        "bundled_registered": reg,
        "load_post": len(bpy.app.handlers.load_post),
        "load_post_names": [getattr(h, "__qualname__", repr(h)) + "@" + getattr(h, "__module__", "?").rsplit(".", 1)[-1] for h in bpy.app.handlers.load_post],
        "save_pre": len(bpy.app.handlers.save_pre),
        "menu_import": len(bpy.types.TOPBAR_MT_file_import._dyn_ui_initialize()),
        "addons": sorted(k.rsplit(".", 1)[-1] for k in bpy.context.preferences.addons.keys() if "mmd" in k or "poc" in k),
        "err": getattr(m, "last_error", None),
    }


def rec(label, **extra):
    entry = {"label": label, **snap(), **extra}
    records.append(entry)
    print("R|" + json.dumps(entry), flush=True)
    return entry


def expect(label, cond, **extra):
    entry = rec(label, ok=bool(cond), **extra)
    if not cond:
        failures.append(label)
    return entry


def do(label, fn):
    try:
        fn()
        rec(label)
    except BaseException as exc:
        failures.append(label)
        rec(label, error="%s: %s" % (type(exc).__name__, exc))


def enable(name):
    return lambda: addon_utils.enable(name, default_set=True, handle_error=lambda e: (_ for _ in ()).throw(e))


def disable(name):
    return lambda: addon_utils.disable(name, default_set=True, handle_error=lambda e: (_ for _ in ()).throw(e))


def make_model(name):
    before = set(bpy.data.objects)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.mmd_tools.create_mmd_model_root_object(name_j=name, name_e=name, scale=0.08)
    root = next(o for o in bpy.data.objects if o not in before and getattr(o, "mmd_type", "") == "ROOT")
    root.name = name
    root.mmd_root.comment_text = "keep-" + name


def roots():
    return sorted((o.name, o.mmd_root.comment_text) for o in bpy.data.objects if getattr(o, "mmd_type", "") == "ROOT")


def wait_ticks(n=3):
    start = mgr().ticks
    deadline = time.time() + 15
    while mgr().ticks < start + n and time.time() < deadline:
        yield 0.2


# Same resolution Core uses: the module of the registered VMD import operator.
def owner():
    cls = getattr(bpy.types, "MMD_TOOLS_OT_import_vmd", None)
    return cls.__module__ if cls else None


def consistent_internal():
    s = snap()
    o = owner() or ""
    return s["mode"] == "internal" and o.startswith(POC) and s["ops"] > 0 and s["props"] == 5 and s["bundled_registered"] == len(sys.modules[POC + ".third_party.mmd_tools.auto_load"].ordered_classes)


def consistent_external():
    s = snap()
    o = owner() or ""
    return s["mode"] == "external" and o.startswith(STD) and s["ops"] > 0 and s["props"] == 5


def save_reopen():
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    bpy.ops.wm.open_mainfile(filepath=BLEND)


def sc_bundled_first():
    do("enable poc", enable(POC))
    expect("internal after enable", consistent_internal())
    do("make model m1", lambda: make_model("m1"))
    do("enable standalone", enable(STD))
    # Straight after enabling, before any timer tick: what does the world look like?
    before = snap()
    expect("window: both handler sets present before any tick", before["load_post"] >= 4)
    do("window: create model before tick", lambda: make_model("m_window"))
    do("window: save and reopen before tick", save_reopen)
    yield from wait_ticks(3)
    expect("handed over to standalone", consistent_external(), roots=roots())
    expect("handlers back to one set", snap()["load_post"] == 3)
    do("make model m2 on standalone", lambda: make_model("m2"))
    do("disable standalone", disable(STD))
    yield from wait_ticks(3)
    expect("bundled returned", consistent_internal(), roots=roots())
    do("make model m3 on bundled", lambda: make_model("m3"))
    wanted = [("m1", "keep-m1"), ("m2", "keep-m2"), ("m3", "keep-m3")]
    expect("models keep data", [r for r in roots() if r[0] in ("m1", "m2", "m3")] == wanted, roots=roots())
    for i in range(4):
        do("round trip %d: enable standalone" % i, enable(STD))
        yield from wait_ticks(2)
        expect("round trip %d: external" % i, consistent_external())
        do("round trip %d: disable standalone" % i, disable(STD))
        yield from wait_ticks(2)
        expect("round trip %d: internal" % i, consistent_internal())
    do("disable poc", disable(POC))
    expect("nothing left after disable", snap()["ops"] == 0 and snap()["props"] == 0)


def sc_standalone_first():
    do("enable standalone", enable(STD))
    do("enable poc", enable(POC))
    expect("external", consistent_external())
    yield from wait_ticks(2)
    expect("still external after ticks", consistent_external())
    do("disable standalone", disable(STD))
    yield from wait_ticks(3)
    expect("bundled took over", consistent_internal())
    do("make model", lambda: make_model("s1"))
    do("enable standalone again", enable(STD))
    yield from wait_ticks(3)
    expect("external again", consistent_external(), roots=roots())
    do("disable poc while external", disable(POC))
    expect("standalone untouched after poc disabled", snap()["ops"] > 0 and snap()["props"] == 5 and (owner() or "").startswith(STD))
    do("disable standalone", disable(STD))
    expect("clean", snap()["ops"] == 0 and snap()["props"] == 0)


def sc_persistence():
    do("enable poc", enable(POC))
    do("make model", lambda: make_model("p1"))
    do("script.reload", lambda: bpy.ops.script.reload())
    yield from wait_ticks(2)
    expect("alive after script.reload", consistent_internal() and bpy.app.timers.is_registered(mgr().check), roots=roots())
    do("save", lambda: bpy.ops.wm.save_as_mainfile(filepath=BLEND))
    do("new file", lambda: bpy.ops.wm.read_homefile(use_empty=True))
    yield from wait_ticks(2)
    expect("timer survives new file", bpy.app.timers.is_registered(mgr().check) and consistent_internal())
    do("open saved", lambda: bpy.ops.wm.open_mainfile(filepath=BLEND))
    expect("data after reopen", ("p1", "keep-p1") in roots(), roots=roots())
    do("disable poc", disable(POC))
    do("save with poc disabled", lambda: bpy.ops.wm.save_as_mainfile(filepath=BLEND))
    do("reopen with poc disabled", lambda: bpy.ops.wm.open_mainfile(filepath=BLEND))
    do("enable poc", enable(POC))
    expect("data after re-enable", ("p1", "keep-p1") in roots(), roots=roots())


def sc_failure():
    import importlib
    importlib.import_module(POC)
    mm = sys.modules[POC + ".mmd_manager"]
    _module, auto_load, _h, _m = mm._parts()
    target = next(x for x in auto_load.modules if x.__name__.endswith("model_validation"))
    original = target.register

    def boom():
        raise RuntimeError("injected")

    target.register = boom
    do("enable with injected failure", enable(POC))
    expect("failed mode, nothing registered", snap()["mode"] == "failed" and snap()["ops"] == 0 and snap()["props"] == 0 and snap()["load_post"] == 2)
    yield from wait_ticks(2)
    expect("still failed after ticks (no retry loop)", snap()["mode"] == "failed")
    target.register = original
    do("disable", disable(POC))
    do("enable (recover)", enable(POC))
    expect("recovered", consistent_internal())
    do("disable", disable(POC))
    expect("clean", snap()["ops"] == 0 and snap()["props"] == 0)


def sc_broken_standalone():
    # A standalone that is listed but cannot register (too old for this Blender).
    try:
        addon_utils.enable(STD, default_set=True, handle_error=lambda e: (_ for _ in ()).throw(e))
        rec("standalone enable unexpectedly succeeded")
    except BaseException as exc:
        rec("standalone enable failed as expected", error=str(exc)[:80])
    do("enable poc", enable(POC))
    expect("bundled copy used despite listed-but-broken standalone", consistent_internal())
    yield from wait_ticks(3)
    expect("stays internal across ticks", consistent_internal())
    do("make model", lambda: make_model("b1"))
    do("disable poc", disable(POC))
    expect("clean", snap()["ops"] == 0 and snap()["props"] == 0)
    do("enable poc with broken standalone listed first time order 2", enable(POC))
    expect("internal again", consistent_internal())
    try:
        addon_utils.enable(STD, default_set=True, handle_error=lambda e: (_ for _ in ()).throw(e))
    except BaseException:
        pass
    yield from wait_ticks(3)
    expect("bundled-first then broken standalone: still intact", consistent_internal())
    do("disable poc", disable(POC))


def sc_startup_prepare():
    order = os.environ["POC_ORDER"].split(",")
    for name in order:
        do("enable " + name, enable(POC if name == "poc" else STD))
    do("save userpref", lambda: bpy.ops.wm.save_userpref())
    yield 0.2


def sc_startup_check():
    yield from wait_ticks(4)
    s = snap()
    expect("both add-ons enabled at launch", "ninesync_poc" in s["addons"] and "mmd_tools" in s["addons"])
    ok = consistent_external() or consistent_internal()
    expect("coherent registration after launch (%s)" % s["mode"], ok, owner=owner())
    expect("exactly one set of mmd handlers", s["load_post"] == 3 and s["save_pre"] == 1 + (0 if s["mode"] else 0) or s["load_post"] == 3, load_post_names=s["load_post_names"])
    expect("menus not duplicated", s["menu_import"] == 6)
    do("make model", lambda: make_model("st1"))
    do("disable standalone", disable(STD))
    yield from wait_ticks(3)
    expect("bundled takes over after standalone disabled", consistent_internal())
    do("enable standalone", enable(STD))
    yield from wait_ticks(3)
    expect("external again", consistent_external())


def sc_window_flip():
    do("enable poc", enable(POC))
    do("make model", lambda: make_model("w1"))
    do("enable standalone", enable(STD))
    do("disable standalone before any tick", disable(STD))
    expect("broken state visible before tick", snap()["ops"] == 0 or snap()["bundled_registered"] != len(sys.modules[POC + ".third_party.mmd_tools.auto_load"].ordered_classes))
    yield from wait_ticks(3)
    expect("repaired by tick", consistent_internal(), roots=roots())
    do("make model after repair", lambda: make_model("w2"))
    expect("data kept", [("w1", "keep-w1"), ("w2", "keep-w2")] == [r for r in roots() if r[0] in ("w1", "w2")], roots=roots())
    do("disable poc", disable(POC))
    expect("clean", snap()["ops"] == 0 and snap()["props"] == 0)


def sc_window_disable_poc():
    do("enable poc", enable(POC))
    do("enable standalone", enable(STD))
    do("disable poc before any tick", disable(POC))
    expect("standalone fully functional", snap()["ops"] > 0 and snap()["props"] == 5 and (owner() or "").startswith(STD))
    do("make model on standalone", lambda: make_model("x1"))
    yield from wait_ticks(1) if mgr() and bpy.app.timers.is_registered(mgr().check) else iter(())
    do("disable standalone", disable(STD))
    expect("clean", snap()["ops"] == 0 and snap()["props"] == 0)


def sc_window_quit():
    do("enable poc", enable(POC))
    do("enable standalone", enable(STD))
    expect("quitting inside the window", True)
    yield 0.0


def sc_shutdown():
    do("enable poc", enable(POC))
    do("make model", lambda: make_model("q1"))
    expect("ready to quit with bundled registered", consistent_internal())
    yield 0.5


SCENARIOS = {"bundled_first": sc_bundled_first, "standalone_first": sc_standalone_first,
             "persistence": sc_persistence, "startup_prepare": sc_startup_prepare, "startup_check": sc_startup_check, "broken_standalone": sc_broken_standalone, "window_flip": sc_window_flip, "window_disable_poc": sc_window_disable_poc, "window_quit": sc_window_quit, "failure": sc_failure, "shutdown": sc_shutdown}
gen = None


def finish():
    summary = {"scenario": SCEN, "failures": failures, "records": len(records)}
    print("R|" + json.dumps({"summary": summary}), flush=True)
    with open(OUT, "w") as f:
        json.dump({"summary": summary, "records": records}, f, indent=1)
    bpy.ops.wm.quit_blender()


def pump():
    global gen
    if gen is None:
        gen = SCENARIOS[SCEN]()
    try:
        return next(gen)
    except StopIteration:
        finish()
        return None
    except BaseException as exc:
        import traceback
        traceback.print_exc()
        failures.append("driver crash: %r" % (exc,))
        finish()
        return None


bpy.app.timers.register(pump, first_interval=2.0, persistent=True)
