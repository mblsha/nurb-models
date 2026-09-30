from math import cos, radians, sin

from nurb import *
from neewer_feet import folding_feet, foot_swing_clearance
from parts._neewer_exterior import BLACK_METAL, camera_plate_components, exterior_hardware_components, exterior_marking_components


def _styled_component(solid, name):
    silver = {"front guide rod", "rear guide rod", "lead screw", "large focus knob", "clamp knob"}
    if name == "exact outer focus sleeve":
        return component(solid, name, color="#CF9542", metalness=0.0, roughness=0.72)
    if name in silver:
        return component(solid, name, color="#C7CBD1", metalness=0.45, roughness=0.30)
    return component(solid, name, color="#3A3F46", metalness=0.25, roughness=0.50)


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


def _round_x_envelope(center, stations):
    _, y, z = center
    return loft([Pos(at, y, z) * Rot(0, 90, 0) * Circle(radius)
                 for at, radius in stations])


def _large_focus_knob(center, length=19.5):
    x, y, z = center
    left = x - length / 2.0
    # The supplied sleeve occupies x=-17..-12. Preserve its original eight-lobe
    # contact section exactly; scan-derived rounding lives outside that band.
    right = -5.0
    core_center = ((left + right) / 2.0, y, z)
    knob = _cylinder_x(8.1, right - left, core_center)
    for angle in range(0, 360, 45):
        radial = (core_center[0], y + 7.85 * cos(radians(angle)),
                  z + 7.85 * sin(radians(angle)))
        knob += _cylinder_x(2.08, right - left, radial)
    front = _round_x_envelope(center, [
        (left, 8.25), (left + 0.5, 8.95), (left + 1.5, 9.5),
        (left + 2.5, 10.3),
    ])
    middle = _cylinder_x(10.3, -12.0 - (left + 2.5),
                         (((left + 2.5) - 12.0) / 2.0, y, z))
    shoulder = _round_x_envelope(center, [
        (-12.0, 10.3), (-11.0, 9.45), (-10.0, 8.64), (-9.0, 7.55),
        (-8.0, 6.64), (-7.0, 5.98), (-6.0, 5.49), (-5.0, 5.24),
    ])
    return knob & (front + middle + shoulder)


def _detailed_end_block(x, frame_y):
    # Independent scan rays locate both end planes; the old 13 mm boxes
    # narrowed the available travel and intersected the carriage at its stops.
    x_min, x_max = (0.0, 11.31) if x < 100.0 else (195.34, 206.80)
    block = _rounded_box(x_max - x_min, 44.5, 24.2,
                         ((x_min + x_max) / 2.0, frame_y, 12.1), 2.3)
    # Repeated scan sections resolve a shallow counterbore and recessed drive
    # socket, but not a screw thread or an exact socket standard.
    socket_x = 5.6 if x < 100.0 else 201.0
    for y in (12.1, 32.1):
        recess = Pos(socket_x, y, 24.2) * Cylinder(3.8, 1.6)
        socket = loft([Pos(socket_x, y, z) * Circle(radius)
                       for z, radius in ((21.8, 0.95), (22.5, 1.35),
                                         (23.0, 1.65), (23.45, 2.15))])
        block -= recess + socket
    # The small dimples above each guide-rod axis are visible surface seats.
    # Their concealed fastener threads are deliberately not reconstructed.
    seat_x = 7.2 if x < 100.0 else 199.5
    for y in (4.6, 39.6):
        seat = loft([Pos(seat_x, y, z) * Circle(radius)
                     for z, radius in ((22.7, 0.4), (23.0, 0.8),
                                       (23.5, 1.35), (24.3, 2.45))])
        block -= seat
    return block


def _small_clamp_knob(center):
    x, y, z = center
    # Eight shallow axial flutes dominate the scan's angular profile. The
    # rounded envelope makes them fade into both shoulders rather than stop.
    body = _cylinder_y(8.1, 18.8, (x, y - 1.4, z))
    for angle in range(12, 372, 45):
        groove = _cylinder_y(2.4, 20.0,
                            (x + 9.7 * cos(radians(angle)), y - 1.4,
                             z + 9.7 * sin(radians(angle))))
        body -= groove
    def shoulder(stations):
        return loft([Pos(x, y + at, z) * Rot(90, 0, 0) * Circle(radius)
                     for at, radius in stations])
    inner = shoulder([(-10.8, 4.7), (-9.8, 5.8), (-8.8, 6.9),
                      (-7.8, 7.45), (-6.8, 8.15), (-5.8, 8.2)])
    middle = _cylinder_y(8.2, 10.0, (x, y - 0.8, z))
    outer = shoulder([(4.2, 8.2), (5.2, 8.0), (6.2, 7.6),
                      (7.2, 7.4), (8.0, 6.75)])
    envelope = inner + middle + outer
    return body & envelope


