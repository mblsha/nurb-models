"""Smooth symmetric front aluminium skin inferred from the rough assembled scan."""

from nurb import *
from palm_front_geometry import front_half, window_face, rocker_face, BUTTON_CENTERS


@part
def palm_v_front_cover(sheet_thickness_mm=0.65, button_clearance_mm=0.15, draft=False):
    if not 0.35 <= sheet_thickness_mm <= 0.9:
        reject(
            "Use a provisional front sheet gauge between0.35 and0.9mm.",
            "sheet_thickness_mm",
        )
    face = front_half()
    half = Solid.thicken(face, sheet_thickness_mm, normal_override=(0, 0, -1))
    tools = [
        extrude(window_face(), amount=20, dir=(0, 0, 1)).translate((0, 0, -10)),
        extrude(rocker_face(button_clearance_mm), amount=20, dir=(0, 0, 1)).translate(
            (0, 0, -10)
        ),
    ]
    for x, y in BUTTON_CENTERS:
        tools.append(Cylinder(3.55 + button_clearance_mm, 20).translate((x, y, 0)))
    for tool in tools:
        half = half - tool
    body = half.fuse(half.mirror(Plane.YZ))
    if not body.is_valid or len(body.solids()) != 1:
        raise ValueError("Front cover did not form one valid sheet")
    return body
