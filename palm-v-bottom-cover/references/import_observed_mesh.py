#!/usr/bin/env python3
"""Preserve measured THREE scan triangles in the Palm bilateral frame.

No fusion, resampling, new connectivity, symmetry or hole filling is applied.
Side-return selection is a reproducible spatial observation mask, not proof
that every retained sample is uncontaminated metal.
"""

from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import pathlib
import zipfile
import numpy as np

ARCHIVE_SHA256 = "52900e9ad09d24b552cea788ea0dbb743e9fa22dde0095cad362bf95ddb1da3f"
FRAME = np.array(
    [
        [
            -0.9921722997277009,
            -0.09816707037842172,
            0.07718389693688062,
            0.5127422980524605,
        ],
        [
            0.11743632027012417,
            -0.5233330643547212,
            0.8439971649445928,
            2.0664488040153772,
        ],
        [
            -0.042459843787487545,
            0.8464548009471121,
            0.5307649495013088,
            -0.06027522193935719,
        ],
        [0, 0, 0, 1],
    ]
)
VDTYPE = np.dtype(
    [(n, "<f4") for n in ("x", "y", "z", "nx", "ny", "nz")]
    + [("source_group", "<u4"), ("source_scan", "<u4"), ("source_vertex", "<u4")]
)
FDTYPE = np.dtype(
    [
        ("count", "u1"),
        ("indices", "<i4", (3,)),
        ("source_scan", "<u4"),
        ("source_face", "<u4"),
    ]
)


