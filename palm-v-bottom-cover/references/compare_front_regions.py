"""Measure exterior-front fit in both directions without scoring hidden sheet faces."""

from pathlib import Path
import json
import hashlib
import numpy as np
import trimesh
from nurb.compare import _surface, _to_surface
from scipy.spatial import cKDTree
from build123d import import_step

from read_palm_reference import whole_reference

ROOT = Path(__file__).resolve().parents[1]

q, n, frame = whole_reference()
x, y, z = q.T
metal = (n[:, 2] > 0.25) & (z > 0) & (abs(x) < 40.5) & (y > -57) & (y < 58)
metal &= ~((abs(x) < 29.3) & (y > -33) & (y < 47))
metal &= ~((abs(x) < 6) & (y < -36) & (y > -54))
for cx, cy in [(13, -44), (26.2, -42), (-13, -44), (-26.2, -42)]:
    metal &= (x - cx) ** 2 + (y - cy) ** 2 > 5.2**2
shape = import_step(ROOT / "build/palm_v_front_cover.step")
v, f = shape.tessellate(0.03, 0.1)
mesh = trimesh.Trimesh(np.array([tuple(p) for p in v]), np.array(f), process=False)
centers = mesh.triangles_center
normals = mesh.face_normals
side_roll = (abs(centers[:, 0]) > 35) & (normals[:, 0] * np.sign(centers[:, 0]) > 0.25)
end_roll = (abs(centers[:, 1]) > 49) & (normals[:, 1] * np.sign(centers[:, 1]) > 0.25)
front = mesh.submesh(
    [np.flatnonzero((normals[:, 2] > 0.1) | side_roll | end_roll)],
    append=True,
    repair=False,
)
obs = q[metal][::4]
dist = _to_surface(obs, _surface(front))
points, faces = trimesh.sample.sample_surface(front, 12000, seed=2718)
nearest, _ = cKDTree(q[z > 0]).query(points)


def stats(a):
    return dict(
        zip(
            ["median", "p95", "p99", "max"],
            np.quantile(a, [0.5, 0.95, 0.99, 1]).tolist(),
        )
    )


regions = {}
for name, keep in [
    ("side_borders", abs(obs[:, 0]) > 30),
    ("upper_border", obs[:, 1] > 48),
    ("lower_border", obs[:, 1] < -34),
]:
    regions[name] = stats(dist[keep])
r = {
    "front_step_sha256": hashlib.sha256(
        (ROOT / "build/palm_v_front_cover.step").read_bytes()
    ).hexdigest(),
    "unambiguous_front_skin_to_cad_mm": stats(dist[obs[:, 2] > 2.5]),
    "low_depth_ambiguous_border_to_cad_mm": stats(dist[obs[:, 2] <= 2.5]),
    "all_front_facing_candidates_to_cad_mm": stats(dist),
    "regions_reference_to_cad_mm": regions,
    "cad_to_observed_vertices_mm": stats(nearest),
    "method": "Unambiguous skin uses Z>2.5mm; lower-depth positive-normal candidates include black chassis ledges and are reported separately rather than called metal fit. Observed positive-normal metal regions excluding display and key disks; distance to tessellated exterior at0.03mm deflection. Reverse:12000 deterministic area samples on exterior, nearest original positive-depth scan vertex without excluding steep side normals; vertex spacing makes reverse values upper bounds. Hidden inner sheet face is intentionally not compared to exterior scan.",
    "physical_fit_verified": False,
    "worst_reference_points": [
        {"point": obs[i].tolist(), "distance": float(dist[i])}
        for i in np.argsort(dist)[-12:]
    ],
    "worst_cad_points": [
        {"point": points[i].tolist(), "distance": float(nearest[i])}
        for i in np.argsort(nearest)[-12:]
    ],
}
(ROOT / "build/front-region-comparison.json").write_text(json.dumps(r, indent=2) + "\n")
print(json.dumps(r, indent=2))
