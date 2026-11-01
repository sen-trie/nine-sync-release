import json
import os
import shutil
import sys

import addon_utils
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "bl_ext.user_default."
POC = REPO + "ninesync_poc"
STD = REPO + "mmd_tools"
results = []


def install(profile):
    target = os.path.join(profile, "extensions", "user_default")
    os.makedirs(target, exist_ok=True)
    for name, src in (("ninesync_poc", "ext/ninesync_poc"), ("mmd_tools", "ext_standalone/mmd_tools")):
        dst = os.path.join(target, name)
        if not os.path.exists(dst):
            shutil.copytree(os.path.join(HERE, src), dst)


def snap():
    ops = [n for n in dir(bpy.ops.mmd_tools) if not n.startswith("_")] if hasattr(bpy.ops, "mmd_tools") else []
    names = ("mmd_root", "mmd_type", "mmd_camera", "mmd_rigid", "mmd_joint")
    return {
        "ops": len(ops),
        "obj_props": sorted(n for n in names if n in bpy.types.Object.bl_rna.properties),
        "pose_bone_mmd_bone": "mmd_bone" in bpy.types.PoseBone.bl_rna.properties,
        "load_post": len(bpy.app.handlers.load_post),
        "depsgraph_post": len(bpy.app.handlers.depsgraph_update_post),
        "addons": sorted(k for k in bpy.context.preferences.addons.keys() if "mmd" in k or "poc" in k),
    }


def step(label, fn=None):
    err = None
    if fn:
        try:
            fn()
        except BaseException as exc:
            err = "%s: %s" % (type(exc).__name__, exc)
    entry = {"step": label, "error": err, **snap()}
    results.append(entry)
    print("STEP", json.dumps(entry), flush=True)


def enable(name):
    def go():
        mod = addon_utils.enable(name, default_set=True, handle_error=lambda e: (_ for _ in ()).throw(e))
        if mod is None:
            raise RuntimeError("enable returned None for " + name)
    return go


def disable(name):
    return lambda: addon_utils.disable(name, default_set=True, handle_error=lambda e: (_ for _ in ()).throw(e))


def poc_mode():
    import importlib
    return getattr(sys.modules.get(POC + ".mmd_manager"), "mode", "n/a")


def make_model(name="m"):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.mmd_tools.create_mmd_model_root_object(name_j=name, name_e=name, scale=0.08)
    root = next(o for o in bpy.data.objects if o.mmd_type == "ROOT")
    root.mmd_root.comment_text = "keep-me"
    return root


def scenario_internal_only():
    step("start")
    step("enable poc", enable(POC))
    print("MODE", poc_mode())
    step("make model", make_model)
    root = next(o for o in bpy.data.objects if getattr(o, "mmd_type", "") == "ROOT")
    for i in range(3):
        step("disable poc #%d" % i, disable(POC))
        step("enable poc #%d" % i, enable(POC))
        root = bpy.data.objects[root.name]
        results.append({"check": "property survives cycle %d" % i, "value": root.mmd_root.name, "comment": root.mmd_root.comment_text})
        print("CHECK", results[-1], flush=True)
    path = os.path.join(bpy.app.tempdir, "poc.blend")
    step("disable poc before save", disable(POC))
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    step("reopen with poc disabled")
    step("enable poc after reopen", enable(POC))
    root = next(o for o in bpy.data.objects if o.name == "m" or getattr(o, "mmd_type", "") == "ROOT")
    results.append({"check": "after reopen", "comment": root.mmd_root.comment_text})
    print("CHECK", results[-1], flush=True)


def scenario_external_first():
    step("start")
    step("enable standalone", enable(STD))
    step("enable poc", enable(POC))
    print("MODE", poc_mode())
    step("make model", make_model)
    step("disable poc", disable(POC))
    step("enable poc again", enable(POC))
    print("MODE", poc_mode())
    step("disable standalone", disable(STD))
    mgr = sys.modules[POC + ".mmd_manager"]
    step("check() after standalone gone", mgr.check)
    print("MODE", mgr.mode)
    step("make model on bundled", lambda: make_model("m3"))
    step("disable poc", disable(POC))


def scenario_internal_first():
    step("start")
    step("enable poc", enable(POC))
    print("MODE", poc_mode())
    step("make model", make_model)
    step("enable standalone while bundled active", enable(STD))
    step("disable standalone", disable(STD))
    step("disable poc", disable(POC))


def menu_counts():
    out = {}
    for n in ("TOPBAR_MT_file_import", "TOPBAR_MT_file_export", "VIEW3D_MT_armature_add", "VIEW3D_MT_object"):
        out[n] = len(getattr(bpy.types, n)._dyn_ui_initialize())
    return out


