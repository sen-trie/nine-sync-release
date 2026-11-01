# Runs Core's real-sync validation with the BUNDLED mmd_tools as the only mmd_tools.
# usage: blender -b --factory-startup --python pmm_sync_bundled.py -- <file.pmm>
# Needs Core installed as an extension and the POC extension installed; the PMM's PMX
# paths must exist. Core finds mmd_tools through the registered operator's module, so no
# adapter is involved.
import runpy
import sys

import addon_utils
import bpy

addon_utils.enable("bl_ext.user_default.ninesync_poc", default_set=False)
assert hasattr(bpy.types, "MMD_TOOLS_OT_import_vmd"), "bundled mmd_tools did not register"
print("PMMSYNC mmd_tools operator module:", bpy.types.MMD_TOOLS_OT_import_vmd.__module__)
core = "/".join([__import__("os").environ["NINESYNC_CORE_SRC"], "tests", "manual", "validate_real.py"])
sys.argv = [core, "--"] + sys.argv[sys.argv.index("--") + 1 :]
runpy.run_path(core, run_name="__main__")
