#!/usr/bin/env python3
"""Build the measured Palm V back-cover reference from the authoritative MAF group."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np


DATASET_ID = "scan-018109effc1ab56b0920"
REVISION = "f6722ad291d3c3a3c1a7806de1b2234bea7e78cd5361351b62bcfa0133a0b7af"
ARCHIVE_SHA256 = "52900e9ad09d24b552cea788ea0dbb743e9fa22dde0095cad362bf95ddb1da3f"
SOURCE_SHA256 = "a5ce15c73eaf8eb19f5bebc330d2de8243d138e092c0d2ac9d66dbbbd95cc073"
MERGE_MANIFEST_SHA256 = "c785daaacc7a19d83b24b62f5433644a470bf379acc7c8b695c54873b8192631"
MERGED_SHA256 = "dc2cb15fec9003020dcdf7be31cf66bea5a8bf57dcca5bf5801a65ea5eb389f5"
SOURCE_POINTS = 2_083_708
MERGED_POINTS = 5_434_687
VOXEL_MM = 0.17
EXPECTED_OUTPUT_POINTS = 495_454
MAX_OUTPUT_POINTS = 500_000

FRAME_ORIGIN_MM = np.array(
    [0.26349328494840996, 1.1827956451851473, -1.7516604056513603], dtype=np.float64
)
FRAME_BASIS_ROWS = np.array(
    [
        [-0.9921722997277009, -0.09816707037842172, 0.07718389693688062],
        [0.11743632027012417, -0.5233330643547212, 0.8439971649445928],
        [-0.042459843787487545, 0.8464548009471121, 0.5307649495013088],
    ],
    dtype=np.float64,
)
FRAME_TRANSFORM = np.eye(4, dtype=np.float64)
FRAME_TRANSFORM[:3, :3] = FRAME_BASIS_ROWS
FRAME_TRANSFORM[:3, 3] = -FRAME_BASIS_ROWS @ FRAME_ORIGIN_MM

PLY_DTYPE = np.dtype(
    [
        ("x", "<f4"),
        ("y", "<f4"),
        ("z", "<f4"),
        ("nx", "<f4"),
        ("ny", "<f4"),
        ("nz", "<f4"),
        ("red", "u1"),
        ("green", "u1"),
        ("blue", "u1"),
        ("source_group", "<u4"),
        ("source_scan", "<u4"),
        ("source_angle", "<i4"),
    ]
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path: Path, **extra: Any) -> dict[str, Any]:
    return {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256(path), **extra}


def read_vertex_table(path: Path) -> tuple[np.memmap, int]:
    properties: list[tuple[str, str]] = []
    vertex_count: int | None = None
    with path.open("rb") as stream:
        if stream.readline() != b"ply\n" or stream.readline() != b"format binary_little_endian 1.0\n":
            raise ValueError("source must be a binary little-endian PLY")
        while True:
            line = stream.readline()
            if not line:
                raise ValueError("truncated PLY header")
            words = line.decode("ascii").strip().split()
            if words[:2] == ["element", "vertex"]:
                vertex_count = int(words[2])
            elif words[:1] == ["property"] and vertex_count is not None:
                properties.append((words[2], words[1]))
            elif words == ["end_header"]:
                offset = stream.tell()
                break
    expected = [
        ("x", "float"),
        ("y", "float"),
        ("z", "float"),
        ("nx", "float"),
        ("ny", "float"),
        ("nz", "float"),
        ("red", "uchar"),
        ("green", "uchar"),
        ("blue", "uchar"),
        ("source_group", "uint"),
        ("source_scan", "uint"),
        ("source_angle", "int"),
    ]
    if vertex_count is None or properties != expected:
        raise ValueError("source PLY does not have the expected MAF measured-row schema")
    expected_bytes = offset + vertex_count * PLY_DTYPE.itemsize
    if path.stat().st_size != expected_bytes:
        raise ValueError("source PLY size does not match its vertex table")
    return np.memmap(path, mode="r", dtype=PLY_DTYPE, offset=offset, shape=(vertex_count,)), offset


def validate_inputs(source: Path, merge_path: Path) -> dict[str, Any]:
    if sha256(source) != SOURCE_SHA256:
        raise ValueError("source hash does not match the frozen MAF back group")
    if sha256(merge_path) != MERGE_MANIFEST_SHA256:
        raise ValueError("merge manifest hash does not match the frozen MAF bilateral export")
    merge = json.loads(merge_path.read_text())
    if merge.get("schema") != "maf-three-library-merge/v1":
        raise ValueError("merge manifest has an unexpected schema")
    if merge.get("id") != DATASET_ID or merge.get("revision") != REVISION:
        raise ValueError("merge manifest identifies a different MAF dataset revision")
    if merge.get("source_archive", {}).get("sha256") != ARCHIVE_SHA256:
        raise ValueError("merge manifest identifies a different source archive")
    if merge.get("output", {}).get("sha256") != MERGED_SHA256 or merge.get("points") != MERGED_POINTS:
        raise ValueError("merge manifest does not identify the frozen three-group export")
    sources = merge.get("sources", [])
    if not any(
        item.get("sha256") == SOURCE_SHA256 and item.get("points") == SOURCE_POINTS
        for item in sources
    ):
        raise ValueError("merge manifest does not include the authoritative back group")
    groups = merge.get("registration", {}).get("groups", [])
    back = next((item for item in groups if item.get("id") == 1), None)
    if back is None or not np.allclose(back.get("transform"), FRAME_TRANSFORM, rtol=0, atol=1e-12):
        raise ValueError("group 1 registration does not match the frozen bilateral frame")
    if not np.allclose(FRAME_BASIS_ROWS @ FRAME_BASIS_ROWS.T, np.eye(3), atol=1e-12):
        raise AssertionError("frozen frame basis is not orthonormal")
    if not np.isclose(np.linalg.det(FRAME_BASIS_ROWS), 1.0, atol=1e-12):
        raise AssertionError("frozen frame does not preserve handedness")
    return merge


def make_reference(source: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    vertices, _ = read_vertex_table(source)
    if len(vertices) != SOURCE_POINTS:
        raise ValueError(f"source has {len(vertices):,} points; expected {SOURCE_POINTS:,}")
    if np.unique(vertices["source_group"]).tolist() != [1]:
        raise ValueError("source contains rows outside authoritative group 1")

    points = np.column_stack([vertices[name] for name in ("x", "y", "z")]).astype(np.float64)
    transformed = points @ FRAME_BASIS_ROWS.T + FRAME_TRANSFORM[:3, 3]
    source_bounds = np.array([transformed.min(axis=0), transformed.max(axis=0)])

    voxel_keys = np.floor(transformed / VOXEL_MM).astype(np.int32)
    _, indices = np.unique(voxel_keys, axis=0, return_index=True)
    indices.sort()
    if len(indices) != EXPECTED_OUTPUT_POINTS or len(indices) > MAX_OUTPUT_POINTS:
        raise ValueError(
            f"0.17 mm downsample produced {len(indices):,} points; expected {EXPECTED_OUTPUT_POINTS:,}"
        )

    selected = vertices[indices].copy()
    selected_points = transformed[indices]
    normals = np.column_stack([selected[name] for name in ("nx", "ny", "nz")]).astype(np.float64)
    transformed_normals = normals @ FRAME_BASIS_ROWS.T
    for column, name in enumerate(("x", "y", "z")):
        selected[name] = selected_points[:, column]
    for column, name in enumerate(("nx", "ny", "nz")):
        selected[name] = transformed_normals[:, column]
    output_bounds = np.array(
        [
            [float(selected[name].min()) for name in ("x", "y", "z")],
            [float(selected[name].max()) for name in ("x", "y", "z")],
        ]
    )
    return selected, source_bounds, output_bounds


def write_reference(path: Path, vertices: np.ndarray) -> None:
    header = "\n".join(
        [
            "ply",
            "format binary_little_endian 1.0",
            "comment Measured Palm V back exterior in the fitted bilateral frame; no mirroring or surface completion",
            f"element vertex {len(vertices)}",
            "property float x",
            "property float y",
            "property float z",
            "property float nx",
            "property float ny",
            "property float nz",
            "property uchar red",
            "property uchar green",
            "property uchar blue",
            "property uint source_group",
            "property uint source_scan",
            "property int source_angle",
            "end_header",
            "",
        ]
    ).encode("ascii")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
                compressed.write(header)
                compressed.write(vertices.tobytes())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_manifest(
    path: Path,
    source: Path,
    merge_path: Path,
    output: Path,
    source_bounds: np.ndarray,
    output_bounds: np.ndarray,
) -> None:
    generator = Path(__file__).resolve()
    record = {
        "schema": "palm-v-bottom-cover-reference/v1",
        "units": "millimetres",
        "source": {
            "archive_sha256": ARCHIVE_SHA256,
            "maf_dataset_id": DATASET_ID,
            "maf_revision": REVISION,
            "merge_manifest": {
                "bytes": merge_path.stat().st_size,
                "sha256": sha256(merge_path),
            },
            "merged_observation": {
                "points": MERGED_POINTS,
                "sha256": MERGED_SHA256,
                "use": "registration provenance only",
            },
            "geometry_authority": {
                "group_id": 1,
                "group_name": "back",
                "points": SOURCE_POINTS,
                "bytes": source.stat().st_size,
                "sha256": SOURCE_SHA256,
                "reason": "clean exterior observation; side groups are not admitted into reference geometry",
            },
            "excluded_groups": [
                {
                    "group_id": 2,
                    "group_name": "side1",
                    "sha256": "0a17f6da68003d533267e3dda7c7cde0eca95ea5b46b7eedd63bde6c270b2239",
                    "reason": "excluded by group selection because interior glue and fixture/clamp observations are outside the exterior CAD reference",
                },
                {
                    "group_id": 3,
                    "group_name": "side2",
                    "sha256": "87006b10777db27b23a80b4185a3b79a3344957fa1d0796c6819c5ee6a406ea7",
                    "reason": "excluded by group selection because interior glue and fixture/clamp observations are outside the exterior CAD reference",
                },
            ],
        },
        "alignment": {
            "frame": "exterior-derived bilateral world frame; existing THREE hierarchy registration retained without refinement",
            "origin_in_prepared_group_mm": FRAME_ORIGIN_MM.tolist(),
            "basis_rows": {
                "x": FRAME_BASIS_ROWS[0].tolist(),
                "y": FRAME_BASIS_ROWS[1].tolist(),
                "z": FRAME_BASIS_ROWS[2].tolist(),
            },
            "prepared_group_to_reference": FRAME_TRANSFORM.tolist(),
            "reference_to_future_cad": "identity",
        },
        "downsampling": {
            "method": "first measured source row in each floor-quantized XYZ voxel, retained in original row order",
            "voxel_mm": VOXEL_MM,
            "source_points": SOURCE_POINTS,
            "output_points": EXPECTED_OUTPUT_POINTS,
            "maximum_points": MAX_OUTPUT_POINTS,
            "preserves": ["measured position", "rotated measured normal", "RGB", "source group", "source scan", "source angle"],
            "symmetrized": False,
            "averaged": False,
            "synthetic_points": 0,
        },
        "symmetry_evidence": {
            "operation": "reflect observed back points across reference x=0 and measure nearest-neighbour residual",
            "median_mm": 0.0916,
            "p90_mm": 0.1929,
            "p95_mm": 0.2349,
            "within_0_25_mm_percent": 96.1167,
            "use": "frame-fit evidence only; observed coordinates remain asymmetric",
        },
        "source_bounds_in_reference_mm": {
            "min": source_bounds[0].tolist(),
            "max": source_bounds[1].tolist(),
            "extent": (source_bounds[1] - source_bounds[0]).tolist(),
        },
        "output": artifact(
            output,
            points=EXPECTED_OUTPUT_POINTS,
            bounds_mm={
                "min": output_bounds[0].tolist(),
                "max": output_bounds[1].tolist(),
                "extent": (output_bounds[1] - output_bounds[0]).tolist(),
            },
        ),
        "mesh": {
            "generated": False,
            "reason": "the authoritative source is an unorganized, vertex-only cloud over a thin folded shell; triangulation would choose unsupported connectivity, bridge the reset hole or scan gaps, and/or invent closure",
            "comparison_authority": output.name,
        },
        "generator": {
            "file": "references/generate_reference.py",
            "sha256": sha256(generator),
            "requirements": ["Python 3.11 or newer", "NumPy"],
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="MAF revision group 1 full.ply")
    parser.add_argument("--merge-manifest", required=True, type=Path, help="MAF bilateral export merge.json")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "scans" / "palm-v-bottom-cover-back-observed.ply.gz",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=Path(__file__).resolve().parent / "import-alignment.json",
    )
    args = parser.parse_args()
    validate_inputs(args.source, args.merge_manifest)
    vertices, source_bounds, output_bounds = make_reference(args.source)
    write_reference(args.output, vertices)
    write_manifest(
        args.manifest_output,
        args.source,
        args.merge_manifest,
        args.output,
        source_bounds,
        output_bounds,
    )
    print(json.dumps({"output": artifact(args.output, points=len(vertices)), "manifest": artifact(args.manifest_output)}))


if __name__ == "__main__":
    main()
