"""Validate the symmetric formed blank, Reset exception, and reopened exports."""
from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import trimesh
from build123d import Plane, Vertex, import_step
from OCP.BRepAdaptor import BRepAdaptor_Surface


ROOT = Path(__file__).resolve().parents[1]
NAME = "palm_v_bottom_cover"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_module():
    spec = importlib.util.spec_from_file_location(NAME, ROOT / "parts" / f"{NAME}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reflected_boundary_error(shape):
    boundary = shape.shells()[0]
    errors = []
    for edge in shape.edges():
        count = max(5, min(80, int(np.ceil(edge.length / 2.0))))
        for parameter in np.linspace(0.0, 1.0, count):
            point = edge.position_at(float(parameter))
            errors.append(Vertex(-point.X, point.Y, point.Z).distance_to(boundary))
    for face in shape.faces():
        surface = BRepAdaptor_Surface(face.wrapped)
        for u in np.linspace(surface.FirstUParameter(), surface.LastUParameter(), 11):
            for v in np.linspace(surface.FirstVParameter(), surface.LastVParameter(), 7):
                point = surface.Value(float(u), float(v))
                if face.is_inside((point.X(), point.Y(), point.Z())):
                    errors.append(Vertex(-point.X(), point.Y(), point.Z()).distance_to(boundary))
    return errors


def mesh_from_3mf(path):
    with zipfile.ZipFile(path) as package:
        document = ET.fromstring(package.read("3D/3dmodel.model"))
    require(document.get("unit") == "millimeter", "the 3MF is not declared in millimetres")
    namespace = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    vertices = [
        [float(node.get(axis)) for axis in ("x", "y", "z")]
        for node in document.findall(".//m:vertex", namespace)
    ]
    triangles = [
        [int(node.get(axis)) for axis in ("v1", "v2", "v3")]
        for node in document.findall(".//m:triangle", namespace)
    ]
    return trimesh.Trimesh(vertices=vertices, faces=triangles)


def main():
    module = load_module()
    parameters = {
        "sheet_thickness_mm": 0.40,
        "crown_height_mm": 0.30,
        "skirt_depth_mm": 1.10,
        "return_width_mm": 1.35,
        "reset_hole_diameter_mm": 1.80,
    }
    symmetric = module._formed_shell(
        parameters["sheet_thickness_mm"],
        parameters["crown_height_mm"],
        parameters["skirt_depth_mm"],
        parameters["return_width_mm"],
        draft=True,
    )
    final = module.palm_v_bottom_cover(**parameters)
    require(symmetric.is_valid and final.is_valid, "the symmetric blank or final cover is invalid")
    require(len(symmetric.solids()) == len(final.solids()) == 1, "both stages must contain exactly one solid")

    reflection_errors = reflected_boundary_error(symmetric)
    maximum_reflection_error = max(reflection_errors)
    require(maximum_reflection_error < 0.01, "the pre-hole shell is not symmetric within 0.01 mm")

    center_x, center_y = 12.80, 19.16
    reset = module._reset_cutter(center_x, center_y, parameters["reset_hole_diameter_mm"])
    removed = symmetric.cut(final)
    expected_removed = symmetric.intersect(reset)[0]
    require(removed.volume > 0.1, "the final body does not contain the Reset opening")
    require(abs(removed.volume - expected_removed.volume) < 1e-5, "the final change is not exactly the Reset cut")
    require(final.cut(symmetric).volume < 1e-7, "the final body adds material outside the symmetric shell")
    require(removed.cut(reset).volume < 1e-7, "asymmetric removal escapes the Reset-hole cutter")

    mirrored_removed = removed.mirror(Plane.YZ)
    left_center = removed.center()
    right_center = mirrored_removed.center()
    require(removed.volume > 0.1 and mirrored_removed.volume > 0.1, "the final cover did not retain the intentional asymmetric exception")
    require(left_center.X * right_center.X < 0, "the two reflected exceptions do not straddle X=0")
    require(abs(left_center.X + right_center.X) < 1e-5, "the reflected Reset exceptions are not paired")

    step = import_step(ROOT / "build" / f"{NAME}.step")
    stl = trimesh.load_mesh(ROOT / "build" / f"{NAME}.stl")
    three_mf = mesh_from_3mf(ROOT / "build" / f"{NAME}.3mf")
    stl_components = list(stl.split(only_watertight=False))
    stl_main = max(stl_components, key=lambda component: len(component.faces))
    stl_artifacts = [component for component in stl_components if component is not stl_main]
    require(step.is_valid and len(step.solids()) == 1, "the reopened STEP is not one valid solid")
    require(stl_main.is_watertight and three_mf.is_watertight, "the principal STL mesh or 3MF is not watertight")
    require(all(len(component.faces) <= 1 and abs(component.volume) < 1e-8 for component in stl_artifacts), "the STL has a material disconnected component")
    require(len(three_mf.split()) == 1, "the 3MF is disconnected")
    require(np.allclose(stl_main.bounds, three_mf.bounds, atol=0.02), "the STL and 3MF bounds differ")
    require(abs(step.volume / final.volume - 1.0) < 1e-6, "the reopened STEP volume differs from the source B-rep")

    result = {
        "accepted": True,
        "geometry": {
            "valid_single_solid": True,
            "faces": len(final.faces()),
            "volume_mm3": final.volume,
            "bounds_mm": [list(final.bounding_box().min), list(final.bounding_box().max)],
        },
        "pre_hole_symmetry": {
            "plane": "X=0",
            "samples": len(reflection_errors),
            "maximum_reflection_error_mm": maximum_reflection_error,
            "tolerance_mm": 0.01,
        },
        "final_asymmetry": {
            "only_exception": "Reset hole",
            "removed_volume_mm3": removed.volume,
            "expected_reset_intersection_volume_mm3": expected_removed.volume,
            "outside_reset_cutter_volume_mm3": removed.cut(reset).volume,
            "reset_center_mm": [center_x, center_y],
            "reset_diameter_mm": parameters["reset_hole_diameter_mm"],
        },
        "exports": {
            "step_reopened_valid": True,
            "stl_principal_component_watertight": True,
            "stl_degenerate_artifact_triangles": sum(len(component.faces) for component in stl_artifacts),
            "stl_raw_watertight": stl.is_watertight,
            "three_mf_watertight": True,
            "mesh_bounds_mm": stl_main.bounds.tolist(),
        },
        "parameters": parameters,
        "scope": {
            "included": "formed aluminium sheet, perimeter skirt and return, end notch, Reset hole",
            "excluded": "glue, clamp/support artifacts, cosmetic interior marks",
            "physical_fit_verified": False,
        },
    }
    output = ROOT / "build" / "reconstruction_validation.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"accepted": False, "error": f"{type(error).__name__}: {error}"}, indent=2))
        sys.exit(1)
