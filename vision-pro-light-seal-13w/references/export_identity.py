"""Build-bound exports: never attach today's source hash to yesterday's geometry."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import tempfile
import zipfile
from pathlib import Path

import lib3mf
import trimesh
from build123d import Mesher, export_step, import_step
from nurb import builder, feature_evidence


ROOT = Path(__file__).resolve().parents[1]
NAME = "vision_pro_light_seal_13w"
PART = ROOT / "parts" / (NAME + ".py")
MANIFEST = ROOT / "build" / "export-manifest.json"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export_digest(path):
    path = Path(path)
    if path.suffix == ".step":
        content = re.sub(rb"'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'", b"'<generated>'", path.read_bytes(), count=1)
    elif path.suffix == ".3mf":
        with zipfile.ZipFile(path) as package:
            content = re.sub(rb'p:UUID="[^"]+"', b'p:UUID="<generated>"', package.read("3D/3dmodel.model"))
    else:
        content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def inputs():
    files = [PART, ROOT / "measurements.toml", Path(__file__).resolve()]
    versions = {}
    for package in ("nurb", "build123d", "cadquery-ocp", "trimesh"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "unavailable"
    return {"files": {str(path.relative_to(ROOT)): digest(path) for path in files}, "runtime_versions": versions}


def build_current():
    body, params, _ = builder.build(PART)
    if not body.is_valid or len(body.solids()) != 1:
        raise RuntimeError("current source must build one valid solid before acceptance")
    return body, {param["name"]: param["value"] for param in params}


def prepare():
    before = inputs()
    body, parameters = build_current()
    geometry = feature_evidence.shape_identity(body)
    directory = ROOT / "build"
    directory.mkdir(exist_ok=True)
    # Publish the manifest last. Interrupted regeneration cannot make mixed exports current.
    with tempfile.TemporaryDirectory(prefix="lightseal-exports-", dir=directory) as temporary:
        temporary = Path(temporary)
        paths = {suffix: temporary / (NAME + suffix) for suffix in (".step", ".stl", ".3mf")}
        export_step(body, paths[".step"])
        # Preserve the model's explicit absolute display tessellation for mesh exports.
        vertices, faces, _ = builder._triangulate(body, 0.04, remesh=False)
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
        mesh.export(paths[".stl"])
        mesher = Mesher()
        obj = mesher.model.AddMeshObject()
        obj.SetGeometry([lib3mf.Position(Coordinates=tuple(vertex)) for vertex in mesh.vertices],
                        [lib3mf.Triangle(Indices=tuple(int(value) for value in face)) for face in mesh.faces])
        obj.SetType(lib3mf.ObjectType.Model)
        mesher.model.AddBuildItem(obj, mesher.wrapper.GetIdentityTransform())
        mesher.write(str(paths[".3mf"]))
        reopened = import_step(paths[".step"])
        if not reopened.is_valid or len(reopened.solids()) != 1:
            raise RuntimeError("fresh STEP export did not reopen as one valid solid")
        if inputs() != before:
            raise RuntimeError("source changed during export; repeat the build")
        manifest = {"schema_version": 1, "inputs": before, "parameters": parameters,
                    "built_geometry_sha256": geometry,
                    "exports": {suffix: export_digest(path) for suffix, path in paths.items()},
                    "binding": "All exports were generated from this single fresh body. Every validation rebuilds current source and compares exact B-rep identity before accepting any export."}
        for suffix, path in paths.items():
            path.replace(directory / (NAME + suffix))
        destination = directory / "export-manifest.tmp"
        destination.write_text(json.dumps(manifest, indent=2) + "\n")
        destination.replace(MANIFEST)
    return manifest


def verify():
    if not MANIFEST.is_file():
        raise RuntimeError("exports have no build manifest; run python references/export_identity.py")
    manifest = json.loads(MANIFEST.read_text())
    started_with = inputs()
    if manifest.get("schema_version") != 1 or manifest.get("inputs") != started_with:
        raise RuntimeError("export manifest is stale for current source or runtime; regenerate exports")
    for suffix in (".step", ".stl", ".3mf"):
        path = ROOT / "build" / (NAME + suffix)
        if not path.is_file() or export_digest(path) != manifest.get("exports", {}).get(suffix):
            raise RuntimeError(f"{suffix} export is stale or changed; regenerate exports")
    body, parameters = build_current()
    if parameters != manifest.get("parameters") or feature_evidence.shape_identity(body) != manifest.get("built_geometry_sha256"):
        raise RuntimeError("fresh source geometry differs from the exported geometry; regenerate exports")
    if inputs() != started_with:
        raise RuntimeError("source changed during validation; repeat validation")
    return body, manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
