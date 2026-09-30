"""Fit low-complexity nominal sections to the unchanged aligned observations."""

from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import PchipInterpolator
from shapely.geometry import Polygon, box

import argparse, gzip, io

parser = argparse.ArgumentParser(
    description="Fit smooth nominal Palm body sections from original source triangles"
)
parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()
OUT = args.output_dir
OUT.mkdir(parents=True, exist_ok=True)
source = trimesh.load(
    io.BytesIO(
        gzip.decompress(
            (args.project / "scans/palm-v-body-observed.ply.gz").read_bytes()
        )
    ),
    file_type="ply",
    process=False,
)
source = max(source.split(only_watertight=False), key=lambda q: q.area)
frame = json.loads(
    (args.project / "references/palm-new-reference-frames.json").read_text()
)["body"]["source_to_canonical"]
source.apply_transform(np.array(frame))
a = {"vertices": source.vertices, "faces": source.faces}
mesh = trimesh.Trimesh(a["vertices"], a["faces"], process=False)


def profile(axis, station, region):
    origin = np.zeros(3)
    origin[axis] = station
    normal = np.zeros(3)
    normal[axis] = 1
    cut = mesh.section(plane_origin=origin, plane_normal=normal)
    polygons = []
    for loop in cut.discrete:
        q = loop[:, [1 - axis, 2]]
        if region == "rail" and q[:, 0].mean() < 20:
            continue
        p = Polygon(q)
        if not p.is_valid:
            p = p.buffer(0)
        if region == "top":
            p = p.intersection(box(46, -12, 65, 12))
        if region == "bottom":
            p = p.intersection(box(-65, -12, -43, 12))
        if p.geom_type == "MultiPolygon":
            polygons.extend(p.geoms)
        elif p.geom_type == "Polygon" and p.area > 0.2:
            polygons.append(p)
    p = max(polygons, key=lambda x: x.area).simplify(0.11, preserve_topology=True)
    q = np.array(p.exterior.coords)[:-1]
    if np.sum(q[:, 0] * np.roll(q[:, 1], -1) - q[:, 1] * np.roll(q[:, 0], -1)) < 0:
        q = q[::-1]
    q = np.vstack([q, q[0]])
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))]
    s = np.linspace(0, d[-1], 64, endpoint=False)
    q = np.column_stack([np.interp(s, d, q[:, i]) for i in range(2)])
    return gaussian_filter1d(q, 0.6, axis=0, mode="wrap")


def aligned(q, reference):
    k = min(
        range(len(q)), key=lambda k: np.sum((np.roll(q, k, axis=0) - reference) ** 2)
    )
    return np.roll(q, k, axis=0)


# Nominal rail is one repeated C section, not a longitudinal scan tracing.
rail = [profile(1, y, "rail") for y in [-30, -15, 0, 15, 30]]
rail = np.median([aligned(q, rail[0]) for q in rail], axis=0)
rail_rows = []
for y in np.linspace(-45, 50.7, 24):
    t = np.clip((-y - 30) / 18, 0, 1)
    flare = 1.85 * t * t * (3 - 2 * t)
    q = rail.copy()
    q[:, 0] += flare
    depth_t = np.clip((-y - 38) / 10, 0, 1)
    depth_t = depth_t * depth_t * (3 - 2 * depth_t)
    q[:, 1] = q[:, 1] * (1 - 0.35 * depth_t) - 0.6 * depth_t
    rail_rows.append({"station": y, "profile": q.tolist()})
segments = {"right_rail": {"axis": 1, "sections": rail_rows}}
# The top rail uses the same physical C section, enabling tangent corner sweeps.
top_profile = rail.copy()
top_profile[:, 0] += 18.70
segments["top_bridge"] = {
    "axis": 0,
    "sections": [
        {"station": float(x), "profile": top_profile.tolist()} for x in [-32.3, 32.3]
    ],
}
# Smooth connector-end front lip follows the measured quadratic plan bow.
front_profile = profile(0, 0, "bottom")
segments["bottom_bridge"] = {
    "axis": 0,
    "sections": [
        {
            "station": x,
            "profile": (front_profile + np.array([0.0053 * x * x, 0])).tolist(),
        }
        for x in [-39, -30, -20, -10, 0, 10, 20, 30, 39]
    ],
}
# Rear seating returns stop at the central connector opening; no end-to-end mirror.
rear_profile = profile(0, 24, "bottom")
p = Polygon(rear_profile)
p = p.intersection(box(p.bounds[0] - 0.1, -12, -44.0, 0.9))
q = np.array(p.exterior.coords)[:-1]
if np.sum(q[:, 0] * np.roll(q[:, 1], -1) - q[:, 1] * np.roll(q[:, 0], -1)) < 0:
    q = q[::-1]
q = np.vstack([q, q[0]])
d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))]
ss = np.linspace(0, d[-1], 64, endpoint=False)
q = np.column_stack([np.interp(ss, d, q[:, i]) for i in range(2)])
q = gaussian_filter1d(q, 0.5, axis=0, mode="wrap")
rear_rows = []
for x in [17, 24, 31, 39]:
    qr = q.copy()
    weight = np.clip((-44 - qr[:, 0]) / (-44 - qr[:, 0].min()), 0, 1)
    qr[:, 0] += 0.0053 * (x * x - 24 * 24) * weight
    rear_rows.append({"station": x, "profile": qr.tolist()})
segments["bottom_right_return"] = {"axis": 0, "sections": rear_rows}
report = {
    "source": "scans/palm-v-body-observed.ply.gz",
    "frame": "palm-new-reference-frames.json",
    "status": "Preliminary nominal frame: excludes unresolved internal tabs and ports",
    "method": "Repeated median C rail profile from five Y sections; independent front/rear ledges; symmetric low-station end profiles. Original scan untouched.",
    "segments": segments,
}
(OUT / "palm-body-profile-fit.json").write_text(json.dumps(report, indent=2) + "\n")
print("Nominal profiles written", flush=True)