def scenario_handoff():
    mgr_name = POC + ".mmd_manager"
    step("start")
    print("MENUS base", menu_counts())
    step("enable poc", enable(POC))
    mgr = sys.modules[mgr_name]
    print("MODE", mgr.mode, "MENUS", menu_counts())
    step("make model", make_model)
    step("enable standalone while bundled active", enable(STD))
    print("MENUS shadowed", menu_counts())
    step("check() -> handover", mgr.check)
    print("MODE", mgr.mode, "MENUS", menu_counts())
    results.append({"check": "ops belong to standalone", "ops": [c.__module__ for c in bpy.types.Operator.__subclasses__() if getattr(c, "bl_idname", "").startswith("mmd_tools.")][:2]})
    print("CHECK", results[-1], flush=True)
    step("make model with standalone", lambda: make_model("m2"))
    step("disable standalone", disable(STD))
    print("MENUS after std off", menu_counts())
    al = sys.modules[POC + ".third_party.mmd_tools.auto_load"]
    odd = [(c.__name__, hasattr(c, "bl_rna"), getattr(c, "is_registered", None)) for c in al.ordered_classes if hasattr(c, "bl_rna") or getattr(c, "is_registered", False)]
    print("PROBE ours after std off:", len(odd), odd[:12], flush=True)
    sub = [(c.__module__.split(".")[2], getattr(c, "is_registered", None)) for c in bpy.types.PropertyGroup.__subclasses__() if c.__name__ == "MMDMaterial"]
    print("PROBE MMDMaterial subclasses:", sub, flush=True)
    step("check() -> bundled returns", mgr.check)
    print("MODE", mgr.mode, "MENUS", menu_counts())
    roots = [o for o in bpy.data.objects if getattr(o, "mmd_type", "") == "ROOT"]
    results.append({"check": "models after return", "roots": [(o.name, o.mmd_root.comment_text) for o in roots]})
    print("CHECK", results[-1], flush=True)
    step("disable poc", disable(POC))
    print("MENUS final", menu_counts(), "handler counts", len(bpy.app.handlers.load_post), len(bpy.app.handlers.save_pre))


def owners():
    ops = {}
    for c in bpy.types.Operator.__subclasses__():
        bid = getattr(c, "bl_idname", "")
        if bid.startswith("mmd_tools.") and getattr(c, "is_registered", False):
            ops.setdefault(c.__module__.split(".")[2], []).append(bid)
    root = bpy.types.Object.bl_rna.properties.get("mmd_root")
    pg = root.fixed_type.__class__.__module__ if root else None
    return {"op_owner_counts": {k: len(v) for k, v in ops.items()}, "mmd_root_type": getattr(root.fixed_type, "bl_rna", None) and root.fixed_type.identifier if root else None}


def classes_state():
    out = {}
    mgr = sys.modules[POC + ".mmd_manager"]
    al = sys.modules[POC + ".third_party.mmd_tools.auto_load"]
    out["bundled_classes"] = len(al.ordered_classes)
    out["bundled_registered"] = sum(1 for c in al.ordered_classes if getattr(c, "is_registered", False))
    sa = sys.modules.get(STD + ".auto_load")
    if sa:
        out["std_classes"] = len(sa.ordered_classes)
        out["std_registered"] = sum(1 for c in sa.ordered_classes if getattr(c, "is_registered", False))
    return out


def scenario_probe():
    mgr_name = POC + ".mmd_manager"
    step("start")
    step("enable poc", enable(POC))
    mgr = sys.modules[mgr_name]
    step("enable standalone over bundled", enable(STD))
    print("PROBE shadowed", owners(), classes_state(), menu_counts(), flush=True)
    step("full bundled unregister (H1)", lambda: sys.modules[POC + ".third_party.mmd_tools"].unregister())
    print("PROBE after H1", owners(), classes_state(), menu_counts(), flush=True)
    mgr.mode = None
    step("toggle standalone (H2)", lambda: (addon_utils.disable(STD, default_set=True), addon_utils.enable(STD, default_set=True)))
    print("PROBE after H2", owners(), classes_state(), menu_counts(), flush=True)
    step("make model", make_model)
    step("disable standalone", disable(STD))
    print("PROBE end", owners(), classes_state(), menu_counts(), flush=True)


def scenario_failure():
    step("start")
    import importlib
    mgr_name = POC + ".mmd_manager"
    enable_failed = {}

    def patched():
        module = importlib.import_module(POC)
        mgr = importlib.import_module(mgr_name)
        bundled = mgr._import_bundled()
        al = importlib.import_module(".auto_load", bundled.__package__)
        target = next(m for m in al.modules if m.__name__.endswith("handlers") is False and hasattr(m, "register") and m.__name__ != al.__name__)
        original = target.register

        def boom():
            raise RuntimeError("simulated failure in " + target.__name__)

        target.register = boom
        enable_failed["restore"] = (target, original)
        addon_utils.enable(POC, default_set=True, handle_error=lambda e: None)

    step("enable poc with injected failure", patched)
    mgr = sys.modules.get(mgr_name)
    print("MODE", getattr(mgr, "mode", "n/a"), "ERR", getattr(mgr, "last_error", None))
    step("after failed start")
    target, original = enable_failed["restore"]
    target.register = original
    step("retry start", lambda: mgr.start())
    print("MODE", mgr.mode)
    step("stop", lambda: mgr.stop())


def scenario_reload():
    step("start")
    step("enable poc", enable(POC))
    step("script.reload", lambda: bpy.ops.script.reload())
    step("after reload")
    print("MODE", poc_mode())
    step("disable poc", disable(POC))


SCENARIOS = {
    "internal_only": scenario_internal_only,
    "external_first": scenario_external_first,
    "internal_first": scenario_internal_first,
    "failure": scenario_failure,
    "probe": scenario_probe,
    "handoff": scenario_handoff,
    "reload": scenario_reload,
}

if __name__ == "__main__":
    name = sys.argv[sys.argv.index("--") + 1]
    install(os.environ["BLENDER_USER_RESOURCES"])
    bpy.ops.extensions.repo_refresh_all() if hasattr(bpy.ops, "extensions") else None
    SCENARIOS[name]()
    print("DONE", name, flush=True)
