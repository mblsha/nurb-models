"""Reproduce scan-derived clamp details and provisional carriage interfaces."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from build123d import Vertex
from nurb import builder, scan
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / 'parts/neewer_macro_slide_gm_mp2.py'
REFERENCE = ROOT / 'scans/neewer-macro-slide-GM-MP2.ply.gz'
OUTPUT = ROOT / 'references/clamp-detail-evidence.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def circle_fit(points):
    solution = np.linalg.lstsq(np.c_[2 * points, np.ones(len(points))], np.sum(points**2, axis=1), rcond=None)[0]
    center = solution[:2]
    radius = np.sqrt(solution[2] + center @ center)
    residual = np.linalg.norm(points - center, axis=1) - radius
    return {'center_mm': center.tolist(), 'radius_mm': float(radius), 'rms_mm': float(np.sqrt(np.mean(residual**2))), 'sample_count': len(points)}


def nearest_segment_distances(points, segments):
    start = segments[:, 0]
    delta = segments[:, 1] - start
    length2 = np.sum(delta**2, axis=1)
    relative = points[:, None, :] - start
    fraction = np.clip(np.sum(relative * delta, axis=2) / np.maximum(length2, 1e-20), 0, 1)
    nearest = start + fraction[:, :, None] * delta
    return np.sqrt(np.min(np.sum((points[:, None, :] - nearest)**2, axis=2), axis=1))


def top_heights(mesh, xy):
    """Intersect vertical rays with triangles without optional ray dependencies."""
    triangles = mesh.triangles
    centers = triangles.mean(axis=1)
    radius = np.linalg.norm(triangles[:, :, :2] - centers[:, None, :2], axis=2).max() + 1e-6
    candidates = cKDTree(centers[:, :2]).query_ball_point(xy, radius)
    ray_ids = np.repeat(np.arange(len(xy)), [len(row) for row in candidates])
    triangle_ids = np.concatenate(candidates).astype(int)
    chosen = triangles[triangle_ids]
    a, b, c = chosen[:, 0, :2], chosen[:, 1, :2], chosen[:, 2, :2]
    p = xy[ray_ids]
    denominator = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    valid = abs(denominator) > 1e-12
    u = np.full(len(denominator), -1.0)
    v = u.copy()
    u[valid] = ((b[:, 1] - c[:, 1]) * (p[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (p[:, 1] - c[:, 1]))[valid] / denominator[valid]
    v[valid] = ((c[:, 1] - a[:, 1]) * (p[:, 0] - c[:, 0]) + (a[:, 0] - c[:, 0]) * (p[:, 1] - c[:, 1]))[valid] / denominator[valid]
    w = 1 - u - v
    valid &= (u >= -1e-8) & (v >= -1e-8) & (w >= -1e-8)
    z = u * chosen[:, 0, 2] + v * chosen[:, 1, 2] + w * chosen[:, 2, 2]
    heights = np.full(len(xy), -np.inf)
    np.maximum.at(heights, ray_ids[valid], z[valid])
    return heights


def overlap_volume(first, second):
    intersection = first.intersect(second)
    if intersection is None:
        return 0.0
    if hasattr(intersection, 'volume'):
        return float(intersection.volume)
    return sum(float(piece.volume) for piece in intersection)


def capsule_samples(center, length, width, z):
    x, y = center
    r = width / 2
    d = (length - width) / 2
    left = np.linspace(np.pi / 2, 3 * np.pi / 2, 60)
    right = np.linspace(-np.pi / 2, np.pi / 2, 60)
    xy = np.r_[np.c_[x - d + r * np.cos(left), y + r * np.sin(left)], np.c_[x + d + r * np.cos(right), y + r * np.sin(right)], np.c_[np.linspace(x-d, x+d, 80), np.full(80, y-r)], np.c_[np.linspace(x-d, x+d, 80), np.full(80, y+r)]]
    return np.c_[xy, np.full(len(xy), z)]


def run():
    mesh, _, _ = scan.load(REFERENCE, units='mm')
    shape, _, _ = builder.build(PART, overrides={'arca_detent': 0, 'carriage_position_mm': 70.35})
    components = {component.label: component.solid for component in shape._nurb_scene.components}
    clamp = components['fixed top Arca clamp']
    sections = {}
    for z in (38.0, 39.5):
        segments = trimesh.intersections.mesh_plane(mesh, plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        midpoint = segments.mean(axis=1)
        sections[z] = segments[(midpoint[:, 0] > 76) & (midpoint[:, 0] < 131) & (midpoint[:, 1] > 6) & (midpoint[:, 1] < 42)]
    points = sections[38.0].reshape(-1, 3)
    pockets = []
    for name, center, lower, upper, angles in (
        ('left', (90.50, 22.01), 91.0, 99.0, (-np.pi/2, np.pi/2)),
        ('right', (116.31, 22.01), 109.0, 116.0, (np.pi/2, 3*np.pi/2)),
    ):
        selected = points[(points[:, 0] > lower) & (points[:, 0] < upper) & (points[:, 1] > 16) & (points[:, 1] < 29)]
        theta = np.linspace(*angles, 151)
        samples = np.c_[center[0] + 6.36*np.cos(theta), center[1] + 6.36*np.sin(theta), np.full(len(theta), 38.0)]
        distances = nearest_segment_distances(samples, sections[38.0])
        cad_error = max(Vertex(*point).distance_to(clamp) for point in samples[::10])
        pockets.append({'name': name, 'independent_circle_fit': circle_fit(selected[:, :2]), 'modeled_center_mm': list(center), 'modeled_radius_mm': 6.36, 'scan_distance_p95_mm': float(np.percentile(distances, 95)), 'cad_requirement_max_error_mm': float(cad_error), 'accepted': bool(np.percentile(distances, 95) < 0.25 and cad_error < 1e-6)})
    strips = []
    for name, center, length, width, floor in (
        ('front', (103.45, 11.0), 42.35, 5.70, 39.20),
        ('rear', (103.45, 35.28), 42.75, 8.25, 39.13),
    ):
        samples = capsule_samples(center, length, width, 39.5)
        distances = nearest_segment_distances(samples, sections[39.5])
        xy = np.c_[np.linspace(87, 119, 25), np.full(25, center[1])]
        observed = top_heights(mesh, xy)
        cad_error = max(Vertex(*point).distance_to(clamp) for point in samples[::20])
        strips.append({'name': name, 'modeled_mid_height_contour_mm': {'center': list(center), 'length': length, 'width': width, 'z': 39.5}, 'modeled_floor_z_mm': floor, 'observed_floor_median_z_mm': float(np.median(observed)), 'observed_floor_range_z_mm': [float(observed.min()), float(observed.max())], 'scan_contour_p95_mm': float(np.percentile(distances, 95)), 'cad_requirement_max_error_mm': float(cad_error), 'accepted': bool(np.percentile(distances, 95) < 0.25 and abs(np.median(observed)-floor) < 0.1 and cad_error < 1e-5)})
    interfaces = []
    for first, second, gap in (
        ('sliding carriage', 'front guide rod', 0.15),
        ('sliding carriage', 'rear guide rod', 0.15),
        ('sliding carriage', 'lead screw', 0.15),
        ('sliding carriage', 'rotary connector', 0.0),
        ('rotary base', 'rotary connector', 0.0),
        ('fixed top Arca clamp', '90-degree positioning lock', 0.0),
    ):
        distance = float(components[first].distance_to(components[second]))
        volume = overlap_volume(components[first], components[second])
        interfaces.append({'components': [first, second], 'expected_gap_mm': gap, 'actual_gap_mm': distance, 'overlap_mm3': volume, 'accepted': abs(distance-gap) < 1e-5 and volume < 1e-7})
    validity = [{'component': name, 'valid': bool(components[name].is_valid), 'solids': len(components[name].solids())} for name in ('sliding carriage', 'rotary connector', 'rotary base', 'fixed top Arca clamp', 'movable top Arca jaw', '90-degree positioning lock')]
    report = {
        'status': 'accepted' if all(row['accepted'] for row in pockets + strips + interfaces) and all(row['valid'] and row['solids'] == 1 for row in validity) else 'failed',
        'identity': {'model_sha256': sha256(PART), 'reference_sha256': sha256(REFERENCE), 'evidence_script_sha256': sha256(Path(__file__)), 'pose': {'arca_detent': 0, 'carriage_position_mm': 70.35}},
        'scan_evidence': {'pockets': pockets, 'shallow_strips': strips, 'uncertainty_mm': 0.25, 'note': 'The scan is sampled at approximately 0.66 mm mesh-edge spacing. Least-squares residuals describe agreement to this mesh, not scanner accuracy.'},
        'mechanical_interfaces': interfaces,
        'geometry': validity,
        'provisional_hidden_geometry': {'guide_bore_radial_allowance_mm': 0.15, 'lead_screw_bore_diameter_mm': 6.0, 'rotary_stem_diameter_mm': 12.0, 'rotary_stem_z_range_mm': [23.0, 25.0], 'rotary_socket_diameter_mm': 12.3, 'rotary_socket_floor_z_mm': 23.0, 'bearing_underside_relief_ceiling_z_mm': 12.30, 'bearing_underside_relief_y_mm': [[-0.10, 8.23], [35.97, 44.30]], 'reason': 'Visible continuous shafts and a connected swiveling assembly establish the interfaces; the external scan does not measure the concealed diameters, bearing fits, thread or latch mechanism.'},
        'lock_tab': {'label_source': 'https://usdb.oss-us-west-1.aliyuncs.com/neewer_support/instruction/GM-MP2%20%E8%AF%B4%E6%98%8E%E4%B9%A6_EN.pdf', 'modeled_external_envelope_mm': {'x': [99.45, 107.65], 'y': [-6.10, -2.55], 'z': [33.8, 36.9]}, 'evidence': 'The scan X=103.5 mm section reaches y=-6.034 mm and has upper and lower ledges at approximately z=36.88 and 33.81 mm. The manual names the visible feature a 90-degree swivel positioning lock. The hidden latch is not modeled.', 'uncertainty_mm': 0.4},
        'noncontact_corner_radii_mm': {'outer_vertical': 1.1, 'outer_top': 0.55, 'uncertainty': 'Nominal exterior softening, constrained to outward edges; all functional jaw-flank coordinates are unchanged.'},
        'stationary_rail_clearance': {'components': ['sliding carriage', 'bottom Arca plate'], 'overlap_mm3': overlap_volume(components['sliding carriage'], components['bottom Arca plate']), 'note': 'The fitted outer skirts retain the observed silhouette while concealed underside relief removes the original rail overlap. This does not establish unobserved bearing or manufacturing fits.'},
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'accepted' else 1


if __name__ == '__main__':
    raise SystemExit(run())
