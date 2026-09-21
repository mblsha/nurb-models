"""A plain smooth shell, constrained by the two Light Seal 13W mating rims."""

from math import hypot

import numpy as np
from scipy.interpolate import make_interp_spline

from nurb import *
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.Geom import Geom_BSplineCurve
from OCP.gp import gp_Pnt
from OCP.TColgp import TColgp_Array1OfPnt
from OCP.TColStd import TColStd_Array1OfInteger, TColStd_Array1OfReal


def _mirrored_loop(half):
    return tuple(half) + tuple((-x, y, z) for x, y, z in half[-2:0:-1])


# Sparse paired landmarks in the symmetric millimetre datum. These describe
# the hard shell only; the black cloth and fine internal structure are excluded.
# Temple rim centers are inset from the observed exterior edge by the lip halfwidth.
HEADSET_RIM_HALF = (
    (0.0, -47.99413, 14.251911),
    (30.001784, -45.794181, 8.651895),
    (55.005349, -37.894539, -7.498222),
    (69.743575, -22.995906, -22.248667),
    (77.188188, -8.504759, -29.251549),
    (78.062254, 8.492947, -29.402297),
    (71.5002, 22.49799, -23.500654),
    (57.001338, 31.596207, -11.001235),
    (38.000069, 34.84523, 1.198447),
    (25.001748, 33.345245, 5.448452),
    (12.005837, 25.346231, 7.648773),
    (0.0, 19.996909, 8.698994),
)
HEADSET_RIM = _mirrored_loop(HEADSET_RIM_HALF)
CUSHION_RIM_HALF = (
    (0.0, -35.297214, 45.200907),
    (29.999603, -33.997172, 40.250921),
    (55.002135, -27.497529, 28.400805),
    (69.992523, -10.549365, 18.000207),
    (72.890425, -3.001955, 16.249363),
    (72.898116, 9.496357, 16.148814),
    (69.994991, 17.796797, 17.998957),
    (54.999992, 37.493778, 25.997974),
    (38.000892, 41.392787, 36.497651),
    (25.000676, 36.643088, 44.24775),
    (12.002049, 27.744007, 50.748049),
    (0.0, 23.794411, 53.69818),
)
CUSHION_RIM = _mirrored_loop(CUSHION_RIM_HALF)


MID_EXTERIOR_HALF = (
    (0.0, -41.995593, 29.001435),
    (29.999316, -40.645522, 23.251458),
    (55.002671, -31.496155, 9.501252),
    (69.997746, -18.497496, 0.000815),
    (74.897013, -5.517046, -7.00555),
    (74.397088, 12.475582, -7.007951),
    (69.000575, 28.496252, -2.50122),
    (54.999992, 42.493894, 7.998012),
    (37.998424, 45.243081, 17.997747),
    (25.004484, 41.493104, 28.997755),
    (12.00643, 32.494058, 34.998065),
    (0.0, 26.694825, 35.398315),
)
MID_EXTERIOR = _mirrored_loop(MID_EXTERIOR_HALF)

