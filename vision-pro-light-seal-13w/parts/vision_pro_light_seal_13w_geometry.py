from nurb import *

from system import light_seal_geometry


@part
def vision_pro_light_seal_13w_geometry(
    vision_flange_offset_mm=0.0,
    cushion_rail_offset_mm=0.0,
    interface_rail_depth_mm=0.8,
):
    """The complete six-solid CAD geometry behind the named Light Seal assembly.

    vision_flange_offset_mm: Moves the Vision Pro mating rim along the interface axis.
    cushion_rail_offset_mm: Moves the soft-cushion mating rim along the interface axis.
    interface_rail_depth_mm: Sets the shallow Vision Pro rim relief.
    """
    return light_seal_geometry(
        vision_flange_offset_mm=vision_flange_offset_mm,
        cushion_rail_offset_mm=cushion_rail_offset_mm,
        interface_rail_depth_mm=interface_rail_depth_mm,
    )
