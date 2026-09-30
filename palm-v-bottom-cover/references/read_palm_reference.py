"""Read preserved original triangle coordinates into the frozen bilateral frame."""

from pathlib import Path
import gzip
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def whole_reference():
    source = ROOT / "scans/palm-v-rough-observed.ply.gz"
    with gzip.open(source, "rb") as stream:
        count = face_count = None
        while True:
            line = stream.readline()
            if not line:
                raise ValueError("PLY header is incomplete")
            if line.startswith(b"element vertex "):
                count = int(line.split()[-1])
            if line.startswith(b"element face "):
                face_count = int(line.split()[-1])
            if line == b"end_header\n":
                break
        if count is None or face_count is None:
            raise ValueError("Expected original triangulated PLY counts")
        raw = (
            np.frombuffer(stream.read(count * 12), dtype="<f4")
            .reshape(-1, 3)
            .astype(float)
        )
        dtype = np.dtype(
            [
                ("n", "u1"),
                ("indices", "<i4", (3,)),
                ("normal", "<f4", (3,)),
                ("attribute", "<u2"),
                ("source", "<u4"),
            ]
        )
        records = np.frombuffer(stream.read(face_count * dtype.itemsize), dtype=dtype)
        if np.any(records["n"] != 3):
            raise ValueError("Reference contains non-triangle faces")
        faces = records["indices"]
    triangles = raw[faces]
    face_normals = np.cross(
        triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    )
    normals = np.zeros_like(raw)
    for column in range(3):
        np.add.at(normals, faces[:, column], face_normals)
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
    frame = json.loads(
        (ROOT / "references/palm-new-reference-frames.json").read_text()
    )["whole"]
    transform = np.array(frame["source_to_canonical"])
    if not np.allclose(
        transform[:3, :3].T @ transform[:3, :3], np.eye(3), atol=1e-8
    ) or not np.isclose(np.linalg.det(transform[:3, :3]), 1):
        raise ValueError("Reference pose is not a proper rigid transform")
    points = raw @ transform[:3, :3].T + transform[:3, 3]
    normals = normals @ transform[:3, :3].T
    return points, normals, frame
