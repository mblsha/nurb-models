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
    arca_detent=1,
    carriage_position_mm=70.0,
    draft=False,
):
    """Editable reconstruction of the Neewer GM-MP2 macro focusing rail.

    arca_detent: quarter-turn position of the rotating top Arca assembly, from 0 to 3
    carriage_position_mm: carriage travel from the left end of the published 140 mm range
    """
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

    # Repeated X-normal scan sections expose the two rails as the male halves of a
    # continuous Arca-Swiss plate. The 46-degree engagement flanks are kept sharp;
    # rounding them would change the mounting interface.
    bottom_arca_left_profile = Plane.YZ * Polygon(
        (0.05, 5.25),
        (0.05, 11.05),
        (0.45, 11.75),
        (1.05, 12.13),
        (7.05, 12.13),
        (7.70, 11.85),
        (8.08, 11.15),
        (8.08, 0.50),
        (7.60, 0.06),
        (3.55, 0.06),
        (3.15, 0.50),
        (3.15, 1.75),
        (5.10, 3.85),
        (4.70, 4.50),
        (0.55, 4.53),
        (0.15, 4.90),
        align=None,
    )
    bottom_arca_right_profile = Plane.YZ * Polygon(
        *((44.20 - y, z) for y, z in reversed((
            (0.05, 5.25),
            (0.05, 11.05),
            (0.45, 11.75),
            (1.05, 12.13),
            (7.05, 12.13),
            (7.70, 11.85),
            (8.08, 11.15),
            (8.08, 0.50),
            (7.60, 0.06),
            (3.55, 0.06),
            (3.15, 0.50),
            (3.15, 1.75),
            (5.10, 3.85),
            (4.70, 4.50),
            (0.55, 4.53),
            (0.15, 4.90),
        ))),
        align=None,
    )
    bottom_arca = Pos(203.0, 0.0, 0.0) * (
        extrude(bottom_arca_left_profile, 199.0)
        + extrude(bottom_arca_right_profile, 199.0)
    )
    bottom_arca = component(bottom_arca, "bottom Arca plate")
    left_end = _rounded_box(13.0, 44.5, 23.0, (left_end_x, frame_y, 11.5), 2.3)
    right_end = _rounded_box(13.0, 44.5, 23.0, (right_end_x, frame_y, 11.5), 2.3)
    end_blocks = component(left_end + right_end, "end blocks")

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
    # In the scanned detent the upper clamp spans x=78.85..127.95 and
    # y=-2.55..51.70. Its dovetail opening is 37.9 mm at the jaw tips and 42.8 mm
    # at the seat, giving the measured 50-degree clamping flanks.
    clamp_x_min = 78.85 - carriage_x
    clamp_x_max = 127.95 - carriage_x
    clamp_length = clamp_x_max - clamp_x_min
    clamp_y_min = -2.55 - frame_y
    fixed_flank_low_y = 3.40 - frame_y
    fixed_tip_y = 5.60 - frame_y
    movable_tip_y = 43.50 - frame_y
    movable_flank_low_y = 46.20 - frame_y
    clamp_y_max = 51.70 - frame_y

    fixed_profile = Plane.YZ * Polygon(
        (clamp_y_min, 31.20),
        (movable_tip_y, 31.20),
        (movable_tip_y, 39.90),
        (fixed_flank_low_y, 39.90),
        (fixed_tip_y, 44.40),
        (clamp_y_min, 44.40),
        align=None,
    )
    fixed_clamp_local = Pos(clamp_x_min, 0.0, 0.0) * extrude(
        fixed_profile, clamp_length
    )
    # Twin top pockets match the scan while the central 15 mm bridge retains the
    # pivot load path. Their floor is measured at z=36.95 mm.
    pocket_y_center = ((17.0 + 27.5) / 2.0) - frame_y
    pocket_width = 27.5 - 17.0
    for pocket_global_x_min, pocket_global_x_max in ((79.0, 96.0), (111.0, 128.0)):
        pocket_x_min = pocket_global_x_min - carriage_x
        pocket_x_max = pocket_global_x_max - carriage_x
        fixed_clamp_local -= Pos(
            (pocket_x_min + pocket_x_max) / 2.0,
            pocket_y_center,
            (36.95 + 45.0) / 2.0,
        ) * Box(
            pocket_x_max - pocket_x_min,
            pocket_width,
            45.0 - 36.95,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
    fixed_clamp = Pos(carriage_x, frame_y, 0.0) * Rot(
        0, 0, top_rotation
    ) * fixed_clamp_local
    fixed_clamp = component(fixed_clamp, "fixed top Arca clamp")

    movable_profile = Plane.YZ * Polygon(
        (movable_tip_y, 31.20),
        (clamp_y_max, 31.20),
        (clamp_y_max, 44.40),
        (movable_tip_y, 44.40),
        (movable_flank_low_y, 39.90),
        (movable_tip_y, 39.90),
        align=None,
    )
    movable_jaw_local = Pos(clamp_x_min, 0.0, 0.0) * extrude(
        movable_profile, clamp_length
    )
    movable_jaw = Pos(carriage_x, frame_y, 0.0) * Rot(
        0, 0, top_rotation
    ) * movable_jaw_local
    movable_jaw = component(movable_jaw, "movable top Arca jaw")

    clamp_shaft_local = _cylinder_y(
        4.52,
        18.0,
        (103.30 - carriage_x, 34.9, 35.5),
    )
    clamp_knob_local = _cylinder_y(
        7.85,
        16.0,
        (103.30 - carriage_x, 69.8 - frame_y, 35.5),
    )
    clamp_knob = Pos(carriage_x, frame_y, 0.0) * Rot(0, 0, top_rotation) * (
        clamp_shaft_local + clamp_knob_local
    )
    clamp_knob = component(clamp_knob, "clamp knob")

    return (
        bottom_arca,
        end_blocks,
        front_rod,
        rear_rod,
        lead_screw,
        focus_knob,
        sleeve,
        carriage,
        rotary_base,
        fixed_clamp,
        movable_jaw,
        clamp_knob,
    )
