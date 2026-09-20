from nurb import *


def _at(sketch, x=0.0, y=0.0, z=0.0):
    return sketch.moved(Location((x, y, z)))


def _rounded_profile(width, height, radius, x, y, z):
    return _at(
        RectangleRounded(width, height, radius, align=(Align.MIN, Align.MIN)),
        x,
        y,
        z,
    )


def _pocket_profile(z, lower_y, upper_y, pocket_tip_x, diagonal_x):
    tip_slope = (diagonal_x - pocket_tip_x) / 19.7
    lower_x = pocket_tip_x + (lower_y - 3.0) * tip_slope
    upper_x = pocket_tip_x + (upper_y - 3.0) * tip_slope
    return _at(
        Polygon(
            (-2.0, lower_y),
            (lower_x, lower_y),
            (upper_x, upper_y),
            (-2.0, upper_y),
            align=(Align.NONE, Align.NONE),
        ),
        z=z,
    )


def _through_hole():
    upper_left_top = (55.206518, 25.5)
    upper_right_top = (67.0, 25.5)
    upper_right_side = (69.0, 23.5)
    lower_right_side = (69.0, 7.891679)
    lower_right_diagonal = (66.3076, 6.9817)
    upper_left_diagonal = (54.0141, 23.09)

    with BuildSketch() as hole:
        with BuildLine():
            Line(upper_left_top, upper_right_top)
            RadiusArc(upper_right_top, upper_right_side, 2.0)
            Line(upper_right_side, lower_right_side)
            RadiusArc(lower_right_side, lower_right_diagonal, 1.5)
            Line(lower_right_diagonal, upper_left_diagonal)
            RadiusArc(upper_left_diagonal, upper_left_top, 1.5)
        make_face()
    return extrude(hole.sketch, amount=7.5).moved(Location((0.0, 0.0, -1.0)))


def _tongue_profile(nose_radius, back_radius):
    left_x = 13.0 - nose_radius
    right_x = 13.0 + nose_radius
    left_center = (left_x + back_radius, 24.5)
    right_center = (right_x - back_radius, 24.5)
    return Face(
        Wire(
            [
                Line((left_x, 24.5), (left_x, 20.375)).edge(),
                CenterArc((13.0, 20.375), nose_radius, 180.0, 180.0).edge(),
                Line((right_x, 20.375), (right_x, 24.5)).edge(),
                CenterArc(right_center, back_radius, 0.0, 90.0).edge(),
                Line(
                    (right_center[0], 24.5 + back_radius),
                    (left_center[0], 24.5 + back_radius),
                ).edge(),
                CenterArc(left_center, back_radius, 90.0, 90.0).edge(),
            ]
        )
    )


def _spring_slot_face(spring_gap, spring_slot_height, expansion=0.0, z=0.0):
    half_width = spring_gap / 2.0 + expansion
    corner_radius = 1.25
    nose_radius = 1.875
    if not 0.0 < half_width < corner_radius:
        raise ValueError(
            "spring_gap plus its bottom bevel must leave room for the 1.25 mm root radius"
        )
    inside_corner = corner_radius - half_width
    outside_corner = corner_radius + half_width
    outer_nose = nose_radius + half_width
    inner_nose = nose_radius - half_width
    low_y = 25.75 - half_width
    high_y = 25.75 + half_width
    long_low_y = 25.5 - expansion
    nominal_long_high_y = 25.5 + spring_slot_height
    long_high_y = nominal_long_high_y + expansion
    end_center_x = 39.375
    nominal_end_radius = spring_slot_height / 2.0
    end_radius = nominal_end_radius + expansion
    end_center_y = 25.5 + nominal_end_radius
    raised_root_center_y = nominal_long_high_y - (1.25 + spring_gap / 2.0)
    root_left_x = 16.125 - outside_corner

    def line(a, b):
        return Line(a, b).edge()

    def arc(center, radius, angle, sweep):
        return CenterArc(center, radius, angle, sweep).edge()

    end_arc = arc((end_center_x, end_center_y), end_radius, -90.0, 180.0)
    lower_transition = []
    if abs(low_y - long_low_y) > 1e-9:
        lower_transition.append(line((16.125, low_y), (16.125, long_low_y)))
    raised_root = [
        arc(
            (16.125, raised_root_center_y),
            outside_corner,
            90.0,
            90.0,
        )
    ]
    if abs(raised_root_center_y - 24.5) > 1e-9:
        raised_root.append(
            line((root_left_x, raised_root_center_y), (root_left_x, 24.5))
        )

    outline = Wire(
        [
            line((-2.0, low_y), (9.875, low_y)),
            arc((9.875, 24.5), inside_corner, 90.0, -90.0),
            line((13.0 - outer_nose, 24.5), (13.0 - outer_nose, 20.375)),
            arc((13.0, 20.375), outer_nose, 180.0, 180.0),
            line((13.0 + outer_nose, 20.375), (13.0 + outer_nose, 24.5)),
            arc((16.125, 24.5), inside_corner, 180.0, -90.0),
            *lower_transition,
            line((16.125, long_low_y), (end_center_x, long_low_y)),
            end_arc,
            line((end_center_x, long_high_y), (16.125, long_high_y)),
            *raised_root,
            line((13.0 + inner_nose, 24.5), (13.0 + inner_nose, 20.375)),
            arc((13.0, 20.375), inner_nose, 0.0, -180.0),
            line((13.0 - inner_nose, 20.375), (13.0 - inner_nose, 24.5)),
            arc((9.875, 24.5), outside_corner, 0.0, 90.0),
            line((9.875, high_y), (-2.0, high_y)),
            line((-2.0, high_y), (-2.0, low_y)),
        ]
    )
    return _at(Face(outline), z=z)


