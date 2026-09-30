#!/usr/bin/env python3
"""Compare exact STEP section edges across straightened rim cores and blends."""

from pathlib import Path
import argparse
import json
import numpy as np
from build123d import import_step, section, Plane
from import_observed_mesh import sha


def section_profiles(body, tip, tangent, outward):
    origin = np.asarray(tip, float)
    normal = np.asarray(tangent, float)
    normal /= np.linalg.norm(normal)
    outward = np.asarray(outward, float)
    outward /= np.linalg.norm(outward)
    cut = section(body, section_by=Plane(tuple(origin), x_dir=tuple(outward), z_dir=tuple(normal)))
    profiles = []
    for edge in cut.edges():
        points = np.asarray(
            [
                tuple(v)
                for v in edge.positions(
                    np.linspace(0, 1, max(8, int(edge.length / 0.08)))
                )
            ]
        )
        radial = (points - origin) @ outward
        good = (radial > -8) & (radial < 3) & (points[:, 2] > -2) & (points[:, 2] < 7)
        # Preserve edge identity and split each cropped run to avoid false closures.
        indices = np.flatnonzero(good)
        for group in np.split(indices, np.flatnonzero(np.diff(indices) > 1) + 1):
            if len(group) >= 2:
                profiles.append(np.c_[radial[group], points[group, 2]].tolist())
    joined = np.concatenate([np.asarray(p) for p in profiles])
    return {
        "profiles_radial_z": profiles,
        "outward_bulge_from_nominal_crest_mm": float(joined[:, 0].max()),
        "section_z_range_mm": [float(joined[:, 1].min()), float(joined[:, 1].max())],
        "edge_count_in_band": len(profiles),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bodies = {"before": import_step(args.before), "after": import_step(args.after)}
    samples = []
    for x in (2, 10, 20, 27, 29, 31, 34):
        samples.append(("continuous_end", x, [x, 55.73, 3.12], [1, 0, 0], [0, 1, 0]))
    slope = 0.00601854
    for y in (-34, -29, -27, -20, 0, 20, 39, 42, 48):
        samples.append(
            (
                "long_side",
                y,
                [38.54173 + slope * y, y, 1.30],
                [slope, 1, 0],
                [1, -slope, 0],
            )
        )
    slope = 0.21745228
    for x in (17, 19, 24, 30, 35, 37, 39):
        samples.append(
            (
                "split_end",
                x,
                [x, -61.42917 + slope * x, 4.646],
                [1, slope, 0],
                [slope, -1, 0],
            )
        )
    result = {
        "schema": "palm-independent-fold-profiles/v1",
        "before_sha256": sha(args.before),
        "after_sha256": sha(args.after),
        "script_sha256": sha(Path(__file__)),
        "method": "Exact STEP B-rep sections perpendicular to each straight run. Sample individual section edges at approximately 0.08 mm arc spacing. Crop to the bend vicinity without joining disjoint curves. Positive radial coordinate means outward of the nominal crest, demonstrating retained inward curl.",
        "validity": {
            name: {"valid": body.is_valid, "solids": len(body.solids())}
            for name, body in bodies.items()
        },
        "sections": [],
    }
    for name, station, tip, tangent, outward in samples:
        row = {"run": name, "station_mm": station, "nominal_crest": tip}
        for version, body in bodies.items():
            row[version] = section_profiles(body, tip, tangent, outward)
        result["sections"].append(row)
        print(
            name,
            station,
            "bulge before/after",
            row["before"]["outward_bulge_from_nominal_crest_mm"],
            row["after"]["outward_bulge_from_nominal_crest_mm"],
            flush=True,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
