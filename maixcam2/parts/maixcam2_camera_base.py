from nurb import *

from system import cylinder, disk


@part
def maixcam2_camera_base(
    ear_width=26.3,
    ear_depth=6.32,
    flange_radius=8.72,
    height=1.0,
    screw_spacing=20.0,
    draft=False,
):
    """The flat default camera foot captured by the adapter's underside pocket.

    screw_spacing: center distance between the two camera fasteners
    """
    ears = extrude(SlotOverall(ear_width, ear_depth, align=(Align.CENTER, Align.CENTER)), amount=height)
    base = ears + cylinder(flange_radius, height)
    screw_holes = Compound(
        [
            loft(
                [
                    disk(1.15, x, 0.0, 0.22),
                    disk(1.65, x, 0.0, 1.08),
                ],
                ruled=False,
            )
            for x in (-screw_spacing / 2.0, screw_spacing / 2.0)
        ]
    )
    return base - screw_holes
