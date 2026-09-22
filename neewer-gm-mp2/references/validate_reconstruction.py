"""Reproduce the GM-MP2 motion, fit, and local Arca-interface acceptance checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import trimesh
from build123d import Mesher, Vector, Vertex, import_step
from nurb import builder, checks, scan, validator_evidence


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = Path(__file__).resolve()
MEASUREMENTS = ROOT / "measurements.toml"
PART = ROOT / "parts" / "neewer_macro_slide_gm_mp2.py"
SLEEVE_PART = ROOT / "parts" / "neewer_outer_focus_sleeve.py"
REFERENCE = ROOT / "scans" / "neewer-macro-slide-GM-MP2.ply.gz"
SLEEVE_STEP = ROOT / "references" / "neewer-outer-focus-sleeve.step"
POSE = {"arca_detent": 0, "carriage_position_mm": 70.0}
TRAVELS = (0.0, 70.0, 140.0)
DETENTS = (0, 1, 2, 3)
ATTACHED = ("fixed top Arca clamp", "movable top Arca jaw", "clamp knob")
TOLERANCE_MM = 0.75

# Functional contact flanks in the scan frame. Each is sampled from its exact
# analytic CAD segment and checked against an independent mesh-plane section.
BOTTOM_FLANKS = {
    "left": ((3.15, 1.75), (5.10, 3.85)),
    "right": ((41.05, 1.75), (39.10, 3.85)),
}
TOP_FLANKS = {
    "fixed": ((3.40, 39.90), (5.60, 44.40)),
    "movable": ((46.20, 39.90), (43.50, 44.40)),
}
BOTTOM_PRESENT_X = (5.0, 40.0, 100.0, 202.0)
BOTTOM_BAY_X = (20.0, 185.0)
TRANSITION_CHECKS = (
    {"nominal_x_mm": 10.0, "retained_x_mm": 9.74, "bay_x_mm": 10.26},
    {"nominal_x_mm": 31.75, "retained_x_mm": 32.01, "bay_x_mm": 31.49},
    {"nominal_x_mm": 175.25, "retained_x_mm": 174.99, "bay_x_mm": 175.51},
    {"nominal_x_mm": 197.5, "retained_x_mm": 197.76, "bay_x_mm": 197.24},
)
MOTION_ERROR_LIMIT = 1e-7
CAD_REQUIREMENT_ERROR_LIMIT_MM = 1e-6
# Independently recorded scan datum: carriage at 70 mm and the midpoint between
# the two measured rod axes. These are acceptance data, not model expressions.
SCAN_PIVOT_MM = (103.5, 22.10675, 28.0)
TRANSLATING = ("sliding carriage", "rotary base")
VIEWER_FEATURE_IDS = ("bottom-plate", "fixed-jaw", "moving-jaw", "drive-knob", "focus-sleeve", "front-rod", "rear-rod")
VIEWER_INPUTS = (PART, SLEEVE_PART, VALIDATOR, MEASUREMENTS, REFERENCE, SLEEVE_STEP)


def json_hash(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def acceptance_specification():
    return {
        "pose": POSE,
        "travels_mm": list(TRAVELS),
        "detents": list(DETENTS),
        "attached_components": list(ATTACHED),
        "motion_error_limit": MOTION_ERROR_LIMIT,
        "scan_pivot_mm": SCAN_PIVOT_MM,
        "commanded_rotation_deg": [0, 90, 180, 270],
        "arca_tolerance_mm": TOLERANCE_MM,
        "cad_requirement_error_limit_mm": CAD_REQUIREMENT_ERROR_LIMIT_MM,
        "bottom_flanks": BOTTOM_FLANKS,
        "top_flanks": TOP_FLANKS,
        "bottom_present_x_mm": list(BOTTOM_PRESENT_X),
        "bottom_bay_x_mm": list(BOTTOM_BAY_X),
        "bottom_bay_transition_checks": TRANSITION_CHECKS,
        "bottom_bay_transition_uncertainty_mm": 0.25,
    }


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def components(shape):
    return {item.label: item.solid for item in shape._nurb_scene.components}


def vector_list(value):
    return [float(value.X), float(value.Y), float(value.Z)]


def location_list(location):
    position, orientation = tuple(location)
    return [vector_list(position), vector_list(orientation)]


def relative_vertices(solid, origin):
    points = np.array([vector_list(vertex.center()) for vertex in solid.vertices()])
    points -= np.asarray(origin)
    return points


def vertex_set_error(first, second):
    """Bidirectional set distance, avoiding unstable ordering at symmetric vertices."""
    delta = first[:, None, :] - second[None, :, :]
    distances = np.sqrt(np.sum(delta * delta, axis=2))
    return float(max(np.max(np.min(distances, axis=0)), np.max(np.min(distances, axis=1))))


def geometry_fingerprint(items):
    records = []
    for name, solid in sorted(items.items()):
        bounds = solid.bounding_box()
        vertices = np.round(
            np.array([vector_list(vertex.center()) for vertex in solid.vertices()]), 8
        )
        order = np.lexsort((vertices[:, 2], vertices[:, 1], vertices[:, 0]))
        records.append(
            {
                "name": name,
                "bounds_mm": [vector_list(bounds.min), vector_list(bounds.max)],
                "volume_mm3": float(solid.volume),
                "vertices_mm": vertices[order].tolist(),
            }
        )
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def section_paths(mesh, x):
    path = mesh.section(plane_origin=(x, 0.0, 0.0), plane_normal=(1.0, 0.0, 0.0))
    if path is None:
        return []
    return [np.asarray(entity.discrete(path.vertices)) for entity in path.entities]


def section_points(mesh, x):
    paths = section_paths(mesh, x)
    return np.concatenate(paths) if paths else np.empty((0, 3))


def line_samples(x, endpoints, count=101, trim=0.0):
    start, end = (np.asarray(point, dtype=float) for point in endpoints)
    yz = start + np.linspace(trim, 1.0 - trim, count)[:, None] * (end - start)
    return np.column_stack((np.full(count, x), yz))


def nearest_distances(query, points):
    delta = query[:, None, :] - points[None, :, :]
    return np.sqrt(np.min(np.sum(delta * delta, axis=2), axis=1))


def percentiles(values):
    p50, p95, maximum = np.percentile(values, (50, 95, 100))
    return {"p50_mm": float(p50), "p95_mm": float(p95), "max_mm": float(maximum)}


def shape_mesh(shape, tolerance=0.03):
    vertices, faces, _ = builder._triangulate(shape, tolerance)
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def combine_meshes(shapes):
    return trimesh.util.concatenate([shape_mesh(shape) for shape in shapes])


def svg_path(points, map_point):
    if len(points) == 0:
        return ""
    coordinates = [map_point(point) for point in points]
    return "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in coordinates)


def write_section_svg(reference_mesh, built_components, output):
    panels = [
        ("Bottom plate, solid station x=100 mm", 100.0, (0.0, 44.2, -0.5, 12.8), [built_components["bottom Arca plate"]]),
        ("Bottom plate, folded-foot bay x=20 mm", 20.0, (0.0, 44.2, -0.5, 12.8), [built_components["bottom Arca plate"]]),
        ("Top clamp, scan pose x=103.4 mm", 103.4, (-4.5, 53.5, 29.5, 45.2), [built_components["fixed top Arca clamp"], built_components["movable top Arca jaw"]]),
    ]
    width, panel_height, gap, margin = 760, 280, 24, 42
    height = margin + len(panels) * (panel_height + gap)
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#11151b"/>',
        '<style>text{font-family:system-ui,sans-serif;fill:#e7edf4}.title{font-size:17px;font-weight:600}.note{font-size:12px;fill:#a9b5c2}.ref{fill:none;stroke:#9aa5b1;stroke-width:1.2}.cad{fill:none;stroke:#ff9e45;stroke-width:2}</style>',
    ]
    for index, (title, station, bounds, cad_shapes) in enumerate(panels):
        y_top = margin + index * (panel_height + gap)
        y_min, y_max, z_min, z_max = bounds
        inner_x, inner_y = 58, y_top + 34
        inner_w, inner_h = width - 92, panel_height - 52

        def map_point(point):
            px = inner_x + (point[1] - y_min) / (y_max - y_min) * inner_w
            py = inner_y + inner_h - (point[2] - z_min) / (z_max - z_min) * inner_h
            return px, py

        elements.append(f'<text class="title" x="{inner_x}" y="{y_top + 20}">{title}</text>')
        elements.append(f'<text class="note" x="{inner_x + 355}" y="{y_top + 20}">grey: PLY.GZ scan  orange: current CAD section</text>')
        elements.append(f'<rect x="{inner_x}" y="{inner_y}" width="{inner_w}" height="{inner_h}" fill="none" stroke="#34404d"/>')
        elements.append(f'<defs><clipPath id="panel-{index}"><rect x="{inner_x}" y="{inner_y}" width="{inner_w}" height="{inner_h}"/></clipPath></defs>')
        elements.append(f'<g clip-path="url(#panel-{index})">')
        for path in section_paths(reference_mesh, station):
            elements.append(f'<path class="ref" d="{svg_path(path, map_point)}"/>')
        cad_mesh = combine_meshes(cad_shapes)
        for path in section_paths(cad_mesh, station):
            elements.append(f'<path class="cad" d="{svg_path(path, map_point)}"/>')
        elements.append('</g>')
        elements.append(f'<text class="note" x="{inner_x + inner_w - 185}" y="{inner_y + inner_h - 8}">Y horizontal, Z vertical</text>')
    elements.append("</svg>")
    output.write_text("\n".join(elements) + "\n")


def verify_sleeve_exports(sleeve):
    with tempfile.TemporaryDirectory(prefix="neewer-sleeve-exports-") as directory:
        directory = Path(directory)
        stl = directory / "sleeve.stl"
        archive = directory / "sleeve.3mf"
        mesher = Mesher()
        mesher.add_shape(sleeve)
        mesher.write(stl)
        mesher = Mesher()
        mesher.add_shape(sleeve)
        mesher.write(archive)
        stl_mesh = trimesh.load_mesh(stl)
        with zipfile.ZipFile(archive) as package:
            document = ET.fromstring(package.read("3D/3dmodel.model"))
        namespace = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
        vertices = document.findall(".//m:vertex", namespace)
        triangles = document.findall(".//m:triangle", namespace)
        if not stl_mesh.is_watertight or float(stl_mesh.volume) <= 0:
            raise RuntimeError("the temporary sleeve STL is not one positive-volume watertight mesh")
        if document.get("unit") != "millimeter":
            raise RuntimeError("the temporary sleeve 3MF is not declared in millimetres")
        if not vertices or not triangles:
            raise RuntimeError("the temporary sleeve 3MF contains no mesh")
        return {
            "accepted": True,
            "source_step_sha256": sha256(SLEEVE_STEP),
            "source_step_reopened_valid": import_step(SLEEVE_STEP).is_valid,
            "stl_reopened_watertight": True,
            "stl_triangles": int(len(stl_mesh.faces)),
            "three_mf_unit": document.get("unit"),
            "three_mf_vertices": len(vertices),
            "three_mf_triangles": len(triangles),
            "scope": "The exact sleeve is the only separately printable part placed by this assembly; the generated rail reconstruction is context geometry and is not exported as one printable object.",
        }


def finding_record(finding):
    return {
        "rule": finding.rule,
        "severity": finding.severity,
        "message": finding.message,
        "value": finding.value,
        "where": list(finding.where) if finding.where is not None else None,
        "components": list(finding.components) if finding.components is not None else None,
        "measurements": finding.measurements,
    }


def current_source_identity():
    specification = json.loads(json.dumps(acceptance_specification()))
    return {
        "model_source": str(PART.relative_to(ROOT)),
        "model_source_sha256": sha256(PART),
        "sleeve_model_source": str(SLEEVE_PART.relative_to(ROOT)),
        "sleeve_model_source_sha256": sha256(SLEEVE_PART),
        "validator": str(VALIDATOR.relative_to(ROOT)),
        "validator_sha256": sha256(VALIDATOR),
        "measurements": str(MEASUREMENTS.relative_to(ROOT)),
        "measurements_sha256": sha256(MEASUREMENTS),
        "reference": str(REFERENCE.relative_to(ROOT)),
        "reference_sha256": sha256(REFERENCE),
        "sleeve_source_step": str(SLEEVE_STEP.relative_to(ROOT)),
        "sleeve_source_step_sha256": sha256(SLEEVE_STEP),
        "acceptance_specification": specification,
        "acceptance_specification_sha256": json_hash(specification),
        "parameters_sha256": json_hash(POSE),
        "acceptance_pose": POSE,
    }


def add_failure(failures, code, message, **evidence):
    failures.append({"code": code, "message": message, "evidence": evidence})


def commanded_pose_check(found, baseline, detent, travel):
    """Check requested world motion against one fixed scan-pose oracle."""
    angle = np.radians(90.0 * detent)
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0.0],
                         [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    pivot = np.asarray(SCAN_PIVOT_MM)
    shift = np.array([travel - 70.0, 0.0, 0.0])
    rows = []
    for name, original in baseline.items():
        expected = relative_vertices(original, (0, 0, 0))
        if name in ATTACHED:
            expected = (expected - pivot) @ rotation.T + pivot + shift
            requirement = "quarter turn about scan pivot, then commanded travel"
        elif name in TRANSLATING:
            expected = expected + shift
            requirement = "commanded travel without rotation"
        else:
            requirement = "stationary rail and drive component"
        actual = relative_vertices(found[name], (0, 0, 0))
        error = vertex_set_error(actual, expected)
        accepted = actual.shape == expected.shape and error < MOTION_ERROR_LIMIT
        rows.append({"component": name, "requirement": requirement,
                     "maximum_world_vertex_error_mm": error, "accepted": accepted})
    expected_pivot = pivot + shift
    actual_pivot = np.asarray(vector_list(found["rotary base"].bounding_box().center()))
    pivot_error = float(np.linalg.norm(actual_pivot - expected_pivot))
    return {"expected_pivot_mm": expected_pivot.tolist(), "actual_pivot_mm": actual_pivot.tolist(),
            "pivot_error_mm": pivot_error, "components": rows,
            "accepted": pivot_error < MOTION_ERROR_LIMIT and all(row["accepted"] for row in rows)}


def validate(write=True):
    started_with = current_source_identity()
    reference_mesh, unit, unit_source = scan.load(REFERENCE, units="mm")
    printable_sleeve, _, _ = builder.build(SLEEVE_PART)
    failures = []
    if unit != "mm":
        add_failure(failures, "reference.units", "reference did not load in millimetres", actual=unit)
    rows = []
    maximum_relative_vertex_error = 0.0
    maximum_relative_transform_error = 0.0
    geometry_hash = None
    baseline_by_detent = {}
    scan_pose_components = None
    scan_pose_shape = None
    sleeve = None
    oracle_shape, _, _ = builder.build(PART, overrides=POSE)
    oracle = components(oracle_shape)
    for detent in DETENTS:
        # Establish the fixed mid-travel baseline first, then compare both ends.
        for travel in (70.0, 0.0, 140.0):
            parameters = {"arca_detent": detent, "carriage_position_mm": travel}
            shape, _, _ = builder.build(PART, overrides=parameters)
            found = components(shape)
            commanded = commanded_pose_check(found, oracle, detent, travel)
            if not commanded["accepted"]:
                add_failure(failures, "motion.commanded_pose", "geometry does not implement the requested travel and detent", parameters=parameters, check=commanded)
            base = found["rotary base"]
            base_origin = vector_list(base.bounding_box().center())
            findings = checks.run(shape)
            serialized_findings = [finding_record(finding) for finding in findings]
            for finding in serialized_findings:
                add_failure(failures, "pose.check", finding["message"], parameters=parameters, finding=finding)
            current = {}
            for name in ATTACHED:
                relative_location = base.location.inverse() * found[name].location
                current[name] = {
                    "relative_location": location_list(relative_location),
                    "relative_vertices": relative_vertices(found[name], base_origin),
                    "volume_mm3": float(found[name].volume),
                }
            if travel == 70.0:
                baseline_by_detent[detent] = current
            baseline = baseline_by_detent.get(detent)
            attachment_checks = []
            if baseline is not None:
                for name in ATTACHED:
                    same_vertex_count = current[name]["relative_vertices"].shape == baseline[name]["relative_vertices"].shape
                    vertex_error = vertex_set_error(current[name]["relative_vertices"], baseline[name]["relative_vertices"])
                    location_error = float(np.max(np.abs(np.asarray(current[name]["relative_location"]) - np.asarray(baseline[name]["relative_location"]))))
                    volume_error = abs(current[name]["volume_mm3"] - baseline[name]["volume_mm3"])
                    accepted = same_vertex_count and vertex_error < MOTION_ERROR_LIMIT and location_error < MOTION_ERROR_LIMIT and volume_error < MOTION_ERROR_LIMIT
                    attachment_checks.append({
                        "component": name,
                        "same_vertex_count": same_vertex_count,
                        "relative_vertex_error_mm": vertex_error,
                        "relative_location_error_mm_or_deg": location_error,
                        "volume_error_mm3": volume_error,
                        "accepted": accepted,
                    })
                    if not accepted:
                        add_failure(failures, "motion.relative_geometry", f"{name} moved relative to the rotary base", parameters=parameters, check=attachment_checks[-1])
                    maximum_relative_vertex_error = max(maximum_relative_vertex_error, vertex_error)
                    maximum_relative_transform_error = max(maximum_relative_transform_error, location_error)
            rows.append(
                {
                    "parameters": parameters,
                    "clearance_check_findings": serialized_findings,
                    "attached_relative_locations": {name: current[name]["relative_location"] for name in ATTACHED},
                    "attachment_checks": attachment_checks,
                    "commanded_pose": commanded,
                    "accepted": commanded["accepted"] and not serialized_findings and all(check["accepted"] for check in attachment_checks),
                }
            )
            if parameters == POSE:
                scan_pose_components = found
                scan_pose_shape = shape
                geometry_hash = geometry_fingerprint(found)
                sleeve = found["exact outer focus sleeve"]
    if scan_pose_components is None or scan_pose_shape is None or sleeve is None:
        raise RuntimeError("the declared scan pose was not built")
    rows.sort(key=lambda row: (row["parameters"]["arca_detent"], row["parameters"]["carriage_position_mm"]))

    fixed_bounds = scan_pose_components["fixed top Arca clamp"].bounding_box()
    movable_bounds = scan_pose_components["movable top Arca jaw"].bounding_box()
    expected_bounds = {
        "fixed_min": (78.85, -2.55, 31.20), "fixed_max": (127.95, 43.50, 44.40),
        "movable_min": (78.85, 43.50, 31.20), "movable_max": (127.95, 51.70, 44.40),
    }
    actual_bounds = {
        "fixed_min": vector_list(fixed_bounds.min), "fixed_max": vector_list(fixed_bounds.max),
        "movable_min": vector_list(movable_bounds.min), "movable_max": vector_list(movable_bounds.max),
    }
    bounds_accepted = all(np.allclose(actual_bounds[key], expected, atol=CAD_REQUIREMENT_ERROR_LIMIT_MM) for key, expected in expected_bounds.items())
    if not bounds_accepted:
        add_failure(failures, "motion.default_geometry", "default top-clamp bounds changed", expected=expected_bounds, actual=actual_bounds)

    sleeve_gap = float(scan_pose_components["large focus knob"].distance_to(sleeve))
    sleeve_overlap = scan_pose_components["large focus knob"].intersect(sleeve)
    declarations = scan_pose_shape._nurb_scene.clearances
    declaration = declarations[0] if len(declarations) == 1 else None
    declared_components = [] if declaration is None else [declaration.first.label, declaration.second.label]
    declared_minimum = None if declaration is None else float(declaration.minimum)
    expected_pair = {"large focus knob", "exact outer focus sleeve"}
    overlap_volume = 0.0 if sleeve_overlap is None else float(sleeve_overlap.volume)
    sleeve_accepted = (
        declaration is not None
        and set(declared_components) == expected_pair
        and sleeve_gap >= declared_minimum
        and overlap_volume <= 1e-9
    )
    if not sleeve_accepted:
        add_failure(
            failures,
            "assembly.outer_sleeve_clearance",
            "the declared outer-sleeve CAD clearance failed",
            declaration_count=len(declarations),
            declared_components=declared_components,
            declared_minimum_mm=declared_minimum,
            actual_minimum_distance_mm=sleeve_gap,
            overlap_mm3=overlap_volume,
        )

    bottom_shape = scan_pose_components["bottom Arca plate"]
    section_acceptance = {
        "bottom_present": [],
        "bottom_bays": [],
        "bottom_bay_transitions": [],
        "top_clamp": [],
    }
    for station in BOTTOM_PRESENT_X:
        reference_points = section_points(reference_mesh, station)
        for side, endpoints in BOTTOM_FLANKS.items():
            samples = line_samples(station, endpoints)
            scan_distances = nearest_distances(samples, reference_points)
            cad_distances = np.array([Vertex(*point).distance_to(bottom_shape) for point in samples])
            scan_metrics = percentiles(scan_distances)
            cad_error = float(np.max(cad_distances))
            accepted = scan_metrics["p95_mm"] <= TOLERANCE_MM and cad_error < CAD_REQUIREMENT_ERROR_LIMIT_MM
            record = {"x_mm": station, "side": side, "scan_distance": scan_metrics, "maximum_cad_requirement_error_mm": cad_error, "accepted": accepted}
            section_acceptance["bottom_present"].append(record)
            if not accepted:
                add_failure(failures, "arca.bottom_present", "a retained bottom Arca flank failed", **record)
    for station in BOTTOM_BAY_X:
        reference_points = section_points(reference_mesh, station)
        for side, endpoints in BOTTOM_FLANKS.items():
            # Endpoints meet the retained upper shell. The middle 80% is the
            # functional lower flank whose absence defines the bay.
            samples = line_samples(station, endpoints, trim=0.1)
            scan_distances = nearest_distances(samples, reference_points)
            cad_distances = np.array([Vertex(*point).distance_to(bottom_shape) for point in samples])
            scan_metrics = percentiles(scan_distances)
            cad_distance = float(np.min(cad_distances))
            accepted = scan_metrics["p50_mm"] >= TOLERANCE_MM and cad_distance >= TOLERANCE_MM
            record = {"x_mm": station, "side": side, "scan_distance_to_absent_flank": scan_metrics, "minimum_cad_distance_to_absent_flank_mm": cad_distance, "accepted": accepted}
            section_acceptance["bottom_bays"].append(record)
            if not accepted:
                add_failure(failures, "arca.bottom_bay", "a folded-foot bay still contains the excluded lower flank", **record)
    # The scan-derived transitions are documented to ±0.25 mm. Test material
    # immediately outside that band and absence immediately inside it instead of
    # treating an uncertain boundary section as exact.
    for transition in TRANSITION_CHECKS:
        for side, y in (("left", 4.0), ("right", 40.2)):
            retained = bottom_shape.is_inside(Vector(transition["retained_x_mm"], y, 2.0))
            absent = not bottom_shape.is_inside(Vector(transition["bay_x_mm"], y, 2.0))
            accepted = retained and absent
            record = {**transition, "uncertainty_mm": 0.25, "side": side, "retained_outside_uncertainty_band": retained, "absent_inside_uncertainty_band": absent, "accepted": accepted}
            section_acceptance["bottom_bay_transitions"].append(record)
            if not accepted:
                add_failure(failures, "arca.bottom_bay_transition", "a folded-foot bay transition failed outside its uncertainty band", **record)
    top_reference = section_points(reference_mesh, 103.4)
    top_shapes = {
        "fixed": scan_pose_components["fixed top Arca clamp"],
        "movable": scan_pose_components["movable top Arca jaw"],
    }
    for name, endpoints in TOP_FLANKS.items():
        samples = line_samples(103.4, endpoints)
        scan_distances = nearest_distances(samples, top_reference)
        cad_distances = np.array([Vertex(*point).distance_to(top_shapes[name]) for point in samples])
        scan_metrics = percentiles(scan_distances)
        cad_error = float(np.max(cad_distances))
        accepted = scan_metrics["p95_mm"] <= TOLERANCE_MM and cad_error < CAD_REQUIREMENT_ERROR_LIMIT_MM
        record = {"x_mm": 103.4, "jaw": name, "scan_distance": scan_metrics, "maximum_cad_requirement_error_mm": cad_error, "accepted": accepted}
        section_acceptance["top_clamp"].append(record)
        if not accepted:
            add_failure(failures, "arca.top_clamp", "a top-clamp Arca flank failed", **record)

    exports = verify_sleeve_exports(printable_sleeve)
    motion_accepted = bounds_accepted and all(row["accepted"] for row in rows)
    arca_accepted = all(record["accepted"] for records in section_acceptance.values() for record in records)
    accepted = not failures and motion_accepted and sleeve_accepted and arca_accepted and exports["accepted"]
    source_identity = current_source_identity()
    if source_identity != started_with:
        raise RuntimeError("validation inputs changed while inspecting; repeat validation")

    result = {
        "status": "accepted_for_current_modeled_CAD_scope" if accepted else "failed",
        "accepted": accepted,
        "findings": failures,
        "identity": {
            **source_identity,
            "model_geometry_sha256": geometry_hash,
            "pose_geometry_sha256": geometry_hash,
            "reference_unit": unit,
            "reference_unit_source": unit_source,
            "alignment": "identity",
        },
        "viewer_evidence": validator_evidence.viewer_contract(
            ROOT,
            list(VIEWER_FEATURE_IDS),
            [str(path.relative_to(ROOT)) for path in VIEWER_INPUTS],
            environment={
                "runtime_versions": validator_evidence.runtime_versions(("python", "nurb", "build123d", "cadquery-ocp", "trimesh", "numpy", "scipy", "lib3mf")),
                "nurb_source_sha256": validator_evidence.engine_source_digest(),
            },
        ),
        "motion": {
            "accepted": motion_accepted,
            "tested_builds": len(rows),
            "detents": list(DETENTS),
            "travel_positions_mm": list(TRAVELS),
            "attached_components": list(ATTACHED),
            "method": "Require world-space travel, quarter-turn rotation about the independently recorded scan pivot, and immobility of every rail/drive component against one scan-pose oracle; additionally verify relative attachment against each detent's mid-travel baseline.",
            "maximum_relative_transform_error_mm_or_deg": maximum_relative_transform_error,
            "maximum_relative_vertex_error_mm": maximum_relative_vertex_error,
            "rows": rows,
        },
        "outer_sleeve_fit": {
            "accepted": sleeve_accepted,
            "declared_components": declared_components,
            "declared_minimum_mm": declared_minimum,
            "actual_minimum_distance_mm": sleeve_gap,
            "positive_volume_intersection": overlap_volume > 1e-9,
            "overlap_mm3": overlap_volume,
            "check_findings": next(row["clearance_check_findings"] for row in rows if row["parameters"] == POSE),
            "scope": "CAD-to-CAD regression only; physical fit and manufactured clearance remain unverified.",
        },
        "arca_sections": {
            "accepted": arca_accepted,
            "tolerance_mm": TOLERANCE_MM,
            "method": "Sample exact analytic contact-flank requirements, verify they lie on the current CAD where present (or remain absent in folded-foot bays), and measure each sample to an independent X-normal section of the declared PLY.GZ reference.",
            "acceptance": section_acceptance,
            "svg": "neewer-arca-sections.svg",
            "limitations": [
                "This is feature-local one-directional CAD requirement to scan evidence, not whole-model coverage.",
                "The scan contains omitted feet, threads, markings, rubber pads, fasteners, and texture, so those are excluded from these acceptance regions.",
                "Reference sections are mesh intersections; physical mating remains unverified.",
            ],
        },
        "exports": exports,
        "verification_classes": {
            "geometry_validity": ("accepted: 12 assembly poses built successfully" if motion_accepted else "failed: at least one pose or attached relative geometry check failed"),
            "reconstruction_agreement": ("accepted only for the recorded local Arca flanks and interrupted lower dovetail" if arca_accepted else "failed: at least one local Arca requirement exceeded its threshold"),
            "assembly_fit": ("accepted: declared sleeve clearance passes in CAD" if sleeve_accepted else "failed: declared sleeve clearance or component identity did not pass"),
            "printability": "separate nurb check result; assembly context is not exported as one printable object",
            "physical_verification": "not performed",
        },
    }
    if accepted and write:
        output = ROOT / "references" / "neewer-current-acceptance.json"
        output.write_text(json.dumps(result, indent=2) + "\n")
        write_section_svg(reference_mesh, scan_pose_components, ROOT / "references" / "neewer-arca-sections.svg")
    return result


def check_report(path):
    report = json.loads(Path(path).read_text())
    recorded = report.get("identity", {})
    current = current_source_identity()
    changed = {key: {"recorded": recorded.get(key), "current": value} for key, value in current.items() if recorded.get(key) != value}
    try:
        relative = Path(path).resolve().relative_to(ROOT).as_posix()
        viewer = validator_evidence.load_reports(ROOT, [{"file": relative, "label": "Neewer reconstruction"}])[0][0]
        if viewer["freshness"] != "current":
            changed["viewer_evidence"] = viewer["changed"]
    except ValueError as exc:
        changed["viewer_evidence"] = str(exc)
    return {
        "status": "current" if report.get("accepted") is True and not changed else "stale",
        "report": str(Path(path)),
        "changed": changed,
        "identity": current,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-report", nargs="?", const=str(ROOT / "references" / "neewer-current-acceptance.json"), help="check an existing report without rebuilding or writing evidence")
    args = parser.parse_args(argv)
    if args.check_report:
        result = check_report(args.check_report)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "current" else 1
    try:
        result = validate(write=True)
    except Exception as exc:
        result = {"status": "failed", "accepted": False, "findings": [{"code": "validation.error", "message": f"{type(exc).__name__}: {exc}"}]}
    print(json.dumps(result, indent=2))
    return 0 if result.get("accepted") is True else 1


if __name__ == "__main__":
    sys.exit(main())