def _base_upper_windows():
    # Smoothed scan contours at z=7.5 mm. The two end-land profiles are not
    # rectangles; retaining their curved shoulders avoids invented straight faces.
    outlines = (
        (
            (70.19, 36.078), (71.845, 36.154), (73.502, 36.181), (75.16, 36.176),
            (76.819, 36.153), (78.48, 36.131), (80.141, 36.125), (81.803, 36.142),
            (83.449, 36.092), (85.07, 35.943), (86.701, 35.944), (88.353, 36.122),
            (90.013, 36.287), (91.669, 36.264), (93.302, 36.12), (94.915, 36.055),
            (96.625, 36.088), (98.363, 35.936), (99.511, 35.034), (99.843, 33.521),
            (99.612, 31.907), (99.061, 30.311), (98.426, 28.728), (97.877, 27.154),
            (97.393, 25.584), (96.913, 24.015), (96.389, 22.443), (95.822, 20.871),
            (95.233, 19.301), (94.643, 17.736), (94.072, 16.18), (93.542, 14.635),
            (93.073, 13.087), (92.675, 11.381), (92.148, 9.707), (91.126, 8.63),
            (89.637, 8.178), (87.945, 8.047), (86.251, 8.003), (84.579, 8.004),
            (82.922, 8.036), (81.278, 8.086), (79.641, 8.142), (78.006, 8.191),
            (76.369, 8.191), (74.724, 8.1), (73.074, 8.054), (71.419, 8.091),
            (69.757, 8.137), (68.085, 8.121), (66.412, 8.057), (64.748, 8.014),
            (63.104, 8.05), (61.473, 8.138), (59.839, 8.212), (58.19, 8.215),
            (56.531, 8.162), (54.877, 8.106), (53.245, 8.101), (51.619, 8.14),
            (49.961, 8.166), (48.238, 8.131), (46.515, 8.148), (44.907, 8.417),
            (43.532, 9.134), (42.469, 10.335), (41.748, 11.854), (41.399, 13.513),
            (41.411, 15.181), (41.706, 16.817), (42.199, 18.391), (42.819, 19.909),
            (43.515, 21.418), (44.19, 22.962), (44.392, 24.496), (43.927, 26.016),
            (43.213, 27.612), (42.628, 29.248), (42.511, 30.824), (43.104, 32.247),
            (44.253, 33.444), (45.7, 34.346), (47.237, 34.964), (48.794, 35.486),
            (50.376, 35.888), (51.993, 36.116), (53.637, 36.207), (55.301, 36.205),
            (56.975, 36.153), (58.652, 36.095), (60.323, 36.074), (61.981, 36.114),
            (63.627, 36.158), (65.264, 36.12), (66.897, 35.993), (68.539, 35.972),
        ),
        (
            (111.381, 24.26), (110.792, 22.707), (110.22, 21.151), (109.665, 19.592),
            (109.124, 18.031), (108.596, 16.469), (108.08, 14.906), (107.579, 13.33),
            (107.123, 11.671), (106.962, 10.019), (107.692, 8.773), (109.16, 8.12),
            (110.825, 7.973), (112.513, 7.977), (114.187, 7.998), (115.849, 8.027),
            (117.501, 8.059), (119.146, 8.085), (120.786, 8.099), (122.424, 8.097),
            (124.067, 8.083), (125.72, 8.063), (127.385, 8.041), (129.054, 8.024),
            (130.719, 8.017), (132.378, 8.023), (134.031, 8.036), (135.681, 8.054),
            (137.328, 8.073), (138.975, 8.089), (140.622, 8.098), (142.273, 8.098),
            (143.925, 8.089), (145.58, 8.073), (147.237, 8.051), (148.896, 8.023),
            (150.558, 7.993), (152.219, 7.973), (153.875, 7.996), (155.52, 8.098),
            (157.151, 8.313), (158.761, 8.676), (160.343, 9.221), (161.852, 9.977),
            (163.192, 10.961), (164.267, 12.19), (165.022, 13.631), (165.438, 15.209),
            (165.502, 16.846), (165.275, 18.489), (164.882, 20.104), (164.456, 21.659),
            (164.232, 23.202), (164.454, 24.838), (164.854, 26.473), (165.192, 28.072),
            (165.359, 29.689), (165.249, 31.376), (164.798, 33.048), (163.981, 34.476),
            (162.782, 35.435), (161.265, 35.904), (159.576, 36.057), (157.86, 36.078),
            (156.185, 36.068), (154.536, 36.047), (152.897, 36.033), (151.254, 36.033),
            (149.607, 36.045), (147.956, 36.063), (146.302, 36.083), (144.644, 36.1),
            (142.984, 36.109), (141.321, 36.108), (139.657, 36.1), (137.994, 36.086),
            (136.334, 36.069), (134.678, 36.053), (133.029, 36.038), (131.386, 36.029),
            (129.746, 36.029), (128.102, 36.043), (126.453, 36.074), (124.802, 36.111),
            (123.156, 36.14), (121.513, 36.152), (119.85, 36.151), (118.138, 36.14),
            (116.466, 35.967), (115.152, 35.178), (114.345, 33.776), (113.963, 32.143),
            (113.64, 30.497), (113.152, 28.916), (112.583, 27.36), (111.985, 25.81),
        ),
    )
    return [Face(Wire(Spline(*[(x, y, 0) for x, y in points], periodic=True).edges())) for points in outlines]



