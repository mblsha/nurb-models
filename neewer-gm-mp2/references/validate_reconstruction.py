"""Reproduce the GM-MP2 motion, fit, and local Arca-interface acceptance checks."""
from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import trimesh
from build123d import Mesher, Vector, Vertex, import_step
from nurb import builder, checks, scan


ROOT = Path(__file__).resolve().parents[1]
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
        assert stl_mesh.is_watertight and float(stl_mesh.volume) > 0
        assert document.get("unit") == "millimeter"
        assert vertices and triangles
        return {
            "source_step_sha256": sha256(SLEEVE_STEP),
            "source_step_reopened_valid": import_step(SLEEVE_STEP).is_valid,
            "stl_reopened_watertight": True,
            "stl_triangles": int(len(stl_mesh.faces)),
            "three_mf_unit": document.get("unit"),
            "three_mf_vertices": len(vertices),
            "three_mf_triangles": len(triangles),
            "scope": "The exact sleeve is the only separately printable part placed by this assembly; the generated rail reconstruction is context geometry and is not exported as one printable object.",
        }


def main():
    reference_mesh, unit, unit_source = scan.load(REFERENCE, units="mm")
    printable_sleeve, _, _ = builder.build(SLEEVE_PART)
    assert unit == "mm"
    rows = []
    maximum_relative_vertex_error = 0.0
    maximum_relative_transform_error = 0.0
    geometry_hash = None
    baseline_by_detent = {}
    scan_pose_components = None
    scan_pose_shape = None
    sleeve = None
    for detent in DETENTS:
        # Establish the fixed mid-travel baseline first, then compare both ends.
        for travel in (70.0, 0.0, 140.0):
            parameters = {"arca_detent": detent, "carriage_position_mm": travel}
            shape, _, _ = builder.build(PART, overrides=parameters)
            found = components(shape)
            base = found["rotary base"]
            base_origin = vector_list(base.bounding_box().center())
            findings = checks.run(shape)
            assert findings == []
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
            if baseline is not None:
                for name in ATTACHED:
                    assert current[name]["relative_vertices"].shape == baseline[name]["relative_vertices"].shape
                    vertex_error = vertex_set_error(current[name]["relative_vertices"], baseline[name]["relative_vertices"])
                    location_error = float(np.max(np.abs(np.asarray(current[name]["relative_location"]) - np.asarray(baseline[name]["relative_location"]))))
                    volume_error = abs(current[name]["volume_mm3"] - baseline[name]["volume_mm3"])
                    assert vertex_error < 1e-7 and location_error < 1e-7 and volume_error < 1e-7
                    maximum_relative_vertex_error = max(maximum_relative_vertex_error, vertex_error)
                    maximum_relative_transform_error = max(maximum_relative_transform_error, location_error)
            rows.append(
                {
                    "parameters": parameters,
                    "clearance_check_findings": [],
                    "attached_relative_locations": {name: current[name]["relative_location"] for name in ATTACHED},
                }
            )
            if parameters == POSE:
                scan_pose_components = found
                scan_pose_shape = shape
                geometry_hash = geometry_fingerprint(found)
                sleeve = found["exact outer focus sleeve"]
    assert scan_pose_components is not None and scan_pose_shape is not None and sleeve is not None
    rows.sort(key=lambda row: (row["parameters"]["arca_detent"], row["parameters"]["carriage_position_mm"]))

    fixed_bounds = scan_pose_components["fixed top Arca clamp"].bounding_box()
    movable_bounds = scan_pose_components["movable top Arca jaw"].bounding_box()
    assert np.allclose(vector_list(fixed_bounds.min), (78.85, -2.55, 31.20), atol=1e-6)
    assert np.allclose(vector_list(fixed_bounds.max), (127.95, 43.50, 44.40), atol=1e-6)
    assert np.allclose(vector_list(movable_bounds.min), (78.85, 43.50, 31.20), atol=1e-6)
    assert np.allclose(vector_list(movable_bounds.max), (127.95, 51.70, 44.40), atol=1e-6)

    sleeve_gap = float(scan_pose_components["large focus knob"].distance_to(sleeve))
    sleeve_overlap = scan_pose_components["large focus knob"].intersect(sleeve)
    declarations = scan_pose_shape._nurb_scene.clearances
    assert len(declarations) == 1
    declaration = declarations[0]
    assert {declaration.first.label, declaration.second.label} == {"large focus knob", "exact outer focus sleeve"}
    assert declaration.minimum == 0.05 and sleeve_gap >= declaration.minimum and sleeve_overlap is None

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
            assert scan_metrics["p95_mm"] <= TOLERANCE_MM
            assert float(np.max(cad_distances)) < 1e-6
            section_acceptance["bottom_present"].append(
                {"x_mm": station, "side": side, "scan_distance": scan_metrics, "maximum_cad_requirement_error_mm": float(np.max(cad_distances)), "accepted": True}
            )
    for station in BOTTOM_BAY_X:
        reference_points = section_points(reference_mesh, station)
        for side, endpoints in BOTTOM_FLANKS.items():
            # Endpoints meet the retained upper shell. The middle 80% is the
            # functional lower flank whose absence defines the bay.
            samples = line_samples(station, endpoints, trim=0.1)
            scan_distances = nearest_distances(samples, reference_points)
            cad_distances = np.array([Vertex(*point).distance_to(bottom_shape) for point in samples])
            scan_metrics = percentiles(scan_distances)
            assert scan_metrics["p50_mm"] >= TOLERANCE_MM
            assert float(np.min(cad_distances)) >= TOLERANCE_MM
            section_acceptance["bottom_bays"].append(
                {"x_mm": station, "side": side, "scan_distance_to_absent_flank": scan_metrics, "minimum_cad_distance_to_absent_flank_mm": float(np.min(cad_distances)), "accepted": True}
            )
    # The scan-derived transitions are documented to ±0.25 mm. Test material
    # immediately outside that band and absence immediately inside it instead of
    # treating an uncertain boundary section as exact.
    transition_checks = (
        {"nominal_x_mm": 10.0, "retained_x_mm": 9.74, "bay_x_mm": 10.26},
        {"nominal_x_mm": 31.75, "retained_x_mm": 32.01, "bay_x_mm": 31.49},
        {"nominal_x_mm": 175.25, "retained_x_mm": 174.99, "bay_x_mm": 175.51},
        {"nominal_x_mm": 197.5, "retained_x_mm": 197.76, "bay_x_mm": 197.24},
    )
    for transition in transition_checks:
        for side, y in (("left", 4.0), ("right", 40.2)):
            retained = bottom_shape.is_inside(Vector(transition["retained_x_mm"], y, 2.0))
            absent = not bottom_shape.is_inside(Vector(transition["bay_x_mm"], y, 2.0))
            assert retained and absent
            section_acceptance["bottom_bay_transitions"].append(
                {**transition, "uncertainty_mm": 0.25, "side": side, "retained_outside_uncertainty_band": retained, "absent_inside_uncertainty_band": absent, "accepted": True}
            )
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
        assert scan_metrics["p95_mm"] <= TOLERANCE_MM
        assert float(np.max(cad_distances)) < 1e-6
        section_acceptance["top_clamp"].append(
            {"x_mm": 103.4, "jaw": name, "scan_distance": scan_metrics, "maximum_cad_requirement_error_mm": float(np.max(cad_distances)), "accepted": True}
        )

    result = {
        "status": "accepted_for_current_modeled_CAD_scope",
        "identity": {
            "model_source": str(PART.relative_to(ROOT)),
            "model_source_sha256": sha256(PART),
            "model_geometry_sha256": geometry_hash,
            "pose_geometry_sha256": geometry_hash,
            "parameters_sha256": hashlib.sha256(json.dumps(POSE, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "reference": str(REFERENCE.relative_to(ROOT)),
            "reference_sha256": sha256(REFERENCE),
            "reference_unit": unit,
            "reference_unit_source": unit_source,
            "alignment": "identity",
            "acceptance_pose": POSE,
        },
        "motion": {
            "tested_builds": len(rows),
            "detents": list(DETENTS),
            "travel_positions_mm": list(TRAVELS),
            "attached_components": list(ATTACHED),
            "method": "Compare each component's relative Location and full B-rep vertex set in the rotary-base frame against the same detent at 70 mm travel.",
            "maximum_relative_transform_error_mm_or_deg": maximum_relative_transform_error,
            "maximum_relative_vertex_error_mm": maximum_relative_vertex_error,
            "rows": rows,
        },
        "outer_sleeve_fit": {
            "declared_components": [declaration.first.label, declaration.second.label],
            "declared_minimum_mm": declaration.minimum,
            "actual_minimum_distance_mm": sleeve_gap,
            "positive_volume_intersection": False,
            "check_findings": [],
            "scope": "CAD-to-CAD regression only; physical fit and manufactured clearance remain unverified.",
        },
        "arca_sections": {
            "tolerance_mm": TOLERANCE_MM,
            "method": "Sample exact analytic contact-flank requirements, assert they lie on the current CAD where present (or remain absent in folded-foot bays), and measure each sample to an independent X-normal section of the declared PLY.GZ reference.",
            "acceptance": section_acceptance,
            "svg": "neewer-arca-sections.svg",
            "limitations": [
                "This is feature-local one-directional CAD requirement to scan evidence, not whole-model coverage.",
                "The scan contains omitted feet, threads, markings, rubber pads, fasteners, and texture, so those are excluded from these acceptance regions.",
                "Reference sections are mesh intersections; physical mating remains unverified.",
            ],
        },
        "exports": verify_sleeve_exports(printable_sleeve),
        "verification_classes": {
            "geometry_validity": "12 assembly poses built successfully",
            "reconstruction_agreement": "accepted only for the recorded local Arca flanks and interrupted lower dovetail",
            "assembly_fit": "declared sleeve clearance passes in CAD",
            "printability": "separate nurb check result; assembly context is not exported as one printable object",
            "physical_verification": "not performed",
        },
    }
    output = ROOT / "references" / "neewer-current-acceptance.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    write_section_svg(reference_mesh, scan_pose_components, ROOT / "references" / "neewer-arca-sections.svg")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