# Measured headset seating frames: origin, across-seat direction, normal toward
# cushion, and the limits of the flat contact run. Last three stations are a
# conservative narrow hard-nose strip because the cloth obscures that region.
HEADSET_SEATS_HALF = (
    ((-0.0, -47.629057, 13.145643), (-0.0, 0.949627, 0.313382), (0.0, -0.313382, 0.949627), (1.432759, 18.601981)),
    ((29.544386, -45.472218, 7.695971), (-0.02355, 0.943965, 0.329204), (0.412982, -0.290699, 0.863099), (0.527694, 18.128717)),
    ((54.72418, -37.818349, -7.769898), (-0.141285, 0.905489, 0.400161), (0.705865, -0.191272, 0.682034), (-0.046514, 16.22166)),
    ((69.651994, -22.985201, -22.323533), (-0.423154, 0.66718, 0.613035), (0.771073, -0.090134, 0.630336), (-1.590927, 14.095195)),
    ((76.780494, -8.475152, -29.633234), (-0.606445, 0.412482, 0.679767), (0.728986, -0.052939, 0.682479), (-0.243271, 15.008123)),
    ((77.549098, 8.490942, -29.915289), (-0.663659, -0.342135, 0.665207), (0.707217, 0.002763, 0.706991), (-0.868892, 14.148557)),
    ((71.599154, 22.492793, -23.381087), (-0.577507, -0.682292, 0.44829), (0.637216, -0.033464, 0.769959), (-5.922275, 8.564488)),
    ((56.813272, 31.664993, -11.261715), (-0.274323, -0.960037, -0.055458), (0.5724, -0.209356, 0.792798), (-12.887429, 0.946798)),
    ((37.724909, 35.101596, 0.567844), (-0.19124, -0.935563, -0.296899), (0.374759, -0.349163, 0.85886), (-12.013876, 0.93733)),
    ((24.773333, 33.54113, 4.816427), (0.23829, -0.899976, -0.36505), (0.326307, -0.279836, 0.902893), (-6.0, 1.5)),
    ((11.895204, 25.3854, 6.958682), (0.454908, -0.882004, -0.122992), (0.158047, -0.055956, 0.985845), (-2.5, 2.5)),
    ((0.0, 19.826582, 8.020033), (0.0, -0.969945, 0.243325), (0.0, 0.243325, 0.969945), (-2.0, 2.0)),
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
    # OCCT's automatic periodic interpolation chooses an asymmetric seam tangent.
    # Solve the unique periodic cubic explicitly so mirrored data produces C2
    # curves with exact bilateral symmetry, including the closure.
    spline = make_interp_spline(parameters, np.array([*points, points[0]]), k=3, bc_type="periodic")
    values, counts = np.unique(spline.t, return_counts=True)
    poles = TColgp_Array1OfPnt(1, len(spline.c))
    knots = TColStd_Array1OfReal(1, len(values))
    multiplicities = TColStd_Array1OfInteger(1, len(values))
    for i, point in enumerate(spline.c, 1):
        poles.SetValue(i, gp_Pnt(*point))
    for i, (value, count) in enumerate(zip(values, counts), 1):
        knots.SetValue(i, float(value))
        multiplicities.SetValue(i, int(count))
    curve = Geom_BSplineCurve(poles, knots, multiplicities, 3, False)
    curve.SetPeriodic()
    return Wire([Edge(BRepBuilderAPI_MakeEdge(curve, 0.0, 1.0).Edge())])


def _skin(wires, ruled=False):
    loft = BRepOffsetAPI_ThruSections(False, ruled, 1e-6)
    loft.CheckCompatibility(False)
    loft.SetMaxDegree(3)
    for wire in wires:
        loft.AddWire(wire.wrapped)
    loft.Build()
    if not loft.IsDone():
        raise ValueError("The smooth shell loft could not be built.")
    return Shell(loft.Shape()).faces()


# Paired scan return contours in the seating frame, from the outer stem down
# around the rounded foot and back to the inner stem. Seven regularized anchors
# describe each side; the contact spans remain the measured flat seating faces.
HEADSET_RETURNS_HALF = (
    (((5.5196, 8.0), (4.0611, 6.6404), (2.5984, 5.2989), (1.0241, 4.0857), (-0.3627, 2.6756), (0.0814, 0.8773), (1.4328, 0.0)), ((18.602, 0.0), (17.7053, 2.4144), (14.4294, 3.4875), (11.0192, 3.9879), (7.7364, 4.8715), (5.5225, 5.5653), (7.9641, 8.0))),
    (((5.3428, 8.0), (3.9926, 6.686), (2.5991, 5.4136), (1.1699, 4.1835), (-0.223, 2.9098), (-0.6772, 1.2132), (0.5277, 0.0)), ((18.1287, 0.0), (17.6238, 1.9873), (15.3633, 3.014), (12.9589, 3.712), (12.8885, 5.3446), (14.8192, 6.9225), (16.9113, 8.0))),
    (((9.0476, 8.0), (6.8726, 6.7643), (4.6871, 5.5583), (2.444, 4.4628), (0.178, 3.4046), (-1.4292, 1.6182), (-0.0465, 0.0)), ((16.2217, 0.0), (16.804, 1.0946), (17.4252, 2.3643), (17.6766, 3.7561), (17.706, 5.1677), (17.6342, 6.5814), (17.674, 8.0))),
    (((11.5356, 8.0), (8.8341, 6.8477), (6.0745, 5.8448), (3.2747, 4.9569), (0.4938, 4.0401), (-1.9212, 2.4122), (-1.5909, 0.0)), ((14.0952, 0.0), (14.5591, 1.6157), (14.0549, 3.4827), (12.9507, 5.0446), (14.1039, 6.195), (15.9147, 7.0769), (17.7056, 8.0))),
    (((11.571, 8.0), (9.0711, 6.8991), (6.549, 5.8479), (3.989, 4.8923), (1.4383, 3.9138), (-0.7269, 2.2945), (-0.2433, 0.0)), ((15.0081, 0.0), (15.2629, 1.7175), (14.99, 3.4884), (13.9626, 4.941), (14.3763, 6.2221), (16.0002, 7.1104), (17.6221, 8.0))),
    (((9.5226, 8.0), (7.0792, 6.8941), (4.6335, 5.7983), (2.1674, 4.7282), (-0.2721, 3.6121), (-2.1774, 1.84), (-0.8689, 0.0)), ((14.1486, 0.0), (14.5161, 1.5902), (14.2256, 3.2472), (13.3563, 4.8822), (12.5547, 6.0889), (14.0408, 7.005), (15.6436, 8.0))),
    (((2.9215, 8.0), (0.9658, 6.7899), (-1.0192, 5.6393), (-3.0323, 4.5423), (-5.0662, 3.4673), (-6.6474, 1.8914), (-5.9223, 0.0)), ((8.5645, 0.0), (9.4738, 1.0943), (10.4636, 2.392), (10.6475, 3.9732), (10.176, 5.4706), (9.2501, 6.7808), (8.6711, 8.0))),
    (((-8.3266, 8.0), (-9.2698, 6.6782), (-10.1895, 5.3341), (-11.1051, 3.9876), (-12.055, 2.6681), (-12.7949, 1.2526), (-12.8874, 0.0)), ((0.9468, 0.0), (0.8789, 1.743), (-0.552, 2.9479), (-1.9775, 4.012), (-1.2967, 5.5186), (0.2016, 6.7632), (1.7066, 8.0))),
    (((-14.106, 8.0), (-13.8236, 6.5968), (-13.5422, 5.1944), (-13.2285, 3.7963), (-12.9316, 2.3958), (-12.4254, 1.0727), (-12.0139, 0.0)), ((0.9373, 0.0), (0.6594, 2.1116), (-1.1772, 3.2129), (-3.3215, 3.7132), (-5.1222, 4.466), (-3.797, 5.9556), (-3.1246, 8.0))),
    (((-3.4021, 4.175), (-2.4466, 3.0363), (-2.3541, 2.3), (-3.8406, 2.3), (-5.327, 2.3), (-6.0, 1.4865), (-6.0, -0.0)), ((1.5, 0.0), (1.5, 0.8794), (1.5, 1.7588), (1.1618, 2.3), (0.5285, 2.8277), (-0.0368, 3.5013), (-0.6021, 4.175))),
    (((-1.5832, 3.25), (-1.3152, 2.5136), (-1.3653, 2.0), (-2.149, 2.0), (-2.5, 1.5673), (-2.5, 0.7837), (-2.5, 0.0)), ((2.5, -0.0), (2.5, 0.6931), (2.5, 1.3862), (2.4208, 2.0), (1.7277, 2.0), (1.4538, 2.5987), (1.2168, 3.25))),
    (((-0.7, 2.88), (-1.0212, 2.3446), (-1.3825, 1.88), (-2.0, 1.8731), (-2.0, 1.2487), (-2.0, 0.6244), (-2.0, -0.0)), ((2.0, -0.0), (2.0, 0.591), (2.0, 1.1821), (2.0, 1.7731), (1.5159, 1.88), (1.7959, 2.3732), (2.1, 2.88))),
)


def _headset_profile(headset):
    outer_bands = [[] for _ in range(7)]
    inner_bands = [[] for _ in range(7)]
    for i, ((origin, across, normal, span), returns) in enumerate(zip(HEADSET_SEATS_HALF, HEADSET_RETURNS_HALF)):
        origin, across, normal = Vector(origin), Vector(across), Vector(normal)
        origin += Vector(headset[i]) - Vector(HEADSET_RIM[i])
        for bands, points in zip((outer_bands, inner_bands), returns):
            for band, (q, depth) in zip(bands, points):
                point = origin + across * q + normal * depth
                band.append((0.0 if i in (0, 11) else point.X, point.Y, point.Z))
    return {"outer": [_mirrored_loop(half) for half in outer_bands], "inner": [_mirrored_loop(half) for half in inner_bands]}


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
    profile = _headset_profile(headset)
    cushion_outer = _inner_wall(cushion, middle, cushion, -1.6)
    cushion_inner = _inner_wall(cushion, middle, cushion, 1.6)
    outside = [profile["outer"][0], middle, cushion_outer]
    inside = [profile["inner"][-1], _inner_wall(middle, outside[0], outside[-1], wall_mm), cushion_inner]
    outer_wires = [_curve(points, parameters) for points in outside]
    inner_wires = [_curve(points, parameters) for points in inside]
    outer_return = [_curve(points, parameters) for points in profile["outer"]]
    inner_return = [_curve(points, parameters) for points in profile["inner"]]
    faces = [*_skin(outer_wires), *_skin(inner_wires), *_skin(outer_return), *_skin(inner_return)]
    faces.extend(_skin([outer_return[-1], inner_return[0]], ruled=True))
    faces.extend(_skin([outer_wires[-1], inner_wires[-1]], ruled=True))
    body = Solid(Shell(faces))
    if not body.is_valid or body.volume <= 0:
        raise ValueError("The smooth shell is not a closed positive-volume solid.")
    return body