def _spring_slot_cutter(spring_gap, spring_slot_height, bottom_bevel, height):
    if bottom_bevel < 0.0:
        raise ValueError("bottom_bevel cannot be negative")
    bottom = _spring_slot_face(spring_gap, spring_slot_height, bottom_bevel)
    nominal = _spring_slot_face(spring_gap, spring_slot_height, z=bottom_bevel)
    through = extrude(nominal, amount=height + 1.0 - bottom_bevel)
    if bottom_bevel:
        through += loft([bottom, nominal], ruled=True)
    through += extrude(bottom, amount=-1.0)
    return through.clean()


def _spring_tongue_island(spring_gap, z=0.0):
    half_width = spring_gap / 2.0
    root_radius = 1.25 + half_width
    nose_radius = 1.875 - half_width
    high_y = 25.75 + half_width
    outline = Wire(
        [
            CenterArc((9.875, 24.5), root_radius, 90.0, -90.0).edge(),
            Line(
                (13.0 - nose_radius, 24.5),
                (13.0 - nose_radius, 20.375),
            ).edge(),
            CenterArc((13.0, 20.375), nose_radius, 180.0, 180.0).edge(),
            Line(
                (13.0 + nose_radius, 20.375),
                (13.0 + nose_radius, 24.5),
            ).edge(),
            CenterArc((16.125, 24.5), root_radius, 180.0, -90.0).edge(),
            Line((16.125, high_y), (9.875, high_y)).edge(),
        ]
    )
    return _at(Face(outline), z=z)


def _thumb_relief():
    center_x = 22.3125
    at_26_left = [
        (5.0, 5.363636),
        (5.210072, 4.936621),
        (5.597704, 4.472075),
        (6.110535, 4.090477),
        (6.529406, 3.914455),
        (6.889215, 3.829354),
        (7.260293, 3.8),
    ]
    at_31_left = [
        (5.0, 4.0),
        (5.298329, 3.915019),
        (5.611554, 3.84953),
        (5.858717, 3.811298),
        (6.120302, 3.8),
    ]

    def section(points, y):
        right = [(2.0 * center_x - x, z) for x, z in reversed(points)]
        outline = [(x, y, z) for x, z in points + right]
        outline.extend([(39.625, y, 7.0), (5.0, y, 7.0)])
        return Wire.make_polygon(outline)

    return Solid.make_loft(
        [section(at_26_left, 26.0), section(at_31_left, 31.0)],
        ruled=True,
    )


