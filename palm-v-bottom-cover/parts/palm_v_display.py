"""Visible display insert; hidden electronics and stack thickness are provisional."""

from nurb import *
from palm_front_geometry import window_face


@part
def palm_v_display(insert_thickness_mm=0.8, surface_z_mm=3.593, draft=False):
    return extrude(
        window_face(-0.15), amount=insert_thickness_mm, dir=(0, 0, 1)
    ).translate((0, 0, surface_z_mm - insert_thickness_mm))
