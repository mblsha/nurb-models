"""Verify the provisional folding feet against a current assembly build."""
from pathlib import Path
import argparse
import hashlib
import inspect
import json
import sys
import numpy as np
from nurb import builder
from build123d import Vector, Vertex

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from neewer_feet import folded_foot, foot_at_angle, foot_swing_clearance, opposite_foot


def volume_intersection(first, second):
    common = first & second
    return 0.0 if common is None else float(common.volume)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=ROOT / "parts/neewer_macro_slide_gm_mp2.py")
    parser.add_argument("--scan-travel", type=float, default=70.35)
    args = parser.parse_args()
    shape, _, _ = builder.build(args.model, overrides={"arca_detent": 0, "carriage_position_mm": args.scan_travel})
    found = {item.label: item.solid for item in shape._nurb_scene.components}
    cutter = foot_swing_clearance()
    stationary = {name: found[name] - cutter for name in ("bottom Arca plate", "end blocks")}
    # Reconstruct the measured end blocks before their foot accommodation. The
    # supplied assembly may already contain that subtraction, so intersecting
    # its finished end blocks would incorrectly report no removed material.
    part_function = inspect.unwrap(builder.load(args.model))
    end_block = part_function.__globals__["_detailed_end_block"]
    original_ends = end_block(6.0, 22.10675) + end_block(200.5, 22.10675)
    foot = folded_foot()
    rows = []
    for angle in range(66):
        left = foot_at_angle(foot, float(angle))
        right = opposite_foot(left)
        contacts = {f"{side}/{name}": volume_intersection(leg, solid)
                    for side, leg in (("left", left), ("right", right))
                    for name, solid in stationary.items()}
        rows.append({"angle_deg": angle, "valid": bool(left.is_valid and right.is_valid),
                     "maximum_frame_overlap_mm3": max(contacts.values()),
                     "volume_error_mm3": abs(left.volume - foot.volume)})
    flank_errors = {}
    stations = [5, 6, 7, 8, 9, 9.74, 32.01, 40, 100, 174.99, 197.76, 198, 199, 200, 202]
    for side, start, end in (("left", (3.15, 1.75), (5.1, 3.85)), ("right", (41.05, 1.75), (39.1, 3.85))):
        flank_errors[side] = max(Vertex(x, y, z).distance_to(stationary["bottom Arca plate"])
                                 for x in stations for y, z in np.linspace(start, end, 21))
    # All removed end-block material is below the fastener seats. Quantify the
    # support separation from their lowest modeled floor rather than treating
    # the original filleted exterior as a rectangular wall-thickness estimate.
    removed_end = original_ends & cutter
    removed_top = float(removed_end.bounding_box().max.Z)
    seat_separations = {f"{end}-{y}": Vertex(x, y, 21.8).distance_to(removed_end)
                        for end, x in (("left", 5.6), ("right", 201.0)) for y in (12.1, 32.1)}
    moving = [solid for name, solid in found.items() if name in ("sliding carriage", "rotary base", "fixed top Arca clamp", "movable top Arca jaw", "clamp knob")]
    moving_vertical_gap = min(float(solid.bounding_box().min.Z) for solid in moving) - 4.42
    result = {"scope": "Prospective current assembly with the same static accommodation cutter subtracted from base and end blocks in every foot state. Hidden hinge and deployment remain inferred, not physically qualified.",
              "model_filename": args.model.name, "model_sha256": hashlib.sha256(args.model.read_bytes()).hexdigest(),
              "helper_sha256": hashlib.sha256((ROOT / "neewer_feet.py").read_bytes()).hexdigest(),
              "folded_envelope": {"x_left_mm": [10.1, 31.5], "x_right_mm": [175.5, 196.9], "y_mm": [5.15, 39.05], "z_mm": [.02, 4.42],
                                  "lower_side_radius_mm": 4.4, "side_inset_from_scan_mm": .15},
              "inferences": {"left_pivot_mm": [10.1, 22.1, 4.42], "right_pivot_mm": [196.9, 22.1, 4.42],
                             "axis": "Y", "deployed_angle_deg": 65, "source": "Bay seams constrain folded placement. Hidden pivot and deployment angle are provisional interpretations of scan continuity and the official product photograph."},
              "static_frame_valid": all(solid.is_valid for solid in stationary.values()),
              "removed_end_block_material_mm3": float(removed_end.volume), "uppermost_removed_end_block_material_z_mm": removed_top,
              "fastener_seat_floor_z_mm": 21.8, "minimum_vertical_support_below_seat_mm": 21.8 - removed_top,
              "seat_floor_to_accommodation_distances_mm": seat_separations,
              "minimum_vertical_gap_to_moving_assembly_mm": moving_vertical_gap,
              "arca_flank_maximum_error_mm": flank_errors, "tested_angles": rows,
              "accommodation_method": "Exact continuous rotational sweep of every foot boundary face, fused with the folded solid; no sampled-angle Boolean approximation."}
    result["accepted"] = (result["static_frame_valid"] and moving_vertical_gap > 0 and max(flank_errors.values()) < 1e-6
                          and all(row["valid"] and row["maximum_frame_overlap_mm3"] < 1e-6 and row["volume_error_mm3"] < 1e-6 for row in rows))
    (ROOT / "references/foot-detail-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "tested_angles"}, indent=2))
    if not result["accepted"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
