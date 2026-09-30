from pathlib import Path
import hashlib, json
import numpy as np, trimesh
from scipy.spatial import cKDTree
import argparse, gzip, io

parser = argparse.ArgumentParser(
    description="Independently sample observed body regions against exported CAD triangles"
)
parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument("--mesh", type=Path, required=True)
parser.add_argument("--step", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = args.project
raw = root / "scans/palm-v-body-observed.ply.gz"
source = trimesh.load(
    io.BytesIO(gzip.decompress(raw.read_bytes())), file_type="ply", process=False
)
source = max(source.split(only_watertight=False), key=lambda q: q.area)
frame = json.loads((root / "references/palm-new-reference-frames.json").read_text())[
    "body"
]["source_to_canonical"]
source.apply_transform(np.array(frame))
v = source.vertices
n = source.vertex_normals
cad = trimesh.load(args.mesh, process=False)
tri = cad.triangles
nondegenerate = trimesh.triangles.area(tri) > 1e-12
skipped_degenerate = int((~nondegenerate).sum())
tri = tri[nondegenerate]
tree = cKDTree(tri.mean(axis=1))
rng = np.random.default_rng(31)
regions = {
    "main_outer_rails": (abs(v[:, 0]) > 35)
    & (abs(v[:, 1]) < 30)
    & (n[:, 0] * np.sign(v[:, 0]) > 0.45),
    "main_full_C_sections": (abs(v[:, 0]) > 32) & (abs(v[:, 1]) < 30),
    "front_seating_rails": (abs(v[:, 0]) > 33) & (abs(v[:, 1]) < 30) & (v[:, 2] > 2),
    "rear_seating_rails": (abs(v[:, 0]) > 33) & (abs(v[:, 1]) < 30) & (v[:, 2] < -2),
    "lower_flare": (abs(v[:, 0]) > 33) & (v[:, 1] < -35) & (v[:, 1] > -51),
    "upper_bridge": v[:, 1] > 49,
    "connector_end": v[:, 1] < -49,
    "asymmetric_internal_tabs": (abs(v[:, 0]) < 34) & (v[:, 1] > -43) & (v[:, 1] < 48),
}
report = {
    "step_sha256": hashlib.sha256((args.step).read_bytes()).hexdigest(),
    "mesh_sha256": hashlib.sha256((args.mesh).read_bytes()).hexdigest(),
    "source_ply_gz_sha256": hashlib.sha256((raw).read_bytes()).hexdigest(),
    "method": "Original vertex sample seed31, point-to-triangle distance over128 nearest triangle centroids; candidate acceleration is approximate on elongated triangles. Not a certified global nearest-surface bound.",
    "skipped_zero_area_triangles": skipped_degenerate,
    "regions": {},
}
for name, mask in regions.items():
    ids = np.flatnonzero(mask)
    ids = rng.choice(ids, min(5000, len(ids)), replace=False)
    points = v[ids]
    ds = []
    for q in np.array_split(points, 25):
        _, ix = tree.query(q, k=min(128, len(tri)))
        p = np.repeat(q, ix.shape[1], axis=0)
        closest = trimesh.triangles.closest_point(tri[ix.ravel()], p)
        d = np.linalg.norm(closest - p, axis=1).reshape(len(q), -1).min(axis=1)
        ds.extend(d)
    ds = np.array(ds)
    report["regions"][name] = {
        "sampled_vertices": len(ds),
        "p50_mm": float(np.median(ds)),
        "p95_mm": float(np.quantile(ds, 0.95)),
        "max_mm": float(ds.max()),
        "fraction_within_0_4mm": float(np.mean(ds <= 0.4)),
    }
    print(name, report["regions"][name], flush=True)
args.output.write_text(json.dumps(report, indent=2) + "\n")
