"""Reproduce scan-derived exterior-control observations without optional graph packages."""

import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "scans" / "neewer-macro-slide-GM-MP2.ply.gz"


def radial_section(mesh, axis, station, center, radius_limit=15.0):
    origin = np.zeros(3)
    origin[axis] = station
    normal = np.zeros(3)
    normal[axis] = 1.0
    path = mesh.section(plane_origin=origin, plane_normal=normal)
    points = path.vertices[:, [i for i in range(3) if i != axis]]
    vectors = points - center
    vectors = vectors[np.linalg.norm(vectors, axis=1) < radius_limit]
    radii = np.linalg.norm(vectors, axis=1)
    angles = np.arctan2(vectors[:, 1], vectors[:, 0])
    order = np.argsort(angles)
    samples = np.interp(np.linspace(-np.pi, np.pi, 2048, endpoint=False),
                        angles[order], radii[order], period=2 * np.pi)
    harmonics = np.fft.rfft(samples) / 1024
    return {
        "axis": "xyz"[axis], "station_mm": station,
        "section_vertices": len(radii),
        "radial_mm_min_p10_p50_p90_max": np.percentile(radii, [0, 10, 50, 90, 100]).tolist(),
        "harmonics": {str(i): float(abs(harmonics[i])) for i in (1, 2, 4, 6, 8, 12, 16)},
    }


def end_recess_sections(mesh, z):
    path = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    points = path.vertices
    parents = list(range(len(points)))

    def find(index):
        while parents[index] != index:
            index = parents[index]
        return index

    for entity in path.entities:
        for index in entity.points[1:]:
            parents[find(int(index))] = find(int(entity.points[0]))
    groups = {}
    for index in range(len(points)):
        groups.setdefault(find(index), []).append(index)
    contours = []
    for indices in groups.values():
        loop = points[indices, :2]
        low, high = loop.min(0), loop.max(0)
        if (high[0] < 15 or low[0] > 191) and max(high - low) < 15 and len(loop) >= 18:
            contours.append({"xy_bounds_mm": [low.tolist(), high.tolist()], "vertices": len(loop)})
    return {"z_mm": z, "local_contours": contours}


def measure():
    mesh = trimesh.load(io.BytesIO(gzip.decompress(REFERENCE.read_bytes())),
                        file_type="ply", process=False)
    return {
        "reference": str(REFERENCE.relative_to(ROOT)),
        "reference_sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
        "scope": "Exterior surfaces resolved by this repaired geometry scan. Provisional dimensions, not manufactured fit certification.",
        "large_knob": {
            "center_yz_mm": [22.1955, 17.3643],
            "preserved_exact_cad_sleeve_band_x_mm": [-17.0, -12.0],
            "section_estimate_uncertainty_mm": 0.3,
            "sections": [radial_section(mesh, 0, x, [22.1955, 17.3643])
                         for x in (-28, -27, -26, -20, -17, -15, -12, -10, -9, -8, -7, -6, -5, -3)],
            "model_policy": "Original eight-lobe section is unchanged throughout the sleeve band. Round the front cap and taper the rear shoulder outside that protected band.",
        },
        "clamp_knob": {
            "center_xz_mm": [103.3, 35.5],
            "section_estimate_uncertainty_mm": 0.3,
            "sections": [radial_section(mesh, 1, y, [103.3, 35.5], 12.0)
                         for y in (53, 56, 59, 61, 63, 65, 67, 70, 72, 74, 76, 77)],
            "flute_count": 8,
            "count_basis": "The eightfold angular harmonic is dominant at y=70 mm (about 0.293 mm amplitude); the sixteenfold harmonic is about 0.087 mm.",
            "modeled_outer_radius_mm": 8.1,
            "modeled_groove": {"cutter_radius_mm": 2.4, "cutter_axis_radius_mm": 9.7, "phase_deg": 12},
        },
        "end_blocks": {
            "section_estimate_uncertainty_mm": 0.35,
            "modeled_top_z_mm": 24.2,
            "large_recess_centers_xy_mm": [[5.6, 12.1], [5.6, 32.1], [201.0, 12.1], [201.0, 32.1]],
            "small_seat_centers_xy_mm": [[7.2, 4.6], [7.2, 39.6], [199.5, 4.6], [199.5, 39.6]],
            "counterbore_radius_mm": 3.8,
            "counterbore_floor_z_mm": 23.4,
            "socket_floor_z_mm": 21.8,
            "sections": [end_recess_sections(mesh, z) for z in (22, 22.5, 23, 23.25, 23.5, 23.75, 24.0)],
            "model_policy": "Reconstruct visible recessed exterior seats only. Socket is a rounded provisional envelope; hex/Torx standard, screw threads and internal bearing bores are unobserved.",
        },
        "lead_screw": {
            "thread_pitch_mm": None,
            "modeled_proxy_radius_mm": 2.85,
            "status": "Smooth provisional envelope retained. Neither the official manual nor repaired scan establishes a trustworthy pitch; no arbitrary helix is added.",
        },
    }


if __name__ == "__main__":
    result = measure()
    output = ROOT / "references" / "controls-detail-evidence.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(output)
