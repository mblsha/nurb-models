"""Audit the nominal broad-plane and bilateral surface on a reopened rear STEP."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from build123d import import_step
from OCP.BRep import BRep_Tool


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--rear", type=Path, default=Path("build/palm_v_bottom_cover.step"))
parser.add_argument("--output", type=Path, default=Path("build/analysis/planar-field/exact-plane-report.json"))
args = parser.parse_args()
shape = import_step(args.rear)
if not shape.is_valid or len(shape.solids()) != 1:
    raise ValueError("Rear STEP must be one valid solid")

faces = sorted(
    (face for face in shape.faces() if face.area > 4000 and face.geom_type.name == "BSPLINE"),
    key=lambda face: face.bounding_box().max.X,
)
if len(faces) != 2:
    raise ValueError(f"Expected two mirrored broad exterior faces, found {len(faces)}")
left, right = (BRep_Tool.Surface_s(face.wrapped) for face in faces)
plane_z = -0.30
regions = {}
for name, coords in (
    ("lower_field", [(x, y) for x in np.arange(0, 35.1, .5) for y in np.arange(-35, 2.1, .5)]),
    ("upper_field", [(x, y) for x in np.arange(0, 25.1, .5) for y in np.arange(35, 50.1, .5)]),
    ("lateral_field_at_feature_y", [(x, y) for x in np.arange(35, 37.1, .5) for y in np.arange(8, 30.1, .5)]),
):
    errors = np.array([abs(right.Value(float(x), float(y)).Z() - plane_z) for x, y in coords])
    regions[name] = {
        "points": len(coords),
        "max_abs_plane_error_mm": float(errors.max()),
        "rms_plane_error_mm": float(np.sqrt(np.mean(errors * errors))),
    }
mirror_errors = []
for x in np.arange(0, 37.1, 1):
    for y in np.arange(-35, 50.1, 1):
        a = left.Value(float(x), float(y))
        b = right.Value(float(x), float(y))
        mirror_errors.append(max(abs(a.X() + b.X()), abs(a.Y() - b.Y()), abs(a.Z() - b.Z())))
report = {
    "step_sha256": hashlib.sha256(args.rear.read_bytes()).hexdigest(),
    "valid": True,
    "solids": 1,
    "faces": len(shape.faces()),
    "nominal_plane_z_mm": plane_z,
    "method": "Evaluate reopened STEP B-spline exterior surfaces at broad-field UV locations away from the local center form and perimeter bends.",
    "regions": regions,
    "mirror_surface": {
        "points": len(mirror_errors),
        "max_coordinate_error_mm": float(max(mirror_errors)),
        "rms_coordinate_error_mm": float(np.sqrt(np.mean(np.square(mirror_errors)))),
    },
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2), flush=True)
if max(region["max_abs_plane_error_mm"] for region in regions.values()) > 1e-5:
    raise SystemExit("Broad field departed from nominal plane")
