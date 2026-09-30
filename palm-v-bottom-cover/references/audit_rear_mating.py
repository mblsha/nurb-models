"""Probe reopened rear/body STEP boundaries across continuous seating bands."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from build123d import Axis, import_step
from audit_step_geometry import intersections


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rear", type=Path, required=True)
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--poses", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--contact-only",
        action="store_true",
        help="Skip the expensive global Boolean and report overlap as untested",
    )
    args = parser.parse_args()
    rear = import_step(args.rear)
    body = import_step(args.body)
    pose = json.loads(args.poses.read_text())["rear_cover"]
    # Probe in the back-cover frame, independently reversing the assembly pose.
    body = body.translate((0, 0, -0.8))
    body = body.translate(tuple(-v for v in pose["translation_mm"]))
    body = body.rotate(Axis.X, -pose["rotation_x_degrees"])
    bands = {
        "right side": [
            (x, y) for x in (35.0, 36.5, 37.5) for y in np.linspace(-33, 43, 17)
        ],
        "left side": [
            (-x, y) for x in (35.0, 36.5, 37.5) for y in np.linspace(-33, 43, 17)
        ],
        "upper return": [
            (x, y) for x in np.linspace(-29, 29, 17) for y in (52.0, 53.5, 54.5)
        ],
        "right lower return": [
            (x, y) for x in np.linspace(19, 34, 9) for y in (-55.0, -54.0)
        ],
        "left lower return": [
            (-x, y) for x in np.linspace(19, 34, 9) for y in (-55.0, -54.0)
        ],
    }
    reports = {}
    for name, points in bands.items():
        samples = []
        for x, y in points:
            rh = intersections(rear, (float(x), float(y), 0.0), (0.0, 0.0, 1.0))
            bh = intersections(body, (float(x), float(y), 0.0), (0.0, 0.0, 1.0))
            samples.append(
                {
                    "xy_back_frame_mm": [float(x), float(y)],
                    "rear_hits_z_mm": [r[0] for r in rh],
                    "body_hits_z_mm": [r[0] for r in bh],
                    "vertical_gap_mm": bh[0][0] - rh[-1][0] if rh and bh else None,
                }
            )
        gaps = [
            r["vertical_gap_mm"] for r in samples if r["vertical_gap_mm"] is not None
        ]
        reports[name] = {
            "samples": samples,
            "missing_material_samples": sum(
                r["vertical_gap_mm"] is None for r in samples
            ),
            "outside_rear_footprint_samples": sum(
                not r["rear_hits_z_mm"] for r in samples
            ),
            "missing_body_under_existing_rear_samples": sum(
                bool(r["rear_hits_z_mm"]) and not r["body_hits_z_mm"] for r in samples
            ),
            "gap_range_mm": [min(gaps), max(gaps)] if gaps else None,
            "max_absolute_gap_mm": max(abs(g) for g in gaps) if gaps else None,
            "contact_samples_within_0_01_mm": sum(abs(g) < 0.01 for g in gaps),
        }
        print(
            name, {k: v for k, v in reports[name].items() if k != "samples"}, flush=True
        )
    overlap = None if args.contact_only else rear.intersect(body)
    overlap_solids = list(overlap.solids()) if overlap is not None else []
    signed_volumes = [float(s.volume) for s in overlap_solids]
    report = {
        "method": "Reopened STEP boundaries, fixed assembly pose, independent Z-ray grid in back frame; positive gap separates rear inner face and body lower face. Bands must be reviewed against intended seat extents. OCCT Common is retained as a signed diagnostic and cannot alone establish physical overlap when contact faces coincide.",
        "audit_script_sha256": sha(Path(__file__)),
        "source_sha256": {
            "rear": sha(args.rear),
            "body": sha(args.body),
            "poses": sha(args.poses),
        },
        "rear_valid_single_solid": rear.is_valid and len(rear.solids()) == 1,
        "body_valid_single_solid": body.is_valid and len(body.solids()) == 1,
        "intersection_tested": not args.contact_only,
        "intersection_solid_count": None if args.contact_only else len(overlap_solids),
        "intersection_signed_volumes_mm3": None if args.contact_only else signed_volumes,
        "intersection_solid_bounds_mm": None if args.contact_only else [
            {"min": [s.bounding_box().min.X, s.bounding_box().min.Y, s.bounding_box().min.Z], "max": [s.bounding_box().max.X, s.bounding_box().max.Y, s.bounding_box().max.Z]}
            for s in overlap_solids
        ],
        "intersection_has_negative_signed_volume": None if args.contact_only else any(v < 0 for v in signed_volumes),
        "intersection_interpretation": (
            "OCCT Common returned a negative signed-volume solid, so its absolute volume cannot be interpreted as a physical overlap. Inspect independent solid-occupancy rays and the exact mating bands."
            if any(v < 0 for v in signed_volumes)
            else "No negative signed-volume Common solids; inspect any positive overlap and named contact bands."
        ) if not args.contact_only else "Global Boolean skipped; contact bands only.",
        "intersection_volume_mm3": None
        if args.contact_only
        else sum(abs(s.volume) for s in overlap_solids),
        "bands": reports,
        "physical_fit_verified": False,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "bands"}, indent=2))
    for name, data in reports.items():
        print(name, {k: v for k, v in data.items() if k != "samples"})


if __name__ == "__main__":
    main()
