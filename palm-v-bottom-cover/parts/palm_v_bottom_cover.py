"""Nominal Palm V sheet, with observed longitudinal bow optionally retained."""

import json
from pathlib import Path
import numpy as np
from scipy.interpolate import make_interp_spline
from nurb import *
from OCP.Geom import Geom_BSplineSurface
from OCP.gp import gp_Pnt
from OCP.TColgp import TColgp_Array2OfPnt
from OCP.TColStd import TColStd_Array1OfInteger, TColStd_Array1OfReal
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeEdge

# Exterior rim landmarks measured in the supplied aligned scan groups.
RIM_HALF = (
    (0, 56.24, 3.0),
    (10, 56.14, 3.0),
    (20, 56.03, 2.9),
    (30, 55.83, 2.85),
    (35, 55.58, 2.2),
    (38, 55.12, 1.4),
    (39.15, 54, 1.5),
    (39.13, 50, 1.5),
    (39.04, 40, 1.5),
    (38.91, 30, 1.6),
    (38.84, 20, 1.6),
    (38.79, 10, 1.55),
    (38.79, 0, 1.5),
    (38.79, -10, 1.5),
    (38.78, -20, 1.45),
    (38.78, -30, 1.4),
    (38.9, -35, 1.35),
    (39.32, -40, 1.6),
    (40.02, -45, 2.2),
    (40.54, -48, 2.95),
    (40.95, -50, 4.25),
    (40.75, -52, 4.45),
    (38, -53.09, 4.45),
    (35, -53.94, 4.45),
    (30, -55.23, 4.45),
    (25, -56.37, 4.45),
    (20, -57.24, 4.45),
    (17, -57.71, 4.45),
    (16, -57.7, 4.4),
    (16, -49.4, 0.8),
    (15, -49.04, 0.8),
    (10, -47.72, 0.8),
    (5, -46.97, 0.7),
    (0, -46.67, 0.7),
)


def _uv(points):
    p = np.asarray(points, dtype=float)
    z = (p[:, 2] + np.sqrt(p[:, 2] ** 2 + 0.01)) / 2

    def smooth(t):
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)

    return np.c_[
        p[:, 0] + np.sign(p[:, 0]) * 0.9 * z * smooth((abs(p[:, 0]) - 33) / 6),
        p[:, 1] + np.sign(p[:, 1]) * 0.9 * z * smooth((abs(p[:, 1]) - 42) / 12),
    ]


def _arrays(knots):
    values, counts = np.unique(knots, return_counts=True)
    a = TColStd_Array1OfReal(1, len(values))
    b = TColStd_Array1OfInteger(1, len(values))
    for i, (v, n) in enumerate(zip(values, counts), 1):
        a.SetValue(i, float(v))
        b.SetValue(i, int(n))
    return a, b


