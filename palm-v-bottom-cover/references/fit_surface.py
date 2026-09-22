"""Fit a bilateral parametric exterior, unrolling steep rims in parameter space."""

import argparse
import json
import zipfile
from pathlib import Path
import numpy as np
from scipy.interpolate import BSpline
from scipy.sparse import coo_matrix, vstack, kron, eye, diags
from scipy.sparse.linalg import lsmr

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--archive",
    type=Path,
    help="Original THREE project ZIP; its frozen SHA-256 is checked",
)
parser.add_argument(
    "--cache-dir", type=Path, help="Prepared group NPZ directory for local development"
)
args = parser.parse_args()
if args.archive is None and args.cache_dir is None:
    parser.error("Supply --archive with the original THREE project ZIP")


def observed_group(group_id):
    if args.archive is None:
        return dict(np.load(args.cache_dir / f"group-{group_id}.npz"))
    from import_observed_mesh import ARCHIVE_SHA256, FRAME, sha, matrix, walk, read_scan

    if sha(args.archive) != ARCHIVE_SHA256:
        raise ValueError("The source archive differs from the frozen measured project")
    points = []
    normals = []
    with zipfile.ZipFile(args.archive) as archive:
        project = json.loads(
            archive.read(
                next(
                    n
                    for n in archive.namelist()
                    if n.startswith("Project-") and n.endswith(".json")
                )
            )
        )
        root = project["groups"]
        group = root["groups"][group_id - 1]
        for scan, pose in walk(group, matrix(root)):
            vertices, _ = read_scan(archive, scan)
            pose = FRAME @ pose
            points.append(
                np.column_stack([vertices[k] for k in ("x", "y", "z")]) @ pose[:3, :3].T
                + pose[:3, 3]
            )
            normals.append(
                np.column_stack([vertices[k] for k in ("nx", "ny", "nz")])
                @ pose[:3, :3].T
            )
    return {"points": np.concatenate(points), "normals": np.concatenate(normals)}


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def uv_of(p):
    z = (p[:, 2] + np.sqrt(p[:, 2] ** 2 + 0.01)) / 2
    return np.c_[
        p[:, 0] + np.sign(p[:, 0]) * 0.9 * z * smooth((abs(p[:, 0]) - 33) / 6),
        p[:, 1] + np.sign(p[:, 1]) * 0.9 * z * smooth((abs(p[:, 1]) - 42) / 12),
    ]


positive = [
    0,
    4,
    8,
    12,
    16,
    20,
    24,
    28,
    31,
    33,
    35,
    36,
    37,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    46,
]
xb = np.array([-v for v in positive[:0:-1]] + positive, float)
yb = np.array(
    [
        -64,
        -63,
        -62,
        -61,
        -60,
        -59,
        -58,
        -57,
        -56,
        -55,
        -54,
        -53,
        -52,
        -51,
        -50,
        -49,
        -48,
        -47,
        -46,
        -45,
        -42,
        -38,
        -34,
        -30,
        -26,
        -22,
        -18,
        -14,
        -10,
        -6,
        -2,
        2,
        6,
        10,
        12,
        13,
        14,
        14.5,
        15,
        15.5,
        16,
        17,
        18,
        20,
        23,
        26,
        30,
        34,
        38,
        42,
        46,
        50,
        52,
        53,
        54,
        55,
        56,
        57,
        58,
        59,
        60,
        61,
    ],
    float,
)
tx = np.r_[np.repeat(xb[0], 3), xb, np.repeat(xb[-1], 3)]
ty = np.r_[np.repeat(yb[0], 3), yb, np.repeat(yb[-1], 3)]
rows = []
for group in (1, 2, 3):
    d = observed_group(group)
    p = d["points"]
    n = d["normals"]
    k = (abs(p[:, 0]) < 42) & (abs(p[:, 1]) < 58) & (p[:, 2] > -1.2) & (p[:, 2] < 5.1)
    outward = n[:, 0] * np.sign(p[:, 0]) * (abs(p[:, 0]) > 37) + n[:, 1] * np.sign(
        p[:, 1]
    ) * (abs(p[:, 1]) > 52)
    k &= (n[:, 2] < -0.3) | ((outward > 0.65) & (n[:, 2] < 0.35))
    p = p[k].copy()
    p[:, 0] = abs(p[:, 0])
    uv = uv_of(p)
    q = np.c_[uv, p]
    cells = np.floor(q[:, :2] / 0.40).astype(int)
    keys = cells[:, 0] * 1000 + cells[:, 1] + 500
    order = np.argsort(keys)
    q = q[order]
    keys = keys[order]
    starts = np.r_[0, np.flatnonzero(np.diff(keys)) + 1]
    ends = np.r_[starts[1:], len(q)]
    for a, b in zip(starts, ends):
        if b - a >= 3:
            rows.append([*np.median(q[a:b], axis=0), group, b - a])
samples = np.array(rows)
mirror = samples.copy()
mirror[:, 0] *= -1
mirror[:, 2] *= -1
samples = np.vstack((samples, mirror))
Bx = BSpline.design_matrix(samples[:, 0], tx, 3)
By = BSpline.design_matrix(samples[:, 1], ty, 3)
nx = Bx.shape[1]
ny = By.shape[1]
ri = []
ci = []
va = []
for j in range(len(samples)):
    for ix, vx in zip(
        Bx.indices[Bx.indptr[j] : Bx.indptr[j + 1]],
        Bx.data[Bx.indptr[j] : Bx.indptr[j + 1]],
    ):
        for iy, vy in zip(
            By.indices[By.indptr[j] : By.indptr[j + 1]],
            By.data[By.indptr[j] : By.indptr[j + 1]],
        ):
            ri.append(j)
            ci.append(ix * ny + iy)
            va.append(vx * vy)
