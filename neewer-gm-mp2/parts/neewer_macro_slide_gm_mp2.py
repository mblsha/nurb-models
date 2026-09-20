from math import cos, radians, sin

from nurb import *


def _cylinder_x(radius, length, center):
    return Pos(*center) * Rot(0, 90, 0) * Cylinder(
        radius, length, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )


def _cylinder_y(radius, length, center):
    return Pos(*center) * Rot(90, 0, 0) * Cylinder(
        radius, length, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )


def _rounded_box(length, width, height, center, radius=1.5):
    shape = Pos(*center) * Box(
        length, width, height, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )
    return fillet(shape.edges(), radius=radius)


def _large_focus_knob(center, length=19.5):
    x, y, z = center
    knob = _cylinder_x(8.1, length, center)
    for angle in range(0, 360, 45):
        radial = Pos(
            x,
            y + 7.85 * cos(radians(angle)),
            z + 7.85 * sin(radians(angle)),
        )
        knob += radial * Rot(0, 90, 0) * Cylinder(
            2.08, length, align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )
    return knob


@assembly
def neewer_macro_slide_gm_mp2(
    feet_open_deg=55.0,
    arca_detent=1,
    carriage_position_mm=70.0,
    draft=False,
):
    """Editable reconstruction of the Neewer GM-MP2 macro focusing rail.

    feet_open_deg: how far the two support feet swing down from their folded position
    arca_detent: quarter-turn position of the rotating top Arca assembly, from 0 to 3
    carriage_position_mm: carriage travel from the left end of the published 140 mm range
    """
    if feet_open_deg < 0.0 or feet_open_deg > 65.0:
        reject("support feet move from 0 to 65 degrees", "feet_open_deg")
    if arca_detent not in (0, 1, 2, 3):
        reject("Arca mount locks only at quarter turns 0, 1, 2, or 3", "arca_detent")
    if carriage_position_mm < 0.0 or carriage_position_mm > measured("slider_range"):
        reject("carriage travel is limited to the published 140 mm range", "carriage_position_mm")

    rod_y_front = measured("front_guide_rod_center_y")
    rod_y_back = measured("rear_guide_rod_center_y")
    screw_y = measured("lead_screw_center_y")
    drive_z = measured("guide_rod_center_z")
    rod_radius = measured("guide_rod_diameter") / 2.0

    left_end_x = 6.0
    right_end_x = 200.5
    frame_y = (rod_y_front + rod_y_back) / 2.0
    frame_width = 46.0

    # The rail extrusions are centred on the guide rods. Keeping them on the scan's
    # measured 0..44 mm envelope avoids the broad false side faces produced by a
    # symmetric 46 mm guess. The shallow centre web is visible in clear sections away
    # from the carriage; it ties the scale bed together below the lead screw.
    front_rail = _rounded_box(201.0, 9.0, 8.0, (106.5, rod_y_front, 4.0), 1.2)
    rear_rail = _rounded_box(201.0, 9.0, 8.0, (106.5, rod_y_back, 4.0), 1.2)
    centre_web = _rounded_box(181.0, 22.0, 3.6, (103.0, frame_y, 1.8), 0.8)
    # The folded feet sit flush in two pockets rather than occupying the web. The
    # extra half millimetre around each outline leaves their declared sweep clear.
    centre_web -= Pos(27.5, frame_y, 2.0) * Box(
        30.0, 12.0, 5.0, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )
    centre_web -= Pos(179.0, frame_y, 2.0) * Box(
        30.0, 12.0, 5.0, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )
    left_end = _rounded_box(13.0, 44.5, 23.0, (left_end_x, frame_y, 11.5), 2.3)
    right_end = _rounded_box(13.0, 44.5, 23.0, (right_end_x, frame_y, 11.5), 2.3)
    frame = component(
        front_rail + rear_rail + centre_web + left_end + right_end,
        "frame and end blocks",
    )

    front_rod = component(
        _cylinder_x(rod_radius, 194.5, (103.25, rod_y_front, drive_z)),
        "front guide rod",
    )
    rear_rod = component(
        _cylinder_x(rod_radius, 194.5, (103.25, rod_y_back, drive_z)),
        "rear guide rod",
    )
    lead_screw = component(
        _cylinder_x(2.85, 204.0, (102.0, screw_y, drive_z)), "lead screw"
    )

    knob_center = (
        measured("large_focus_knob_center_x"),
        measured("large_focus_knob_center_y"),
        measured("large_focus_knob_center_z"),
    )
    knob_neck = _cylinder_x(5.2, 12.0, (-3.0, knob_center[1], knob_center[2]))
    focus_knob = component(_large_focus_knob(knob_center) + knob_neck, "large focus knob")

    # The sibling part stands the exact B-rep on end for printing. Undo that display
    # transform here so the following scan-derived translation stays unchanged.
    sleeve = Rot(0.0, 90.0, 0.0) * Pos(-17.2, 0.0, -17.0) * use(
        "neewer_outer_focus_sleeve"
    )
    sleeve = Pos(
        measured("outer_sleeve_alignment_x"),
        measured("outer_sleeve_alignment_y"),
        measured("outer_sleeve_alignment_z"),
    ) * sleeve
    sleeve = component(sleeve, "exact outer focus sleeve")

    carriage_x = 33.5 + carriage_position_mm
    # The carriage is an open casting around the two guide bearings and lead-screw
    # nut. A pair of full boxes put large invented faces through the centre of the
    # scan. Two bearing housings, the nut boss, and a thin upper deck preserve the
    # visible envelope while leaving the real openings between them.
    front_bearing = _rounded_box(43.0, 11.5, 12.0, (carriage_x, rod_y_front, 15.0), 1.8)
    rear_bearing = _rounded_box(43.0, 11.5, 12.0, (carriage_x, rod_y_back, 15.0), 1.8)
    nut_block = _rounded_box(22.0, 12.5, 11.0, (carriage_x, screw_y, 15.5), 1.5)
    upper_deck = _rounded_box(40.0, 42.0, 4.0, (carriage_x, frame_y, 22.0), 1.6)
    carriage = component(
        front_bearing + rear_bearing + nut_block + upper_deck,
        "sliding carriage",
    )

    rotary_base = component(
        Pos(carriage_x, frame_y, 28.0)
        * Cylinder(21.0, 6.0, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "rotary base",
    )

    top_rotation = float(arca_detent) * 90.0
    # The scanned upper body's envelope is x=78.85..128 and y=-2.6..51.9 in
    # the sideways reference detent. Keep both clamp layers on that measured
    # footprint; the earlier narrow, over-long plate missed its far edge.
    arca_clamp_local = _rounded_box(49.2, 54.5, 9.0, (0.0, 2.55, 34.0), 2.0)
    arca_clamp = Pos(carriage_x, frame_y, 0.0) * Rot(0, 0, top_rotation) * arca_clamp_local
    arca_clamp = component(arca_clamp, "rotating Arca clamp")

    arca_plate_local = _rounded_box(49.2, 54.5, 7.0, (0.0, 2.55, 42.0), 2.3)
    arca_plate_local -= Pos(0.0, 0.0, 37.0) * Cylinder(3.2, 10.0)
    arca_plate = Pos(carriage_x, frame_y, 0.0) * Rot(0, 0, top_rotation) * arca_plate_local
    arca_plate = component(arca_plate, "top Arca plate")

    clamp_shaft_local = _cylinder_y(4.52, 18.0, (0.0, 34.9, 35.5))
    clamp_knob_local = _cylinder_y(7.85, 16.8, (0.0, 47.3, 35.5))
    clamp_knob = Pos(carriage_x, frame_y, 0.0) * Rot(0, 0, top_rotation) * (
        clamp_shaft_local + clamp_knob_local
    )
    clamp_knob = component(clamp_knob, "Arca clamp knob")

    left_foot = hinge(
        _rounded_box(29.0, 11.0, 4.0, (27.5, frame_y, -1.0), 1.0),
        Axis((13.0, frame_y, -3.0), (0.0, 1.0, 0.0)),
        through=(0.0, 65.0),
        at=feet_open_deg,
        name="left support foot",
        step=5.0,
    )
    left_foot = component(left_foot, "left support foot")
    right_foot = hinge(
        _rounded_box(29.0, 11.0, 4.0, (179.0, frame_y, -1.0), 1.0),
        Axis((193.5, frame_y, -3.0), (0.0, -1.0, 0.0)),
        through=(0.0, 65.0),
        at=feet_open_deg,
        name="right support foot",
        step=5.0,
    )
    right_foot = component(right_foot, "right support foot")

    return (
        frame,
        front_rod,
        rear_rod,
        lead_screw,
        focus_knob,
        sleeve,
        carriage,
        rotary_base,
        arca_clamp,
        arca_plate,
        clamp_knob,
        left_foot,
        right_foot,
    )
