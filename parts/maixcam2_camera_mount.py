from nurb import *


@part
def maixcam2_camera_mount(draft=False):
    """The supplied flat camera adapter in its native, pocket-down coordinates."""
    return import_step("references/maixcam2-camera-mount.step")