def sha(path: pathlib.Path) -> str:
    """Hash complete artifact content, including deterministic gzip bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def matrix(node: dict) -> np.ndarray:
    """Convert THREE axis-angle radians and millimetre translation to a pose."""
    v = np.asarray(node.get("rotation", [0, 0, 0]), float)
    if v.shape != (3,) or not np.isfinite(v).all():
        raise ValueError("THREE rotation must contain three finite axis-angle values")
    a = np.linalg.norm(v)
    m = np.eye(4)
    if a > 1e-12:
        x, y, z = v / a
        k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
        m[:3, :3] = np.eye(3) + np.sin(a) * k + (1 - np.cos(a)) * (k @ k)
    translation = np.asarray(node.get("translation", [0, 0, 0]), dtype=float)
    if translation.shape != (3,) or not np.isfinite(translation).all():
        raise ValueError(
            "THREE translation must contain three finite millimetre values"
        )
    m[:3, 3] = translation
    return m


def walk(node: dict, parent: np.ndarray):
    """Compose all hierarchy ancestors in their original order."""
    t = parent @ matrix(node)
    if "scan" in node:
        yield node["scan"], t
    for c in node.get("groups", []):
        yield from walk(c, t)


def read_scan(z: zipfile.ZipFile, scan: int) -> tuple[np.ndarray, np.ndarray]:
    """Read the original fixed schema without guessing surface connectivity."""
    b = z.read(f"Scans/Scan-{scan}/Scan-{scan}.ply")
    end = b.index(b"end_header\n") + len(b"end_header\n")
    lines = b[:end].decode("ascii").splitlines()
    if lines[:2] != ["ply", "format binary_little_endian 1.0"]:
        raise ValueError(f"Scan {scan}: expected binary little-endian PLY")
    nv = int(
        next(line.split()[-1] for line in lines if line.startswith("element vertex"))
    )
    nf = int(
        next(line.split()[-1] for line in lines if line.startswith("element face"))
    )
    names = []
    in_v = False
    for line in lines:
        if line.startswith("element "):
            in_v = line.startswith("element vertex")
        elif in_v and line.startswith("property "):
            _, typ, name = line.split()
            if typ != "float":
                raise ValueError(
                    f"Scan {scan}: expected float vertex property, got {typ}"
                )
            names.append(name)
    d = np.dtype([(n, "<f4") for n in names])
    v = np.frombuffer(b, dtype=d, count=nv, offset=end)
    fd = np.dtype([("count", "u1"), ("indices", "<i4", (3,))])
    f = np.frombuffer(b, dtype=fd, count=nf, offset=end + nv * d.itemsize)
    if not np.all(f["count"] == 3) or end + nv * d.itemsize + nf * 13 != len(b):
        raise ValueError(
            f"Scan {scan}: PLY must contain triangle-only faces and no trailing data"
        )
    if not len(f) or f["indices"].min() < 0 or f["indices"].max() >= nv:
        raise ValueError(f"Scan {scan}: missing faces or out-of-range vertex indices")
    return v, f["indices"]


def write_mesh(path, vertices, faces):
    lines = [
        "ply",
        "format binary_little_endian 1.0",
        "comment Original observed triangles; no closure or remeshing",
        f"element vertex {len(vertices)}",
    ]
    lines += ["property float " + n for n in ("x", "y", "z", "nx", "ny", "nz")] + [
        "property uint " + n for n in ("source_group", "source_scan", "source_vertex")
    ]
    lines += [
        f"element face {len(faces)}",
        "property list uchar int vertex_indices",
        "property uint source_scan",
        "property uint source_face",
        "end_header",
        "",
    ]
    with open(path, "wb") as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6
        ) as out:
            out.write("\n".join(lines).encode())
            out.write(vertices.tobytes())
            out.write(faces.tobytes())


def side_return_mask(points):
    """Retain observed perimeter bands while rejecting distant scan fixtures.

    This intentionally does not classify all glue. The manifest exposes the
    region so a later local material mask can refine it without altering source.
    """
    x, y, z = points.T
    return (
        (abs(x) < 42)
        & (abs(y) < 59)
        & (z > -1.5)
        & (z < 5.5)
        & ((abs(x) > 34) | (abs(y) > 49) | ((y < -43) & (abs(x) < 19)))
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=pathlib.Path)
    ap.add_argument("--output-dir", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if sha(args.archive) != ARCHIVE_SHA256:
        raise ValueError(
            "Archive hash differs from the measured Palm V source; "
            "supply the original project ZIP"
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    chunks = {name: [[], [], 0] for name in ["back", "side-returns", "comparison"]}
    records = []
    with zipfile.ZipFile(args.archive) as z:
        p = json.loads(
            z.read(
                next(
                    n
                    for n in z.namelist()
                    if n.startswith("Project-") and n.endswith(".json")
                )
            )
        )
        root = p["groups"]
        for gid, group in enumerate(root["groups"], 1):
            for scan, t in walk(group, matrix(root)):
                v, f = read_scan(z, scan)
                t = FRAME @ t
                p = (
                    np.column_stack([v[n] for n in ["x", "y", "z"]]) @ t[:3, :3].T
                    + t[:3, 3]
                )
                n = np.column_stack([v[k] for k in ["nx", "ny", "nz"]]) @ t[:3, :3].T
                keep = np.isfinite(p).all(1) & np.isfinite(n).all(1)
                target = "back" if gid == 1 else "side-returns"
                if gid != 1:
                    keep &= side_return_mask(p)
                face_ids = np.flatnonzero(keep[f].all(1))
                f = f[face_ids]
                ids = np.unique(f)
                remap = np.full(len(v), -1, dtype=np.int32)
                remap[ids] = np.arange(len(ids))
                vv = np.empty(len(ids), VDTYPE)
                for j, k in enumerate(["x", "y", "z"]):
                    vv[k] = p[ids, j]
                for j, k in enumerate(["nx", "ny", "nz"]):
                    vv[k] = n[ids, j]
                vv["source_group"] = gid
                vv["source_scan"] = scan
                vv["source_vertex"] = ids
                ff = np.empty(len(f), FDTYPE)
                ff["count"] = 3
                ff["indices"] = remap[f] + chunks[target][2]
                ff["source_scan"] = scan
                ff["source_face"] = face_ids
                chunks[target][0].append(vv)
                chunks[target][1].append(ff)
                chunks[target][2] += len(vv)
                if scan in (17, 1, 10):
                    cf = ff.copy()
                    cf["indices"] = remap[f] + chunks["comparison"][2]
                    chunks["comparison"][0].append(vv)
                    chunks["comparison"][1].append(cf)
                    chunks["comparison"][2] += len(vv)
                records.append(
                    dict(
                        group=gid,
                        scan=scan,
                        vertices=len(vv),
                        faces=len(ff),
                        transform=t.tolist(),
                    )
                )
    for label, (vs, fs, _) in chunks.items():
        v = np.concatenate(vs)
        f = np.concatenate(fs)
        path = args.output_dir / f"palm-v-bottom-cover-{label}-triangles.ply.gz"
        write_mesh(path, v, f)
        outputs[label] = dict(
            file=path.name,
            sha256=sha(path),
            bytes=path.stat().st_size,
            vertices=len(v),
            faces=len(f),
            bounds=[
                [float(v[k].min()) for k in ["x", "y", "z"]],
                [float(v[k].max()) for k in ["x", "y", "z"]],
            ],
        )
    manifest = dict(
        schema="palm-original-triangles/v1",
        archive_sha256=ARCHIVE_SHA256,
        units="mm",
        frame=FRAME.tolist(),
        operations=[
            "compose original THREE hierarchy",
            "rigid bilateral frame",
            "subset original faces only",
        ],
        side_mask=(
            "All triangle vertices within |x|<42, |y|<59, -1.5<z<5.5 and "
            "(|x|>34 or |y|>49 or (y<-43 and |x|<19)); "
            "candidate observed returns, possible residual glue"
        ),
        comparison_scans=[17, 1, 10],
        comparison_scope=(
            "one complete back observation and masked side returns from two "
            "independent side groups; all selected scan triangles retained "
            "except explicit spatial side mask"
        ),
        packaged_outputs=["comparison"],
        original_vertex_indices=True,
        original_face_indices=True,
        scan_records=records,
        outputs=outputs,
    )
    (args.output_dir / "original-triangle-provenance.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
