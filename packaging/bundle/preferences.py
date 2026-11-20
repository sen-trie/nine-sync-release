# The combined extension's one preferences class. Blender allows one AddonPreferences per add-on id, and this
# package is one add-on, so Core's and FX's settings live together in a single class registered on the bundle's
# own id. The components register no preferences class of their own while this package marks itself
# NINESYNC_PREFERENCES_OWNER, and each finds this one by walking its package parents.
#
# Nothing is redefined here: Core's properties come from its CorePreferenceProperties mixin and FX's from the
# annotations of its own preferences class, so a new property in either component shows up without edits. FX's
# property names are unchanged, and the id is the one FX's class had in earlier bundled releases, so values users
# already stored are kept.
import importlib

import bpy
from bpy.types import AddonPreferences

_state = {"cls": None}


def build_class(core, fx):
    core_mixin = core.CorePreferenceProperties
    fx_names = list(getattr(fx.NineSyncFXPreferences, "__annotations__", {}))
    annotations = {**getattr(core_mixin, "__annotations__", {}), **getattr(fx.NineSyncFXPreferences, "__annotations__", {})}

    def draw(self, context):
        self.draw_core(self.layout)
        self.layout.separator()
        for name in fx_names:
            self.layout.prop(self, name)

    return type(
        "NineSyncPreferences",
        (core_mixin, AddonPreferences),
        {"bl_idname": __package__, "__annotations__": annotations, "draw": draw, "__module__": __name__},
    )


# Registered before the components so their startup lookups already find it.
def register():
    if _state["cls"] is not None:
        return
    core = importlib.import_module(".ninesync_core.ui.preferences", __package__)
    fx = importlib.import_module(".ninesync_fx.ui.preferences", __package__)
    cls = build_class(core, fx)
    bpy.utils.register_class(cls)
    _state["cls"] = cls


def unregister():
    cls, _state["cls"] = _state["cls"], None
    if cls is not None:
        bpy.utils.unregister_class(cls)
