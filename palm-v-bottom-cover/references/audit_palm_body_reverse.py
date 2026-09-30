import gzip, io, json, hashlib
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree
import argparse

parser = argparse.ArgumentParser(
    description="Deterministic CAD-to-observed vertex-distance upper-bound audit"
)
parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument(
    "--mesh",
    type=Path,
    required=True,
    help="Auxiliary CAD tessellation used for sampling; not a validated manufacturing mesh",
)
args = parser.parse_args()
root = args.project
mesh = trimesh.load(args.mesh)
source = trimesh.load(
    io.BytesIO(
        gzip.decompress((root / "scans/palm-v-body-observed.ply.gz").read_bytes())
    ),
    file_type="ply",
    process=False,
)
source = max(source.split(only_watertight=False), key=lambda q: q.area)
T = np.array(
    json.loads((root / "references/palm-new-reference-frames.json").read_text())[
        "body"
    ]["source_to_canonical"]
)
source.apply_transform(T)
p, fi = trimesh.sample.sample_surface(mesh, 12000, seed=718)
n = mesh.face_normals[fi]
d = cKDTree(source.vertices).query(p)[0]
regions = {
    "all_cad": np.ones(len(p), bool),
    "main_outer_rails": (abs(p[:, 0]) > 35)
    & (abs(p[:, 1]) < 30)
    & (n[:, 0] * np.sign(p[:, 0]) > 0.45),
    "front_rails": (abs(p[:, 0]) > 33) & (abs(p[:, 1]) < 30) & (p[:, 2] > 2),
    "rear_rails_and_master_seats": (abs(p[:, 0]) > 33)
    & (abs(p[:, 1]) < 30)
    & (p[:, 2] < -2),
    "upper_bridge": p[:, 1] > 49,
    "connector_end": p[:, 1] < -49,
    "lower_flare": (abs(p[:, 0]) > 33) & (p[:, 1] < -35) & (p[:, 1] > -51),
    "asymmetric_internal_features": (abs(p[:, 0]) < 34)
    & (p[:, 1] > -43)
    & (p[:, 1] < 48),
}
report = {
    "method": "12000 deterministic area-weighted CAD samples, seed718, nearest original observed vertex. Vertex distance is an upper bound on nearest original triangle distance, not exact mesh deviation. Master-derived rear seats deliberately depart from independent scan fit.",
    "analysis_mesh_sha256": hashlib.sha256(args.mesh.read_bytes()).hexdigest(),
    "observed_ply_gz_sha256": hashlib.sha256((root / "scans/palm-v-body-observed.ply.gz").read_bytes()).hexdigest(),
    "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "analysis_mesh_is_deliverable": False,
    "step_sha256": hashlib.sha256(
        (root / "build/palm_v_body.step").read_bytes()
    ).hexdigest(),
    "regions": {},
}
for name, mask in regions.items():
    q = d[mask]
    report["regions"][name] = {
        "samples": len(q),
        "p50_mm": float(np.median(q)),
        "p95_mm": float(np.quantile(q, 0.95)),
        "max_mm": float(q.max()),
    }
(root / "build/palm-body-reverse-fit.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(json.dumps(report, indent=2), flush=True)
