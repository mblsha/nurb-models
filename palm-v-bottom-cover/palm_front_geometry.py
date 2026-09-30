"""Shared nominal front-skin geometry and measured visible feature profiles."""

import json
from pathlib import Path
import numpy as np
from scipy.interpolate import make_interp_spline
from scipy.optimize import brentq
from build123d import Edge, Wire, Face, Plane
from OCP.Geom import Geom_BSplineSurface
from OCP.Geom2d import Geom2d_BSplineCurve
from OCP.TColgp import TColgp_Array2OfPnt, TColgp_Array1OfPnt2d
from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
from OCP.gp import gp_Pnt, gp_Pnt2d
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace
from OCP.BRepLib import BRepLib
from OCP.GCE2d import GCE2d_MakeSegment

ROOT = Path(__file__).resolve().parent
BUTTON_CENTERS = [(-26.2, -42.0), (-13.0, -44.0), (13.0, -44.0), (26.2, -42.0)]


def arrays(knots):
    v, c = np.unique(knots, return_counts=True)
    a = TColStd_Array1OfReal(1, len(v))
    b = TColStd_Array1OfInteger(1, len(v))
    for i, (x, n) in enumerate(zip(v, c), 1):
        a.SetValue(i, float(x))
        b.SetValue(i, int(n))
    return a, b


def fitted_surface():
    d = json.loads((ROOT / "references/front-fit.json").read_text())
    tx = np.array(d["x_knots"])
    ty = np.array(d["y_knots"])
    xyz = np.array(d["xyz_coefficients"])
    p = TColgp_Array2OfPnt(1, xyz.shape[0], 1, xyz.shape[1])
    for i in range(xyz.shape[0]):
        for j in range(xyz.shape[1]):
            p.SetValue(i + 1, j + 1, gp_Pnt(*xyz[i, j]))
    kx, mx = arrays(tx)
    ky, my = arrays(ty)
    return Geom_BSplineSurface(p, kx, ky, mx, my, 3, 3, False, False)


def front_half():
    surf = fitted_surface()

    def z(x, y):
        return surf.Value(x, y).Z()

    # The 1.5mm level is the provisional visible front/body seam.
    # Few section landmarks keep the boundary smooth and avoid scan ripple.
    def crossing(fn, start, end):
        samples = np.linspace(start, end, 101)
        values = [fn(value) for value in samples]
        for a, b, fa, fb in zip(samples[:-1], samples[1:], values[:-1], values[1:]):
            if fa >= 0 and fb < 0:
                return brentq(fn, min(a, b), max(a, b))
        raise ValueError(
            "Observed front roll does not reach the selected cut-edge level"
        )

    points = []
    for x in [0, 10, 20, 30, 35, 38]:
        y = crossing(lambda y: z(x, y) - 1.5, 56, 63)
        points.append([x, y])
    for y in [54, 48, 35, 15, -10, -30, -42, -48]:
        x = crossing(lambda x: z(x, y) - 1.5, 36, 45)
        points.append([x, y])
    for x in [36, 28, 18, 8, 0]:
        y = crossing(lambda y: z(x, y) - 1.5, -47, -63)
        points.append([x, y])
    points = np.array(points)
    t = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    sp = make_interp_spline(
        t, points, k=3, bc_type=([(1, [1.0, 0.0])], [(1, [-1.0, 0.0])])
    )
    poles = TColgp_Array1OfPnt2d(1, len(sp.c))
    for i, p in enumerate(sp.c, 1):
        poles.SetValue(i, gp_Pnt2d(*p))
    k, m = arrays(sp.t)
    curve = Geom2d_BSplineCurve(poles, k, m, 3)
    outside = Edge(BRepBuilderAPI_MakeEdge(curve, surf).Edge())
    center = GCE2d_MakeSegment(gp_Pnt2d(*points[-1]), gp_Pnt2d(*points[0])).Value()
    inside = Edge(BRepBuilderAPI_MakeEdge(center, surf).Edge())
    wire = Wire([outside, inside])
    BRepLib.BuildCurves3d_s(wire.wrapped)
    face = Face(BRepBuilderAPI_MakeFace(surf, wire.wrapped, True).Face())
    BRepLib.SameParameter_s(face.wrapped, 1e-6, True)
    if not face.is_valid:
        raise ValueError("Front half surface is invalid")
    return face


def window_face(clearance=0.0):
    x = 28.5 + clearance
    top = 46.0 + clearance
    side_bottom = -29.0 - clearance
    bottom = -32.0 - clearance
    edges = [
        Edge.make_line((-x, top, 0), (x, top, 0)),
        Edge.make_line((x, top, 0), (x, side_bottom, 0)),
        Edge.make_three_point_arc(
            (x, side_bottom, 0), (0, bottom, 0), (-x, side_bottom, 0)
        ),
        Edge.make_line((-x, side_bottom, 0), (-x, top, 0)),
    ]
    face = Face(Wire(edges))
    return face.fillet_2d(0.8 + clearance, face.vertices())


def rocker_face(clearance=0.0):
    # Symmetric hourglass contour from the two-ended scroll key in the scan.
    w = 3.7 + clearance
    waist = 2.6 + clearance
    yc = -46.3
    runs = [
        [(0, 7.3 + clearance), (2.4, 7.3 + clearance), (w, 6.7), (w, 4.7)],
        [(w, 4.7), (w, 3.3), (waist, 2), (waist, 0)],
        [(waist, 0), (waist, -2), (w, -3.3), (w, -4.7)],
        [(w, -4.7), (w, -6.7), (2.4, -7.3 - clearance), (0, -7.3 - clearance)],
    ]
    right = [Edge.make_bezier(*[(x, y + yc, 0) for x, y in run]) for run in runs]
    return Face(Wire([*right, *[e.mirror(Plane.YZ) for e in right]]))
