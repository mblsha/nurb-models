#!/usr/bin/env python3
"""Import supplied Palm meshes without inventing scan registration or topology."""

from __future__ import annotations
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np
import trimesh


def digest(data):
    return hashlib.sha256(data).hexdigest()


def compress(path, payload):
    with path.open("wb") as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0
        ) as stream:
            stream.write(payload)


def stl_to_ply(payload):
    count = int(np.frombuffer(payload[80:84], dtype="<u4")[0])
    dtype = np.dtype(
        [("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")]
    )
    if 84 + count * dtype.itemsize != len(payload):
        raise ValueError("Expected a complete binary STL")
    triangles = np.frombuffer(payload, dtype=dtype, count=count, offset=84)
    flat = triangles["vertices"].reshape(-1, 3)
    vertices, inverse = np.unique(flat, axis=0, return_inverse=True)
    if not np.isfinite(vertices).all():
        raise ValueError("STL contains nonfinite vertex coordinates")
    faces = inverse.reshape(-1, 3).astype("<i4")
    if not np.array_equal(vertices[faces], triangles["vertices"]):
        raise ValueError("Exact vertex indexing failed to preserve STL triangles")
    face_dtype = np.dtype(
        [
            ("count", "u1"),
            ("indices", "<i4", (3,)),
            ("nx", "<f4"),
            ("ny", "<f4"),
            ("nz", "<f4"),
            ("attribute", "<u2"),
            ("source_face", "<u4"),
        ]
    )
    records = np.empty(count, dtype=face_dtype)
    records["count"] = 3
    records["indices"] = faces
    for axis, key in enumerate(["nx", "ny", "nz"]):
        records[key] = triangles["normal"][:, axis]
    records["attribute"] = triangles["attribute"]
    records["source_face"] = np.arange(count)
    header = [
        "ply",
        "format binary_little_endian 1.0",
        "comment Exact original STL triangles; coordinates retained; units assumed mm",
        f"element vertex {len(vertices)}",
        "property float x",
        "property float y",
        "property float z",
        f"element face {count}",
        "property list uchar int vertex_indices",
        "property float nx",
        "property float ny",
        "property float nz",
        "property ushort attribute",
        "property uint source_face",
        "end_header",
        "",
    ]
    return (
        "\n".join(header).encode()
        + vertices.astype("<f4").tobytes()
        + records.tobytes()
    )


def import_one(archive, output, label):
    archive_data = archive.read_bytes()
    with zipfile.ZipFile(io.BytesIO(archive_data)) as z:
        files = [n for n in z.namelist() if n.lower().endswith((".ply", ".stl"))]
        if len(files) != 1:
            raise ValueError("Expected one supplied mesh per archive")
        name = files[0]
        raw = z.read(name)
    source_format = Path(name).suffix[1:].lower()
    payload = raw if source_format == "ply" else stl_to_ply(raw)
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / (label + ".ply.gz")
    compress(artifact, payload)
    mesh = trimesh.load(io.BytesIO(payload), file_type="ply", process=False)
    points = np.asarray(mesh.vertices)
    center = points.mean(0)
    values, axes = np.linalg.eigh(np.cov(points.T))
    axes = axes[:, np.argsort(values)[::-1]]
    if np.linalg.det(axes) < 0:
        axes[:, 2] *= -1
    q = (points - center) @ axes
    # Principal axes describe only a reversible inspection frame, not assembly alignment.
    matrix = np.eye(4)
    matrix[:3, :3] = axes.T
    matrix[:3, 3] = -axes.T @ center
    record = {
        "schema": "palm-supplied-mesh-reference/v1",
        "label": label,
        "archive": {
            "file": archive.name,
            "bytes": len(archive_data),
            "sha256": digest(archive_data),
        },
        "source_mesh": {
            "file": name,
            "format": source_format,
            "bytes": len(raw),
            "sha256": digest(raw),
        },
        "output": {
            "file": artifact.name,
            "bytes": artifact.stat().st_size,
            "sha256": digest(artifact.read_bytes()),
            "decompressed_sha256": digest(payload),
        },
        "coordinates": "Original source coordinates retained; no alignment or scale transform applied",
        "units": {
            "assumed": "millimetres",
            "declared_by_source": False,
            "basis": "Extent plausibility and comparison with measured Palm back cover; verify before manufacturing",
        },
        "topology": {
            "vertices": len(mesh.vertices),
            "triangles": len(mesh.faces),
            "watertight": bool(mesh.is_watertight),
            "winding_consistent": bool(mesh.is_winding_consistent),
            "face_components": len(mesh.split(only_watertight=False)),
        },
        "source_to_output": "Original PLY byte-for-byte decompressed"
        if source_format == "ply"
        else "Exact duplicate STL vertices indexed; every triangle, facet normal, attribute word and face order retained; no welding tolerance or repair",
        "bounds_original": mesh.bounds.tolist(),
        "extents_original": mesh.extents.tolist(),
        "inspection_pca": {
            "transform": matrix.tolist(),
            "bounds": np.array([q.min(0), q.max(0)]).tolist(),
            "extents": np.ptp(q, axis=0).tolist(),
            "role": "Inspection only; axes not assigned anatomical meaning",
        },
        "textures": False,
        "original_registration_metadata": False,
    }
    (output / (label + ".json")).write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--whole", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    import_one(args.body, args.output_dir, "palm-v-body-observed")
    import_one(args.whole, args.output_dir, "palm-v-rough-observed")


if __name__ == "__main__":
    main()
