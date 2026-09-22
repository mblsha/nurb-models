"""Export the CAD and remove only proven zero-area tessellation components."""

from pathlib import Path
import hashlib
import importlib.util
import json
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from build123d import export_step, export_stl

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
    export_stl(solid, stl)
    raw = trimesh.load_mesh(stl)
    components = raw.split(only_watertight=False, repair=False)
    physical = max(components, key=lambda p: len(p.faces))
    artifacts = [p for p in components if p is not physical]
    if not all(
        len(p.faces) <= 2 and p.area < 1e-8 and abs(p.volume) < 1e-10 for p in artifacts
    ):
        raise RuntimeError(
            "Export contains a material disconnected component; refusing cleanup"
        )
    welds = []
    counts = np.bincount(physical.edges_unique_inverse)
    bad_edges = physical.edges_unique[np.flatnonzero(counts > 2)].copy()
    faces = physical.faces.copy()
    for edge in bad_edges:
        incident = np.flatnonzero(
            np.any(np.sum(np.isin(physical.faces, edge), axis=1)[:, None] >= 2, axis=1)
        )
        length = float(
            np.linalg.norm(physical.vertices[edge[0]] - physical.vertices[edge[1]])
        )
        if length >= 0.0005 or np.any(physical.area_faces[incident] >= 1e-8):
            raise RuntimeError(
                "Nonmanifold edge exceeds the strictly bounded submicron tessellation repair"
            )
        welds.append(
            {
                "edge_length_mm": length,
                "incident_triangle_area_max_mm2": float(
                    physical.area_faces[incident].max()
                ),
            }
        )
        faces[faces == edge[1]] = edge[0]
    keep = (
        (faces[:, 0] != faces[:, 1])
        & (faces[:, 1] != faces[:, 2])
        & (faces[:, 0] != faces[:, 2])
    )
    physical.faces = faces[keep]
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
        "artifacts_removed": len(artifacts),
        "submicron_nonmanifold_edge_welds": welds,
        "artifact_area_total_mm2": sum(p.area for p in artifacts),
        "cleanup_rule": "Isolated at-most-two-triangle components with area below 1e-8 mm2 and volume below 1e-10 mm3; nonmanifold edges shorter than 0.0005 mm only when every incident triangle area is below 1e-8 mm2",
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
