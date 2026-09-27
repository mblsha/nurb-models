"""Constrain measured bend bands to straight, horizontal physical fold runs."""

from pathlib import Path
from copy import deepcopy
import json
import hashlib
import numpy as np
from scipy.interpolate import BSpline, CubicSpline
from scipy.sparse import coo_matrix, vstack, kron, diags, eye
from scipy.sparse.linalg import lsmr

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "references/surface-fit.json").read_text())
tx = np.array(data["x_knots"])
ty = np.array(data["y_knots"])
base = np.array(data["xyz_coefficients"])
nx, ny, _ = base.shape


def matrix(uv):
    x = BSpline.design_matrix(uv[:, 0], tx, 3)
    y = BSpline.design_matrix(uv[:, 1], ty, 3)
    rows = []
    cols = []
    values = []
    for k in range(len(uv)):
        for i, a in zip(
            x.indices[x.indptr[k] : x.indptr[k + 1]],
            x.data[x.indptr[k] : x.indptr[k + 1]],
        ):
            for j, b in zip(
                y.indices[y.indptr[k] : y.indptr[k + 1]],
                y.data[y.indptr[k] : y.indptr[k + 1]],
            ):
                rows.append(k)
                cols.append(i * ny + j)
                values.append(a * b)
    return coo_matrix((values, (rows, cols)), shape=(len(uv), nx * ny)).tocsr()


def uv_of(p):
    p = np.asarray(p, float)
    z = (p[:, 2] + np.sqrt(p[:, 2] ** 2 + 0.01)) / 2

    def smooth(x):
        x = np.clip(x, 0, 1)
        return x * x * (3 - 2 * x)

    return np.c_[
        p[:, 0] + np.sign(p[:, 0]) * 0.9 * z * smooth((abs(p[:, 0]) - 33) / 6),
        p[:, 1] + np.sign(p[:, 1]) * 0.9 * z * smooth((abs(p[:, 1]) - 42) / 12),
    ]


nominal = base.copy()
yy = nominal[:, :, 1]
nominal[:, :, 2] -= (
    data["longitudinal_bow"]["quadratic_y_coefficient"] * (yy + 40) * (yy - 48)
)
# The quoted line levels/locations are robust estimates from the original scan.
bands = [
    {
        "name": "far_end",
        "uv_a": [0, 58.7],
        "uv_b": [28, 58.7],
        "xyz_a": [0, 55.73, 3.12],
        "xyz_b": [28, 55.73, 3.12],
        "width": 7.5,
        "inward": [0, -1],
    },
    {
        "name": "long_side",
        "xyz_a": [38.54173 + 0.00601854 * (-28), -28, 1.30],
        "xyz_b": [38.54173 + 0.00601854 * 40, 40, 1.30],
        "width": 6.0,
    },
    {
        "name": "split_end",
        "xyz_a": [18, -61.42917 + 0.21745228 * 18, 4.646],
        "xyz_b": [36, -61.42917 + 0.21745228 * 36, 4.646],
        "width": 7.0,
    },
]
for b in bands[1:]:
    p = np.array([b["xyz_a"], b["xyz_b"]])
    p[:, 2] = 1.55 if b["name"] == "long_side" else 4.45
    uv = uv_of(p)
    b["uv_a"] = uv[0].tolist()
    b["uv_b"] = uv[1].tolist()
    d = uv[1] - uv[0]
    n = np.array([-d[1], d[0]])
    n /= np.linalg.norm(n)
    if b["name"] == "long_side" and n[0] > 0:
        n = -n
    if b["name"] == "split_end" and n[1] < 0:
        n = -n
    b["inward"] = n.tolist()


