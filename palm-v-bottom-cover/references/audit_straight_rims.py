"""Independently inspect actual STEP boundaries near scan-derived rim lines."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from build123d import Vertex, import_step


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", type=Path)
    parser.add_argument("fit", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    shape = import_step(args.step)
    bands = json.loads(args.fit.read_text())["bands"]
    runs = []
    far = bands["continuous_end"]
    targets = np.array(
        [
            [x, far["plan_constant_median_mm"], far["level_z_median_mm"]]
            for x in np.linspace(-28, 28, 29)
        ]
    )
    runs.append(("continuous_end", targets))
    side = bands["long_sides"]
    a, b = side["plan_line_intercept_slope"]
    near = bands["split_end"]
    c, d = near["plan_line_intercept_slope"]
    for sign in (-1, 1):
        runs.append(
            (
                f"long_side_{sign:+d}",
                np.array(
                    [
                        [sign * (a + b * y), y, side["level_z_median_mm"]]
                        for y in np.linspace(-28, 40, 29)
                    ]
                ),
            )
        )
        runs.append(
            (
                f"split_end_{sign:+d}",
                np.array(
                    [
                        [sign * x, c + d * x, near["level_z_median_mm"]]
                        for x in np.linspace(20, 34, 21)
                    ]
                ),
            )
        )
    result = {
        "step_sha256": hashlib.sha256(args.step.read_bytes()).hexdigest(),
        "method": "Nearest actual reopened STEP boundary points to independent scan-derived target lines, then orthogonal line fit. Only edges tangent within 37 degrees of the run direction qualify; this excludes transverse patch seams. Core runs exclude corner transitions.",
        "runs": [],
    }
    edges = list(shape.edges())
    for name, targets in runs:
        points, distances = [], []
        run_direction = targets[-1] - targets[0]
        run_direction /= np.linalg.norm(run_direction)
        for target in targets:
            probe = Vertex(*target)
            candidates = []
            for edge in edges:
                candidate = probe.distance_to_with_closest_points(edge)
                tangent = np.array(tuple(edge.tangent_at(candidate[2])))
                if abs(tangent @ run_direction) > 0.8:
                    candidates.append(candidate)
            dist, _, nearest = min(candidates, key=lambda v: v[0])
            points.append(list(nearest))
            distances.append(dist)
        points = np.array(points)
        center = np.mean(points, axis=0)
        _, _, axes = np.linalg.svd(points - center, full_matrices=False)
        direction = axes[0]
        residual = np.linalg.norm(
            (points - center) - np.outer((points - center) @ direction, direction),
            axis=1,
        )
        result["runs"].append(
            {
                "name": name,
                "sample_count": len(points),
                "line_max_residual_mm": float(max(residual)),
                "height_span_mm": float(np.ptp(points[:, 2])),
                "height_mean_mm": float(np.mean(points[:, 2])),
                "target_distance_p95_mm": float(np.quantile(distances, 0.95)),
                "target_distance_max_mm": float(max(distances)),
                "line_direction": direction.tolist(),
                "actual_boundary_points_mm": points.tolist(),
            }
        )
    result["all_core_runs_straight_and_level_within_0_01_mm"] = all(
        r["line_max_residual_mm"] < 0.01 and r["height_span_mm"] < 0.01
        for r in result["runs"]
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                **result,
                "runs": [
                    {k: v for k, v in r.items() if k != "actual_boundary_points_mm"}
                    for r in result["runs"]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
