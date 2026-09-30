"""Nominal circular application button, without invisible switch internals."""

from nurb import *


@part
def palm_v_button(radius_mm=3.55, thickness_mm=0.9, edge_radius_mm=0.35, draft=False):
    body = Cylinder(
        radius_mm, thickness_mm, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    if not draft:
        body = fillet(body.edges().filter_by(GeomType.CIRCLE), radius=edge_radius_mm)
    return body