A = coo_matrix((va, (ri, ci)), shape=(len(samples), nx * ny)).tocsr()


def diff(n):
    return diags(
        [np.ones(n - 2), -2 * np.ones(n - 2), np.ones(n - 2)],
        [0, 1, 2],
        shape=(n - 2, n),
    )


R = vstack((kron(diff(nx), eye(ny)), kron(eye(nx), diff(ny)))).tocsr()
grx = np.array([tx[i + 1 : i + 4].mean() for i in range(nx)])
gry = np.array([ty[i + 1 : i + 4].mean() for i in range(ny)])
basecoef = np.stack(
    (
        np.repeat(grx[:, None], ny, axis=1),
        np.repeat(gry[None, :], nx, axis=0),
        np.zeros((nx, ny)),
    ),
    axis=2,
).reshape(-1, 3)
# Fit a deformation from a flat parametric sheet, avoiding unconstrained XYZ collapse.
target = samples[:, 2:5] - A @ basecoef
base = np.where(samples[:, 5] == 1, 1.0, 0.7)
weights = base.copy()
delta = np.zeros((nx * ny, 3))
for it in range(4):
    system = vstack(
        [A.multiply(weights[:, None]), R * 0.25, eye(nx * ny) * 0.0005]
    ).tocsr()
    for axis in range(3):
        rhs = np.r_[weights * target[:, axis], np.zeros(R.shape[0] + nx * ny)]
        result = lsmr(system, rhs, atol=2e-7, btol=2e-7, maxiter=800, x0=delta[:, axis])
        delta[:, axis] = result[0]
    coeff = (basecoef + delta).reshape(nx, ny, 3)
    mirror = coeff[::-1].copy()
    mirror[:, :, 0] *= -1
    coeff = 0.5 * (coeff + mirror)
    delta = coeff.reshape(-1, 3) - basecoef
    res = np.linalg.norm(A @ coeff.reshape(-1, 3) - samples[:, 2:5], axis=1)
    weights = base * np.minimum(1, 0.10 / np.maximum(res, 1e-8)) ** 0.5
    print(it, np.quantile(res, [0.5, 0.9, 0.95, 0.99]), flush=True)
# The user requests the intended straight panel rather than accidental longitudinal bow.
# Fit only broad side stripes, outside the stamp and formed perimeter.
stripe = (
    (samples[:, 5] == 1)
    & (abs(samples[:, 2]) >= 26)
    & (abs(samples[:, 2]) <= 32)
    & (samples[:, 3] >= -40)
    & (samples[:, 3] <= 48)
)
sp = samples[stripe, 2:5]
B = np.c_[np.ones(len(sp)), sp[:, 0] ** 2, sp[:, 1], sp[:, 1] ** 2]
w = np.ones(len(sp))
for _ in range(6):
    beta = np.linalg.lstsq(B * w[:, None], sp[:, 2] * w, rcond=None)[0]
    e = B @ beta - sp[:, 2]
    w = np.minimum(1, 0.035 / np.maximum(abs(e), 1e-9)) ** 0.5
bow = {
    "straightening_anchor_y_mm": [-40, 48],
    "straightening_correction": "Subtract a*(Y+40)*(Y-48) from the exterior before normal offset; preserve endpoint datums and linear frame tilt",
    "maximum_in_span_correction_mm": float(abs(beta[3]) * 44**2),
    "constant_mm": float(beta[0]),
    "transverse_x2_coefficient": float(beta[1]),
    "linear_y_coefficient": float(beta[2]),
    "quadratic_y_coefficient": float(beta[3]),
    "stripe_abs_x_mm": [26, 32],
    "stripe_y_mm": [-40, 48],
    "sample_count": int(len(sp)),
    "robust_residual_median_mm": float(np.median(abs(e))),
    "uncorrected_fit_offsets_at_y_minus40_0_plus48_mm": (
        -np.array([-40, 0, 48]) * beta[2] - np.array([-40, 0, 48]) ** 2 * beta[3]
    ).tolist(),
    "interpretation": "Nominal-design inference requested by user; preserve transverse crown, stamp, and rim rise relative to adjacent skin",
}
data = {
    "longitudinal_bow": bow,
    "source_archive_sha256": "52900e9ad09d24b552cea788ea0dbb743e9fa22dde0095cad362bf95ddb1da3f",
    "degree": 3,
    "x_knots": tx.tolist(),
    "y_knots": ty.tolist(),
    "xyz_coefficients": coeff.tolist(),
    "fit": "robust parametric tensor B-spline with mirrored poles; steep rim unrolled in UV",
    "samples": len(samples),
    "residual_quantiles_mm": np.quantile(res, [0.5, 0.9, 0.95, 0.99]).tolist(),
    "source_groups": [1, 2, 3],
    "selection": "exterior-facing normals and outward-facing rim observations in bounded metal envelope",
}
(ROOT / "references" / "surface-fit.json").write_text(json.dumps(data, indent=2) + "\n")
