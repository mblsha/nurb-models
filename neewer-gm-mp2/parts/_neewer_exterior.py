"""Photo-supported exterior details; concealed dimensions remain provisional.

Helpers return (shape, label, appearance) rows for component(shape, label, **appearance).
The installed camera plate is optional because it is absent from the scan.
"""
from math import atan2, degrees, hypot, sqrt

from build123d import Align, Box, Compound, Cylinder, Helix, Plane, Polygon, Pos, RegularPolygon, Rot, SlotOverall, extrude, fillet, sweep

BLACK_METAL = {'color': '#3A3F46', 'metalness': 0.25, 'roughness': 0.50}
SILVER = {'color': '#C7CBD1', 'metalness': 0.45, 'roughness': 0.30}
RUBBER = {'color': '#17181B', 'metalness': 0.0, 'roughness': 0.92}
WHITE_INK = {'color': '#D9DADB', 'metalness': 0.0, 'roughness': 0.85}


def _rounded_block(length, width, height, center, radius):
    block = Pos(*center) * Box(length, width, height)
    return fillet(block.edges().filter_by(lambda e: e.bounding_box().size.Z > height - 1e-6), radius)


def camera_plate_components(carriage_x, frame_y, top_rotation):
    """Place the removable plate, pads and nominal quarter-inch camera stud."""
    pose = Pos(carriage_x, frame_y, 0) * Rot(0, 0, top_rotation)
    plate_center_y = 24.8 - frame_y
    # The male profile fits within the recorded clamp opening. The photo gives
    # proportions, not calibrated plate dimensions or a verified clamping fit.
    male_profile = Plane.YZ * Polygon(
        (3.70 - frame_y, 39.90), (45.90 - frame_y, 39.90),
        (43.25 - frame_y, 44.60), (5.85 - frame_y, 44.60), align=None,
    )
    plate = Pos(-34.0, 0, 0) * extrude(male_profile, 68.0)
    plate += _rounded_block(68.0, 44.0, 2.60, (0, plate_center_y, 45.80), 2.5)
    for x, length in ((-20.0, 16.0), (0.0, 8.0), (18.0, 20.0)):
        plate -= Pos(x, plate_center_y, 39.5) * extrude(SlotOverall(length, 6.70), 8.5)
    rows = [(pose * plate, 'removable camera plate', BLACK_METAL)]
    for column, x in enumerate((-22.0, 0.0, 22.0), 1):
        for row, y in enumerate((13.8, 35.8), 1):
            pad = Pos(x, y - frame_y, 47.10) * extrude(SlotOverall(18.0, 10.0), 0.90)
            rows.append((pose * pad, f'camera plate pad {column}-{row}', RUBBER))
    # The diameter is specified in the manual. The 20 TPI thread is a nominal
    # camera-mount standard representation, not a pitch measured from this scan.
    stud = Pos(18.0, plate_center_y, 44.60) * Cylinder(3.175, 3.05, align=(Align.CENTER, Align.CENTER, Align.MIN))
    stud += Pos(18.0, plate_center_y, 47.10) * Cylinder(4.35, 0.55, align=(Align.CENTER, Align.CENTER, Align.MIN))
    thread_profile = Plane.XZ * Polygon(
        (2.35, -0.45), (3.175, -0.08), (3.175, 0.08), (2.35, 0.45), align=None,
    )
    thread = sweep(thread_profile, path=Helix(1.27, 5.05, 2.35), is_frenet=True)
    threaded_tip = Cylinder(2.40, 5.95, align=(Align.CENTER, Align.CENTER, Align.MIN))
    threaded_tip += Pos(0, 0, 0.45) * thread
    stud += Pos(18.0, plate_center_y, 47.65) * threaded_tip
    rows.append((pose * stud, 'quarter-inch camera stud', SILVER))
    return tuple(rows)


