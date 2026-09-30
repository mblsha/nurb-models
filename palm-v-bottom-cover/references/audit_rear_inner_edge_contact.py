"""Read-only rear/body contact audit just inside the actual +Y metal inner edge."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from build123d import Axis, import_step


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument("--rear", type=Path)
parser.add_argument("--body", type=Path)
parser.add_argument("--poses", type=Path)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
args.rear = args.rear or args.project / "build/palm_v_bottom_cover.step"
args.body = args.body or args.project / "build/palm_v_body.step"
args.poses = args.poses or args.project / "references/palm-assembly-poses.json"
args.output = args.output or args.project / "build/rear-inner-edge-contact-audit.json"
sys.path.insert(0, str(args.project / "references"))
from audit_step_geometry import intersections  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


rear = import_step(args.rear)
body = import_step(args.body)
if not rear.is_valid or len(rear.solids()) != 1:
    raise ValueError("Rear STEP must be one valid solid")
if not body.is_valid or len(body.solids()) != 1:
    raise ValueError("Body STEP must be one valid solid")
pose = json.loads(args.poses.read_text())["rear_cover"]
body = body.translate((0, 0, -0.8))
body = body.translate(tuple(-v for v in pose["translation_mm"]))
body = body.rotate(Axis.X, -pose["rotation_x_degrees"])


# In this fixed topology, the positive-X inner offset edges are the +Y core
# crest and its continuous corner. Select geometrically rather than by edge ID.
core = []
corner = []
for edge in rear.edges():
    b = edge.bounding_box()
    if -0.01 < b.min.X < 0.01 and 27.9 < b.max.X < 28.1 and 55 < b.min.Y < 55.2 and 3 < b.min.Z < 3.3 and 27 < edge.length < 29:
        core.append(edge)
    if 27.9 < b.min.X < 28.1 and b.max.X > 37 and b.min.Y > 54.2 and 55 < b.max.Y < 55.2 and 3 < b.max.Z < 3.3 and edge.length > 10:
        corner.append(edge)
if len(core) != 1 or len(corner) != 1:
    raise ValueError(f"Could not identify +Y inner perimeter: core={len(core)}, corner={len(corner)}")
core_points = np.array([tuple(core[0].position_at(t)) for t in np.linspace(0, 1, 1001)])
corner_points = np.array([tuple(corner[0].position_at(t)) for t in np.linspace(0, 1, 2001)])
corner_points = corner_points[np.argsort(corner_points[:, 0])]


xs = [0, 5, 10, 15, 20, 25, 28, 29, 30, 31, 31.9, 32.1, 32.5, 33, 33.5, 34, 34.5, 35]
insets = [0.03, 0.15, 0.3]


def occupied_intervals(shape, hits, x, y):
    zs = sorted(set(hits))
    return [
        [lo, hi]
        for lo, hi in zip(zs[:-1], zs[1:])
        if hi - lo > 1e-5 and shape.is_inside((x, y, (lo + hi) / 2), 1e-9)
    ]


rows = []
for sign in (-1, 1):
    for x0 in xs:
        if x0 == 0 and sign == -1:
            continue
        edge_y = float(np.median(core_points[:, 1])) if x0 <= 28 else float(np.interp(x0, corner_points[:, 0], corner_points[:, 1]))
        for inset in insets:
            x = sign * x0
            y = edge_y - inset  # inside the actual inner face, never on the free cut edge
            rear_hits = [float(h[0]) for h in intersections(rear, (x, y, 0), (0, 0, 1))]
            body_hits = [float(h[0]) for h in intersections(body, (x, y, 0), (0, 0, 1))]
            rear_intervals = occupied_intervals(rear, rear_hits, x, y)
            body_intervals = occupied_intervals(body, body_hits, x, y)
            if not rear_intervals or not body_intervals:
                status = "invalid_or_missing_interval"
                gap = None
            else:
                gaps = [body_lo - rear_hi for _, rear_hi in rear_intervals for body_lo, _ in body_intervals]
                gap = min(gaps, key=abs)
                overlap = max(max(0.0, min(rear_hi, body_hi) - max(rear_lo, body_lo)) for rear_lo, rear_hi in rear_intervals for body_lo, body_hi in body_intervals)
                status = "penetration" if overlap > 0.01 else "contact" if abs(gap) <= 0.01 else "gap" if gap > 0.01 else "penetration"
            rows.append({"x_mm": x, "y_inner_edge_mm": edge_y, "inset_mm": inset, "y_probe_mm": y, "rear_hits_z_mm": rear_hits, "body_hits_z_mm": body_hits, "rear_inside_intervals_z_mm": rear_intervals, "body_inside_intervals_z_mm": body_intervals, "signed_gap_mm": gap, "status": status})
failures = [r for r in rows if r["status"] != "contact"]
report = {
    "method": "Reopened STEP Z-ray intervals 0.03, 0.15, and 0.30 mm inward of the actual rear inner-offset +Y boundary at symmetric X stations, in the rear-cover assembly frame. The free cut edge and exterior upturned lip are excluded. Contact means a metal upper boundary meets a plastic lower boundary within ±0.01 mm with no interval overlap above 0.01 mm; the folded corner can have multiple occupied intervals. This tests the intended +Y seat, not the entire perimeter or global Boolean overlap.",
    "source_sha256": {"rear": sha(args.rear), "body": sha(args.body), "poses": sha(args.poses)},
    "rays_attempted": len(rows),
    "contacts_within_0_01_mm": len(rows) - len(failures),
    "failures": failures,
    "rows": rows,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k not in ("rows", "failures")}, indent=2))
print("failure_count", len(failures))
for row in failures[:40]:
    print("fail", row["x_mm"], round(row["y_probe_mm"], 3), row["inset_mm"], row["status"], None if row["signed_gap_mm"] is None else round(row["signed_gap_mm"], 4))
if failures:
    raise SystemExit(1)
