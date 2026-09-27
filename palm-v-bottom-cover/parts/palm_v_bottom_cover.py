"""Nominal Palm V sheet, with observed longitudinal bow optionally retained."""

import json
import hashlib
from pathlib import Path
import numpy as np
from scipy.interpolate import make_interp_spline
from scipy.optimize import brentq, root
from nurb import *
from OCP.Geom import Geom_BSplineSurface
from OCP.gp import gp_Pnt
from OCP.TColgp import TColgp_Array2OfPnt
from OCP.TColStd import TColStd_Array1OfInteger, TColStd_Array1OfReal
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeEdge

# Exterior rim landmarks based on the aligned scans; the +Y corner trim is
# faired so that both faces of the 0.65 mm sheet descend without a ripple.
RIM_HALF = (
    (0, 56.24, 3.0),
    (10, 56.14, 3.0),
    (20, 56.03, 2.9),
    (30, 56.03, 2.85),
    (35, 55.38, 2.2),
    (38, 55.22, 1.4),
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


def exterior_surface(longitudinal_straightening=1.0, straight_rims=True, smooth_split_end=True, level_inner_rims=True):
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
    rim_fit = None
    if straight_rims:
        rim_fit = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "references"
                / "straight-rim-fit.json"
            ).read_text()
        )
        actual_fit_hash = hashlib.sha256(
            (
                Path(__file__).resolve().parents[1] / "references/surface-fit.json"
            ).read_bytes()
        ).hexdigest()
        if rim_fit["source_fit_sha256"] != actual_fit_hash:
            raise ValueError(
                "The straight-rim fit is stale. Regenerate it with references/straighten_rims.py."
            )
        low = np.array(rim_fit["coefficients_at_bow_0"])
        high = np.array(rim_fit["coefficients_at_bow_1"])
        xyz = low + longitudinal_straightening * (high - low)
        # A broad, smooth adjustment forms the nominal split-side return
        # without importing a scan-induced outward hump into the inner offset.
        # It is mirrored at the control-pole level so the Reset hole remains
        # the only left/right difference.
        def ease(t):
            t = np.clip(t, 0.0, 1.0)
            return t * t * (3.0 - 2.0 * t)

        if smooth_split_end:
            for i in range(30, xyz.shape[0]):
                mirror = xyz.shape[0] - 1 - i
                for j in range(11, 25):
                    x = xyz[i, j, 0]
                    y = 0.5 * (ty[j] + ty[j + 4])
                    weight = ease((y + 55.0) / 6.0) * ease((-36.0 - y) / 9.0)
                    dx = 0.4 * np.tanh((39.8 - x) / 1.0) * np.exp(-((x - 39.5) / 2.0) ** 2) * weight
                    dz = 1.0 * (x - 39.75) * np.exp(-((x - 39.5) / 1.5) ** 2) * weight
                    xyz[i, j, 0] += dx
                    xyz[mirror, j, 0] -= dx
                    xyz[i, j, 2] += dz
                    xyz[mirror, j, 2] += dz
        # Reconstruct the broad sheet as its nominal plane. The scan has a
        # shallow crown and bow in this area, but the small raised form at the
        # openings and the independently formed perimeter remain intentional.
        field_z = -0.30

        def ease(t):
            t = np.clip(t, 0.0, 1.0)
            return t * t * (3.0 - 2.0 * t)

        for i in range(35):
            for j in range(20, 57):
                x, y, observed_z = xyz[i, j]
                form_weight = (
                    ease((26.0 - abs(x)) / 12.0)
                    * ease((y - 9.0) / 5.0)
                    * ease((30.0 - y) / 8.0)
                )
                xyz[i, j, 2] = field_z + form_weight * (observed_z - field_z)
        # Keep the nominal +Y corner seat in contact with the plastic at the
        # compact x=35 mm transition. This correction is confined to the
        # perimeter bend and mirrored on the opposite corner.
        for i in range(29, 36):
            other = xyz.shape[0] - 1 - i
            for j in range(52, 58):
                x, y = xyz[i, j, :2]
                dx = (x - 35.0) / 3.0
                dy = (y - 54.0) / 2.5
                dz = 0.0050 * np.exp(-dx**4 - dy**4)
                xyz[i, j, 2] += dz
                xyz[other, j, 2] += dz
        # A scan-derived pole near the split-side long edge makes the normal
        # offset crest swell even though the exterior trim is level. Fair that
        # pole, then level the neighboring normal field without moving the
        # exterior crest or introducing a kink at either end of the run.
        for i in (37, xyz.shape[0] - 1 - 37):
            for axis in (0, 2):
                neighbor_mean = 0.5 * (xyz[i, 23, axis] + xyz[i, 25, axis])
                xyz[i, 24, axis] += (0.18 if axis == 0 else 0.45) * (neighbor_mean - xyz[i, 24, axis])
        side_normal_fairing = np.array([
            [-0.00511072, -0.26082281, -0.45107155, -0.52033259, -0.01457137, 0.14810135, 0.09185815, 0.00291527],
            [-0.00479264, -0.05414874, 0.13934315, 0.31107236, -0.00852425, -0.05792374, -0.03147965, -0.00037823],
            [-0.00515616, 0.06080307, 0.12604449, 0.18259518, -0.02269319, -0.06885896, -0.04089217, -0.00106975],
            [-0.00183289, 0.01153074, 0.01961494, 0.01455468, 0.00226215, -0.00697530, -0.00723194, -0.00062838],
        ])
        for i in range(35, 39):
            for j in range(21, 29):
                dz = side_normal_fairing[i - 35, j - 21]
                xyz[i, j, 2] += dz
                xyz[xyz.shape[0] - 1 - i, j, 2] += dz
    poles = TColgp_Array2OfPnt(1, xyz.shape[0], 1, xyz.shape[1])
    for i in range(xyz.shape[0]):
        for j in range(xyz.shape[1]):
            poles.SetValue(i + 1, j + 1, gp_Pnt(*xyz[i, j]))
    kx, mx = _arrays(tx)
    ky, my = _arrays(ty)
    surf = Geom_BSplineSurface(poles, kx, ky, mx, my, 3, 3, False, False)
    # Preserve the formed far-end lip while making the long-side sheet crest
    # level in both the exterior and its normal-offset interior. Refining the
    # longitudinal knots localizes this fairing to the last side-bend spans.
    for v_knot in (52.75, 53.0, 54.5, 55.0, 55.5, 56.0, 56.25):
        surf.InsertVKnot(v_knot, 1, 1e-9)
    far_bend_dx = np.array([
        [-0.109925009, -0.083322065, -0.061255343, -0.045924265, -0.034358350, -0.020337350, -0.002282733, +0.013384481, +0.006958116, +0.034427984, +0.068303194],
        [-0.130061238, -0.057364698, -0.015931127, -0.012718259, -0.058851562, -0.089564525, -0.065166883, +0.005838122, +0.009777099, -0.027594338, +0.012188131],
        [+0.032307094, +0.014525930, +0.007930005, +0.013576265, +0.004232703, +0.017535913, +0.022537851, +0.011448695, -0.016168200, -0.039435507, -0.027017031],
        [-0.027117729, -0.015440329, -0.015536487, -0.019094243, +0.004147716, +0.057753359, +0.085427240, +0.070253636, +0.039225116, +0.005204820, -0.025384179],
        [-0.112685117, -0.066445368, -0.028669125, +0.000815710, +0.023930870, +0.041817078, +0.051641144, +0.051663654, +0.042959838, +0.028213128, +0.010650632],
    ])
    far_bend_dz = np.array([
        [+0.004068579, +0.003689447, +0.004390593, +0.007375646, +0.013395019, +0.022435859, +0.033711995, +0.044369979, +0.047378181, -0.002170827, -0.048108599],
        [+0.010505320, +0.003135397, -0.000449534, +0.000040073, +0.005068623, +0.006806635, +0.000102302, -0.013264968, -0.013114758, -0.013804184, -0.006701252],
        [-0.004410952, -0.003081762, -0.002428732, -0.002359073, -0.001809448, -0.002118873, -0.000430715, +0.005734496, +0.018185053, +0.029565096, +0.035277682],
        [+0.006278805, +0.004649872, +0.004368482, +0.005645543, +0.004005134, -0.000306282, -0.001282732, +0.003459488, +0.011631595, +0.020493405, +0.028836568],
        [+0.016374526, +0.011380112, +0.007397786, +0.004525149, +0.002564496, +0.001297793, +0.000954444, +0.001672700, +0.003338085, +0.005701067, +0.008412235],
    ])
    for i in range(34, 39):
        mirror = surf.NbUPoles() - 1 - i
        for j in range(54, 65):
            dx = far_bend_dx[i - 34, j - 54]
            dz = far_bend_dz[i - 34, j - 54]
            for side_i, sign in ((i, 1), (mirror, -1)):
                pole = surf.Pole(side_i + 1, j + 1)
                surf.SetPole(side_i + 1, j + 1, gp_Pnt(pole.X() + sign * dx, pole.Y(), pole.Z() + dz))
    if straight_rims and level_inner_rims:
        # These edits level the normal-offset inner crests without moving the
        # exterior trims or changing the 0.65 mm normal sheet gauge.
        inner_fit = json.loads(
            (Path(__file__).resolve().parents[1] / "references/inner-rim-fit.json").read_text()
        )
        if inner_fit["straight_rim_fit_sha256"] != hashlib.sha256(
            (Path(__file__).resolve().parents[1] / "references/straight-rim-fit.json").read_bytes()
        ).hexdigest():
            raise ValueError("The inner-rim fit is stale. Regenerate it with references/level_inner_rims.py.")
        for knot in inner_fit["extra_v_knots"]:
            surf.InsertVKnot(knot, 1, 1e-9)
        if (surf.NbUPoles(), surf.NbVPoles()) != tuple(inner_fit["pole_grid"]):
            raise ValueError("The inner-rim correction no longer matches the spline grid.")
        for i, j, dz in inner_fit["symmetric_z_pole_corrections"]:
            for side_i in ({i, surf.NbUPoles() - 1 - i}):
                pole = surf.Pole(side_i + 1, j + 1)
                surf.SetPole(side_i + 1, j + 1, gp_Pnt(pole.X(), pole.Y(), pole.Z() + dz))
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
    if rim_fit is None:
        edges = [
            spline_edge(p[: corner + 1], [1.0, 0.0]),
            line_edge(p[corner], p[corner + 1]),
            spline_edge(p[corner + 1 :], end_tangent=[-1.0, 0.0]),
            line_edge(p[-1], p[0]),
        ]
    else:
        bands = {b["name"]: b for b in rim_fit["targets"]}
        far, side, near = [bands[n] for n in ("far_end", "long_side", "split_end")]
        fa, fb = np.array(far["uv_a"]), np.array(far["uv_b"])
        sa, sb = np.array(side["uv_a"]), np.array(side["uv_b"])
        na, nb = np.array(near["uv_a"]), np.array(near["uv_b"])
        nd = (na - nb) / np.linalg.norm(na - nb)
        # The scan-derived core stops at -28/+40, but the manufactured crest
        # continues through both compact corner approaches. Trace the native
        # surface's Z=1.30 contour so its side elevation is exactly level.
        side_uv = np.array([
            [brentq(lambda u: surf.Value(u, v).Z() - 1.30, 35.0, 41.0), v]
            for v in np.r_[np.linspace(56.0, 55.0, 101)[:-1], np.linspace(55.0, -40.0, 381)]
        ])
        top_tangent = side_uv[1] - side_uv[0]
        top_tangent /= np.linalg.norm(top_tangent)
        bottom_tangent = side_uv[-1] - side_uv[-2]
        bottom_tangent /= np.linalg.norm(bottom_tangent)
        # At the far end the level side reaches the upright before it turns.
        # The former p[6] landmark made this bend spread across several mm.
        # A mirrored pair of tangent circular arcs gives the +Y lip its
        # nominal end elevation. It meets the level long-side crest exactly.
        crest = surf.Value(float(fb[0]), float(fb[1]))
        finish = surf.Value(float(side_uv[0, 0]), float(side_uv[0, 1]))
        crest_z, end_x, end_z = crest.Z(), finish.X(), finish.Z()
        corner_radius = 3.45
        fall = crest_z - end_z
        start_x = end_x - np.sqrt(4 * corner_radius * fall - fall * fall)
        join_x = 0.5 * (start_x + end_x)
        sample_x = np.r_[
            np.linspace(crest.X(), start_x, 17),
            np.linspace(start_x, join_x, 33)[1:],
            np.linspace(join_x, end_x, 33)[1:],
        ]
        far_corner = np.empty((len(sample_x), 2))
        guess = np.array(fb)
        for i, x in enumerate(sample_x):
            if x <= start_x:
                z = crest_z
            elif x <= join_x:
                z = crest_z - corner_radius + np.sqrt(corner_radius**2 - (x - start_x)**2)
            else:
                z = end_z + corner_radius - np.sqrt(corner_radius**2 - (x - end_x)**2)
            solved = root(
                lambda uv: (
                    surf.Value(float(uv[0]), float(uv[1])).X() - x,
                    surf.Value(float(uv[0]), float(uv[1])).Z() - z,
                ),
                guess,
                tol=1e-11,
            )
            if np.linalg.norm(solved.fun) > 1e-6:
                raise ValueError(f"Cannot place nominal +Y trim at X={x:.3f}, Z={z:.3f}: {solved.message}")
            guess = solved.x
            far_corner[i] = guess
        far_corner[0] = fb
        far_corner[-1] = side_uv[0]
        # The lower return rises only after the straight long side.
        lower_corner = np.array([
            side_uv[-1], [40.7677, -44.0771], [40.8900, -46.2705],
            [40.8769, -47.3822], [41.1526, -48.5831],
            [41.7150, -49.9183], [42.7010, -51.6582],
            [44.1978, -53.4680], [44.5132, -55.6712],
            [44.0001, -56.1126], [42.9461, -56.5242],
            [41.6715, -56.8694],
            [39.5862, -57.2898], nb,
        ])
        # Solve the trim directly on the native surface so the opening walls
        # are physical X=16 planes, rather than approximately straight UV lines.
        def notch_uv(v):
            return [brentq(lambda u: surf.Value(u, v).X() - 16.0, 14.0, 17.0), v]

        p[28] = notch_uv(-61.6904)
        p[29] = notch_uv(p[29, 1])
        notch_corner = np.array([na, p[27], p[28]])
        notch_wall = np.array([notch_uv(v) for v in np.linspace(p[28, 1], p[29, 1], 49)])
        if not smooth_split_end:
            # The plastic seat uses the denser, stable interpolation master.
            # Its measured gap to the smoothed sheet is below 0.004 mm.
            lower_corner = np.array([
                side_uv[-1], [40.5631, -42.0044],
                [40.7677, -44.0771], [40.9327, -46.2774],
                [41.0102, -47.4094], [41.0411, -47.9810],
                [41.1526, -48.5831], [41.3556, -49.2187],
                [41.7150, -49.9183], [42.1801, -50.7311],
                [42.7010, -51.6582], [43.3923, -52.5597],
                [44.1978, -53.4680], [44.5132, -55.6712],
                [44.0001, -56.1126], [42.9461, -56.5242],
                [41.6715, -56.8694], [39.5862, -57.2898], nb,
            ])
        edges = [
            line_edge(fa, fb),
            spline_edge(far_corner, [1.0, 0.0], top_tangent),
            spline_edge(side_uv, top_tangent, bottom_tangent),
            spline_edge(lower_corner, bottom_tangent, nd),
            line_edge(nb, na),
            spline_edge(notch_corner, nd),
            spline_edge(notch_wall),
            spline_edge(p[corner + 1 :], end_tangent=[-1.0, 0.0]),
            line_edge(p[-1], fa),
        ]
    wire = Wire(edges)
    BRepLib.BuildCurves3d_s(wire.wrapped)
    face = Face(BRepBuilderAPI_MakeFace(surf, wire.wrapped, True).Face())
    BRepLib.SameParameter_s(face.wrapped, 1e-6, True)
    if not face.is_valid:
        raise ValueError("Measured exterior half surface is invalid")
    return face