def exterior_hardware_components(knob_center):
    """Return stationary hardware at the measured end-block seats."""
    rows = []
    for end, x in (('left', 5.6), ('right', 201.0)):
        for index, y in enumerate((12.1, 32.1), 1):
            head = Pos(x, y, 23.40) * Cylinder(3.30, 0.55, align=(Align.CENTER, Align.CENTER, Align.MIN))
            # The scan resolves the recessed drive, not its exact screw standard.
            drive = Pos(x, y, 23.52) * extrude(RegularPolygon(2.5 / sqrt(3), 6), 0.60)
            head -= drive
            rows.append((head, f'{end} end-block screw head {index}', SILVER))
    x, y, z = knob_center
    cap = Pos(x - 9.79, y, z) * Rot(0, 90, 0) * Cylinder(7.2, 0.08)
    rows.append((cap, 'focus knob dark end cap', RUBBER))
    return tuple(rows)


_SEGMENTS = {
    'a': ((0.0, 1.0), (0.6, 1.0)), 'b': ((0.6, 1.0), (0.6, 0.5)),
    'c': ((0.6, 0.5), (0.6, 0.0)), 'd': ((0.0, 0.0), (0.6, 0.0)),
    'e': ((0.0, 0.0), (0.0, 0.5)), 'f': ((0.0, 0.5), (0.0, 1.0)),
    'g': ((0.0, 0.5), (0.6, 0.5)),
}
_DIGITS = {'0': 'abcdef', '1': 'bc', '2': 'abdeg', '3': 'abcdg', '4': 'bcfg', '5': 'acdfg', '6': 'acdefg', '7': 'abc', '8': 'abcdefg', '9': 'abcdfg'}
_LETTERS = {
    'N': (((0, 0), (0, 1)), ((0, 1), (.6, 0)), ((.6, 0), (.6, 1))),
    'E': (((0, 0), (0, 1)), ((0, 1), (.6, 1)), ((0, .5), (.5, .5)), ((0, 0), (.6, 0))),
    'W': (((0, 1), (.12, 0)), ((.12, 0), (.3, .48)), ((.3, .48), (.48, 0)), ((.48, 0), (.6, 1))),
    'R': (((0, 0), (0, 1)), ((0, 1), (.5, 1)), ((.5, 1), (.6, .8)), ((.6, .8), (.5, .55)), ((.5, .55), (0, .55)), ((.3, .55), (.65, 0))),
}


def _stroke_xz(first, second, y, width):
    x1, z1 = first
    x2, z2 = second
    angle = -degrees(atan2(z2-z1, x2-x1))
    return Pos((x1+x2)/2, y, (z1+z2)/2) * Rot(0, angle, 0) * Box(hypot(x2-x1, z2-z1), 0.04, width)


def _lettering(text, center_x, bottom_z, height, y, width):
    advance = .85 * height
    start = center_x - (len(text)-1)*advance/2 - .3*height
    strokes = []
    for index, character in enumerate(text):
        lines = [_SEGMENTS[key] for key in _DIGITS[character]] if character in _DIGITS else _LETTERS[character]
        for first, second in lines:
            points = [(start + index*advance + x*height, bottom_z + z*height) for x, z in (first, second)]
            strokes.append(_stroke_xz(*points, y, width))
    return strokes


def exterior_marking_components(carriage_x, frame_y, rod_y_front):
    """Thin surface inlays convey the photographed scales and wordmark."""
    marks = []
    for value in range(-70, 71):
        length = 2.2 if value % 10 == 0 else 1.55 if value % 5 == 0 else 0.9
        marks.append(Pos(103.5 + value, 0.03, 10.70-length/2) * Box(0.12, 0.04, length))
    for value in range(-70, 71, 10):
        marks.extend(_lettering(str(abs(value)), 103.5+value, 6.35, 1.35, 0.03, 0.085))
    front_scale = Compound(children=marks)
    reverse = Pos(103.5, frame_y, 0) * Rot(0, 0, 180) * Pos(-103.5, -frame_y, 0)
    lettering = Compound(children=_lettering('NEEWER', carriage_x+.175, 16.3, 3.4, rod_y_front-7.02, .32))
    return (
        (front_scale, 'front rail scale', WHITE_INK),
        (reverse * front_scale, 'rear rail scale', WHITE_INK),
        (lettering, 'carriage wordmark', WHITE_INK),
    )
