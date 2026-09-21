"""Convert the textured scanner PLY into a clean, self-contained GLB reference.

The source PLY stores texture coordinates per face corner rather than per vertex.
GLB stores them per vertex, so UV seams are preserved by splitting only the vertices
whose face corners use different coordinates. The largest connected component is the
light seal; the remaining tiny disconnected scan specks are deliberately discarded.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "Light seal.ply"
TEXTURE = HERE / "Light seal.png"
OUTPUT = HERE.parent.parent / "scans" / "vision-pro-light-seal-13w-reference.glb"

U = np.array((0.99844165, 0.03435446, 0.04397764), dtype=np.float32)
V = np.array((-0.01550981, -0.58617662, 0.81003483), dtype=np.float32)
W = np.array((0.05360697, -0.80945460, -0.58473032), dtype=np.float32)
DATUM = np.column_stack((U, V, W))


def _pad4(data: bytes, fill: bytes = b"\0") -> bytes:
    return data + fill * ((-len(data)) % 4)


def _read() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    raw = SOURCE.read_bytes()
    header_end = raw.index(b"end_header\n") + len(b"end_header\n")
    header = raw[:header_end].decode("ascii")
    vertex_count = int(next(line.split()[2] for line in header.splitlines() if line.startswith("element vertex ")))
    face_count = int(next(line.split()[2] for line in header.splitlines() if line.startswith("element face ")))
    vertices = np.frombuffer(raw, dtype="<f4", count=vertex_count * 6, offset=header_end).reshape(vertex_count, 6)
    face_offset = header_end + vertex_count * 6 * 4
    face_dtype = np.dtype(
        [("vertex_count", "u1"), ("indices", "<i4", (3,)), ("uv_count", "u1"), ("uv", "<f4", (6,))]
    )
    faces = np.frombuffer(raw, dtype=face_dtype, count=face_count, offset=face_offset)
    if not np.all(faces["vertex_count"] == 3) or not np.all(faces["uv_count"] == 6):
        raise ValueError("Expected textured triangles with six UV values per face")
    return vertices[:, :3], vertices[:, 3:], faces["indices"], faces["uv"].reshape(-1, 3, 2)


def _dominant_component(vertex_count: int, faces: np.ndarray) -> np.ndarray:
    parent = np.arange(vertex_count, dtype=np.int32)
    sizes = np.ones(vertex_count, dtype=np.int32)

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = int(parent[item])
        return item

    def union(left: int, right: int) -> None:
        left = find(int(left))
        right = find(int(right))
        if left == right:
            return
        if sizes[left] < sizes[right]:
            left, right = right, left
        parent[right] = left
        sizes[left] += sizes[right]

    for a, b, c in faces:
        union(a, b)
        union(b, c)
    roots = np.fromiter((find(i) for i in range(vertex_count)), dtype=np.int32, count=vertex_count)
    labels, counts = np.unique(roots, return_counts=True)
    dominant = labels[int(np.argmax(counts))]
    return np.all(roots[faces] == dominant, axis=1)


def _append(buffer: bytearray, payload: bytes) -> tuple[int, int]:
    while len(buffer) % 4:
        buffer.append(0)
    offset = len(buffer)
    buffer.extend(payload)
    return offset, len(payload)


def convert() -> None:
    positions, normals, faces, face_uvs = _read()
    keep = _dominant_component(len(positions), faces)
    faces = faces[keep]
    face_uvs = face_uvs[keep]

    corner_indices = faces.reshape(-1).astype(np.uint32)
    corner_uvs = face_uvs.reshape(-1, 2).astype(np.float32)
    key_dtype = np.dtype([("vertex", "<u4"), ("u", "<u4"), ("v", "<u4")])
    keys = np.empty(len(corner_indices), dtype=key_dtype)
    keys["vertex"] = corner_indices
    keys["u"] = corner_uvs[:, 0].view(np.uint32)
    keys["v"] = corner_uvs[:, 1].view(np.uint32)
    unique, first, inverse = np.unique(keys, return_index=True, return_inverse=True)
    source_indices = unique["vertex"].astype(np.int64)
    glb_positions = np.ascontiguousarray(positions[source_indices] @ DATUM, dtype=np.float32)
    glb_normals = np.ascontiguousarray(normals[source_indices] @ DATUM, dtype=np.float32)
    glb_uvs = np.ascontiguousarray(corner_uvs[first], dtype=np.float32)
    glb_indices = np.ascontiguousarray(inverse.astype(np.uint32))

    binary = bytearray()
    views: list[dict[str, int]] = []

    def add(payload: bytes, target: int | None = None) -> int:
        offset, length = _append(binary, payload)
        view: dict[str, int] = {"buffer": 0, "byteOffset": offset, "byteLength": length}
        if target is not None:
            view["target"] = target
        views.append(view)
        return len(views) - 1

    position_view = add(glb_positions.tobytes(), 34962)
    normal_view = add(glb_normals.tobytes(), 34962)
    uv_view = add(glb_uvs.tobytes(), 34962)
    index_view = add(glb_indices.tobytes(), 34963)
    texture_bytes = TEXTURE.read_bytes()
    image_view = add(texture_bytes)

    accessors = [
        {
            "bufferView": position_view,
            "componentType": 5126,
            "count": len(glb_positions),
            "type": "VEC3",
            "min": glb_positions.min(axis=0).tolist(),
            "max": glb_positions.max(axis=0).tolist(),
        },
        {"bufferView": normal_view, "componentType": 5126, "count": len(glb_normals), "type": "VEC3"},
        {"bufferView": uv_view, "componentType": 5126, "count": len(glb_uvs), "type": "VEC2"},
        {"bufferView": index_view, "componentType": 5125, "count": len(glb_indices), "type": "SCALAR"},
    ]
    document = {
        "asset": {"version": "2.0", "generator": "nurb light-seal PLY converter"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "Light seal 13W scan"}],
        "meshes": [
            {
                "name": "Dominant textured shell",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                        "indices": 3,
                        "material": 0,
                    }
                ],
            }
        ],
        "materials": [
            {
                "name": "Original scan texture",
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": 0},
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.9,
                },
                "doubleSided": True,
            }
        ],
        "textures": [{"sampler": 0, "source": 0}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
        "images": [{"name": "Light seal.png", "mimeType": "image/png", "bufferView": image_view}],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": views,
        "accessors": accessors,
    }
    json_chunk = _pad4(json.dumps(document, separators=(",", ":")).encode("utf-8"), b" ")
    binary_chunk = _pad4(bytes(binary))
    total = 12 + 8 + len(json_chunk) + 8 + len(binary_chunk)
    glb = bytearray(struct.pack("<4sII", b"glTF", 2, total))
    glb.extend(struct.pack("<I4s", len(json_chunk), b"JSON"))
    glb.extend(json_chunk)
    glb.extend(struct.pack("<I4s", len(binary_chunk), b"BIN\0"))
    glb.extend(binary_chunk)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(glb)
    print(
        f"wrote {OUTPUT}: {len(glb_positions):,} seam-preserving vertices, "
        f"{len(faces):,} triangles, {len(positions) - len(np.unique(faces)):,} speck vertices removed"
    )


if __name__ == "__main__":
    convert()
