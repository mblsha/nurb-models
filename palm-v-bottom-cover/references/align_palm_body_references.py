from pathlib import Path
import gzip, io, json
import numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.optimize import least_squares
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import argparse

parser = argparse.ArgumentParser(
    description="Refine a Palm outer-frame bilateral datum from unchanged source meshes"
)
parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()
ROOT = args.output_dir
ROOT.mkdir(parents=True, exist_ok=True)
DEST = ROOT
SCAN = args.project / "scans"
frames = json.loads(
    (args.project / "references/palm-initial-inspection-frames.json").read_text()
)
reports = {}
fig, axs = plt.subplots(1, 2, figsize=(12, 8))
for ax, (name, label) in zip(
    axs, [("body", "palm-v-body-observed"), ("whole", "palm-v-rough-observed")]
):
    m = trimesh.load(
        io.BytesIO(gzip.decompress((SCAN / (label + ".ply.gz")).read_bytes())),
        file_type="ply",
        process=False,
    )
    m = max(m.split(only_watertight=False), key=lambda v: v.area)
    old = np.array(frames[name]["source_to_canonical"])
    p = np.asarray(m.vertices) @ old[:3, :3].T + old[:3, 3]
    n = np.asarray(m.vertex_normals) @ old[:3, :3].T
    outer = (
        (abs(p[:, 0]) > 35) & (abs(p[:, 1]) < 49) & (n[:, 0] * np.sign(p[:, 0]) > 0.45)
    )
    # Only the exposed side-wall envelope drives alignment, not inward ledges.
    ix = np.flatnonzero(outer)
    sp = p[ix]
    keys = np.c_[
        np.sign(sp[:, 0]).astype(int),
        np.floor(sp[:, 1] / 1.5).astype(int),
        np.floor(sp[:, 2] / 0.75).astype(int),
    ]
    _, inverse = np.unique(keys, axis=0, return_inverse=True)
    maxima = np.full(inverse.max() + 1, -np.inf)
    np.maximum.at(maxima, inverse, abs(sp[:, 0]))
    outer[ix] = abs(sp[:, 0]) > maxima[inverse] - 0.25
    q = p[outer]
    norm = n[outer]
    tree = cKDTree(p)
    rng = np.random.default_rng(9146)
    selected = rng.choice(len(q), min(16000, len(q)), replace=False)
    source = q[selected]

    def reflect(parameters):
        normal = np.array([1.0, parameters[0], parameters[1]])
        normal /= np.linalg.norm(normal)
        return source - 2 * (source @ normal - parameters[2])[:, None] * normal

    def residual(parameters):
        mirrored = reflect(parameters)
        dist, nearest = tree.query(mirrored)
        return np.einsum("ij,ij->i", mirrored - p[nearest], n[nearest])

    before = tree.query(reflect([0, 0, 0]))[0]
    fit = least_squares(
        residual,
        [0, 0, 0],
        loss="soft_l1",
        f_scale=0.08,
        diff_step=1e-4,
        max_nfev=120,
        xtol=1e-10,
        ftol=1e-10,
        gtol=1e-10,
    )
    normal = np.array([1.0, fit.x[0], fit.x[1]])
    normal /= np.linalg.norm(normal)
    offset = fit.x[2]
    after = tree.query(reflect(fit.x))[0]
    ydir = np.array([0.0, 1.0, 0.0])
    ydir -= normal * (ydir @ normal)
    ydir /= np.linalg.norm(ydir)
    zdir = np.cross(normal, ydir)
    correction = np.eye(4)
    correction[:3, :3] = np.array([normal, ydir, zdir])
    correction[0, 3] = -offset
    canonical = p @ correction[:3, :3].T + correction[:3, 3]
    # Center only the end/face datums. X is the fitted plane and is never recentered by mass.
    for axis in [1, 2]:
        mid = (
            np.quantile(canonical[:, axis], 0.0005)
            + np.quantile(canonical[:, axis], 0.9995)
        ) / 2
        correction[axis, 3] -= mid
    final = correction @ old
    canonical = np.asarray(m.vertices) @ final[:3, :3].T + final[:3, 3]
    frames[name]["source_to_canonical"] = final.tolist()
    frames[name]["pca_initial_to_bilateral"] = correction.tolist()
    frames[name]["extents_xyz"] = np.ptp(canonical, axis=0).tolist()
    frames[name]["frame"] = (
        "X=0 optimized outer-frame bilateral plane; Y toward top opposite connector/button end, Z front; Y/Z centered by robust end/face bounds, not mass centroid"
    )
    frames[name]["alignment_method"] = (
        "Robust reflected nearest-surface point-plane residual using outward side rails and paired end outline, excluding inner tabs and tiny disconnected components"
    )
    reports[name] = {
        "plane_in_initial_frame": {"normal": normal.tolist(), "offset": float(offset)},
        "fit_parameters": fit.x.tolist(),
        "outer_points": len(q),
        "sample_points": len(source),
        "source_selection": "|X|>35, |Y|<49, outwardNx>.45; retain only outermost0.25mm in each1.5mmY×0.75mmZ side-specific bin; reflect to full original surface",
        "before_nearest_point_quantiles_mm": np.quantile(
            before, [0.5, 0.9, 0.95, 0.99]
        ).tolist(),
        "after_nearest_point_quantiles_mm": np.quantile(
            after, [0.5, 0.9, 0.95, 0.99]
        ).tolist(),
        "after_point_plane_quantiles_mm": np.quantile(
            abs(residual(fit.x)), [0.5, 0.9, 0.95, 0.99]
        ).tolist(),
        "source_to_canonical": final.tolist(),
        "proper_rotation_determinant": float(np.linalg.det(final[:3, :3])),
    }
    print(name, json.dumps(reports[name]), flush=True)
    # Plot boundary-driving points and exact reflected observations, not synthetic fitted geometry.
    cp = canonical[outer]
    take = np.arange(0, len(cp), max(1, len(cp) // 13000))
    cp = cp[take]
    ax.scatter(
        cp[:, 0], cp[:, 1], s=0.25, c="#2074b4", alpha=0.5, label="Observed outer frame"
    )
    ax.scatter(
        -cp[:, 0],
        cp[:, 1],
        s=0.25,
        c="#ee7633",
        alpha=0.5,
        label="Reflected observation",
    )
    ax.axvline(0, c="k", lw=0.6)
    ax.set_aspect("equal")
    ax.set_title(name + " corrected bilateral frame")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.legend(markerscale=6, fontsize=8)
    ax.grid(alpha=0.2)
    np.savez_compressed(
        ROOT / (name + "-canonical-refined.npz"),
        vertices=canonical,
        faces=m.faces,
        normals=np.asarray(m.vertex_normals) @ final[:3, :3].T,
    )
fig.tight_layout()
fig.savefig(ROOT / "bilateral-alignment-overlay.png", dpi=180)
(ROOT / "canonical-frames-refined.json").write_text(json.dumps(frames, indent=2) + "\n")
(DEST / "palm-new-reference-frames.json").write_text(
    json.dumps(frames, indent=2) + "\n"
)
(ROOT / "bilateral-alignment-report.json").write_text(
    json.dumps(reports, indent=2) + "\n"
)
(DEST / "palm-bilateral-alignment-report.json").write_text(
    json.dumps(reports, indent=2) + "\n"
)