def constraints(source_bands, transition_start, quintic):
    bands = deepcopy(source_bands)
    points = []
    targets = []
    weights = []
    labels = []
    for b in bands:
        a = np.array(b["uv_a"])
        d = np.array(b["uv_b"]) - a
        n = np.array(b["inward"])
        p0 = np.array(b["xyz_a"])
        pd = np.array(b["xyz_b"]) - p0
        norm = np.array([-pd[1], pd[0], 0.0])
        norm /= np.linalg.norm(norm)
        if np.dot(norm[:2], n) < 0:
            norm = -norm
        samples = np.linspace(0, 1, 41)
        wvals = np.linspace(0, b["width"], 22)
        crest_uv = a[None, :] + samples[:, None] * d
        original_crest = matrix(crest_uv) @ nominal.reshape(-1, 3)
        profile = []
        for w in wvals:
            original = matrix(crest_uv + w * n) @ nominal.reshape(-1, 3)
            delta = original - original_crest
            transverse = np.median(delta @ norm)
            z = np.median(delta[:, 2])
            profile.append((transverse, z))
            target = p0[None, :] + samples[:, None] * pd + norm[None, :] * transverse
            target[:, 2] += z
            points.extend(crest_uv + w * n)
            targets.extend(target)
            weights.extend([1000.0 if w == 0 else 15.0] * len(samples))
            labels.extend([b["name"]] * len(samples))
        b["profile_offsets_mm"] = [
            {"inward_uv": float(w), "transverse_mm": float(p), "z_mm": float(z)}
            for w, (p, z) in zip(wvals, profile)
        ]
        if b["name"] == "long_side":
            # Constrain the transition itself: an unconstrained spline can overshoot
            # between the flared measured end and the straight ruled core.
            blend_samples = np.linspace(transition_start / 68.0, 0.0, 33)
            yy = -28.0 + 68.0 * blend_samples
            original_xz = CubicSpline(
                [-45, -40, -35, -30, -20],
                [[40.02, 2.2], [39.32, 1.6], [38.9, 1.35], [38.78, 1.4], [38.78, 1.45]],
            )(yy)
            original_uv = uv_of(np.c_[original_xz[:, 0], yy, original_xz[:, 1]])
            line_uv = a[None, :] + blend_samples[:, None] * d
            amount = np.linspace(0.0, 1.0, len(blend_samples))
            amount = amount**3 * (amount * (6.0 * amount - 15.0) + 10.0) if quintic else amount * amount * (3.0 - 2.0 * amount)
            blend_uv = original_uv + amount[:, None] * (line_uv - original_uv)
            b["lower_transition_uv"] = blend_uv.tolist()
            for w, (transverse, z) in zip(wvals, profile):
                uv = blend_uv + w * n
                original = matrix(original_uv + w * n) @ nominal.reshape(-1, 3)
                ruled = p0[None, :] + blend_samples[:, None] * pd
                ruled = ruled + norm[None, :] * transverse
                ruled[:, 2] += z
                blend = original + amount[:, None] * (ruled - original)
                points.extend(uv)
                targets.extend(blend)
                weights.extend([1000.0 if w == 0 else 15.0] * len(blend_samples))
                labels.extend(["long_side_transition"] * len(blend_samples))
        # Extra dense crest samples constrain the actual 3D boundary, not just UV.
        samples = np.linspace(0, 1, 301)
        points.extend(a + samples[:, None] * d)
        targets.extend(p0 + samples[:, None] * pd)
        weights.extend([1000.0] * len(samples))
        labels.extend([b["name"]] * len(samples))
    points = np.array(points)
    targets = np.array(targets)
    weights = np.array(weights)
    mirr = points.copy()
    mirr[:, 0] *= -1
    mt = targets.copy()
    mt[:, 0] *= -1
    points = np.vstack((points, mirr))
    targets = np.vstack((targets, mt))
    weights = np.r_[weights, weights]
    labels = np.r_[labels, labels]
    A = matrix(points)
    return bands, A, targets, weights, labels


# Keep the rest of the sheet close to its observed/straightened surface while
# allowing smooth transitions outside the measured straight runs.
u = np.linspace(-44, 44, 90)
v = np.linspace(-62, 60, 125)
U, V = np.meshgrid(u, v, indexing="ij")
P = matrix(np.c_[U.ravel(), V.ravel()])


def diff(n):
    return diags(
        [np.ones(n - 2), -2 * np.ones(n - 2), np.ones(n - 2)],
        [0, 1, 2],
        shape=(n - 2, n),
    )


