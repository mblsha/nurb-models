"""Export the CAD and remove only proven zero-area tessellation components."""

from pathlib import Path
import hashlib
import importlib.util
import json
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from build123d import export_step, export_stl, import_step

ROOT = Path(__file__).resolve().parents[1]
NAME = "palm_v_bottom_cover"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec = importlib.util.spec_from_file_location(NAME, ROOT / "parts" / f"{NAME}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    solid = module.palm_v_bottom_cover()
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    step = build / f"{NAME}.step"
    stl = build / f"{NAME}.stl"
    three = build / f"{NAME}.3mf"
    export_step(solid, step)
    # The level inner bend bands need finer native tessellation to close
    # micrometre-scale seams. Zero-area slivers are still checked below.
    export_stl(import_step(step), stl, tolerance=0.0024, angular_tolerance=0.025)
    raw = trimesh.load_mesh(stl)
    components = raw.split(only_watertight=False, repair=False)
    physical = max(components, key=lambda p: len(p.faces))
    artifacts = [p for p in components if p is not physical]
    def negligible(mesh):
        if mesh.area == 0.0:
            return True
        local = mesh.copy()
        local.apply_translation(-mesh.bounds.mean(axis=0))
        # Open degenerate triangles have origin-dependent divergence volumes;
        # a local frame plus their enclosing box bounds the discarded material.
        return (
            mesh.extents.max() < 0.1
            and mesh.area < 1e-7
            and abs(local.volume) < 1e-10
            and np.prod(mesh.extents) < 1e-10
        )

    if not all(negligible(p) for p in artifacts):
        raise RuntimeError(
            "Export contains a material disconnected component; refusing cleanup"
        )
    physical.remove_unreferenced_vertices()
    if not physical.is_watertight or not physical.is_winding_consistent:
        raise RuntimeError(
            "Physical STL surface is not watertight with consistent winding"
        )
    physical.export(stl)
    # Write the same verified geometry into a portable millimetre 3MF package.
    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    model = ET.Element("model", xmlns=ns, unit="millimeter")
    resources = ET.SubElement(model, "resources")
    obj = ET.SubElement(resources, "object", id="1", type="model")
    mesh = ET.SubElement(obj, "mesh")
    vertices = ET.SubElement(mesh, "vertices")
    for v in physical.vertices:
        ET.SubElement(vertices, "vertex", **dict(zip(("x", "y", "z"), map(str, v))))
    triangles = ET.SubElement(mesh, "triangles")
    for f in physical.faces:
        ET.SubElement(
            triangles, "triangle", **dict(zip(("v1", "v2", "v3"), map(str, f)))
        )
    ET.SubElement(ET.SubElement(model, "build"), "item", objectid="1")
    with zipfile.ZipFile(three, "w", compression=zipfile.ZIP_DEFLATED) as out:
        out.writestr(
            "3D/3dmodel.model",
            ET.tostring(model, encoding="utf-8", xml_declaration=True),
        )
        out.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>',
        )
        out.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>',
        )
    report = {
        "source_sha256": sha(ROOT / "parts" / f"{NAME}.py"),
        "surface_fit_sha256": sha(ROOT / "references/surface-fit.json"),
        "straight_rim_fit_sha256": sha(ROOT / "references/straight-rim-fit.json"),
        "inner_rim_fit_sha256": sha(ROOT / "references/inner-rim-fit.json"),
        "artifacts_removed": len(artifacts),
        "artifact_triangles_removed": sum(len(p.faces) for p in artifacts),
        "tessellation_relative_linear_setting": 0.0024,
        "tessellation_angular_tolerance_radians": 0.025,
        "physical_surface_repairs": 0,
        "artifact_area_total_mm2": sum(p.area for p in artifacts),
        "cleanup_rule": "Only zero-area components or isolated components smaller than 0.1 mm in every direction with area below 1e-7 mm2, local-frame volume below 1e-10 mm3, and bounding-box volume below 1e-10 mm3. The physical component must be watertight without seam repair.",
        "mesh_watertight": physical.is_watertight,
        "mesh_winding_consistent": physical.is_winding_consistent,
        "mesh_faces": len(physical.faces),
        "mesh_volume_mm3": physical.volume,
        "mesh_bounds_mm": physical.bounds.tolist(),
        "exports": {p.name: sha(p) for p in (step, stl, three)},
    }
    (build / "export-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
