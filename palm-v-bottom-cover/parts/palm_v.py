"""Nominal Palm V exterior assembly with independently editable components."""

import json
from pathlib import Path
from nurb import *


@assembly
def palm_v(front_sheet_mm=0.65, rear_sheet_mm=0.65, draft=False):
    pose = json.loads(
        (Path(__file__).parents[1] / "references/palm-assembly-poses.json").read_text()
    )["rear_cover"]
    rear = use("palm_v_bottom_cover", sheet_thickness_mm=rear_sheet_mm)
    rear = rear.rotate(Axis.X, pose["rotation_x_degrees"]).translate(
        tuple(pose["translation_mm"])
    )
    rear.color = Color(0.68, 0.69, 0.70)
    front = use("palm_v_front_cover", sheet_thickness_mm=front_sheet_mm)
    front.color = Color(0.72, 0.73, 0.74)
    frame = use(
        "palm_v_body", rear_sheet_mm=rear_sheet_mm, front_sheet_mm=front_sheet_mm
    ).translate((0, 0, -0.8))
    frame.color = Color(0.13, 0.14, 0.15)
    display = use("palm_v_display")
    display.color = Color(0.39, 0.47, 0.40)
    rocker = (
        use("palm_v_scroll_button")
        .rotate(Axis((0, -46.3, 0), (1, 0, 0)), 8.0)
        .translate((0, 0, 3.9))
    )
    rocker.color = Color(0.23, 0.24, 0.25)
    result = [
        component(rear, "Rear aluminium cover"),
        component(frame, "Black intermediate chassis"),
        component(front, "Front aluminium cover"),
        component(display, "Display insert"),
        component(rocker, "Scroll rocker"),
    ]
    for x, y, z, name in [
        (-26.2, -42, 3.8, "Left outer application key"),
        (-13, -44, 4.2, "Left inner application key"),
        (13, -44, 4.2, "Right inner application key"),
        (26.2, -42, 3.8, "Right outer application key"),
    ]:
        key = use("palm_v_button").translate((x, y, z))
        key.color = Color(0.23, 0.24, 0.25)
        result.append(component(key, name))
    return result
