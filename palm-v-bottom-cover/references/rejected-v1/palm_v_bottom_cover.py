"""Provisional reconstruction of the formed Palm V aluminium bottom cover."""

from math import hypot

import numpy as np
from scipy.interpolate import make_interp_spline

from nurb import *
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Geom import Geom_BSplineCurve
from OCP.gp import gp_Pnt
from OCP.TColgp import TColgp_Array1OfPnt
from OCP.TColStd import TColStd_Array1OfInteger, TColStd_Array1OfReal
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge


# Sparse half-outline landmarks in the fitted scan frame. The list starts at the
# unnotched end centerline and follows the positive-X side to the center of the
# connector notch. Mirroring happens before interpolation, so the formed blank is
# mathematically bilateral rather than a smoothed copy of scan noise.
OUTER_HALF_OUTLINE_MM = (
    (0.0, 55.98),
    (10.0, 56.00),
    (20.0, 55.80),
    (28.0, 55.68),
    (32.0, 55.49),
    (36.0, 55.34),
    (38.5, 54.78),
    (38.50, 50.0),
    (38.56, 40.0),
    (38.47, 30.0),
    (38.39, 20.0),
    (38.34, 10.0),
    (38.24, 0.0),
    (38.15, -10.0),
    (38.19, -20.0),
    (38.20, -30.0),
    (38.60, -35.0),
    (39.08, -40.0),
    (39.90, -46.0),
    (40.15, -49.0),
    (40.10, -50.0),
    (38.0, -51.0),
    (36.0, -51.69),
    (32.0, -52.91),
    (28.0, -54.12),
    (24.0, -55.06),
    (20.0, -55.82),
    (18.0, -56.17),
    (16.0, -56.20),
    (16.0, -49.0),
    (14.0, -48.39),
    (12.0, -47.86),
    (10.0, -47.42),
    (8.0, -47.05),
    (6.0, -46.77),
    (4.0, -46.56),
    (2.0, -46.44),
    (0.0, -46.40),
)


def _mirror_half_outline(half):
    return tuple((x, y, 0.0) for x, y in half) + tuple(
        (-x, y, 0.0) for x, y in half[-2:0:-1]
    )


def _periodic_parameters(points):
    values = [0.0]
    for first, second in zip(points, points[1:] + points[:1]):
        values.append(values[-1] + hypot(second[0] - first[0], second[1] - first[1]))
    return [value / values[-1] for value in values]


def _periodic_wire(points):
    parameters = _periodic_parameters(points)
    spline = make_interp_spline(
        parameters,
        np.array([*points, points[0]]),
        k=3,
        bc_type="periodic",
    )
    values, counts = np.unique(spline.t, return_counts=True)
    poles = TColgp_Array1OfPnt(1, len(spline.c))
    knots = TColStd_Array1OfReal(1, len(values))
    multiplicities = TColStd_Array1OfInteger(1, len(values))
    for index, point in enumerate(spline.c, 1):
        poles.SetValue(index, gp_Pnt(*point))
    for index, (value, count) in enumerate(zip(values, counts), 1):
        knots.SetValue(index, float(value))
        multiplicities.SetValue(index, int(count))
    curve = Geom_BSplineCurve(poles, knots, multiplicities, 3, False)
    curve.SetPeriodic()
    return Wire([Edge(BRepBuilderAPI_MakeEdge(curve, 0.0, 1.0).Edge())])


def _inset_loop(points, amount):
    result = []
    for index, point in enumerate(points):
        previous, following = points[index - 1], points[(index + 1) % len(points)]
        incoming = np.array((point[0] - previous[0], point[1] - previous[1]), dtype=float)
        outgoing = np.array((following[0] - point[0], following[1] - point[1]), dtype=float)
        incoming /= np.linalg.norm(incoming)
        outgoing /= np.linalg.norm(outgoing)
        # The mirrored loop runs clockwise, so right normals point into material.
        first = np.array((incoming[1], -incoming[0]))
        second = np.array((outgoing[1], -outgoing[0]))
        bisector = first + second
        bisector /= np.linalg.norm(bisector)
        scale = amount / max(0.25, float(np.dot(bisector, first)))
        result.append((point[0] + scale * bisector[0], point[1] + scale * bisector[1], 0.0))
    return tuple(result)


def _transverse_crown(top_z, rise_mm, sheet_offset=0.0):
    half_width = 40.2
    radius = (half_width * half_width + rise_mm * rise_mm) / (2 * rise_mm)
    radius -= sheet_offset
    center_z = top_z - (half_width * half_width + rise_mm * rise_mm) / (2 * rise_mm)
    circle = (Plane.XZ * Circle(radius)).faces()[0]
    return Pos(0, -80, center_z) * Solid.extrude(circle, Vector(0, 160, 0))