R = vstack([kron(diff(nx), eye(ny)), kron(eye(nx), diff(ny))]).tocsr()


def fit(A, targets, weights):
    system = vstack(
        [A.multiply(weights[:, None]), P * 0.08, R * 0.08, eye(nx * ny) * 0.0001]
    ).tocsr()
    outputs = []
    for strength in (0.0, 1.0):
        prior = base.copy()
        y = prior[:, :, 1]
        prior[:, :, 2] -= (
            strength
            * data["longitudinal_bow"]["quadratic_y_coefficient"]
            * (y + 40)
            * (y - 48)
        )
        prior = prior.reshape(-1, 3)
        coef = prior.copy()
        for axis in range(3):
            rhs = np.r_[
                weights * (targets[:, axis] - A @ prior[:, axis]),
                np.zeros(P.shape[0] + R.shape[0] + nx * ny),
            ]
            result = lsmr(system, rhs, atol=1e-10, btol=1e-10, maxiter=4500)
            coef[:, axis] += result[0]
        coef = coef.reshape(nx, ny, 3)
        mirror = coef[::-1].copy()
        mirror[:, :, 0] *= -1
        coef = 0.5 * (coef + mirror)
        residual = np.linalg.norm(A @ coef.reshape(-1, 3) - targets, axis=1)
        print(
            "strength",
            strength,
            "crestmax",
            residual[weights == 1000].max(),
            "bandp95",
            np.quantile(residual[weights < 1000], 0.95),
            flush=True,
        )
        outputs.append(coef.tolist())
    return outputs


# Fit the current straight rim and the smoother lower transition from the
# same surface observations. Both results are generated here; no prior fit JSON
# is read. Y-spline support localizes the correction without introducing a seam.
original_bands, original_A, original_targets, original_weights, original_labels = constraints(
    bands, -12.0, False
)
original = fit(original_A, original_targets, original_weights)
smooth_bands, smooth_A, smooth_targets, smooth_weights, smooth_labels = constraints(
    bands, -16.0, True
)
smooth = fit(smooth_A, smooth_targets, smooth_weights)
outputs = []
for baseline_coefficients, smooth_coefficients in zip(original, smooth):
    baseline_coefficients = np.array(baseline_coefficients)
    local = np.array(smooth_coefficients)
    for j in range(ny):
        if ty[j + 4] > -34.0:
            local[:, j, :] = baseline_coefficients[:, j, :]
    outputs.append(local.tolist())

# The observed continuous-end lip is real, but its scan groups disagree by
# several tenths of a millimetre at the bend root. The fit below creates a
# nominal 0.65 mm sheet with a non-focal inner offset while leaving the
# measured straight crest and the corrected opposite end unchanged. Pole 57
# has Y-parameter support [54, 58], so the crest at 58.7 is exactly unaffected.
def smooth_far_return(coefficients):
    if not (np.array_equal(ty[[54, 58]], [50.0, 55.0]) and np.array_equal(ty[[56, 60]], [53.0, 57.0]) and np.array_equal(ty[[57, 61]], [54.0, 58.0])):
        raise ValueError("Far-end curvature correction requires the measured pole supports for indices 54, 56, and 57.")
    poles = np.array(coefficients)
    x = np.abs(poles[:, 57, 0])
    central = np.clip((36.0 - x) / 6.0, 0.0, 1.0)
    central = central * central * (3.0 - 2.0 * central)
    corner = np.exp(-((x - 35.0) / 2.2) ** 2)
    corner[x < 30.0] = 0.0
    poles[:, 57, 1] -= 0.20 * central
    poles[:, 57, 2] += 0.05 * central
    poles[:, 57, 1] += 0.20 * corner
    poles[:, 57, 2] += 0.05 * corner

    # Broaden the central root, soften the middle corner, and carry a fair
    # transition into the adjacent long side. All weights are bilateral.
    center = np.clip((34.0 - x) / 4.0, 0.0, 1.0)
    center = center * center * (3.0 - 2.0 * center)
    poles[:, 57, 1] -= 0.10 * center
    poles[:, 57, 2] += 0.15 * center
    x56 = np.abs(poles[:, 56, 0])
    middle = np.exp(-((x56 - 34.0) / 2.5) ** 2)
    middle[x56 < 30.0] = 0.0
    poles[:, 56, 1] -= 0.40 * middle
    side56 = np.exp(-((x56 - 38.5) / 2.5) ** 2)
    side56[x56 < 31.0] = 0.0
    poles[:, 56, 1] -= 0.50 * side56
    poles[:, 56, 2] += 0.2123 * side56
    x57 = np.abs(poles[:, 57, 0])
    side57 = np.exp(-((x57 - 38.5) / 2.5) ** 2)
    side57[x57 < 31.0] = 0.0
    poles[:, 57, 2] += 0.1253 * side57
    x54 = np.abs(poles[:, 54, 0])
    adjacent_side = np.exp(-((x54 - 38.5) / 2.0) ** 2)
    poles[:, 54, 2] -= 0.25 * adjacent_side
    return poles.tolist()

