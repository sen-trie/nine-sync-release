import addon_utils
import bpy

NAME = "bl_ext.user_default.ninesync_poc"
mod = addon_utils.enable(NAME, default_set=True)
print("ZIP enabled:", mod is not None)
ops = [n for n in dir(bpy.ops.mmd_tools) if not n.startswith("_")] if hasattr(bpy.ops, "mmd_tools") else []
print("ZIP operators:", len(ops))
before = set(bpy.data.objects)
bpy.ops.mmd_tools.create_mmd_model_root_object(name_j="z", name_e="z", scale=0.08)
print("ZIP model created:", any(o.mmd_type == "ROOT" for o in bpy.data.objects if o not in before))
addon_utils.disable(NAME, default_set=True)
print("ZIP operators after disable:", len([n for n in dir(bpy.ops.mmd_tools) if not n.startswith("_")]) if hasattr(bpy.ops, "mmd_tools") else 0)
