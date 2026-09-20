from nurb import *

from system import cylinder, disk


@part
def maixcam2_lens(neck_radius=6.0, cap_radius=8.0, draft=False):
    """The coaxial lens and cap, modeled from its seating plane upward.

    neck_radius: radius through the adapter's central opening
    cap_radius: radius of the upper lens cap
    """
    if cap_radius <= neck_radius:
        reject("cap_radius must be larger than neck_radius", param="cap_radius")
    lens = cylinder(neck_radius, 5.32)
    lens += cylinder(7.1, 2.12, z=5.28)
    lens += loft(
        [
            disk(7.1, z=7.38),
            disk(cap_radius, z=8.5),
        ],
        ruled=False,
    )
    lens += cylinder(cap_radius, 5.32, z=8.5)
    recess = cylinder(min(6.05, cap_radius - 1.0), 0.8, z=13.31)
    return lens - recess
