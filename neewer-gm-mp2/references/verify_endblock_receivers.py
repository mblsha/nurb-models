"""Verify the provisional endblock receiver envelopes in both foot positions."""

import hashlib
import json
from pathlib import Path

from nurb.builder import build


ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "parts/neewer_macro_slide_gm_mp2.py"


def overlap(first, second):
    common = first.intersect(second)
    if common is None:
        return 0.0
    return float(common.volume) if hasattr(common, "volume") else sum(float(s.volume) for s in common)


def main():
    rows = []
    for deployed in (False, True):
        shape, _, _ = build(PART, overrides={"arca_detent": 0, "carriage_position_mm": 70.35,
                                            "feet_deployed": deployed})
        components = {item.label: item.solid for item in shape._nurb_scene.components}
        end_blocks = components["end blocks"]
        pairs = {name: overlap(end_blocks, components[name])
                 for name in ("front guide rod", "rear guide rod", "lead screw", "large focus knob")}
        rows.append({"feet_deployed": deployed, "assembly_valid": bool(shape.is_valid),
                     "all_components_valid": all(s.is_valid for s in components.values()),
                     "endblock_solid_count": len(end_blocks.solids()),
                     "shaft_endblock_overlap_mm3": pairs})
    result = {
        "part_sha256": hashlib.sha256(PART.read_bytes()).hexdigest(),
        "scope": "Concealed receiver accommodation for existing placed shaft envelopes, not recovered manufactured bearings or threads.",
        "provisional_radial_gap_mm": 0.05,
        "blind_guide_rod_seats_x_mm": [6.0, 200.5],
        "blind_right_screw_seat_x_mm": 204.0,
        "screw_axis_yz_mm": [22.0, 17.58],
        "knob_axis_yz_mm": [22.1955, 17.3643],
        "axis_note": "The independently scan-fitted axes are retained. No coaxial bearing standard is inferred.",
        "poses": rows,
    }
    result["accepted"] = all(row["assembly_valid"] and row["all_components_valid"]
                             and row["endblock_solid_count"] == 2
                             and max(row["shaft_endblock_overlap_mm3"].values()) < 1e-6
                             for row in rows)
    (ROOT / "references/endblock-receiver-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    if not result["accepted"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
