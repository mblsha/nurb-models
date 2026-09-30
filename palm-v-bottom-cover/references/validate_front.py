"""Check the reopened front sheet and visible component interfaces."""

from pathlib import Path
import json
import hashlib
from build123d import import_step, Vertex
from audit_step_geometry import intersections

ROOT = Path(__file__).resolve().parents[1]
front = import_step(ROOT / "build/palm_v_front_cover.step")
probes = []
for x, y in [
    (0, 52),
    (20, 52),
    (32, 40),
    (32, 0),
    (32, -30),
    (34, -44),
    (38, 20),
    (7, -36),
]:
    hits = intersections(front, (x, y, 0), (0, 0, 1), -10, 10)
    if len(hits) != 2:
        raise ValueError(f"Expected one front sheet interval at{x, y}: {hits}")
    _, p, n = hits[-1]
    normal_hits = intersections(front, p, n, -2, 2)
    gauge = min(abs(h[0]) for h in normal_hits if abs(h[0]) > 1e-4)
    mirror = Vertex(-p[0], p[1], p[2]).distance_to(front.shells()[0])
    if abs(gauge - 0.65) > 0.01 or mirror > 0.001:
        raise ValueError("Front gauge or reflection probe failed")
    probes.append({"x": x, "y": y, "normal_gauge": gauge, "mirror_error": mirror})
for x, y in [(0, 0), (0, -30), (13, -44), (26.2, -42), (0, -46.3)]:
    if intersections(front, (x, y, 0), (0, 0, 1), -10, 10):
        raise ValueError(f"Opening is blocked at{x, y}")
results = {
    "valid": front.is_valid,
    "solids": len(front.solids()),
    "probes": probes,
    "openings": "display, four keys and scroll checked",
    "front_step_sha256": hashlib.sha256(
        (ROOT / "build/palm_v_front_cover.step").read_bytes()
    ).hexdigest(),
}
(ROOT / "build/front-validation.json").write_text(json.dumps(results, indent=2) + "\n")
print(results)
