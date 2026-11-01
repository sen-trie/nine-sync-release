from . import mmd_manager


def register():
    mmd_manager.start()


def unregister():
    mmd_manager.stop()