def formed_blank(
    sheet_thickness_mm=0.65, longitudinal_straightening=1.0, straight_rims=True,
    smooth_split_end=True,
):
    """Offset toward the observed interior and mirror the complete sheet half."""
    surface = exterior_surface(longitudinal_straightening, straight_rims, smooth_split_end)
    half = Solid.thicken(surface, sheet_thickness_mm, normal_override=(0, 0, 1))
    body = half.fuse(half.mirror(Plane.YZ))
    if not body.is_valid or len(body.solids()) != 1:
        raise ValueError("Mirrored normal-offset sheet is not one valid solid")
    return body


@part
def palm_v_bottom_cover(
    sheet_thickness_mm=0.65,
    longitudinal_straightening=1.0,
    straight_rims=True,
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
    surface = exterior_surface(longitudinal_straightening, straight_rims)
    half = Solid.thicken(surface, sheet_thickness_mm, normal_override=(0, 0, 1))
    # Cutting the centered opening before joining the halves avoids a fragile
    # coincident seam through the offset surface in the Boolean operation.
    slot = Pos(0, 15.3, 0) * Box(slot_width_mm, slot_height_mm, 20)
    half = half.cut(slot)
    body = half.fuse(half.mirror(Plane.YZ))
    reset = Pos(12.8, 19.16, 0) * Cylinder(reset_diameter_mm / 2, 20)
    body = body.cut(reset)
    if not body.is_valid or len(body.solids()) != 1:
        raise ValueError("Openings did not leave one valid sheet")
    return body