@part
def utility_blade_holder(
    body_length=74.0,
    body_width=31.0,
    thickness=5.5,
    outer_radius=5.0,
    blade_floor=3.0,
    pocket_tip_x=64.0,
    pocket_diagonal_x=48.965435,
    spring_gap=0.5,
    spring_slot_height=2.0,
    draft=False,
):
    if not 0.0 < spring_gap < 0.75:
        raise ValueError(
            "spring_gap must be greater than 0 and less than 0.75 mm so the paired-radius tongue cap remains connected"
        )
    if not 0.5 <= spring_slot_height <= 2.8:
        raise ValueError(
            "spring_slot_height must be between 0.5 and 2.8 mm so the bottom bevel leaves a printable outer rail"
        )
    minimum_slot_height = 0.25 + spring_gap / 2.0
    if spring_slot_height < minimum_slot_height - 1e-9:
        raise ValueError(
            f"spring_slot_height must be at least {minimum_slot_height:.2f} mm with spring_gap={spring_gap:.2f} mm so the raised root fillet stays above the tongue endpoint"
        )
    tongue_width = 3.75 - spring_gap
    tongue_radius = tongue_width / 2.0
    bottom = loft(
        [
            _rounded_profile(
                body_length - 2.0,
                body_width - 2.0,
                outer_radius - 1.0,
                1.0,
                1.0,
                0.0,
            ),
            _rounded_profile(body_length, body_width, outer_radius, 0.0, 0.0, 1.0),
        ],
        ruled=True,
    )
    middle_profile = _rounded_profile(
        body_length, body_width, outer_radius, 0.0, 0.0, 1.0
    )
    middle = extrude(middle_profile, amount=3.0)
    top = loft(
        [
            _rounded_profile(body_length, body_width, outer_radius, 0.0, 0.0, 4.0),
            _rounded_profile(
                body_length - 3.0,
                body_width - 7.0,
                outer_radius - 1.5,
                1.5,
                1.5,
                thickness,
            ),
        ],
        ruled=True,
    )
    body = bottom + middle + top

    # The blade opening interrupts the upper bevel. The left rail and rear wing
    # retain the full X=0 wall where the source's channel opens to the side.
    outer_upper = extrude(
        _rounded_profile(body_length, body_width, outer_radius, 0.0, 0.0, 4.0),
        amount=thickness - 4.0,
    )
    left_rear = _at(
        Box(
            outer_radius,
            body_width - (22.7 - thickness),
            thickness - 4.0,
            align=(Align.MIN, Align.MIN, Align.MIN),
        ),
        0.0,
        22.7 - thickness,
        4.0,
    )
    roof = Plane.YZ * Polygon(
        (0.0, 4.0),
        (body_width, 4.0),
        (body_width - 5.5, thickness),
        (0.0, thickness),
        align=None,
    )
    body += outer_upper & left_rear & extrude(roof, amount=outer_radius)

    pocket_sections = [
        _pocket_profile(blade_floor, 3.0, 22.7, pocket_tip_x, pocket_diagonal_x),
        _pocket_profile(3.6, 3.6, 22.7, pocket_tip_x, pocket_diagonal_x),
        _pocket_profile(4.8172, 4.8172, 21.4828, pocket_tip_x, pocket_diagonal_x),
        _pocket_profile(thickness + 0.2, 4.9172, 21.3828, pocket_tip_x, pocket_diagonal_x),
    ]
    pocket = loft(pocket_sections, ruled=False)
    body = body - pocket - _through_hole()
    spring_slot = _spring_slot_cutter(
        spring_gap, spring_slot_height, 0.4, thickness
    )
    body = body - spring_slot - _thumb_relief()

    if blade_floor >= 3.8:
        raise ValueError("blade_floor must stay below the tongue shoulder at 3.8 mm")
    tongue_island = _spring_tongue_island(spring_gap)
    body -= extrude(_at(tongue_island, z=3.8), amount=thickness - 3.8 + 1.0)
    tongue_lower = extrude(
        _at(tongue_island, z=blade_floor),
        amount=3.8 - blade_floor,
    )
    full_tongue = _tongue_profile(tongue_radius, 1.5)
    tongue_cap = extrude(_at(full_tongue, z=3.8), amount=0.8)
    inset = 0.4
    narrow_tongue = _tongue_profile(tongue_radius - inset, 1.1)
    tongue_top = loft(
        [_at(full_tongue, z=4.6), _at(narrow_tongue, z=5.0)],
        ruled=True,
    )
    body = body + tongue_lower + tongue_cap + tongue_top

    # The selected grip keeps a flat outer lip with one straight inward bevel.
    tip_region = Pos(0.0, 26.0, 3.8) * Box(
        9.0, 5.0, thickness - 3.8 + 1.0, align=(Align.MIN, Align.MIN, Align.MIN)
    )
    body -= tip_region
    hook_profile = Plane.YZ * Polygon(
        (26.0, 3.75),
        (31.0, 3.75),
        (31.0, 5.5),
        (28.0, 5.5),
        (26.0, 4.0),
        align=None,
    )
    hook = extrude(hook_profile, amount=9.0)
    tip_outline = extrude(
        _rounded_profile(body_length, body_width, outer_radius, 0.0, 0.0, 0.0),
        amount=thickness,
    )
    hook = (hook & tip_outline) - spring_slot
    body += hook
    # Tongue material is restored after the first slot cut. Re-cut the finished body so
    # a raised root fillet cannot be refilled below the tongue's shoulder.
    body -= spring_slot

    if draft:
        return body
    return body
