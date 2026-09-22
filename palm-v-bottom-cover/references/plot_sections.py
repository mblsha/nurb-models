from pathlib import Path
import numpy as np
import trimesh
import gzip
from import_observed_mesh import VDTYPE
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
m = trimesh.load(ROOT / "build/palm_v_bottom_cover.stl")
defs = [
    ("Transverse Y=0", 0, 1, 0),
    ("Transverse Y=-45", 0, 1, -45),
    ("Transverse Y=52", 0, 1, 52),
    ("Transverse Y=40", 0, 1, 40),
    ("Longitudinal X=0", 1, 0, 0),
    ("Longitudinal X=32", 1, 0, 32),
    ("Longitudinal X=38", 1, 0, 38),
    ("Longitudinal X=-38", 1, 0, -38),
    ("Transverse Y=-20", 0, 1, -20),
    ("Transverse Y=20", 0, 1, 20),
    ("Transverse Y=-50", 0, 1, -50),
    ("Transverse Y=55", 0, 1, 55),
]
fig, axs = plt.subplots(3, 4, figsize=(18, 10))
with gzip.open(
    ROOT / "scans/palm-v-bottom-cover-comparison-triangles.ply.gz", "rb"
) as f:
    count = None
    while True:
        line = f.readline()
        if line.startswith(b"element vertex "):
            count = int(line.split()[-1])
        if line == b"end_header\n":
            break
    observed = np.frombuffer(f.read(count * VDTYPE.itemsize), VDTYPE)
for g in (1, 2, 3):
    rows = observed[observed["source_group"] == g]
    q = np.column_stack([rows[k] for k in ("x", "y", "z")])
    basic = (q[:, 2] > -1.5) & (q[:, 2] < 5.5)
    for ax, (name, along, cross, at) in zip(axs.flat, defs):
        keep = basic & (abs(q[:, cross] - at) < 0.15)
        ax.scatter(
            q[keep, along],
            q[keep, 2],
            s=0.35,
            alpha=0.23,
            color=["#555555", "#4ca15a", "#4488bb"][g - 1],
            label=f"Observed group {g}",
        )
for ax, (name, along, cross, at) in zip(axs.flat, defs):
    normal = np.zeros(3)
    normal[cross] = 1
    origin = normal * at
    sec = m.section(plane_normal=normal, plane_origin=origin)
    if sec:
        for entity in sec.entities:
            p = sec.vertices[entity.points]
            ax.plot(p[:, along], p[:, 2], color="#d22222", linewidth=1.1)
    ax.set_title(name)
    ax.set_ylim(-1.25, 5.5)
    ax.grid(alpha=0.2)
    ax.set_ylabel("Z (mm)")
    ax.set_xlabel("X (mm)" if along == 0 else "Y (mm)")
axs[0, 0].legend(markerscale=4)
fig.suptitle(
    "Original observations and nominal straightened 0.65 mm sheet (red); Z scale enlarged",
    fontsize=15,
)
fig.tight_layout()
fig.savefig(ROOT / "build/sections-overlay.png", dpi=150)
