"""Check frozen assembly components against the final shared-interface body."""

from pathlib import Path
import argparse
import hashlib
import json
from build123d import import_step, Axis

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--body-step", type=Path, default=ROOT / "build/palm_v_body.step")
parser.add_argument("--output", type=Path, default=ROOT / "build/assembly-front-interface-checks.json")
args = parser.parse_args()
body = import_step(args.body_step).translate((0, 0, -0.8))
paths = {
    name: ROOT / "build" / f"{name}.step"
    for name in [
        "palm_v_front_cover",
        "palm_v_display",
        "palm_v_scroll_button",
        "palm_v_button",
    ]
}
parts = {name: import_step(path) for name, path in paths.items()}
rocker = (
    parts.pop("palm_v_scroll_button")
    .rotate(Axis((0, -46.3, 0), (1, 0, 0)), 8.0)
    .translate((0, 0, 3.9))
)
key = parts.pop("palm_v_button")
parts["scroll_rocker"] = rocker
for x, y, z, label in [
    (-26.2, -42, 3.8, "left_outer_key"),
    (-13, -44, 4.2, "left_inner_key"),
    (13, -44, 4.2, "right_inner_key"),
    (26.2, -42, 3.8, "right_outer_key"),
]:
    parts[label] = key.translate((x, y, z))
results = {}
for name, part in parts.items():
    common = body.intersect(part)
    volume = sum(abs(s.volume) for s in common.solids()) if common is not None else 0
    results[name] = {
        "overlap_mm3": volume,
        "distance_mm": body.distance_to(part),
        "component_valid": part.is_valid,
    }
    print(name, results[name], flush=True)
result = {
    "body_sha256": hashlib.sha256(args.body_step.read_bytes()).hexdigest(),
    "body_valid": body.is_valid,
    "body_solids": len(body.solids()),
    "body_translation_mm": [0, 0, -0.8],
    "source_sha256": {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in paths.items()
    },
    "pairs": results,
    "zero_overlap_at_1e_5_mm3": all(v["overlap_mm3"] < 1e-5 for v in results.values()),
    "note": "Rear contact is checked separately against exact master surfaces. This check detects material conflicts with the independently modeled front/display/keys.",
}
args.output.write_text(
    json.dumps(result, indent=2) + "\n"
)
if not result["zero_overlap_at_1e_5_mm3"]:
    raise ValueError("Assembly body conflicts with front components")
