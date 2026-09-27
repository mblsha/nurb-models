"""Sample principal curvature of the nominal Palm V continuous-end exterior."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import BSpline


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sampled_radius(surface_fit, straight_fit, u, v):
    poles = np.asarray(straight_fit["coefficients_at_bow_1"])
    x_basis = BSpline(np.asarray(surface_fit["x_knots"]), np.eye(poles.shape[0]), 3)
    y_basis = BSpline(np.asarray(surface_fit["y_knots"]), np.eye(poles.shape[1]), 3)

    def derivative(du, dv):
        return np.einsum(
            "ui,vj,ijc->uvc", x_basis(u, nu=du), y_basis(v, nu=dv), poles
        )

    point = derivative(0, 0)
    pu, pv = derivative(1, 0), derivative(0, 1)
    puu, puv, pvv = derivative(2, 0), derivative(1, 1), derivative(0, 2)
    normal = np.cross(pu, pv)
    normal /= np.linalg.norm(normal, axis=2)[..., None]
    E = np.sum(pu * pu, axis=2)
    F = np.sum(pu * pv, axis=2)
    G = np.sum(pv * pv, axis=2)
    e = np.sum(normal * puu, axis=2)
    f = np.sum(normal * puv, axis=2)
    g = np.sum(normal * pvv, axis=2)
    denominator = E * G - F * F
    mean = (E * g - 2 * F * f + G * e) / (2 * denominator)
    gaussian = (e * g - f * f) / denominator
    root = np.sqrt(np.maximum(mean * mean - gaussian, 0))
    max_curvature = np.maximum(np.abs(mean + root), np.abs(mean - root))
    return point, 1 / max_curvature


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.project
    surface_path = root / "references/surface-fit.json"
    straight_path = root / "references/straight-rim-fit.json"
    surface_fit = json.loads(surface_path.read_text())
    straight_fit = json.loads(straight_path.read_text())
    u = np.linspace(0, 40, 161)
    v = np.linspace(52, 58.7, 269)
    point, radius = sampled_radius(surface_fit, straight_fit, u, v)
    bounds = {
        "continuous_end_root": (54.6, 55.8),
        "root_and_adjacent_side": (53.8, 55.8),
    }
    regions = {}
    for name, (y_min, y_max) in bounds.items():
        mask = (
            (point[:, :, 0] >= 0)
            & (point[:, :, 0] <= 40)
            & (point[:, :, 1] >= y_min)
            & (point[:, :, 1] <= y_max)
        )
        i, j = np.unravel_index(np.argmin(np.where(mask, radius, np.inf)), radius.shape)
        regions[name] = {
            "physical_y_bounds_mm": [y_min, y_max],
            "sample_count": int(mask.sum()),
            "minimum_exterior_principal_radius_mm": float(radius[i, j]),
            "minimum_radius_point_xyz_mm": point[i, j].tolist(),
            "minimum_radius_parameter_uv_mm": [float(u[i]), float(v[j])],
            "samples_with_radius_below_0_65_mm": int(np.sum(radius[mask] < 0.65)),
            "conservative_inner_offset_radius_margin_mm": float(radius[i, j] - 0.65),
        }
    report = {
        "method": "Principal curvatures from analytic cubic B-spline derivatives on a fixed 161 by 269 parameter grid. Physical coordinate masks select the positive-X half; the fitted surface is bilateral. The inner-offset margin subtracts the nominal 0.65 mm sheet gauge from exterior radius as a conservative focality indicator, not a complete offset-surface proof.",
        "source_sha256": {
            "surface_fit": sha256(surface_path),
            "straight_rim_fit": sha256(straight_path),
        },
        "regions": regions,
    }
    output = args.output or root / "build/far-end-curvature-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