@assembly
def neewer_macro_slide_gm_mp2(
    arca_detent=1,
    carriage_position_mm=70.35,
    feet_deployed=False,
    camera_plate_installed=False,
    include_sleeve=True,
    draft=False,
):
    """Editable reconstruction of the Neewer GM-MP2 macro focusing rail.

    arca_detent: top Arca position: 0=scan/longitudinal, 1=90° product photo, 2=180°, 3=270°
    carriage_position_mm: carriage travel from the left end of the published 140 mm range
    camera_plate_installed: show the photo-inferred removable plate, six pads and camera stud
    include_sleeve: show the supplied custom sleeve accessory around the focus knob
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

    # Repeated X-normal scan sections expose the two rails as the male halves of an
    # Arca-Swiss plate. The upper rail shell is continuous, while the lower tongue
    # and return stop at the folded-foot bays. The 46-degree engagement flanks are
    # kept sharp; rounding them would change the mounting interface.
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
    bottom_arca = Pos(206.0, 0.0, 0.0) * (
        extrude(bottom_arca_left_profile, 205.25)
        + extrude(bottom_arca_right_profile, 205.25)
    )
    # The lower dovetail is absent where the collapsible feet fold against the
    # rail. Scan-section transitions are repeatable to about ±0.25 mm. Limit the
    # cuts to z < 4.55 mm so the upper side-rail ledges remain continuous from
    # x=0.75 through x=206.0 mm.
    for bay_x_min, bay_x_max in ((10.0, 31.75), (175.25, 197.5)):
        bay_length = bay_x_max - bay_x_min
        bay_center_x = (bay_x_min + bay_x_max) / 2.0
        left_lower_gap = Pos(bay_center_x, 5.6, 2.225) * Box(
            bay_length,
            5.2,
            4.65,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
        right_lower_gap = Pos(bay_center_x, 38.6, 2.225) * Box(
            bay_length,
            5.2,
            4.65,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
        bottom_arca -= left_lower_gap + right_lower_gap
    # The horizontal scan section at z=2.5 mm resolves six rounded diagonal
    # openings. Their common form is a parallelogram with circular corners;
    # independent fits preserve the small measured differences between slots.
    # Face-normal samples place the web's underside at 0.11 and top at 4.23 mm.
    # Keep the web inside the existing rails so the verified contact flanks and
    # folded-foot clearances are unaffected by this detail reconstruction.
    web_bottom, web_top = 0.11, 4.23
    web = Pos(103.5, 22.1, (web_bottom + web_top) / 2.0) * Box(
        143.5, 28.04, web_top - web_bottom,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    for x, y, width, height, shear, radius in (
        (43.58, 8.17, 11.41, 27.91, 0.3651, 3.51),
        (61.67, 8.13, 11.43, 27.96, 0.3651, 3.54),
        (79.75, 8.08, 11.43, 28.02, 0.3661, 3.59),
        (105.35, 8.06, 11.42, 28.02, 0.3662, 3.60),
        (123.49, 8.07, 11.42, 27.99, 0.3640, 3.55),
        (141.61, 8.08, 11.40, 27.97, 0.3639, 3.52),
    ):
        opening = Polygon(
            (x, y), (x + width, y),
            (x + width + shear * height, y + height),
            (x + shear * height, y + height),
            align=None,
        )
        opening = fillet(opening.vertices(), radius=radius)
        web -= Pos(0, 0, web_bottom - 0.1) * extrude(
            opening, web_top - web_bottom + 0.2
        )
    # The central scan opening is retained as an unthreaded envelope. The scan
    # does not resolve the thread form well enough to claim a manufactured fit.
    web -= Pos(103.43, 22.09, web_bottom - 0.1) * Cylinder(
        2.67, web_top - web_bottom + 0.2,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    # Sections above the lower ribs expose two larger lightening windows. Their
    # end lands and center bridge remain below the independently moving carriage.
    upper_web = Pos(103.375, 22.1, (4.23 + 8.3) / 2.0) * Box(
        205.25, 28.04, 8.3 - 4.23,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    for opening in _base_upper_windows():
        upper_web -= Pos(0, 0, 4.13) * extrude(opening, 4.27, dir=(0, 0, 1))
    foot_clearance = foot_swing_clearance()
    bottom_arca = _styled_component(bottom_arca + web + upper_web - foot_clearance, "bottom Arca plate")
    left_end = _detailed_end_block(left_end_x, frame_y)
    right_end = _detailed_end_block(right_end_x, frame_y)

    front_rod = _styled_component(
        _cylinder_x(rod_radius, 194.5, (103.25, rod_y_front, drive_z)),
        "front guide rod",
    )
    rear_rod = _styled_component(
        _cylinder_x(rod_radius, 194.5, (103.25, rod_y_back, drive_z)),
        "rear guide rod",
    )
    # The repaired scan does not resolve a dependable thread pitch. Retain this
    # explicit smooth screw envelope instead of inventing a mating thread.
    lead_screw = _styled_component(
        _cylinder_x(2.85, 204.0, (102.0, screw_y, drive_z)), "lead screw"
    )

    knob_center = (
        measured("large_focus_knob_center_x"),
        measured("large_focus_knob_center_y"),
        measured("large_focus_knob_center_z"),
    )
    knob_neck = _cylinder_x(5.2, 12.0, (-3.0, knob_center[1], knob_center[2]))
    focus_knob = _styled_component(_large_focus_knob(knob_center) + knob_neck, "large focus knob")

    # Concealed receivers need room for the placed shafts. Their 0.05 mm radial
    # gap is a provisional assembly allowance, not a measured bearing fit.
    # Keep the blind axial seats and the independently scan-fitted screw/knob
    # axes; forcing them coaxial would change the supplied sleeve alignment.
    receivers = _cylinder_x(rod_radius + 0.05, 194.5, (103.25, rod_y_front, drive_z))
    receivers += _cylinder_x(rod_radius + 0.05, 194.5, (103.25, rod_y_back, drive_z))
    receivers += _cylinder_x(2.85 + 0.05, 204.0, (102.0, screw_y, drive_z))
    receivers += _cylinder_x(5.2 + 0.05, 12.0, (-3.0, knob_center[1], knob_center[2]))
    end_blocks = _styled_component(left_end + right_end - foot_clearance - receivers, "end blocks")

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
    sleeve = _styled_component(sleeve, "exact outer focus sleeve")

    # The observed end faces and carriage length center the nominal 140 mm
    # stroke at x=103.15. The captured scan is 0.35 mm beyond that midpoint.
    carriage_x = 33.15 + carriage_position_mm
    # The carriage is an open casting around the two guide bearings and lead-screw
    # nut. A pair of full boxes put large invented faces through the centre of the
    # scan. Two bearing housings, the nut boss, and a thin upper deck preserve the
    # visible envelope while leaving the real openings between them.
    # Horizontal scan sections place the outer housing sides at y=-2.45 and
    # 46.58 mm, with rounded skirts spanning approximately z=11..24 mm.
    front_bearing = _rounded_box(43.97, 14.0, 13.0, (carriage_x + 0.175, rod_y_front, 17.5), 2.3)
    rear_bearing = _rounded_box(43.97, 14.0, 13.0, (carriage_x + 0.175, rod_y_back, 17.5), 2.3)
    nut_block = _rounded_box(22.0, 12.5, 11.0, (carriage_x, screw_y, 15.5), 1.5)
    upper_deck = _rounded_box(40.0, 42.0, 4.0, (carriage_x, frame_y, 22.0), 1.6)
    # The exposed shafts continue through the carriage. The 0.15 mm radial
    # running gaps and the hidden rotary socket are provisional mechanical
    # allowances, not dimensions recovered from the outside-only scan.
    carriage_body = front_bearing + rear_bearing + nut_block + upper_deck
    # The exterior skirts sit beside the stationary rails. Their concealed
    # underside relief clears the measured 12.13 mm rail top by 0.17 mm.
    for rail_y in (4.065, 40.135):
        carriage_body -= Pos(carriage_x, rail_y, -1.0) * Box(
            48.0, 8.33, 13.30, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
    for rod_y in (rod_y_front, rod_y_back):
        carriage_body -= _cylinder_x(
            rod_radius + 0.15, 47.0, (carriage_x, rod_y, drive_z)
        )
    carriage_body -= _cylinder_x(3.0, 47.0, (carriage_x, screw_y, drive_z))
    carriage_body -= Pos(carriage_x, frame_y, 23.0) * Cylinder(
        6.15, 1.1, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    carriage = _styled_component(carriage_body, "sliding carriage")
    rotary_connector = _styled_component(
        Pos(carriage_x, frame_y, 23.0)
        * Cylinder(6.0, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "rotary connector",
    )

    rotary_base = _styled_component(
        Pos(carriage_x, frame_y, 28.0)
        * Cylinder(21.0, 6.0, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "rotary base",
    )

    top_rotation = float(arca_detent) * 90.0
    # In the scanned detent the upper clamp spans x=78.85..127.95 and
    # y=-2.55..51.70. Its dovetail opening is 37.9 mm at the jaw tips and 42.8 mm
    # at the seat. Flank slopes from horizontal are 63.95 degrees fixed and
    # 59.04 degrees movable; their fitted coordinate profiles are retained below.
    # All scan coordinates below were measured with the carriage at 70.35 mm travel.
    # Convert them once into that fixed local frame, then pose the complete top
    # assembly from the live carriage position. Subtracting the live carriage_x here
    # would cancel its later translation and leave the clamp behind as the carriage
    # moves.
    scan_carriage_x = 103.5
    clamp_x_min = 78.85 - scan_carriage_x
    clamp_x_max = 127.95 - scan_carriage_x
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
    # The scan's z=38 mm contours fit two 6.36 mm circular pocket ends.
    # Both pockets open at the clamp ends and share the observed 36.95 mm floor.
    pocket_y_center = 22.01 - frame_y
    pocket_radius = 6.36
    for arc_x, outer_x in ((90.50, 77.85), (116.31, 128.95)):
        arc_local_x = arc_x - scan_carriage_x
        outer_local_x = outer_x - scan_carriage_x
        pocket = Pos(arc_local_x, pocket_y_center, 36.95) * Cylinder(
            pocket_radius, 8.05, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        pocket += Pos(
            (arc_local_x + outer_local_x) / 2.0, pocket_y_center, 36.95
        ) * Box(
            abs(arc_local_x - outer_local_x), 2.0 * pocket_radius, 8.05,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        fixed_clamp_local -= pocket

    # These are shallow capsule recesses, not raised pads: section and ray
    # measurements place their floors below the approximately 39.95 mm deck.
    for y, sections in (
        (11.0, ((40.0, 4.2, 39.20), (42.35, 5.70, 39.50), (45.2, 9.0, 40.15))),
        (35.28, ((40.5, 6.5, 39.13), (42.75, 8.25, 39.50), (46.0, 11.0, 40.15))),
    ):
        recess = loft([
            Pos(103.45 - scan_carriage_x, y - frame_y, z)
            * SlotOverall(length, width)
            for length, width, z in sections
        ])
        fixed_clamp_local -= recess

    # Round only the outward corners, leaving both dovetail contact flanks sharp.
    outer_corners = fixed_clamp_local.edges().filter_by(lambda edge:
        abs(edge.bounding_box().min.Y - clamp_y_min) < 1e-6
        and abs(edge.bounding_box().max.Y - clamp_y_min) < 1e-6
        and edge.bounding_box().size.Z > 12.0
    )
    fixed_clamp_local = fillet(outer_corners, radius=1.1)
    outer_top = fixed_clamp_local.edges().filter_by(lambda edge:
        abs(edge.bounding_box().min.Y - clamp_y_min) < 1e-6
        and abs(edge.bounding_box().max.Y - clamp_y_min) < 1e-6
        and abs(edge.bounding_box().min.Z - 44.4) < 1e-6
    )
    fixed_clamp_local = fillet(outer_top, radius=0.55)
    fixed_clamp = Pos(carriage_x, frame_y, 0.0) * Rot(
        0, 0, top_rotation
    ) * fixed_clamp_local
    fixed_clamp = _styled_component(fixed_clamp, "fixed top Arca clamp")

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
    outer_corners = movable_jaw_local.edges().filter_by(lambda edge:
        abs(edge.bounding_box().min.Y - clamp_y_max) < 1e-6
        and abs(edge.bounding_box().max.Y - clamp_y_max) < 1e-6
        and edge.bounding_box().size.Z > 12.0
    )
    movable_jaw_local = fillet(outer_corners, radius=1.1)
    outer_top = movable_jaw_local.edges().filter_by(lambda edge:
        abs(edge.bounding_box().min.Y - clamp_y_max) < 1e-6
        and abs(edge.bounding_box().max.Y - clamp_y_max) < 1e-6
        and abs(edge.bounding_box().min.Z - 44.4) < 1e-6
    )
    movable_jaw_local = fillet(outer_top, radius=0.55)
    movable_jaw = Pos(carriage_x, frame_y, 0.0) * Rot(
        0, 0, top_rotation
    ) * movable_jaw_local
    movable_jaw = _styled_component(movable_jaw, "movable top Arca jaw")

    # The manual identifies this visible tab as the 90-degree positioning lock.
    # Its external envelope is fitted to the scan; no hidden latch is invented.
    lock_tab_local = _rounded_box(
        8.2, 3.55, 3.10,
        (103.55 - scan_carriage_x, -4.325 - frame_y, 35.35), 0.65,
    )
    lock_tab = _styled_component(
        Pos(carriage_x, frame_y, 0.0) * Rot(0, 0, top_rotation) * lock_tab_local,
        "90-degree positioning lock",
    )

    clamp_shaft_local = _cylinder_y(
        4.52,
        18.0,
        (103.30 - scan_carriage_x, 34.9, 35.5),
    )
    clamp_knob_local = _small_clamp_knob(
        (103.30 - scan_carriage_x, 69.8 - frame_y, 35.5)
    )
    clamp_knob = Pos(carriage_x, frame_y, 0.0) * Rot(0, 0, top_rotation) * (
        clamp_shaft_local + clamp_knob_local
    )
    clamp_knob = _styled_component(clamp_knob, "clamp knob")

    # This is a tight modeled CAD-to-CAD fit around the large focus knob. The
    # 0.05 mm lower bound protects the current 0.089 mm minimum gap from either
    # overlap or an accidental closing of the interface. It is not a claim about
    # manufactured clearance.
    if include_sleeve:
        clearance(
            focus_knob,
            sleeve,
            minimum=measured("outer_sleeve_cad_clearance_minimum"),
        )

    exterior_rows = [
        *exterior_hardware_components(knob_center),
        *exterior_marking_components(carriage_x, frame_y, rod_y_front),
    ]
    if camera_plate_installed:
        exterior_rows.extend(camera_plate_components(carriage_x, frame_y, top_rotation))
    exterior = tuple(component(solid, name, **appearance) for solid, name, appearance in exterior_rows)
    return (
        *folding_feet(feet_deployed, wrap=lambda solid, name: component(solid, name, **BLACK_METAL)),
        bottom_arca,
        end_blocks,
        front_rod,
        rear_rod,
        lead_screw,
        focus_knob,
        *((sleeve,) if include_sleeve else ()),
        carriage,
        rotary_connector,
        rotary_base,
        fixed_clamp,
        movable_jaw,
        lock_tab,
        clamp_knob,
        *exterior,
    )
