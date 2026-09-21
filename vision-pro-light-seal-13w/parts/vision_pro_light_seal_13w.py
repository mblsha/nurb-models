from nurb import *

from system import light_seal_components


@assembly
def vision_pro_light_seal_13w(
    vision_flange_offset_mm=0.0,
    cushion_rail_offset_mm=0.0,
    interface_rail_depth_mm=0.8,
):
    """The editable simplified shell, with its two functional mating rims.

    vision_flange_offset_mm: Moves the Vision Pro mating rim along the interface axis.
    cushion_rail_offset_mm: Moves the soft-cushion mating rim along the interface axis.
    interface_rail_depth_mm: Sets the shallow Vision Pro rim relief.
    """
    values = {
        "vision_flange_offset_mm": vision_flange_offset_mm,
        "cushion_rail_offset_mm": cushion_rail_offset_mm,
        "interface_rail_depth_mm": interface_rail_depth_mm,
    }

    # use() registers the complete six-solid CAD geometry for export. The separately
    # returned regions give the viewer stable names for hiding and isolation.
    use("vision_pro_light_seal_13w_geometry", **values)
    return tuple(
        component(region, name)
        for name, region in light_seal_components(**values)
    )
