"""Fit the six lower-web openings from the unchanged scan in its recorded pose."""
from pathlib import Path
import json
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from scipy.interpolate import splprep, splev
from nurb import scan

ROOT = Path(__file__).resolve().parents[1]


def outline(parameters):
    x, y, width, height, shear, radius = parameters
    corners = np.array(((x, y), (x + width, y),
                        (x + width + shear * height, y + height),
                        (x + shear * height, y + height)))
    return rounded_polygon(corners, [radius] * 4)


def rounded_polygon(corners, radii):
    corners = np.asarray(corners, dtype=float)
    starts, ends, arcs = [], [], []
    for index, corner in enumerate(corners):
        radius = radii[index]
        before = corners[(index - 1) % 4] - corner
        after = corners[(index + 1) % 4] - corner
        before /= np.linalg.norm(before)
        after /= np.linalg.norm(after)
        half_angle = np.arccos(np.dot(before, after)) / 2
        tangent = radius / np.tan(half_angle)
        first, last = corner + tangent * before, corner + tangent * after
        bisector = before + after
        center = corner + radius / np.sin(half_angle) * bisector / np.linalg.norm(bisector)
        first_angle = np.arctan2(*(first - center)[::-1])
        last_angle = np.arctan2(*(last - center)[::-1])
        angles = first_angle + np.linspace(0, (last_angle - first_angle) % (2 * np.pi), 120)
        arcs.append(center + radius * np.column_stack((np.cos(angles), np.sin(angles))))
        starts.append(first)
        ends.append(last)
    edges = [np.linspace(ends[i], starts[(i + 1) % 4], 160) for i in range(4)]
    return np.concatenate(arcs + edges)


def main():
    mesh, _, _ = scan.load(ROOT / "scans/neewer-macro-slide-GM-MP2.ply.gz", units="mm")
    section = mesh.section((0, 0, 1), (0, 0, 2.5))
    contours = [entity.discrete(section.vertices)[:, :2] for entity in section.entities]
    slots = [q for q in contours if 17 < np.ptp(q[:, 0]) < 20 and 27 < np.ptp(q[:, 1]) < 29]
    slots.sort(key=lambda q: q[:, 0].min())
    records = []
    for points in slots:
        start = [points[:, 0].min() - 1, points[:, 1].min(), 11.5, 28.0, .36, 3.0]
        fit = least_squares(lambda p: cKDTree(outline(p)).query(points)[0], start,
                            bounds=([start[0] - 3, 7, 8, 26, .25, 1], [start[0] + 3, 9, 15, 30, .5, 5]),
                            diff_step=1e-4, max_nfev=500)
        residuals = cKDTree(outline(fit.x)).query(points)[0]
        records.append({"parameters": dict(zip(("bottom_left_x_mm", "bottom_y_mm", "width_mm", "height_mm", "shear_dx_dy", "corner_radius_mm"), fit.x.tolist())),
                        "residual_p50_mm": float(np.median(residuals)), "residual_p95_mm": float(np.percentile(residuals, 95)),
                        "scan_bounds_mm": [points.min(0).tolist(), points.max(0).tolist()]})
    centers, normals = mesh.triangles_center, mesh.face_normals
    roi = (centers[:, 0] > 40) & (centers[:, 0] < 166) & (centers[:, 1] > 9) & (centers[:, 1] < 35)
    bottom = centers[roi & (centers[:, 2] > -.1) & (centers[:, 2] < .5) & (normals[:, 2] < -.98), 2]
    top = centers[roi & (centers[:, 2] > 3.5) & (centers[:, 2] < 4.8) & (normals[:, 2] > .98), 2]
    result = {"method": "Rounded parallelogram least-squares fits to six independent scan contours at z=2.5 mm; no photo-derived dimensions.",
              "slots": records, "plane_samples": {"bottom_z_mm_p05_p50_p95": np.percentile(bottom, (5, 50, 95)).tolist(),
                                                      "top_z_mm_p05_p50_p95": np.percentile(top, (5, 50, 95)).tolist()},
              "uncertainty": "Provisional scan fits. Triangle spacing and local edge rounding limit the inferred analytic dimensions."}
    section = mesh.section((0, 0, 1), (0, 0, 7.5))
    windows = [e.discrete(section.vertices)[:, :2] for e in section.entities]
    windows = [q for q in windows if 55 < np.ptp(q[:, 0]) < 62 and 27 < np.ptp(q[:, 1]) < 30]
    windows.sort(key=lambda q: q[:, 0].min())
    upper = []
    upper_points = []
    for index, points in enumerate(windows):
        keep = np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-8]
        points = points[keep]
        curve, _ = splprep(points.T, s=len(points) * .075 ** 2, per=True)
        sampled = np.round(np.column_stack(splev(np.linspace(0, 1, 96, endpoint=False), curve)), 3)
        dense = np.column_stack(splev(np.linspace(0, 1, 2000), curve))
        residuals = cKDTree(dense).query(points)[0]
        upper_points.append(sampled.tolist())
        upper.append({"window": index + 1, "smoothing_rms_target_mm": .075, "sample_count": 96,
                      "scan_to_smoothed_outline_p95_mm": float(np.percentile(residuals, 95))})
    result["upper_windows"] = upper
    result["upper_web_scope"] = "Upper end lands and central bridge fitted at z=7.5 mm, represented through z=8.3 mm to stay below the separately modeled moving carriage; classification is scan-supported but internal assembly boundaries remain provisional."
    (ROOT / "references/base-detail-upper-window-points.json").write_text(json.dumps({"z_mm": 7.5, "scan_smoothing_rms_target_mm": .075, "sample_count": 96, "windows": upper_points}, indent=2) + "\n")
    output = ROOT / "references/base-detail-fit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