def exterior_surface(longitudinal_straightening=1.0):
    """Make the measured right-half surface, optionally removing longitudinal bow."""
    from OCP.Geom2d import Geom2d_BSplineCurve
    from OCP.TColgp import TColgp_Array1OfPnt2d
    from OCP.gp import gp_Pnt2d
    from OCP.GCE2d import GCE2d_MakeSegment
    from OCP.BRepLib import BRepLib

    d = json.loads(
        (
            Path(__file__).resolve().parents[1] / "references" / "surface-fit.json"
        ).read_text()
    )
    tx = np.array(d["x_knots"])
    ty = np.array(d["y_knots"])
    xyz = np.array(d["xyz_coefficients"])
    bow = d["longitudinal_bow"]
    # Straightening holds the measured broad-panel endpoints fixed. The inferred
    # bow is removed before thickening, preserving the true normal sheet gauge.
    y = xyz[:, :, 1]
    xyz[:, :, 2] -= (
        longitudinal_straightening
        * bow["quadratic_y_coefficient"]
        * (y + 40.0)
        * (y - 48.0)
    )
    poles = TColgp_Array2OfPnt(1, xyz.shape[0], 1, xyz.shape[1])
    for i in range(xyz.shape[0]):
        for j in range(xyz.shape[1]):
            poles.SetValue(i + 1, j + 1, gp_Pnt(*xyz[i, j]))
    kx, mx = _arrays(tx)
    ky, my = _arrays(ty)
    surf = Geom_BSplineSurface(poles, kx, ky, mx, my, 3, 3, False, False)
    p = _uv(RIM_HALF)

    def spline_edge(points, start_tangent=None, end_tangent=None):
        t = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        if start_tangent is None:
            start_tangent = (points[1] - points[0]) / np.linalg.norm(
                points[1] - points[0]
            )
        if end_tangent is None:
            end_tangent = (points[-1] - points[-2]) / np.linalg.norm(
                points[-1] - points[-2]
            )
        curve = make_interp_spline(
            t, points, k=3, bc_type=([(1, start_tangent)], [(1, end_tangent)])
        )
        cp = TColgp_Array1OfPnt2d(1, len(curve.c))
        for i, q in enumerate(curve.c, 1):
            cp.SetValue(i, gp_Pnt2d(*q))
        knots, mults = _arrays(curve.t)
        pc = Geom2d_BSplineCurve(cp, knots, mults, 3, False)
        return Edge(BRepBuilderAPI_MakeEdge(pc, surf).Edge())

    def line_edge(a, b):
        line = GCE2d_MakeSegment(gp_Pnt2d(*a), gp_Pnt2d(*b)).Value()
        return Edge(BRepBuilderAPI_MakeEdge(line, surf).Edge())

    # The long notch cut is a straight wall. A single interpolating loop overshoots it.
    corner = next(i for i, v in enumerate(RIM_HALF) if v[0] == 16 and v[1] == -57.7)
    edges = [
        spline_edge(p[: corner + 1], [1.0, 0.0]),
        line_edge(p[corner], p[corner + 1]),
        spline_edge(p[corner + 1 :], end_tangent=[-1.0, 0.0]),
        line_edge(p[-1], p[0]),
    ]
    wire = Wire(edges)
    BRepLib.BuildCurves3d_s(wire.wrapped)
    face = Face(BRepBuilderAPI_MakeFace(surf, wire.wrapped, True).Face())
    BRepLib.SameParameter_s(face.wrapped, 1e-6, True)
    if not face.is_valid:
        raise ValueError("Measured exterior half surface is invalid")
    return face


def formed_blank(sheet_thickness_mm=0.65, longitudinal_straightening=1.0):
    """Offset toward the observed interior and mirror the complete sheet half."""
    surface = exterior_surface(longitudinal_straightening)
    half = Solid.thicken(surface, sheet_thickness_mm, normal_override=(0, 0, 1))
    body = half.fuse(half.mirror(Plane.YZ))
    if not body.is_valid or len(body.solids()) != 1:
        raise ValueError("Mirrored normal-offset sheet is not one valid solid")
    return body


@part
def palm_v_bottom_cover(
    sheet_thickness_mm=0.65,
    longitudinal_straightening=1.0,
    slot_width_mm=7.2,
    slot_height_mm=2.7,
    reset_diameter_mm=1.8,
    draft=False,
):
    if not 0.25 <= sheet_thickness_mm <= 0.7:
        reject("Sheet gauge must be between 0.25 and 0.70 mm.", "sheet_thickness_mm")
    if not 0.0 <= longitudinal_straightening <= 1.0:
        reject(
            "Straightening must be between zero and one.", "longitudinal_straightening"
        )
    if not 5.0 <= slot_width_mm <= 9.0 or not 1.0 <= slot_height_mm <= 4.0:
        reject(
            "Use a slot width of 5 to 9 mm and height of 1 to 4 mm.", "slot_width_mm"
        )
    if not 1.4 <= reset_diameter_mm <= 2.4:
        reject("Use a Reset diameter between 1.4 and 2.4 mm.", "reset_diameter_mm")
    body = formed_blank(sheet_thickness_mm, longitudinal_straightening)
    slot = Pos(0, 15.3, 0) * Box(slot_width_mm, slot_height_mm, 20)
    body = body.cut(slot)
    reset = Pos(12.8, 19.16, 0) * Cylinder(reset_diameter_mm / 2, 20)
    body = body.cut(reset)
    if not body.is_valid or len(body.solids()) != 1:
        raise ValueError("Openings did not leave one valid sheet")
    return body
