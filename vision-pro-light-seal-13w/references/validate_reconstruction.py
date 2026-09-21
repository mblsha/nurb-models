"""Reopen the exports and measure smooth mating curves against the original scan."""

from __future__ import annotations

import importlib.util
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree
from build123d import import_step
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps


ROOT = Path(__file__).resolve().parents[1]
NAME = "vision_pro_light_seal_13w"


def volume(shape):
    # Adaptive integration is necessary for accurate mass of a broad spline face.
    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, properties, 1e-5)
    return properties.Mass()


def stats(distances):
    return {"samples": len(distances), "median_mm": float(np.median(distances)), "p95_mm": float(np.quantile(distances, 0.95)), "max_mm": float(np.max(distances)), "within_1mm_fraction": float(np.mean(distances <= 1.0))}


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
    reference = trimesh.load(ROOT / "scans" / "vision-pro-light-seal-13w-reference.glb", force="mesh")
    card = (ROOT / "parts" / f"{NAME}.md").read_text()
    transform_match = re.search(r"transform\s*=\s*\[([^]]+)\]", card)
    transform = np.array([float(value) for value in transform_match.group(1).split(",")]).reshape(4, 4)
    assert np.allclose(transform[:3, :3].T @ transform[:3, :3], np.eye(3), atol=1e-8)
    assert abs(np.linalg.det(transform[:3, :3]) - 1.0) < 1e-8
    reference.apply_transform(transform)
    symmetry_error = 0.0
    for face in body.faces():
        surface = BRepAdaptor_Surface(face.wrapped)
        u0, u1 = surface.FirstUParameter(), surface.LastUParameter()
        v0, v1 = surface.FirstVParameter(), surface.LastVParameter()
        for u in np.linspace(u0, u1, 45):
            for v in np.linspace(v0, v1, 9):
                point = surface.Value(float(u), float(v))
                reflected = surface.Value(float(u0 + u1 - u), float(v))
                delta = np.array((-point.X() - reflected.X(), point.Y() - reflected.Y(), point.Z() - reflected.Z()))
                symmetry_error = max(symmetry_error, float(np.linalg.norm(delta)))
    assert symmetry_error < 1e-7
    assert body.is_valid and step.is_valid
    assert len(body.solids()) == len(step.solids()) == 1
    assert mesh.is_watertight and archive.is_watertight
    assert len(mesh.split()) == len(archive.split()) == 1
    assert body.volume > 0 and mesh.volume > 0
    assert np.allclose(mesh.bounds, archive.bounds, atol=0.01)
    assert abs(volume(step) / volume(body) - 1.0) < 1e-6
    result = {
        "geometry": {"valid": True, "connected_solids": 1, "faces": len(body.faces()), "surface_continuity": [str(BRepAdaptor_Surface(face.wrapped).UContinuity()).split(".")[-1] for face in body.faces()], "adaptive_volume_mm3": volume(body), "exported_mesh_bounds_mm": mesh.bounds.tolist(), "exported_mesh_extents_mm": mesh.extents.tolist(), "stl_triangles": len(mesh.faces), "stl_watertight_components": 1, "step_reopened_valid": True, "three_mf_reopened_watertight": True},
        "symmetry": {"plane": "X=0", "max_brep_reflection_error_mm": symmetry_error, "surface_samples_each": 405, "scan_to_cad_transform": transform.tolist()},
        "method": {"distance": "exact closest points on 64 nearest-centroid reference triangles, checked against exhaustive search at 8 samples per rim", "rim_samples_each": 1000, "uncertain_headset_region": "abs(X)<30 and Y>0; rear hard saddle obscured by black cloth", "physical_fit_verified": False},
    }
    triangle_tree = cKDTree(reference.triangles_center)
    parameters = module._periodic_parameters(module.HEADSET_RIM, module.CUSHION_RIM)
    for label, points in [("headset", module.HEADSET_RIM), ("cushion", module.CUSHION_RIM)]:
        edge = module._curve(points, parameters).edges()[0]
        sampled = np.array([tuple(edge.position_at(float(t))) for t in np.linspace(0.0, 1.0, 1000, endpoint=False)])
        _, candidates = triangle_tree.query(sampled, k=64)
        repeated = np.repeat(sampled, 64, axis=0)
        nearest = trimesh.triangles.closest_point(reference.triangles[candidates.reshape(-1)], repeated)
        distances = np.linalg.norm(nearest - repeated, axis=1).reshape(-1, 64).min(axis=1)
        max_error = 0.0
        for i in np.linspace(0, len(sampled) - 1, 8, dtype=int):
            exhaustive = trimesh.triangles.closest_point(reference.triangles, np.broadcast_to(sampled[i], (len(reference.faces), 3)))
            true_distance = np.linalg.norm(exhaustive - sampled[i], axis=1).min()
            max_error = max(max_error, abs(distances[i] - true_distance))
        result[label + "_acceleration_max_error_mm"] = max_error
        assert max_error < 1e-8
        if label == "headset":
            uncertain = (np.abs(sampled[:, 0]) < 30.0) & (sampled[:, 1] > 0)
            result["headset_observable_rim"] = stats(distances[~uncertain])
            result["headset_obscured_saddle"] = stats(distances[uncertain])
        else:
            result["cushion_rim"] = stats(distances)
    profile = module._headset_profile(module.HEADSET_RIM)
    expected = module._skin([module._curve(profile["outer"][-1], parameters), module._curve(profile["inner"][0], parameters)], ruled=True)[0]
    contact_face = min(body.faces(), key=lambda face: (face.center() - expected.center()).length)
    assert abs(contact_face.area - expected.area) < 1e-6
    contact = BRepAdaptor_Surface(contact_face.wrapped)
    sampled = []
    for i in range(9):
        for fraction in np.linspace(0.03, 0.97, 80):
            point = contact.Value(parameters[i], float(fraction))
            sampled.append((point.X(), point.Y(), point.Z()))
    sampled = np.array(sampled)
    _, candidates = triangle_tree.query(sampled, k=64)
    repeated = np.repeat(sampled, 64, axis=0)
    nearest = trimesh.triangles.closest_point(reference.triangles[candidates.reshape(-1)], repeated)
    distances = np.linalg.norm(nearest - repeated, axis=1).reshape(-1, 64).min(axis=1)
    max_error = 0.0
    for i in np.argsort(distances)[-8:]:
        exhaustive = trimesh.triangles.closest_point(reference.triangles, np.broadcast_to(sampled[i], (len(reference.faces), 3)))
        exact = np.linalg.norm(exhaustive - sampled[i], axis=1).min()
        max_error = max(max_error, abs(distances[i] - exact))
    assert max_error < 1e-8
    result["actual_contact_face"] = {**stats(distances), "sampling": "actual B-rep seating face, 80 points across 3–97% of the contact span at each visible guide 0–8", "exhaustive_validation_worst_samples": 8, "maximum_acceleration_error_mm": max_error}
    output = ROOT / "build" / "reconstruction_validation.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
