"""Audit reopened artifacts independently of the CAD construction code."""

from pathlib import Path
import hashlib
import json
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
        step,
        ROOT / "build" / f"{NAME}.stl",
        ROOT / "build" / f"{NAME}.3mf",
    ]
    result = {
        "geometry_checks": "passed",
        "physical_fit_verified": False,
        "shape": "nominal longitudinally straightened design inferred from scan",
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
