"""Fit a smooth nominal front skin and feature locations from the assembled scan."""

from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.interpolate import BSpline
from scipy.sparse import coo_matrix, vstack, kron, diags, eye
from scipy.sparse.linalg import lsmr
from scipy.stats import binned_statistic_2d

from read_palm_reference import whole_reference

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "scans/palm-v-rough-observed.ply.gz"

q, normals, frame = whole_reference()
x, y, z = q.T
# Keep the visible outer skin and outward rolled sides, excluding lower
# chassis ledges that share its XY footprint in the assembled scan.
side = (abs(x) > 35) & (normals[:, 0] * np.sign(x) > 0.25)
end = (abs(y) > 49) & (normals[:, 1] * np.sign(y) > 0.25)
mask = (z > 1.15) & ((normals[:, 2] > 0.15) | side | end)
mask &= (z > 2.6) | side | end
mask &= ~((abs(x) < 29.3) & (y > -33) & (y < 47))
mask &= ~((abs(x) < 6) & (y < -36) & (y > -54))
for cx, cy in [(13, -44), (26, -42), (-13, -44), (-26, -42)]:
    mask &= (x - cx) ** 2 + (y - cy) ** 2 > 5.2**2
q = q[mask]
q = np.vstack([q, q * np.array([-1, 1, 1])])


def smooth(a):
    a = np.clip(a, 0, 1)
    return a * a * (3 - 2 * a)


def unroll(p):
    depth = np.maximum(5.3 - p[:, 2], 0)
    return np.c_[
        p[:, 0] + np.sign(p[:, 0]) * 0.9 * depth * smooth((abs(p[:, 0]) - 32) / 7),
        p[:, 1] + np.sign(p[:, 1]) * 0.9 * depth * smooth((abs(p[:, 1]) - 44) / 12),
    ]


uv = unroll(q)
edges = [np.arange(-46, 46.51, 0.5), np.arange(-64, 64.51, 0.5)]
med = np.stack(
    [
        binned_statistic_2d(
            uv[:, 0], uv[:, 1], q[:, axis], statistic="median", bins=edges
        ).statistic
        for axis in range(3)
    ],
    axis=-1,
)
uvmed = np.stack(
    [
        binned_statistic_2d(
            uv[:, 0], uv[:, 1], uv[:, axis], statistic="median", bins=edges
        ).statistic
        for axis in range(2)
    ],
    axis=-1,
)
good = np.isfinite(med[:, :, 0])
obs = med[good]
fit_uv = uvmed[good]
positive = [0, 25, 30, 33, 35, 37, 39, 40, 41, 42, 43, 44, 45, 46]
xb = np.array([-v for v in positive[:0:-1]] + positive, dtype=float)
yb = np.array(
    [
        -64,
        -62,
        -61,
        -60,
        -59,
        -58,
        -57,
        -56,
        -54,
        -52,
        -49,
        -44,
        -36,
        0,
        44,
        50,
        54,
        56,
        58,
        59,
        60,
        61,
        62,
        64.0,
    ]
)
tx = np.r_[[xb[0]] * 3, xb, [xb[-1]] * 3]
ty = np.r_[[yb[0]] * 3, yb, [yb[-1]] * 3]
nx = len(tx) - 4
ny = len(ty) - 4


def basis(points):
    bx = BSpline.design_matrix(points[:, 0], tx, 3)
    by = BSpline.design_matrix(points[:, 1], ty, 3)
    rows = []
    cols = []
    vals = []
    for k in range(len(points)):
        for i, a in zip(
            bx.indices[bx.indptr[k] : bx.indptr[k + 1]],
            bx.data[bx.indptr[k] : bx.indptr[k + 1]],
        ):
            for j, b in zip(
                by.indices[by.indptr[k] : by.indptr[k + 1]],
                by.data[by.indptr[k] : by.indptr[k + 1]],
            ):
                rows.append(k)
                cols.append(i * ny + j)
                vals.append(a * b)
    return coo_matrix((vals, (rows, cols)), shape=(len(points), nx * ny)).tocsr()


def diff(n):
    return diags(
        [np.ones(n - 2), -2 * np.ones(n - 2), np.ones(n - 2)],
        [0, 1, 2],
        shape=(n - 2, n),
    )


A = basis(fit_uv)
R = vstack([kron(diff(nx), eye(ny)), kron(eye(nx), diff(ny))]).tocsr()
gx = np.array([tx[i + 1 : i + 4].mean() for i in range(nx)])
gy = np.array([ty[i + 1 : i + 4].mean() for i in range(ny)])
xx, yy = np.meshgrid(gx, gy, indexing="ij")
prior = np.stack([xx, yy, np.full_like(xx, 5.0)], axis=-1).reshape(-1, 3)
w = np.ones(len(obs))
coef = prior.copy()
for _ in range(5):
    system = vstack([A.multiply(w[:, None]), R * 0.12, eye(nx * ny) * 0.0001])
    for axis in range(3):
        rhs = np.r_[
            w * (obs[:, axis] - A @ prior[:, axis]), np.zeros(R.shape[0] + nx * ny)
        ]
        coef[:, axis] = (
            prior[:, axis] + lsmr(system, rhs, atol=1e-10, btol=1e-10, maxiter=3000)[0]
        )
    residual = np.linalg.norm(A @ coef - obs, axis=1)
    w = np.minimum(1, 0.15 / np.maximum(residual, 1e-10))
coef = coef.reshape(nx, ny, 3)
mirror = coef[::-1].copy()
mirror[:, :, 0] *= -1
coef = (coef + mirror) / 2
residual = np.linalg.norm(A @ coef.reshape(-1, 3) - obs, axis=1)
result = {
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "frame": frame,
    "x_knots": tx.tolist(),
    "y_knots": ty.tolist(),
    "xyz_coefficients": coef.tolist(),
    "measurement_mask": "Positive-depth visible front skin and outward rolled side/end normals. Lower chassis ledges, display and keys excluded. Mirrored0.5mm unrolled cells, robust0.15mm 3D residual weighting.",
    "parameterization": "u=x+sign(x)*.9*max(5.3-z,0)*smoothstep((abs(x)-32)/7); v analogous with(abs(y)-44)/12",
    "sample_cells": len(obs),
    "residual_abs_mm": dict(
        zip(["median", "p95", "p99"], np.quantile(residual, [0.5, 0.95, 0.99]).tolist())
    ),
}
(ROOT / "references/front-fit.json").write_text(json.dumps(result, indent=2) + "\n")
np.savez(
    ROOT / "build/front-fit-evidence.npz",
    observations=obs,
    prediction=A @ coef.reshape(-1, 3),
    parameters=fit_uv,
)
print(result["residual_abs_mm"])
