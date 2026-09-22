#!/usr/bin/env python3
"""Independently compare final STEP surfaces with measured THREE observations.

The forward calculation uses a 0.04 mm STEP tessellation and 96 nearby candidate
triangles. Distances are upper bounds to that mesh, not exact B-rep distances.
The reverse calculation samples the actual STEP tessellation by surface area.
It uses original measured vertices, so observation spacing contributes error.
No numerical pass/fail threshold substitutes for inspection of the cut edges.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

import numpy as np
from scipy.spatial import cKDTree
from build123d import import_step
import trimesh

from import_observed_mesh import ARCHIVE_SHA256, FRAME, matrix, read_scan, sha, walk

SEED = 463
SOURCE_SAMPLES_PER_REGION = 1800
SURFACE_SAMPLES = 150_000
TESSELLATION_TOLERANCE_MM = 0.04
TRIANGLE_CANDIDATES = 96
QUANTILES = [0.5, 0.9, 0.95, 0.99]


def source_groups(archive_path):
    """Load original positions and normals, preserving supplied registration."""
    if sha(archive_path) != ARCHIVE_SHA256:
        raise ValueError("Archive hash does not identify the supplied Palm V scan")
    result = {}
    with zipfile.ZipFile(archive_path) as archive:
        names = [
            n
            for n in archive.namelist()
            if n.startswith("Project-") and n.endswith(".json")
        ]
        if len(names) != 1:
            raise ValueError("Expected exactly one THREE project document")
        root = json.loads(archive.read(names[0]))["groups"]
        for group_id, group in enumerate(root["groups"], 1):
            points, normals = [], []
            for scan, transform in walk(group, matrix(root)):
                vertices, _ = read_scan(archive, scan)
                transform = FRAME @ transform
                points.append(
                    np.column_stack([vertices[n] for n in ("x", "y", "z")])
                    @ transform[:3, :3].T
                    + transform[:3, 3]
                )
                normals.append(
                    np.column_stack([vertices[n] for n in ("nx", "ny", "nz")])
                    @ transform[:3, :3].T
                )
            result[group_id] = (np.concatenate(points), np.concatenate(normals))
    return result


def exterior_mask(points, normals):
    x, y, z = points.T
    outward = normals[:, 0] * np.sign(x) * (abs(x) > 37) + normals[:, 1] * np.sign(
        y
    ) * (abs(y) > 52)
    envelope = (abs(x) < 42) & (abs(y) < 58) & (z > -1.2) & (z < 5.1)
    return envelope & (
        (normals[:, 2] < -0.3) | ((outward > 0.65) & (normals[:, 2] < 0.35))
    )


def regions(points):
    x, y, _ = points.T
    return {
        "all": np.ones(len(points), dtype=bool),
        "broad": (abs(x) < 32) & (y > -42) & (y < 48),
        "rim": (abs(x) > 36) | (abs(y) > 50),
        "notch": (y < -44) & (abs(x) < 20),
        "stamp": (abs(x) < 12) & (y > 12) & (y < 40),
        "reset": (x - 12.8) ** 2 + (y - 19.16) ** 2 < 9,
    }


def summarize(distances):
    return {
        "samples": len(distances),
        "quantiles_mm": np.quantile(distances, QUANTILES).tolist(),
        "maximum_mm": float(np.max(distances)),
    }


def forward_distances(points, triangles, center_tree):
    result = []
    for batch in np.array_split(points, max(1, len(points) // 80)):
        _, candidates = center_tree.query(batch, k=TRIANGLE_CANDIDATES)
        tri = triangles[candidates].reshape(-1, 3, 3)
        repeated = np.repeat(batch, TRIANGLE_CANDIDATES, axis=0)
        closest = trimesh.triangles.closest_point(tri, repeated)
        distances = np.linalg.norm(closest - repeated, axis=1).reshape(
            -1, TRIANGLE_CANDIDATES
        )
        result.extend(distances.min(axis=1))
    return np.asarray(result)


def run(archive_path, step_path):
    source = source_groups(archive_path)
    body = import_step(step_path)
    if not body.is_valid or len(body.solids()) != 1:
        raise ValueError("The STEP must contain one valid solid before comparison")
    vertices, faces = body.tessellate(TESSELLATION_TOLERANCE_MM, 0.10)
    mesh = trimesh.Trimesh(
        np.array([tuple(v) for v in vertices]), np.asarray(faces), process=False
    )
    triangles = mesh.triangles
    center_tree = cKDTree(triangles.mean(axis=1))
    random = np.random.default_rng(SEED)
    forward = {}
    exterior_observations = []
    all_observations = []
    for group_id, (points, normals) in source.items():
        clean = points[exterior_mask(points, normals)]
        exterior_observations.append(clean)
        envelope = (
            (abs(points[:, 0]) < 42)
            & (abs(points[:, 1]) < 59)
            & (points[:, 2] > -1.2)
            & (points[:, 2] < 5.1)
        )
        all_observations.append(points[envelope])
        for name, mask in regions(clean).items():
            candidates = clean[mask]
            selected = random.choice(
                len(candidates),
                min(len(candidates), SOURCE_SAMPLES_PER_REGION),
                replace=False,
            )
            forward[f"group_{group_id}_{name}"] = summarize(
                forward_distances(candidates[selected], triangles, center_tree)
            )
    samples, indices = trimesh.sample.sample_surface(mesh, SURFACE_SAMPLES, seed=SEED)
    normals = mesh.face_normals[indices]
    exterior_samples = samples[exterior_mask(samples, normals)]
    observed_tree = cKDTree(np.concatenate(exterior_observations))
    distances, _ = observed_tree.query(exterior_samples)
    reverse_exterior = {
        name: summarize(distances[mask])
        for name, mask in regions(exterior_samples).items()
    }
    observed_tree = cKDTree(np.concatenate(all_observations))
    distances, _ = observed_tree.query(samples)
    face_masks = {
        "all": np.ones(len(samples), dtype=bool),
        "inner": normals[:, 2] > 0.3,
        "outer": normals[:, 2] < -0.3,
        "cut_walls": abs(normals[:, 2]) <= 0.3,
        "upper_end": samples[:, 1] > 53,
        "lower_end": samples[:, 1] < -50,
        "long_sides": (abs(samples[:, 0]) > 36) & (abs(samples[:, 1]) < 50),
    }
    worst = np.argsort(distances)[-20:]
    return {
        "schema": "palm-independent-observed-fit/v1",
        "archive_sha256": ARCHIVE_SHA256,
        "step_sha256": sha(step_path),
        "script_sha256": sha(Path(__file__)),
        "seed": SEED,
        "source_samples_per_region": SOURCE_SAMPLES_PER_REGION,
        "cad_surface_samples": SURFACE_SAMPLES,
        "quantiles": QUANTILES,
        "tessellation_tolerance_mm": TESSELLATION_TOLERANCE_MM,
        "triangle_candidates": TRIANGLE_CANDIDATES,
        "method_limits": "Forward distances use nearby candidate triangles and are upper bounds to the tessellated surface; reverse distances use measured vertices, including sampling gaps. Regions and normal masks are defined in the hashed audit script. Inner observations may contain glue. Metrics do not prove manufacturing fit.",
        "step_valid": True,
        "step_solids": len(body.solids()),
        "step_tessellation_faces": len(faces),
        "bounds_mm": mesh.bounds.tolist(),
        "source_to_cad": forward,
        "cad_exterior_to_observed_exterior": reverse_exterior,
        "cad_all_to_observed_all": {
            name: summarize(distances[mask]) for name, mask in face_masks.items()
        },
        "worst_all_faces": [
            {"position_mm": point.tolist(), "distance_mm": float(distance)}
            for point, distance in zip(samples[worst], distances[worst])
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.archive, args.step)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "step_sha256": report["step_sha256"],
                "reverse": report["cad_all_to_observed_all"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
