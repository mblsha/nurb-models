"""A plain smooth shell, constrained by the two Light Seal 13W mating rims."""

from math import hypot

import numpy as np
from scipy.interpolate import make_interp_spline, PchipInterpolator

from nurb import *
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Geom import Geom_BSplineCurve, Geom_BSplineSurface
from OCP.gp import gp_Pnt
from OCP.TColgp import TColgp_Array1OfPnt, TColgp_Array2OfPnt
from OCP.TColStd import TColStd_Array1OfInteger, TColStd_Array1OfReal


def _mirrored_loop(half):
    return tuple(half) + tuple((-x, y, z) for x, y, z in half[-2:0:-1])


# Sparse paired landmarks in the symmetric millimetre datum. These describe
# the hard shell only; the black cloth and fine internal structure are excluded.
# Temple rim centers are inset from the observed exterior edge by the lip halfwidth.
FACE_CUSHION_WIDE_RIM_HALF = (
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
FACE_CUSHION_WIDE_RIM = _mirrored_loop(FACE_CUSHION_WIDE_RIM_HALF)
VISION_PRO_NARROW_RIM_HALF = (
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
VISION_PRO_NARROW_RIM = _mirrored_loop(VISION_PRO_NARROW_RIM_HALF)


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

# Measured broad face-cushion seating frames: origin, across-seat direction,
# normal toward the narrow Vision Pro interface, and the limits of the flat contact run. Last three stations are a
# conservative narrow hard-nose strip because the cloth obscures that region.
FACE_CUSHION_WIDE_SEATS_HALF = (
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
FACE_CUSHION_WIDE_RETURNS_HALF = (
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


def _face_cushion_profile(cushion):
    outer_bands = [[] for _ in range(7)]
    inner_bands = [[] for _ in range(7)]
    for i, ((origin, across, normal, span), returns) in enumerate(zip(FACE_CUSHION_WIDE_SEATS_HALF, FACE_CUSHION_WIDE_RETURNS_HALF)):
        origin, across, normal = Vector(origin), Vector(across), Vector(normal)
        origin += Vector(cushion[i]) - Vector(FACE_CUSHION_WIDE_RIM[i])
        for bands, points in zip((outer_bands, inner_bands), returns):
            for band, (q, depth) in zip(bands, points):
                point = origin + across * q + normal * depth
                band.append((0.0 if i in (0, 11) else point.X, point.Y, point.Z))
    return {"outer": [_mirrored_loop(half) for half in outer_bands], "inner": [_mirrored_loop(half) for half in inner_bands]}


# The Vision Pro connection is the small lip on the narrow high-W rim.
# These sparse paired profiles retain the rounded tip, 0.3–0.6 mm outside
# undercut near 3 mm depth, and return into the plain wall at 5.8 mm.
# Deeper broad lining shoulders are deliberately outside this reconstruction.
VISION_PRO_NARROW_FRAMES_HALF = (
    ((0.0, -35.297214, 45.200907), (-0.0, 0.924115, -0.382116), (-0.0, 0.382116, 0.924115)),
    ((29.999603, -33.997172, 40.250921), (-0.182503, 0.91567, -0.358108), (0.259889, 0.396198, 0.880616)),
    ((55.002135, -27.497529, 28.400805), (-0.628339, 0.761088, -0.161043), (0.269035, 0.406831, 0.872989)),
    ((69.992523, -10.549365, 18.000207), (-0.870283, 0.450485, -0.199177), (-0.011673, 0.3854, 0.922676)),
    ((72.890425, -3.001955, 16.249363), (-0.985743, 0.135529, -0.099714), (-0.086592, 0.099506, 0.991262)),
    ((72.898116, 9.496357, 16.148814), (-0.988784, -0.125982, -0.080214), (-0.068194, -0.096991, 0.992946)),
    ((69.994991, 17.796797, 17.998957), (-0.886289, -0.426818, -0.179773), (-0.040546, -0.315169, 0.948169)),
    ((54.999992, 37.493778, 25.997974), (-0.685753, -0.70128, -0.194805), (0.17036, -0.414869, 0.89379)),
    ((38.000892, 41.392787, 36.497651), (0.05676, -0.977441, -0.203438), (0.541018, -0.141143, 0.829083)),
    ((25.000676, 36.643088, 44.24775), (0.351212, -0.892284, -0.283689), (0.521104, -0.065445, 0.85098)),
    ((12.002049, 27.744007, 50.748049), (0.416406, -0.870485, -0.262415), (0.417448, -0.07335, 0.905735)),
    ((0.0, 23.794411, 53.69818), (0.0, -0.987672, -0.15654), (0.0, -0.15654, 0.987672)),
)
VISION_PRO_NARROW_LIP_HALF = (
    ((-0.592932, -5.792819), (-0.333851, -4.392819), (-0.350012, -3.792819), (-0.737233, -3.192819), (-0.672805, -2.792819), (-0.226701, -2.192819), (-0.209286, -1.792819), (-0.413971, -0.992819), (-0.471014, -0.392819), (-0.387565, -0.192819), (0.164591, 0.007181), (0.489107, -0.192819), (0.844538, -0.592819), (1.430085, -1.392819), (2.070311, -2.192819), (2.931739, -2.992819), (3.440741, -3.992819), (4.373182, -5.792819)),
    ((-0.551469, -5.896806), (-0.337918, -4.496806), (-0.299945, -3.896806), (-0.656559, -3.296806), (-0.640532, -2.896806), (-0.175068, -2.296806), (-0.098608, -1.896806), (-0.307619, -1.096806), (-0.294516, -0.496806), (-0.127736, -0.296806), (0.299771, -0.096806), (0.757359, -0.296806), (1.12053, -0.696806), (1.724271, -1.496806), (2.378562, -2.296806), (3.243433, -3.096806), (3.77221, -4.096806), (4.644762, -5.896806)),
    ((-0.988517, -5.938896), (-0.813889, -4.538896), (-0.77192, -3.938896), (-1.125411, -3.338896), (-1.151307, -2.938896), (-0.669965, -2.338896), (-0.522986, -1.938896), (-0.647652, -1.138896), (-0.659552, -0.538896), (-0.513113, -0.338896), (-0.018053, -0.138896), (0.453379, -0.338896), (0.780071, -0.738896), (1.366786, -1.538896), (1.976565, -2.338896), (2.943891, -3.138896), (3.653664, -4.138896), (4.550178, -5.938896)),
    ((-0.572236, -5.348817), (-0.620919, -3.948817), (-0.591198, -3.348817), (-0.915847, -2.748817), (-0.958974, -2.348817), (-0.632062, -1.748817), (-0.482453, -1.348817), (-0.65865, -0.548817), (-0.643408, 0.051183), (-0.410986, 0.251183), (0.004281, 0.451183), (0.328492, 0.251183), (0.782773, -0.148817), (1.505058, -0.948817), (2.502722, -1.748817), (3.476986, -2.548817), (4.007872, -3.548817), (4.92533, -5.348817)),
    ((0.288262, -4.95006), (0.247453, -3.55006), (0.337117, -2.95006), (0.098134, -2.35006), (0.048724, -1.95006), (0.342537, -1.35006), (0.526361, -0.95006), (0.400057, -0.15006), (0.425274, 0.44994), (0.631715, 0.64994), (0.894198, 0.84994), (1.278887, 0.64994), (1.756743, 0.24994), (2.439327, -0.55006), (3.309781, -1.35006), (4.277439, -2.15006), (4.773097, -3.15006), (5.599697, -4.95006)),
    ((0.166189, -5.358594), (0.171545, -3.958594), (0.236677, -3.358594), (-0.003176, -2.758594), (-0.044425, -2.358594), (0.272146, -1.758594), (0.458714, -1.358594), (0.360217, -0.558594), (0.404752, 0.041406), (0.25194, 0.241406), (0.934595, 0.441406), (1.557733, 0.241406), (1.718952, -0.158594), (2.361308, -0.958594), (3.144706, -1.758594), (4.095256, -2.558594), (4.605147, -3.558594), (5.33114, -5.358594)),
    ((-0.605098, -6.325562), (-0.539066, -4.925562), (-0.608692, -4.325562), (-0.879924, -3.725562), (-0.832232, -3.325562), (-0.50882, -2.725562), (-0.394373, -2.325562), (-0.56222, -1.525562), (-0.409312, -0.925562), (-0.619798, -0.725562), (0.112376, -0.525562), (0.789966, -0.725562), (0.895806, -1.125562), (1.596082, -1.925562), (2.524829, -2.725562), (3.458333, -3.525562), (3.947234, -4.525562), (4.74844, -6.325562)),
    ((-0.878912, -5.541211), (-0.690112, -4.141211), (-0.771472, -3.541211), (-0.987397, -2.941211), (-0.87067, -2.541211), (-0.546514, -1.941211), (-0.459705, -1.541211), (-0.584352, -0.741211), (-0.381516, -0.141211), (-0.546006, 0.058789), (0.114412, 0.258789), (0.814355, 0.058789), (0.89492, -0.341211), (1.522123, -1.141211), (2.288341, -1.941211), (3.200711, -2.741211), (3.809416, -3.741211), (4.956329, -5.541211)),
    ((-1.878534, -5.659757), (-1.692505, -4.259757), (-1.198963, -3.659757), (-1.087387, -3.059757), (-1.225217, -2.659757), (-0.960018, -2.059757), (-0.563814, -1.659757), (-0.327946, -0.859757), (-0.161226, -0.259757), (0.050636, -0.059757), (0.491491, 0.140243), (0.930486, -0.059757), (1.197225, -0.459757), (1.557319, -1.259757), (1.927407, -2.059757), (2.546245, -2.859757), (3.142074, -3.859757), (4.093337, -5.659757)),
    ((-2.15382, -5.518003), (-2.104766, -4.118003), (-1.668469, -3.518003), (-1.475236, -2.918003), (-1.660369, -2.518003), (-1.437998, -1.918003), (-0.977466, -1.518003), (-0.781971, -0.718003), (-0.689836, -0.118003), (-0.482779, 0.081997), (0.065789, 0.281997), (0.492771, 0.081997), (0.747376, -0.318003), (1.144134, -1.118003), (1.54174, -1.918003), (2.256417, -2.718003), (2.865097, -3.718003), (3.79406, -5.518003)),
    ((-2.554307, -5.474118), (-2.413166, -4.074118), (-1.881854, -3.474118), (-1.751378, -2.874118), (-2.023334, -2.474118), (-1.841283, -1.874118), (-1.271785, -1.474118), (-1.072762, -0.674118), (-0.980727, -0.074118), (-0.81236, 0.125882), (-0.304872, 0.325882), (0.139906, 0.125882), (0.374413, -0.274118), (0.725682, -1.074118), (1.061882, -1.874118), (1.672223, -2.674118), (2.197723, -3.674118), (3.044214, -5.474118)),
    ((-2.561835, -5.855501), (-1.95727, -4.455501), (-1.441318, -3.855501), (-1.738488, -3.255501), (-1.952089, -2.855501), (-1.657846, -2.255501), (-1.012486, -1.855501), (-0.866519, -1.055501), (-0.787901, -0.455501), (-0.639532, -0.255501), (-0.152576, -0.055501), (0.349005, -0.255501), (0.543387, -0.655501), (0.815179, -1.455501), (1.078398, -2.255501), (1.48168, -3.055501), (2.098303, -4.055501), (2.795754, -5.855501)),
)

def _vision_pro_profile(headset):
    bands = [[] for _ in VISION_PRO_NARROW_LIP_HALF[0]]
    for i, ((origin, inward, toward_device), profile) in enumerate(zip(VISION_PRO_NARROW_FRAMES_HALF, VISION_PRO_NARROW_LIP_HALF)):
        origin, inward, toward_device = Vector(origin), Vector(inward), Vector(toward_device)
        origin += Vector(headset[i]) - Vector(VISION_PRO_NARROW_RIM[i])
        for band, (u, v) in zip(bands, profile):
            point = origin + inward * u + toward_device * v
            band.append((0.0 if i in (0, 11) else point.X, point.Y, point.Z))
    return [_mirrored_loop(half) for half in bands]


def _vision_pro_lip_faces(headset, parameters):
    # Shape-preserving cubics follow each measured 2-D profile without adding
    # cap/join bulbs comparable in size to the real submillimetre undercut.
    # The common periodic perimeter interpolation keeps exact mirror symmetry.
    profiles = np.array(VISION_PRO_NARROW_LIP_HALF)
    lengths = np.linalg.norm(np.diff(profiles, axis=1), axis=2).mean(axis=0)
    stations = np.r_[0.0, np.cumsum(lengths)]
    interpolator = PchipInterpolator(stations, profiles, axis=1)
    derivatives = interpolator.derivative()(stations)
    faces = []
    for segment, width in enumerate(lengths):
        uv_controls = np.stack((profiles[:, segment],
                                profiles[:, segment] + derivatives[:, segment] * width / 3,
                                profiles[:, segment + 1] - derivatives[:, segment + 1] * width / 3,
                                profiles[:, segment + 1]), axis=1)
        rows = []
        for control in range(4):
            half = []
            for i, (origin, inward, toward_device) in enumerate(VISION_PRO_NARROW_FRAMES_HALF):
                point = Vector(origin) + Vector(headset[i]) - Vector(VISION_PRO_NARROW_RIM[i])
                u, v = uv_controls[i, control]
                point += Vector(inward) * u + Vector(toward_device) * v
                half.append((0.0 if i in (0, 11) else point.X, point.Y, point.Z))
            ring = _mirrored_loop(half)
            rows.append(make_interp_spline(parameters, np.array([*ring, ring[0]]), k=3, bc_type="periodic"))
        poles = TColgp_Array2OfPnt(1, len(rows[0].c), 1, 4)
        for vi, row in enumerate(rows, 1):
            for ui, point in enumerate(row.c, 1):
                poles.SetValue(ui, vi, gp_Pnt(*point))
        values, counts = np.unique(rows[0].t, return_counts=True)
        uknots = TColStd_Array1OfReal(1, len(values))
        umults = TColStd_Array1OfInteger(1, len(values))
        for i, (value, count) in enumerate(zip(values, counts), 1):
            uknots.SetValue(i, float(value))
            umults.SetValue(i, int(count))
        vknots = TColStd_Array1OfReal(1, 2)
        vmults = TColStd_Array1OfInteger(1, 2)
        for i, value in enumerate((0.0, 1.0), 1):
            vknots.SetValue(i, value)
            vmults.SetValue(i, 4)
        surface = Geom_BSplineSurface(poles, uknots, vknots, umults, vmults, 3, 3)
        surface.SetUPeriodic()
        faces.append(Face(BRepBuilderAPI_MakeFace(surface, 0.0, 1.0, 0.0, 1.0, 1e-7).Face()))
    return faces


# The broad face-cushion contact has four mirrored pairs of shallow closed
# pockets. Their scan-visible floors do not support interpreting them as bores.
# floor center, outward normal, long axis, opening length/width, blind depth (mm).
FACE_CUSHION_WIDE_POCKETS_HALF = (
    ((43.59, 39.525, 0.327), (-0.4673, 0.2647, -0.8435), (0.8636, -0.0677, -0.4996), 8.36, 4.08, 1.02),
    ((71.922, 15.416, -23.122), (-0.5376, 0.0557, -0.8413), (-0.2072, 0.9585, 0.1959), 8.84, 2.47, 0.97),
    ((61.744, -24.935, -11.414), (-0.6968, 0.1029, -0.7098), (0.6336, 0.5521, -0.542), 8.21, 2.58, 0.99),
    ((23.48, -37.476, 13.518), (-0.3001, 0.2931, -0.9078), (0.9533, 0.1259, -0.2745), 8.31, 4.58, 0.86),
)

def _cushion_pocket_cutters(cushion_fit_offset_mm):
    cutters = []
    for center, normal, major, length, width, depth in FACE_CUSHION_WIDE_POCKETS_HALF:
        normal, center, major = Vector(normal).normalized(), Vector(center), Vector(major)
        major = (major - normal * major.dot(normal)).normalized()
        # Use the nearby rim's outward XY direction for the optional fit offset.
        i = min(range(12), key=lambda j: (Vector(FACE_CUSHION_WIDE_RIM[j]) - center).length)
        shifted = _inset(FACE_CUSHION_WIDE_RIM, -cushion_fit_offset_mm)
        center += Vector(shifted[i]) - Vector(FACE_CUSHION_WIDE_RIM[i])
        plane = Plane(origin=center + normal * (1.0 + depth), x_dir=major, z_dir=normal)
        face = (plane * SlotOverall(length, width)).faces()[0]
        cutter = Solid.extrude(face, -normal * (1.0 + depth))
        cutters.extend((cutter, cutter.mirror(Plane.YZ)))
    return cutters


@part
def vision_pro_light_seal_13w(wall_mm=1.8, headset_fit_offset_mm=0.0, cushion_fit_offset_mm=0.0):
    """Smooth external shell with an open nose passage and no internal details."""
    if not 1.0 <= wall_mm <= 3.0:
        reject("Choose a nominal wall between 1.0 and 3.0 mm.", "wall_mm")
    if abs(headset_fit_offset_mm) > 1.0:
        reject("Keep the headset fit offset between -1.0 and 1.0 mm.", "headset_fit_offset_mm")
    if abs(cushion_fit_offset_mm) > 1.0:
        reject("Keep the cushion fit offset between -1.0 and 1.0 mm.", "cushion_fit_offset_mm")

    headset = _inset(VISION_PRO_NARROW_RIM, -headset_fit_offset_mm)
    cushion = _inset(FACE_CUSHION_WIDE_RIM, -cushion_fit_offset_mm)
    parameters = _periodic_parameters(cushion, headset)
    middle = _inset(MID_EXTERIOR, -(headset_fit_offset_mm + cushion_fit_offset_mm) / 2)
    profile = _face_cushion_profile(cushion)
    vision_pro_profile = _vision_pro_profile(headset)
    headset_outer, headset_inner = vision_pro_profile[0], vision_pro_profile[-1]
    outside = [profile["outer"][0], middle, headset_outer]
    inside = [profile["inner"][-1], _inner_wall(middle, outside[0], outside[-1], wall_mm), headset_inner]
    outer_wires = [_curve(points, parameters) for points in outside]
    inner_wires = [_curve(points, parameters) for points in inside]
    outer_return = [_curve(points, parameters) for points in profile["outer"]]
    inner_return = [_curve(points, parameters) for points in profile["inner"]]
    faces = [*_skin(outer_wires), *_skin(inner_wires), *_skin(outer_return), *_skin(inner_return)]
    faces.extend(_skin([outer_return[-1], inner_return[0]], ruled=True))
    faces.extend(_vision_pro_lip_faces(headset, parameters))
    body = Solid(Shell(faces))
    body = body.cut(*_cushion_pocket_cutters(cushion_fit_offset_mm))
    if not body.is_valid or len(body.solids()) != 1 or body.volume <= 0:
        raise ValueError("The smooth shell is not a closed positive-volume solid.")
    # Absolute deflection avoids excessive subdivision of the tiny retaining lip.
    # This cache affects display/export triangles only; the exact B-rep is unchanged.
    BRepMesh_IncrementalMesh(body.wrapped, 0.04, False, 0.25, True)
    return body
