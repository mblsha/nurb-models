"""Rigidly place independently observed Palm subassemblies in the whole-scan frame."""

from pathlib import Path
import json
import gzip
import numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from import_observed_mesh import VDTYPE

from read_palm_reference import whole_reference

ROOT = Path(__file__).resolve().parents[1]

w, wn, whole_frame = whole_reference()
p = ROOT / "scans/palm-v-bottom-cover-comparison-triangles.ply.gz"
with gzip.open(p, "rb") as f:
    while True:
        line = f.readline()
        if line.startswith(b"element vertex "):
            count = int(line.split()[-1])
        if line == b"end_header\n":
            break
    rows = np.frombuffer(f.read(count * VDTYPE.itemsize), VDTYPE)
q = np.column_stack([rows[k] for k in ["x", "y", "z"]])
keep = (
    (rows["source_group"] == 1)
    & (abs(q[:, 0]) < 38)
    & (q[:, 1] > -47)
    & (q[:, 1] < 54)
    & (q[:, 2] < 2)
)
q = q[keep][::6]
m = (wn[:, 2] < -0.3) & (w[:, 2] < -2.5) & (abs(w[:, 0]) < 39)
target = w[m]
normals = wn[m]
tree = cKDTree(target)
state = np.array([0.0, 1.0, -6.0])


def placed(p, s):
    return p @ Rotation.from_rotvec([s[0], 0, 0]).as_matrix().T + np.array(
        [0, s[1], s[2]]
    )


for _ in range(15):
    current = placed(q, state)
    dist, idx = tree.query(current)
    good = dist < 0.9
    fixed = target[idx[good]]
    n = normals[idx[good]]
    source = q[good]

    def residual(s):
        delta = placed(source, s) - fixed
        return np.r_[np.sum(delta * n, axis=1), 0.12 * delta[:, 1]]

    solved = least_squares(
        residual,
        state,
        loss="soft_l1",
        f_scale=0.12,
        bounds=([-np.pi / 90, -4, -8], [np.pi / 90, 4, -4]),
    )
    if np.linalg.norm(solved.x - state) < 1e-7:
        break
    state = solved.x
res, idx = tree.query(placed(q, state))
result = {
    "rear_cover": {
        "rotation_x_degrees": float(np.degrees(state[0])),
        "translation_mm": [0, float(state[1]), float(state[2])],
        "method": "Rigid Rx/Y/Z point-to-plane alignment of original exterior reference triangles to rough whole rear; X mirror plane preserved. Same transform applies to nominal rear without fitting away deliberate straightening.",
        "reference_to_whole_nn_mm": dict(
            zip(["median", "p95", "p99"], np.quantile(res, [0.5, 0.95, 0.99]).tolist())
        ),
        "points": len(q),
    },
    "whole_frame": json.loads(
        (ROOT / "references/palm-new-reference-frames.json").read_text()
    )["whole"],
}
(ROOT / "references/palm-assembly-poses.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(result["rear_cover"])
