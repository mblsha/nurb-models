"""Audit reopened artifacts independently of the CAD construction code."""

from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from build123d import import_step, Vertex
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from audit_step_geometry import intersections

ROOT = Path(__file__).resolve().parents[1]
NAME = "palm_v_bottom_cover"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    step = ROOT / "build" / f"{NAME}.step"
    shape = import_step(step)
    require(
        shape.is_valid and len(shape.solids()) == 1,
        "Reopened STEP is not one valid solid",
    )
    nominal_edges = {}
    inner_edges = {}
    for sign in (-1, 1):
        side = [
            edge for edge in shape.edges()
            if edge.length > 85
            and edge.bounding_box().min.Y < -35.9
            and edge.bounding_box().max.Y > 50.9
            and sign * edge.center().X > 38
        ]
        require(len(side) == 1, f"Expected one long crest on side {sign:+d}")
        points = np.array([tuple(side[0].position_at(t)) for t in np.linspace(0, 1, 1001)])
        height_span = float(np.ptp(points[:, 2]))
        require(height_span < 0.002, f"Long side {sign:+d} is not level: {height_span:.5f} mm")
        nominal_edges[f"long_side_{sign:+d}"] = {
            "height_span_mm": height_span,
            "physical_y_range_mm": [float(points[:, 1].min()), float(points[:, 1].max())],
        }
        inner_side = [
            edge for edge in shape.edges()
            if 94 < edge.length < 95
            and sign * edge.center().X > 37
            and 1.33 < edge.bounding_box().min.Z < 1.40
        ]
        require(len(inner_side) == 1, f"Expected one inner long crest on side {sign:+d}")
        points = np.array([tuple(inner_side[0].position_at(t)) for t in np.linspace(0, 1, 2001)])
        core = points[(points[:, 1] >= -35) & (points[:, 1] <= 40)]
        core_span = float(np.ptp(core[:, 2]))
        require(core_span < 0.01, f"Inner long core {sign:+d} is not level: {core_span:.5f} mm")
        inner_edges[f"long_side_{sign:+d}"] = {
            "core_y_range_mm": [-35, 40],
            "core_height_span_mm": core_span,
            "full_edge_height_span_including_corner_transitions_mm": float(np.ptp(points[:, 2])),
        }
        wall = [
            edge for edge in shape.edges()
            if 9 < edge.length < 11
            and edge.bounding_box().min.Y < -57.8
            and edge.bounding_box().max.Y > -50.0
            and abs(sign * edge.center().X - 16.0) < 0.01
        ]
        require(len(wall) == 1, f"Expected one split wall on side {sign:+d}")
        points = np.array([tuple(wall[0].position_at(t)) for t in np.linspace(0, 1, 1001)])
        x_span = float(np.ptp(points[:, 0]))
        center_error = float(np.max(np.abs(points[:, 0] - sign * 16.0)))
        require(x_span < 0.001 and center_error < 0.001, f"Split wall {sign:+d} is not vertical in plan")
        nominal_edges[f"split_wall_{sign:+d}"] = {
            "physical_x_span_mm": x_span,
            "maximum_x_error_from_nominal_mm": center_error,
            "physical_y_range_mm": [float(points[:, 1].min()), float(points[:, 1].max())],
        }
        far_inner = [
            edge for edge in shape.edges()
            if abs(edge.length - 28) < 0.01
            and sign * edge.center().X > 10
            and 55.0 < edge.center().Y < 55.2
            and edge.bounding_box().min.Z > 3.15
        ]
        require(len(far_inner) == 1, f"Expected one inner +Y crest on side {sign:+d}")
        points = np.array([tuple(far_inner[0].position_at(t)) for t in np.linspace(0, 1, 1001)])
        span = float(np.ptp(points[:, 2]))
        require(span < 0.01, f"Inner +Y crest {sign:+d} is not level: {span:.5f} mm")
        inner_edges[f"far_end_{sign:+d}"] = {"height_span_mm": span}
        split_inner = [
            edge for edge in shape.edges()
            if 18.3 < edge.length < 18.5
            and sign * edge.center().X > 20
            and -56 < edge.center().Y < -54
            and edge.bounding_box().min.Z > 4.7
        ]
        require(len(split_inner) == 1, f"Expected one inner -Y crest on side {sign:+d}")
        points = np.array([tuple(split_inner[0].position_at(t)) for t in np.linspace(0, 1, 1001)])
        span = float(np.ptp(points[:, 2]))
        require(span < 0.01, f"Inner -Y crest {sign:+d} is not level: {span:.5f} mm")
        inner_edges[f"split_end_{sign:+d}"] = {"height_span_mm": span}
    far_end_profiles = {}
    radius = 3.45
    crest_z, side_z, side_x = 3.12, 1.30, 37.721431
    fall = crest_z - side_z
    arc_start_x = side_x - np.sqrt(4 * radius * fall - fall * fall)
    arc_join_x = 0.5 * (arc_start_x + side_x)
    for sign in (-1, 1):
        candidates = [
            edge for edge in shape.edges()
            if 10.0 < edge.length < 10.7
            and sign * edge.center().X > 28
            and edge.bounding_box().min.Y > 53.5
            and 1.29 < edge.bounding_box().min.Z < 1.31
            and 3.10 < edge.bounding_box().max.Z < 3.20
        ]
        require(len(candidates) == 1, f"Expected one exterior +Y corner trim on side {sign:+d}")
        points = np.array([tuple(candidates[0].position_at(t)) for t in np.linspace(0, 1, 2001)])
        x = np.abs(points[:, 0])
        ideal_z = np.full_like(x, crest_z)
        first_arc = (x > arc_start_x) & (x <= arc_join_x)
        second_arc = x > arc_join_x
        ideal_z[first_arc] = crest_z - radius + np.sqrt(radius**2 - (x[first_arc] - arc_start_x)**2)
        ideal_z[second_arc] = side_z + radius - np.sqrt(radius**2 - (x[second_arc] - side_x)**2)
        max_error = float(np.max(np.abs(points[:, 2] - ideal_z)))
        landing_error = float(abs(x.max() - side_x))
        require(max_error < 0.003, f"+Y trim {sign:+d} deviates from nominal biarc by {max_error:.4f} mm")
        require(landing_error < 0.002, f"+Y trim {sign:+d} misses long-side junction by {landing_error:.4f} mm")
        far_end_profiles[f"corner_{sign:+d}"] = {
            "equal_arc_radius_mm": radius,
            "arc_start_abs_x_mm": float(arc_start_x),
            "arc_tangent_join_abs_x_mm": float(arc_join_x),
            "long_side_level_z_mm": side_z,
            "maximum_end_elevation_error_mm": max_error,
            "junction_abs_x_error_mm": landing_error,
        }
    probes = []
    for x in (0.0, 12.0, 24.0, 35.0, 38.0):
        for y in (-48.0, -40.0, -25.0, -10.0, 5.0, 14.5, 18.0, 25.0, 40.0, 52.0, 55.0):
            hits = intersections(shape, (x, y, 0), (0, 0, 1))
            if not hits:
                continue
            _, point, normal = hits[0]
            nh = intersections(shape, point, normal, -2, 2)
            thickness = [abs(h[0]) for h in nh if abs(h[0]) > 1e-4]
            require(thickness, "No opposite surface for a sampled exterior point")
            gauge = min(thickness)
            mirror = Vertex(-point[0], point[1], point[2]).distance_to(
                shape.shells()[0]
            )
            require(
                abs(gauge - 0.65) < 0.01,
                f"Gauge differs from 0.65 mm at {(x, y)}: {gauge}",
            )
            require(
                mirror < 0.001, f"Symmetric exterior mismatch at {(x, y)}: {mirror}"
            )
            if abs(x) < 32 and -43 < y < 45:
                require(
                    len(hits) == 2,
                    f"Unintended material layers in broad panel at {(x, y)}",
                )
            probes.append(
                {
                    "x_mm": x,
                    "y_mm": y,
                    "gauge_mm": gauge,
                    "mirror_error_mm": mirror,
                    "vertical_intersections": len(hits),
                }
            )
    require(
        not intersections(shape, (0, 15.3, 0), (0, 0, 1)),
        "Centered slot is not open through the sheet",
    )
    require(
        not intersections(shape, (12.8, 19.16, 0), (0, 0, 1)),
        "Reset opening is not open through the sheet",
    )
    require(
        len(intersections(shape, (-12.8, 19.16, 0), (0, 0, 1))) == 2,
        "Reset was incorrectly mirrored",
    )
    mesh = trimesh.load_mesh(ROOT / "build" / f"{NAME}.stl")
    require(
        mesh.is_watertight and mesh.is_winding_consistent,
        "Delivered STL is not watertight and consistently wound",
    )
    require(
        len(mesh.split(only_watertight=False, repair=False)) == 1,
        "Delivered STL contains disconnected components",
    )
    side_profile = {}
    for name, y_samples in {
        "split_approach": np.linspace(-37.0, -25.0, 13),
        "far_upright_approach": np.linspace(51.0, 54.0, 7),
    }.items():
        skyline = []
        for y in y_samples:
            section = trimesh.intersections.mesh_plane(mesh, (0, 1, 0), (0, float(y), 0))
            points = section.reshape(-1, 3)
            side_points = points[(points[:, 0] > 35.0) & (points[:, 0] < 46.0)]
            require(len(side_points) > 0, f"No right-side silhouette at Y={y:.2f} mm")
            skyline.append(float(side_points[:, 2].max()))
        height_span = float(np.ptp(skyline))
        require(height_span < 0.04, f"{name} projected side line varies by {height_span:.4f} mm")
        side_profile[name] = {
            "physical_y_range_mm": [float(y_samples[0]), float(y_samples[-1])],
            "projected_height_span_mm": height_span,
        }
    with zipfile.ZipFile(ROOT / "build" / f"{NAME}.3mf") as f:
        xml = ET.fromstring(f.read("3D/3dmodel.model"))
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    vertices = np.array(
        [
            [float(v.get(k)) for k in ("x", "y", "z")]
            for v in xml.findall(".//m:vertex", ns)
        ]
    )
    faces = np.array(
        [
            [int(v.get(k)) for k in ("v1", "v2", "v3")]
            for v in xml.findall(".//m:triangle", ns)
        ]
    )
    packed = trimesh.Trimesh(vertices, faces)
    require(
        xml.get("unit") == "millimeter" and packed.is_watertight,
        "Delivered 3MF is not watertight millimetre geometry",
    )
    require(
        np.allclose(packed.bounds, mesh.bounds, atol=1e-5), "STL and 3MF bounds differ"
    )
    props = GProp_GProps()
    integration_error = BRepGProp.VolumePropertiesGK_s(
        shape.wrapped, props, 1e-5, True, True
    )
    volume = props.Mass()
    require(
        abs(mesh.volume / volume - 1) < 0.002,
        "Mesh volume differs from adaptive per-span STEP volume by over 0.2 percent",
    )
    files = [
        ROOT / "parts" / f"{NAME}.py",
        ROOT / "references/surface-fit.json",
        ROOT / "references/straight-rim-fit.json",
        ROOT / "references/inner-rim-fit.json",
        step,
        ROOT / "build" / f"{NAME}.stl",
        ROOT / "build" / f"{NAME}.3mf",
    ]
    rim_report = ROOT / "build/rim-lines-validation.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "references/audit_straight_rims.py"),
            str(step),
            str(ROOT / "references/rim-line-measurements.json"),
            str(rim_report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    rim_result = json.loads(rim_report.read_text())
    require(
        rim_result["all_core_runs_straight_and_level_within_0_01_mm"],
        "Reopened rim lines are not straight and level within 0.01 mm",
    )
    result = {
        "geometry_checks": "passed",
        "projected_side_profile": side_profile,
        "straight_horizontal_rim_runs": "all five physical core runs passed 0.01 mm straightness and level checks",
        "extended_nominal_edges": nominal_edges,
        "inner_level_cores": inner_edges,
        "far_end_biarc_profiles": far_end_profiles,
        "rim_geometry_report": "rim-lines-validation.json",
        "physical_fit_verified": False,
        "shape": "nominal planar broad field with localized stamp and formed perimeter inferred from scan",
        "valid_single_solid": True,
        "sample_count": len(probes),
        "normal_gauge_range_mm": [
            min(p["gauge_mm"] for p in probes),
            max(p["gauge_mm"] for p in probes),
        ],
        "maximum_mirrored_surface_error_mm": max(p["mirror_error_mm"] for p in probes),
        "slot_open": True,
        "reset_open_only_on_positive_x": True,
        "step_adaptive_volume_mm3": volume,
        "step_integration_relative_error": integration_error,
        "mesh_volume_mm3": mesh.volume,
        "mesh_bounds_mm": mesh.bounds.tolist(),
        "exports_watertight": True,
        "artifact_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files
        },
        "probes": probes,
        "scope_limit": "These checks verify geometry, sheet gauge, symmetry, openings and artifact integrity. Scan fit is assessed separately by region and both comparison directions.",
    }
    (ROOT / "build/reconstruction_validation.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "probes"}, indent=2))


if __name__ == "__main__":
    main()
