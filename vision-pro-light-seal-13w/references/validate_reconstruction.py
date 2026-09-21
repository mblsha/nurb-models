"""Reopen all exports and check symmetry on the final trimmed CAD boundary."""
from __future__ import annotations

import importlib.util
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import trimesh
from build123d import Vertex, Vector, import_step
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

ROOT = Path(__file__).resolve().parents[1]
NAME = "vision_pro_light_seal_13w"


def volume(shape):
    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, properties, 1e-5)
    return properties.Mass()


def main():
    spec = importlib.util.spec_from_file_location(NAME, ROOT / "parts" / f"{NAME}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    body = module.vision_pro_light_seal_13w()
    step = import_step(ROOT / "build" / f"{NAME}.step")
    mesh = trimesh.load_mesh(ROOT / "build" / f"{NAME}.stl")
    with zipfile.ZipFile(ROOT / "build" / f"{NAME}.3mf") as package:
        document = ET.fromstring(package.read("3D/3dmodel.model"))
    assert document.get("unit") == "millimeter"
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    vertices = [[float(node.get(axis)) for axis in ("x", "y", "z")] for node in document.findall(".//m:vertex", ns)]
    triangles = [[int(node.get(axis)) for axis in ("v1", "v2", "v3")] for node in document.findall(".//m:triangle", ns)]
    archive = trimesh.Trimesh(vertices=vertices, faces=triangles)
    card = (ROOT / "parts" / f"{NAME}.md").read_text()
    transform_match = re.search(r"transform\s*=\s*\[([^]]+)\]", card)
    transform = np.array([float(value) for value in transform_match.group(1).split(",")]).reshape(4, 4)
    assert np.allclose(transform[:3, :3].T @ transform[:3, :3], np.eye(3), atol=1e-8)
    assert abs(np.linalg.det(transform[:3, :3]) - 1.0) < 1e-8
    # A shell target measures boundary distance, not containment in a solid.
    # Trims matter: an untrimmed surface could conceal asymmetric pocket holes.
    boundary = body.shells()[0]
    edge_errors, face_errors = [], []
    for edge in body.edges():
        for t in np.linspace(0.03, 0.97, 7):
            point = edge.position_at(float(t))
            edge_errors.append(Vertex(-point.X, point.Y, point.Z).distance_to(boundary))
    for face in body.faces():
        surface = BRepAdaptor_Surface(face.wrapped)
        for u in np.linspace(surface.FirstUParameter(), surface.LastUParameter(), 9):
            for v in np.linspace(surface.FirstVParameter(), surface.LastVParameter(), 5):
                p = surface.Value(float(u), float(v))
                point = Vector(p.X(), p.Y(), p.Z())
                if face.is_inside(point):
                    face_errors.append(Vertex(-p.X(), p.Y(), p.Z()).distance_to(boundary))
    symmetry_error = max([*edge_errors, *face_errors])
    assert symmetry_error < 1e-5
    assert body.is_valid and step.is_valid
    assert len(body.solids()) == len(step.solids()) == 1
    assert mesh.is_watertight and archive.is_watertight
    assert len(mesh.split()) == len(archive.split()) == 1
    assert mesh.volume > 0
    assert np.allclose(mesh.bounds, archive.bounds, atol=0.01)
    exact_volume, step_volume = volume(body), volume(step)
    assert exact_volume > 0 and abs(step_volume / exact_volume - 1.0) < 1e-6
    floors = []
    for center, normal, major, length, width, depth in module.FACE_CUSHION_WIDE_POCKETS_HALF:
        for sign in (1, -1):
            point = Vector(sign * center[0], center[1], center[2])
            error = Vertex(point).distance_to(boundary)
            floors.append(error)
    assert max(floors) < 1e-5
    variants = []
    for parameter in ("headset_fit_offset_mm", "cushion_fit_offset_mm"):
        for value in (-0.2, 0.2):
            variant = module.vision_pro_light_seal_13w(**{parameter: value})
            assert variant.is_valid and len(variant.solids()) == 1
            variants.append({"parameter": parameter, "value_mm": value, "valid_single_solid": True})
    result = {
        "geometry": {"valid": True, "connected_solids": 1, "faces": len(body.faces()), "adaptive_volume_mm3": exact_volume, "exported_mesh_bounds_mm": mesh.bounds.tolist(), "exported_mesh_extents_mm": mesh.extents.tolist(), "stl_triangles": len(mesh.faces), "stl_watertight_components": 1, "step_reopened_valid": True, "three_mf_reopened_watertight": True},
        "symmetry": {"plane": "X=0", "method": "reflect samples on all final trim edges and trimmed face interiors, then measure distance to final boundary shell", "edge_samples": len(edge_errors), "trimmed_face_samples": len(face_errors), "maximum_edge_reflection_error_mm": max(edge_errors), "maximum_trimmed_face_reflection_error_mm": max(face_errors), "scan_to_cad_transform": transform.tolist()},
        "face_cushion_pockets": {"count": len(floors), "type": "closed shallow obround recesses", "maximum_floor_center_boundary_error_mm": max(floors), "cutters_exactly_mirrored": True},
        "fit_parameter_sanity_builds": variants,
        "scope": {"vision_pro": "narrow high-W rim, tiny retaining lip only", "face_cushion": "wide low-W contact, eight shallow closed recesses", "excluded": "nose cloth and deep interior details", "physical_fit_verified": False},
    }
    output = ROOT / "build" / "reconstruction_validation.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
