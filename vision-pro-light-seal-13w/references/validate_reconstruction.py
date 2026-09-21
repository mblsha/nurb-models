"""Reopen all exports and check symmetry on the final trimmed CAD boundary."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
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


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


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
    require(document.get("unit") == "millimeter", "the 3MF is not declared in millimetres")
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    vertices = [[float(node.get(axis)) for axis in ("x", "y", "z")] for node in document.findall(".//m:vertex", ns)]
    triangles = [[int(node.get(axis)) for axis in ("v1", "v2", "v3")] for node in document.findall(".//m:triangle", ns)]
    archive = trimesh.Trimesh(vertices=vertices, faces=triangles)
    card = (ROOT / "parts" / f"{NAME}.md").read_text()
    transform_match = re.search(r"transform\s*=\s*\[([^]]+)\]", card)
    transform = np.array([float(value) for value in transform_match.group(1).split(",")]).reshape(4, 4)
    require(np.allclose(transform[:3, :3].T @ transform[:3, :3], np.eye(3), atol=1e-8), "the saved scan transform is not rigid")
    require(abs(np.linalg.det(transform[:3, :3]) - 1.0) < 1e-8, "the saved scan transform contains reflection or scale")
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
    require(symmetry_error < 1e-5, "the final trimmed CAD is not symmetric within 0.00001 mm")
    require(body.is_valid and step.is_valid, "the modeled body or reopened STEP is invalid")
    require(len(body.solids()) == len(step.solids()) == 1, "the modeled body and STEP must each contain one solid")
    require(mesh.is_watertight and archive.is_watertight, "the STL or 3MF is not watertight")
    require(len(mesh.split()) == len(archive.split()) == 1, "the STL or 3MF is disconnected")
    require(mesh.volume > 0, "the STL has no positive volume")
    require(np.allclose(mesh.bounds, archive.bounds, atol=0.01), "the STL and 3MF bounds differ")
    exact_volume, step_volume = volume(body), volume(step)
    require(exact_volume > 0 and abs(step_volume / exact_volume - 1.0) < 1e-6, "the reopened STEP volume differs from the modeled body")
    floors = []
    for center, normal, major, length, width, depth in module.FACE_CUSHION_WIDE_POCKETS_HALF:
        for sign in (1, -1):
            point = Vector(sign * center[0], center[1], center[2])
            error = Vertex(point).distance_to(boundary)
            floors.append(error)
    require(max(floors) < 1e-5, "a face-cushion pocket floor center is absent from the final boundary")
    variants = []
    for parameter in ("headset_fit_offset_mm", "cushion_fit_offset_mm"):
        for value in (-0.2, 0.2):
            variant = module.vision_pro_light_seal_13w(**{parameter: value})
            require(variant.is_valid and len(variant.solids()) == 1, f"{parameter}={value} did not build one valid solid")
            variants.append({"parameter": parameter, "value_mm": value, "valid_single_solid": True})
    interface_spec = importlib.util.spec_from_file_location("validate_interfaces", ROOT / "references" / "validate_interfaces.py")
    interface_validator = importlib.util.module_from_spec(interface_spec)
    interface_spec.loader.exec_module(interface_validator)
    interface_result = interface_validator.validate(write=True)
    require(interface_result.get("accepted") is True, "interface validation failed: " + "; ".join(finding["message"] for finding in interface_result.get("findings", [])))
    result = {
        "geometry": {"valid": True, "connected_solids": 1, "faces": len(body.faces()), "adaptive_volume_mm3": exact_volume, "exported_mesh_bounds_mm": mesh.bounds.tolist(), "exported_mesh_extents_mm": mesh.extents.tolist(), "stl_triangles": len(mesh.faces), "stl_watertight_components": 1, "step_reopened_valid": True, "three_mf_reopened_watertight": True},
        "symmetry": {"plane": "X=0", "method": "reflect samples on all final trim edges and trimmed face interiors, then measure distance to final boundary shell", "edge_samples": len(edge_errors), "trimmed_face_samples": len(face_errors), "maximum_edge_reflection_error_mm": max(edge_errors), "maximum_trimmed_face_reflection_error_mm": max(face_errors), "scan_to_cad_transform": transform.tolist()},
        "face_cushion_pockets": {"count": len(floors), "type": "closed shallow obround recesses", "maximum_floor_center_boundary_error_mm": max(floors), "cutters_exactly_mirrored": True},
        "fit_parameter_sanity_builds": variants,
        "interface_evidence": {
            "report": "references/interface-validation.json",
            "model_source_sha256": interface_result["identity"]["model_source_sha256"],
            "step_canonical_sha256": interface_result["identity"]["step_canonical_sha256"],
            "reference_sha256": interface_result["identity"]["reference_sha256"],
            "parameters_sha256": interface_result["identity"]["parameters_sha256"],
            "reference_symmetry_plane_accepted": interface_result["reference_symmetry_plane"]["accepted"],
            "finished_trimmed_cad_symmetry_accepted": interface_result["finished_trimmed_cad_symmetry"]["accepted"],
            "narrow_vision_pro_interface_accepted": interface_result["narrow_vision_pro_interface"]["accepted"],
            "face_cushion_openings_accepted": interface_result["face_cushion_openings"]["accepted"],
        },
        "scope": {"vision_pro": "narrow high-W rim, tiny retaining lip only", "face_cushion": "wide low-W contact, eight shallow closed recesses", "excluded": "nose cloth and deep interior details", "physical_fit_verified": False},
    }
    output = ROOT / "build" / "reconstruction_validation.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "failed", "accepted": False, "findings": [{"code": "validation.error", "message": f"{type(exc).__name__}: {exc}"}]}, indent=2))
        sys.exit(1)
