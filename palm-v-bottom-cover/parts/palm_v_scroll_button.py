"""Smooth scroll rocker contour inferred from the rough front scan."""

from nurb import *
from palm_front_geometry import rocker_face


@part
def palm_v_scroll_button(thickness_mm=1.6, draft=False):
    body = extrude(rocker_face(-0.15), amount=thickness_mm, dir=(0, 0, 1))
    if not draft:
        top = body.edges().filter_by(
            lambda edge: edge.bounding_box().min.Z > thickness_mm - 0.001
        )
        body = fillet(top, radius=0.4)
    return body