outputs = [smooth_far_return(coefficients) for coefficients in outputs]
final = np.array(outputs[-1]).reshape(-1, 3)
residual = np.linalg.norm(smooth_A @ final - smooth_targets, axis=1)
core = smooth_labels != "long_side_transition"
result = {
    "source_fit": "surface-fit.json",
    "source_fit_sha256": hashlib.sha256(
        (ROOT / "references/surface-fit.json").read_bytes()
    ).hexdigest(),
    "targets": smooth_bands,
    "method": "XYZ tensor-spline constraints across averaged measured bend cross-sections; symmetric coefficients; horizontal physical crest lines; quintic lower-transition trial localized to degree-three spline poles with Y support ending at -34 mm; symmetric pole-54/56/57 corrections form a wider continuous-end bend and fair adjacent side transition while preserving the straight crest; regenerate the paired plastic body from this surface",
    "coefficients_at_bow_0": outputs[0],
    "coefficients_at_bow_1": outputs[1],
    "crest_constraint_max_mm": float(residual[core & (smooth_weights == 1000)].max()),
    "bend_band_constraint_p95_mm": float(np.quantile(residual[core & (smooth_weights < 1000)], 0.95)),
    "transition_constraint_p95_mm": float(np.quantile(residual[~core], 0.95)),
    "far_end_curvature_correction": {
        "reason": "The scan resolves a real continuous-end upturned lip but disagrees across groups by 0.3 to 0.5 mm. A nominal 0.65 mm sheet cannot use the fitted 0.53 mm exterior bend radius because its inner normal offset folds. The local correction preserves the straight crest and the observed return envelope.",
        "y_pole_index": 57,
        "y_pole_uv_support": [54.0, 58.0],
        "central_x_profile": "Cubic smoothstep: full for |pole X| <= 30 mm, zero at >= 36 mm",
        "central_delta_y_mm": -0.20,
        "central_delta_z_mm": 0.05,
        "corner_x_profile": "Gaussian centered at |pole X| = 35 mm with width 2.2 mm; zero below 30 mm",
        "corner_delta_y_mm": 0.20,
        "corner_delta_z_mm": 0.05,
        "central_extra_profile": "Cubic smoothstep: full for |pole X| <= 30 mm, zero at >= 34 mm",
        "central_extra_j57_delta_yz_mm": [-0.10, 0.15],
        "middle_j56_profile": "Gaussian centered at |pole X| = 34 mm, width 2.5 mm; zero below 30 mm",
        "middle_j56_delta_y_mm": -0.40,
        "side_j56_profile": "Gaussian centered at |pole X| = 38.5 mm, width 2.5 mm; zero below 31 mm",
        "side_j56_delta_yz_mm": [-0.50, 0.2123],
        "side_j57_delta_z_mm": 0.1253,
        "adjacent_side_j54_profile": "Gaussian centered at |pole X| = 38.5 mm, width 2.0 mm",
        "adjacent_side_j54_delta_z_mm": -0.25,
    },
}
(ROOT / "references/straight-rim-fit.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
