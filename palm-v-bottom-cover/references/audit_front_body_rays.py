"""Probe final body and front sheet as independently reopened STEP intervals."""

from pathlib import Path
import argparse
import json
import hashlib
from build123d import import_step
from audit_step_geometry import intersections

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--body-step", type=Path, required=True)
args = parser.parse_args()
body = import_step(args.body_step).translate((0, 0, -0.8))
front = import_step(ROOT / "build/palm_v_front_cover.step")
rows = []
for x in [0.2, 20.2, 31.8, 35.8, 38.2]:
    for y in [-52.2, -48.2, -42.2, -35.2, -10.2, 20.2, 40.2, 50.2, 55.2, 57.2]:
        values = {}
        for label, shape in [("body", body), ("front", front)]:
            values[label] = [
                h[0] for h in intersections(shape, (x, y, 0), (0, 0, 1), -15, 15)
            ]
        if any(len(v) % 2 for v in values.values()):
            raise ValueError("Odd interval count at probe")
        overlaps = []
        for a, b in zip(values["body"][::2], values["body"][1::2]):
            for c, d in zip(values["front"][::2], values["front"][1::2]):
                if min(b, d) - max(a, c) > 1e-5:
                    overlaps.append(min(b, d) - max(a, c))
        rows.append(
            {
                "x": x,
                "y": y,
                "interval_endpoints": values,
                "overlap_lengths_mm": overlaps,
            }
        )
result = {
    "body_sha256": hashlib.sha256(args.body_step.read_bytes()).hexdigest(),
    "front_sha256": hashlib.sha256(
        (ROOT / "build/palm_v_front_cover.step").read_bytes()
    ).hexdigest(),
    "probes": rows,
    "overlapping_probes": [p for p in rows if p["overlap_lengths_mm"]],
    "scope": "50 independent vertical section rays at broad/side/end positions. This is sampled evidence, not a proof of global clearance.",
}
(ROOT / "build/front-body-ray-audit.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print("ray probes", len(rows), "overlaps", result["overlapping_probes"], flush=True)
