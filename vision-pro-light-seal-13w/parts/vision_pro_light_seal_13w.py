"""A plain smooth shell, constrained by the two Light Seal 13W mating rims."""

from math import hypot

from nurb import *
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections


# Sparse paired landmarks in the reference's millimetre datum. These describe
# the hard shell only; the black cloth and fine internal structure are excluded.
# Temple rim centers are inset from the observed exterior edge by the lip halfwidth.
HEADSET_RIM = (
    (0.0, -48.0, 14.25),
    (30.0, -46.1, 8.4),
    (55.0, -38.4, -8.5),
    (69.75, -23.0, -23.0),
    (76.75, -9.0, -30.0),
    (77.625, 8.0, -30.0),
    (71.5, 22.0, -24.0),
    (57.0, 31.0, -11.0),
    (38.0, 34.5, 1.2),
    (25.0, 33.0, 5.5),
    (12.0, 25.0, 7.3),
    (0.0, 20.0, 8.7),
    (-12.0, 25.7, 8.0),
    (-25.0, 33.7, 5.4),
    (-38.0, 35.2, 1.2),
    (-57.0, 32.2, -11.0),
    (-71.5, 23.0, -23.0),
    (-78.5, 9.0, -28.8),
    (-77.625, -8.0, -28.5),
    (-69.75, -23.0, -21.5),
    (-55.0, -37.4, -6.5),
    (-30.0, -45.5, 8.9),
)
CUSHION_RIM = (
    (0.0, -35.3, 45.2),
    (30.0, -34.2, 40.1),
    (55.0, -28.0, 28.0),
    (70.0, -10.7, 17.9),
    (72.8, -3.0, 16.0),
    (72.8, 9.0, 16.0),
    (70.0, 17.5, 17.9),
    (55.0, 37.0, 26.0),
    (38.0, 41.0, 36.5),
    (25.0, 36.3, 44.5),
    (12.0, 27.5, 50.8),
    (0.0, 23.8, 53.7),
    (-12.0, 28.0, 50.7),
    (-25.0, 37.0, 44.0),
    (-38.0, 41.8, 36.5),
    (-55.0, 38.0, 26.0),
    (-70.0, 18.1, 18.1),
    (-73.0, 10.0, 16.3),
    (-73.0, -3.0, 16.5),
    (-70.0, -10.4, 18.1),
    (-55.0, -27.0, 28.8),
    (-30.0, -33.8, 40.4),
)


MID_EXTERIOR = (
    (0.0, -42.0, 29.0),
    (30.0, -40.8, 23.0),
    (55.0, -32.0, 9.0),
    (70.0, -19.0, 0.0),
    (73.8, -6.0, -7.0),
    (73.0, 12.0, -7.0),
    (69.0, 28.0, -3.0),
    (55.0, 42.0, 8.0),
    (38.0, 45.0, 18.0),
    (25.0, 41.0, 29.0),
    (12.0, 32.0, 35.0),
    (0.0, 26.7, 35.4),
    (-12.0, 33.0, 35.0),
    (-25.0, 42.0, 29.0),
    (-38.0, 45.5, 18.0),
    (-55.0, 43.0, 8.0),
    (-69.0, 29.0, -2.0),
    (-75.8, 13.0, -7.0),
    (-76.0, -5.0, -7.0),
    (-70.0, -18.0, 0.0),
    (-55.0, -31.0, 10.0),
    (-30.0, -40.5, 23.5),
)

def _periodic_parameters(first, second):
    # Corresponding landmarks share a parameter, avoiding loft seam rotation.
    average = [tuple((a + b) / 2 for a, b in zip(p, q)) for p, q in zip(first, second)]
    values = [0.0]
    for p, q in zip(average, average[1:] + average[:1]):
        values.append(values[-1] + sum((a - b) ** 2 for a, b in zip(p, q)) ** 0.5)
    return [value / values[-1] for value in values]


def _inset(points, amount):
    result = []
    for i, (x, y, z) in enumerate(points):
        previous, following = points[i - 1], points[(i + 1) % len(points)]
        dx, dy = following[0] - previous[0], following[1] - previous[1]
        length = hypot(dx, dy)
        # The landmarks run counterclockwise in XY, so the left normal is inward.
        result.append((x - amount * dy / length, y + amount * dx / length, z))
    return result


def _inner_wall(points, first, last, thickness):
    inside = []
    for i, p in enumerate(points):
        previous, following = points[i - 1], points[(i + 1) % len(points)]
        tangent = Vector(*(b - a for a, b in zip(previous, following)))
        depth = Vector(*(b - a for a, b in zip(first[i], last[i])))
        outward = tangent.cross(depth).normalized()
        inside.append(tuple(Vector(p) - outward * thickness))
    return inside


def _curve(points, parameters):
    return Wire([Edge.make_spline(list(points), periodic=True, parameters=parameters)])


def _skin(wires, ruled=False):
    loft = BRepOffsetAPI_ThruSections(False, ruled, 1e-6)
    loft.CheckCompatibility(False)
    for wire in wires:
        loft.AddWire(wire.wrapped)
    loft.Build()
    if not loft.IsDone():
        raise ValueError("The smooth shell loft could not be built.")
    return Shell(loft.Shape()).faces()


@part
def vision_pro_light_seal_13w(wall_mm=1.8, headset_fit_offset_mm=0.0, cushion_fit_offset_mm=0.0):
    """Smooth external shell with an open nose passage and no internal details."""
    if not 1.0 <= wall_mm <= 3.0:
        reject("Choose a nominal wall between 1.0 and 3.0 mm.", "wall_mm")
    if abs(headset_fit_offset_mm) > 1.0:
        reject("Keep the headset fit offset between -1.0 and 1.0 mm.", "headset_fit_offset_mm")
    if abs(cushion_fit_offset_mm) > 1.0:
        reject("Keep the cushion fit offset between -1.0 and 1.0 mm.", "cushion_fit_offset_mm")

    headset = _inset(HEADSET_RIM, -headset_fit_offset_mm)
    cushion = _inset(CUSHION_RIM, -cushion_fit_offset_mm)
    parameters = _periodic_parameters(headset, cushion)
    middle = _inset(MID_EXTERIOR, -(headset_fit_offset_mm + cushion_fit_offset_mm) / 2)
    # The scan's rail tips locate the middle of a roughly 3.2 mm-wide lip.
    outside = [_inner_wall(headset, headset, middle, -1.6), middle, _inner_wall(cushion, middle, cushion, -1.6)]
    inside = [_inner_wall(headset, headset, middle, 1.6), _inner_wall(middle, outside[0], outside[-1], wall_mm), _inner_wall(cushion, middle, cushion, 1.6)]
    outer_wires = [_curve(points, parameters) for points in outside]
    inner_wires = [_curve(points, parameters) for points in inside]

    # Four sewn surfaces form one solid. End faces follow the spatial mating
    # curves; neither interface is incorrectly flattened into a planar cap.
    faces = [
        *_skin(outer_wires),
        *_skin(inner_wires),
        *_skin([outer_wires[0], inner_wires[0]], ruled=True),
        *_skin([outer_wires[-1], inner_wires[-1]], ruled=True),
    ]
    body = Solid(Shell(faces))
    if not body.is_valid or body.volume <= 0:
        raise ValueError("The smooth shell is not a closed positive-volume solid.")
    return body
