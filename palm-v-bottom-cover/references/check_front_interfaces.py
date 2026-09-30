"""Check that the visible front inserts do not overlap the metal skin."""

from pathlib import Path
import json
from build123d import import_step, Axis

ROOT = Path(__file__).resolve().parents[1]
front = import_step(ROOT / "build/palm_v_front_cover.step")
display = import_step(ROOT / "build/palm_v_display.step")
key = import_step(ROOT / "build/palm_v_button.step")
rocker = (
    import_step(ROOT / "build/palm_v_scroll_button.step")
    .rotate(Axis((0, -46.3, 0), (1, 0, 0)), 8.0)
    .translate((0, 0, 3.9))
)
parts = {"display": display, "rocker": rocker}
for x, y, z, label in [
    (-26.2, -42, 3.8, "left_outer"),
    (-13, -44, 4.2, "left_inner"),
    (13, -44, 4.2, "right_inner"),
    (26.2, -42, 3.8, "right_outer"),
]:
    parts[label] = key.translate((x, y, z))
results = {}
for label, p in parts.items():
    common = front.intersect(p)
    overlap = sum(abs(s.volume) for s in common.solids()) if common is not None else 0
    results[label] = {
        "overlap_mm3": overlap,
        "minimum_clearance_mm": front.distance_to(p),
    }
    print(label, results[label], flush=True)
(ROOT / "build/front-interface-checks.json").write_text(
    json.dumps(results, indent=2) + "\n"
)
if any(p["overlap_mm3"] > 1e-5 for p in results.values()):
    raise ValueError("Front insert overlaps metal")