def _ramp_volume(sheet_offset=0.0):
    # One tilted ellipsoid gives the observed steep leading rise near Y=14.5,
    # its crest near Y=18, and a long decay by Y=40 without a rectangular seam.
    unit = Sphere(1.0, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    scaled = unit.transform_geometry(
        Matrix(
            [
                [25.0, 0.0, 0.0, 0.0],
                [0.0, 14.0, 0.0, 0.0],
                [0.0, 0.0, 0.50, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )
    )
    return Pos(0, 28.0, -0.08 - sheet_offset) * Rot(-2.0, 0, 0) * scaled


def _formed_shell(sheet_thickness_mm, crown_height_mm, skirt_depth_mm, return_width_mm, draft=False):
    outer_points = _mirror_half_outline(OUTER_HALF_OUTLINE_MM)
    inner_points = _inset_loop(outer_points, sheet_thickness_mm)
    return_points = _inset_loop(outer_points, return_width_mm)
    outer_face = Face(_periodic_wire(outer_points))
    inner_face = Face(_periodic_wire(inner_points))
    return_face = Face(_periodic_wire(return_points))

    # A large-radius sphere is the low-order fit supported by the broad scan: it
    # gives one smooth shallow crown without reproducing dents or scan texture.
    outer_bottom_z = -skirt_depth_mm
    column_height = skirt_depth_mm + 2.0
    outer_column = Pos(0, 0, outer_bottom_z) * Solid.extrude(
        outer_face,
        Vector(0, 0, column_height),
    )
    outer_crown = _transverse_crown(0.10, crown_height_mm)
    blank = outer_column.intersect(outer_crown)[0].fuse(_ramp_volume())

    # Concentric crown radii derive the inner surface along the crown normal.
    # The inset plan and raised cavity floor carry the same gauge through the
    # skirt and return lip.
    inner_bottom_z = outer_bottom_z + sheet_thickness_mm
    inner_column = Pos(0, 0, inner_bottom_z) * Solid.extrude(
        inner_face,
        Vector(0, 0, column_height),
    )
    inner_crown = _transverse_crown(
        0.10,
        crown_height_mm,
        sheet_offset=sheet_thickness_mm,
    )
    upper_cavity = inner_column.intersect(inner_crown)[0]
    lower_column = Pos(0, 0, outer_bottom_z - 0.5) * Solid.extrude(
        return_face,
        Vector(0, 0, column_height + 0.5),
    )
    lower_opening = lower_column.intersect(inner_crown)[0]
    shell = blank.cut(upper_cavity, lower_opening)
    if not shell.is_valid or len(shell.solids()) != 1 or shell.volume <= 0:
        raise ValueError(
            "The formed aluminium shell is not one valid positive-volume solid "
            f"(valid={shell.is_valid}, solids={len(shell.solids())}, volume={shell.volume:.6g})."
        )
    return shell


def _reset_cutter(center_x_mm, center_y_mm, diameter_mm):
    return Pos(center_x_mm, center_y_mm, -5.0) * Cylinder(diameter_mm / 2, 10.0)


@part
def palm_v_bottom_cover(
    sheet_thickness_mm=0.40,
    crown_height_mm=0.30,
    skirt_depth_mm=1.10,
    return_width_mm=1.35,
    reset_hole_diameter_mm=1.80,
    draft=False,
):
    """Smooth formed cover; the offset Reset hole is the only asymmetry."""
    if not 0.25 <= sheet_thickness_mm <= 0.60:
        reject("Choose an aluminium sheet gauge between 0.25 and 0.60 mm.", "sheet_thickness_mm")
    if not 0.15 <= crown_height_mm <= 0.60:
        reject("Keep the shallow transverse crown between 0.15 and 0.60 mm.", "crown_height_mm")
    if not 0.8 <= skirt_depth_mm <= 1.5:
        reject("Keep the formed perimeter depth between 0.8 and 1.5 mm.", "skirt_depth_mm")
    if not 0.8 <= return_width_mm <= 2.2:
        reject("Keep the inward return between 0.8 and 2.2 mm.", "return_width_mm")
    if not 1.4 <= reset_hole_diameter_mm <= 2.4:
        reject("Choose a Reset-hole diameter between 1.4 and 2.4 mm.", "reset_hole_diameter_mm")

    shell = _formed_shell(
        sheet_thickness_mm,
        crown_height_mm,
        skirt_depth_mm,
        return_width_mm,
        draft=draft,
    )
    # Cut this last. Everything before this line is exactly bilateral about X=0.
    reset = _reset_cutter(12.80, 19.16, reset_hole_diameter_mm)
    body = shell.cut(reset)
    if not body.is_valid or len(body.solids()) != 1 or body.volume <= 0:
        raise ValueError("The Reset cut did not leave one valid cover solid.")
    BRepMesh_IncrementalMesh(body.wrapped, 0.025, False, 0.25, True)
    return body
