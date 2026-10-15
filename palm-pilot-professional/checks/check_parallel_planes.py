"""Check actual native principal faces, not merely the construction constants.

Run with the project's Python environment from any directory. This builds the
closed native components once; optional outputs are disposable audit artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from math import atan2, degrees
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build123d import Axis, GeomType, export_brep
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
import palm_pilot_geometry as geometry

# The unchanged front datum defines nominal design intent. Offsets are local mm.
PRINCIPAL_FACES = {
    "Front casing": {"front exterior": 18.86, "front seam": geometry.FRONT_SEAM_Z},
    "Rear casing": {"rear exterior": 1.8, "rear seam": geometry.REAR_SEAM_Z},
    "Display": {"screen": 17.1708},
    "Battery cover": {"rear exterior": 1.8, "backing": 4.85},
    "Memory cover": {"rear exterior": 1.8, "backing": 4.4},
}
ANGLE_TOLERANCE_DEG = 1e-7
OFFSET_TOLERANCE_MM = 1e-6


# Default closed-body inventory includes every tiny socket-corner fragment.
# Require the complete inventory so a tilted or nonplanar patch cannot vanish
# through a normal-based selector while a large principal face still passes.
MIDDLE_SEAMS = {
    "Front casing": [("front reveal boundary", geometry.FRONT_SEAM_Z, 1)],
    "Rear casing": [("rear reveal boundary", geometry.REAR_SEAM_Z, 4),
                    ("recessed dock backing boundary", geometry.FRONT_SEAM_Z, 1)],
}


def check_middle_seams(pieces):
    normal = Axis.Z.located(geometry.BODY_DATUM).direction
    inverse = geometry.BODY_DATUM.inverse()
    groups = []
    errors = []
    for name, shape in pieces:
        for feature, offset, expected_count in MIDDLE_SEAMS.get(name, []):
            # Deliberately do not filter by the desired face normal. A small
            # tilted plane must be measured and rejected, not silently dropped.
            candidates = [face for face in shape.faces()
                          if face.geom_type == GeomType.PLANE
                          and abs(face.center().dot(normal) - offset) < .2]
            if len(candidates) != expected_count:
                errors.append(f"{name}: {feature} requires all {expected_count} planar fragments, found {len(candidates)}")
            faces = []
            for index, face in enumerate(candidates):
                actual_normal = face.normal_at().normalized()
                angle = degrees(atan2(actual_normal.cross(normal).length, abs(actual_normal.dot(normal))))
                edges = []
                for edge_index, edge in enumerate(face.edges()):
                    local = inverse * edge
                    bounds = Bnd_Box()
                    # Curve extrema, not just endpoints or a finite sample.
                    # OCCT may expand a spline bound by its 1e-7 mm confusion.
                    BRepBndLib.AddOptimal_s(local.wrapped, bounds, False, False)
                    _, _, z_min, _, _, z_max = bounds.Get()
                    edges.append({"edge": edge_index, "curve": edge.geom_type.name,
                                  "length_mm": edge.length, "normal_min_mm": z_min,
                                  "normal_max_mm": z_max,
                                  "normal_range_bound_mm": z_max - z_min})
                    if max(abs(z_min - offset), abs(z_max - offset)) > OFFSET_TOLERANCE_MM:
                        errors.append(f"{name}: {feature} fragment {index} edge {edge_index} leaves its parallel plane")
                if angle > ANGLE_TOLERANCE_DEG:
                    errors.append(f"{name}: {feature} fragment {index} tilts by {angle:.9g} degrees")
                faces.append({"fragment": index, "area_mm2": face.area,
                              "angle_deg": angle, "edges": edges})
            groups.append({"component": name, "feature": feature, "offset_mm": offset,
                           "expected_fragments": expected_count, "fragments": faces,
                           "edge_count": sum(len(face["edges"]) for face in faces)})
    for name in MIDDLE_SEAMS:
        if not any(component == name for component, _ in pieces):
            errors.append(f"Missing {name} for complete middle-seam verification")
    edges = [edge for group in groups for face in group["fragments"] for edge in face["edges"]]
    angles = [face["angle_deg"] for group in groups for face in group["fragments"]]
    return {"passed": not errors, "groups": groups, "edge_count": len(edges),
            "max_angle_deg": max(angles, default=None),
            "max_normal_range_bound_mm": max((edge["normal_range_bound_mm"] for edge in edges), default=None),
            "method": "OCCT native trimmed-curve extrema in BODY_DATUM; no tessellation or endpoint-only sampling",
            "errors": errors}


def check(pieces):
    normal = Axis.Z.located(geometry.BODY_DATUM).direction
    components = {}
    faces = []
    errors = []
    for name, shape in pieces:
        info = {"valid": shape.is_valid, "solids": len(shape.solids()), "volume_mm3": shape.volume}
        components[name] = info
        if not info["valid"] or info["solids"] != 1 or info["volume_mm3"] <= 0:
            errors.append(f"{name} must be one valid positive solid")
        for feature, offset in PRINCIPAL_FACES.get(name, {}).items():
            candidates = [
                face for face in shape.faces()
                if face.geom_type == GeomType.PLANE and face.area > 100
                and abs(face.normal_at().dot(normal)) > .98
                and abs(face.center().dot(normal) - offset) < .6
            ]
            if not candidates:
                errors.append(f"{name}: missing actual planar {feature} face near {offset} mm")
                continue
            face = min(candidates, key=lambda item: (abs(item.center().dot(normal) - offset), -item.area))
            actual_normal = face.normal_at().normalized()
            angle = degrees(atan2(actual_normal.cross(normal).length, abs(actual_normal.dot(normal))))
            actual_offset = face.center().dot(normal)
            record = {"component": name, "feature": feature, "normal": list(actual_normal), "area_mm2": face.area,
                      "angle_deg": angle, "offset_mm": actual_offset, "expected_offset_mm": offset}
            faces.append(record)
            if angle > ANGLE_TOLERANCE_DEG or abs(actual_offset - offset) > OFFSET_TOLERANCE_MM:
                errors.append(f"{name}: {feature} diverges by {angle:.9g} degrees, offset {actual_offset:.9g} mm")
    slides = {}
    for name, values in [("battery", {"x": -60.0}), ("memory", {"y": 60.0})]:
        translation = geometry.cover_slide(**values).position
        normal_motion = abs(translation.dot(normal))
        slides[name] = {"translation_at_60mm": list(translation), "normal_motion_mm": normal_motion}
        if normal_motion > 1e-10 or abs(translation.length - 60.0) > 1e-10:
            errors.append(f"{name}: slide must be rigid 60 mm motion within the body plane")
    middle_seams = check_middle_seams(pieces)
    errors.extend(middle_seams["errors"])
    return {"passed": not errors, "middle_seams": middle_seams, "shared_normal": list(normal), "angle_tolerance_deg": ANGLE_TOLERANCE_DEG,
            "offset_tolerance_mm": OFFSET_TOLERANCE_MM, "max_angle_deg": max((f["angle_deg"] for f in faces), default=None),
            "faces": faces, "components": components, "slides": slides, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--export-dir", type=Path)
    args = parser.parse_args()
    pieces = geometry.detailed_components()
    report = check(pieces)
    source_paths = [ROOT / "palm_pilot_geometry.py", ROOT / "parts/palm_pilot_professional.py", Path(__file__)]
    report["source_sha256"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
    if args.export_dir:
        args.export_dir.mkdir(parents=True, exist_ok=True)
        for name, shape in pieces:
            if name in PRINCIPAL_FACES:
                export_brep(shape, args.export_dir / (name.lower().replace(" ", "-") + ".brep"))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
