"""Revision-bound validation of the two Light Seal interfaces and bilateral symmetry."""
from __future__ import annotations

import ast
import importlib.util
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
from build123d import Compound, Vertex, Vector, import_step
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.gp import gp_Dir, gp_Pln, gp_Pnt
from scipy.spatial import cKDTree

from nurb import scan, checks, compare, validator_evidence


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"
MEASUREMENTS = ROOT / "measurements.toml"
PART = ROOT / "parts" / "vision_pro_light_seal_13w.py"
CARD = PART.with_suffix(".md")
VALIDATOR = Path(__file__).resolve()
STEP = ROOT / "build" / "vision_pro_light_seal_13w.step"
STL = ROOT / "build" / "vision_pro_light_seal_13w.stl"
THREE_MF = ROOT / "build" / "vision_pro_light_seal_13w.3mf"
REFERENCE = ROOT / "scans" / "vision-pro-light-seal-13w-reference.glb"
ALIGNMENT = REFERENCES / "alignment.json"
NARROW_SECTIONS = REFERENCES / "vision-pro-narrow-reference-sections.json"
NARROW_SAMPLES = REFERENCES / "vision-pro-narrow-profile-samples.json"
POCKETS = REFERENCES / "face-cushion-wide-pockets.json"
PART_NAME = "vision_pro_light_seal_13w"
THRESHOLDS = {
    "symmetry_plane_angle_deg": 0.05,
    "symmetry_plane_offset_mm": 0.05,
    "reference_reflection_p95_mm": 1.0,
    "trimmed_cad_reflection_max_mm": 1e-5,
    "narrow_complete_p95_mm": 0.35,
    "narrow_lip_p95_mm": 0.30,
    "narrow_projection_min_mm": 0.20,
    "narrow_projection_max_mm": 0.65,
    "narrow_shoulder_gain_min_mm": 1.0,
    "cushion_opening_p95_mm": 0.05,
    "cushion_pair_mirror_p95_mm": 0.025,
}
STATION_LABELS = {"0": "forehead", "5": "temple", "8": "cheek", "11": "nose"}
REQUIRED_SCAN_SIDES = {"0": ("right",), "5": ("right", "left"), "8": ("right", "left"), "11": ("right",)}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_step_sha256(path):
    text = Path(path).read_text()
    text, count = re.subn(r"'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'", "'<generated>'", text, count=1)
    if count != 1:
        raise RuntimeError("the STEP generation timestamp could not be normalized")
    return hashlib.sha256(text.encode()).hexdigest()


def canonical_three_mf_sha256(path):
    with zipfile.ZipFile(path) as package:
        model = package.read("3D/3dmodel.model")
    model = re.sub(rb'p:UUID="[^"]+"', b'p:UUID="<generated>"', model)
    return hashlib.sha256(model).hexdigest()


def json_hash(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def default_parameters(path):
    tree = ast.parse(Path(path).read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == PART_NAME)
    names = [argument.arg for argument in function.args.args[-len(function.args.defaults) :]]
    return {name: ast.literal_eval(value) for name, value in zip(names, function.args.defaults)}


def stats(values):
    values = np.asarray(values, dtype=float)
    return {
        "count": int(len(values)),
        "median_mm": float(np.median(values)),
        "p95_mm": float(np.quantile(values, 0.95)),
        "max_mm": float(np.max(values)),
    }


def reflect(points, normal, offset):
    points = np.asarray(points, dtype=float)
    normal = np.asarray(normal, dtype=float)
    return points - 2.0 * ((points @ normal - offset)[:, None]) * normal


def validate_alignment(alignment, card_transform):
    """Both evidence extraction and the viewer must use one proper rigid datum."""
    matrix = np.asarray(alignment.get("old_glb_to_symmetric_cad"), dtype=float)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError("alignment must be a finite 4 by 4 transform")
    if not np.array_equal(matrix[3], [0, 0, 0, 1]):
        raise ValueError("alignment must have homogeneous last row 0,0,0,1")
    rotation = matrix[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-9, rtol=0) or abs(np.linalg.det(rotation)-1) > 1e-9:
        raise ValueError("alignment must be rigid and proper, without scale, shear or reflection")
    card = np.asarray(card_transform, dtype=float)
    if card.size != 16 or not np.isfinite(card).all() or not np.array_equal(matrix, card.reshape(4,4)):
        raise ValueError("alignment must exactly match the part card transform")
    return matrix


def require_unchanged_inputs(snapshot):
    if any(sha256(path) != digest for path, digest in snapshot.items()):
        raise RuntimeError("validation inputs changed while inspecting; repeat validation")


def verify_reference_symmetry_plane(reference_mesh, alignment):
    vertices = np.asarray(reference_mesh.vertices)
    faces = np.asarray(reference_mesh.faces)
    triangles = vertices[faces]
    centroids = triangles.mean(axis=1)
    areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1) / 2.0
    transform = np.asarray(alignment["old_glb_to_symmetric_cad"], dtype=float)
    cad_centroids = np.column_stack((centroids, np.ones(len(centroids)))) @ transform.T
    cad_centroids = cad_centroids[:, :3]
    stable = (areas > 1e-8) & ~(
        (np.abs(cad_centroids[:, 0]) < 30.0)
        & (cad_centroids[:, 1] > 8.0)
        & (cad_centroids[:, 2] < 35.0)
    )
    candidates = np.where(stable)[0]
    rng = np.random.default_rng(13013)
    chosen = rng.choice(candidates, 16000, p=areas[candidates] / areas[candidates].sum())
    selected = triangles[chosen]
    root = np.sqrt(rng.random(len(chosen)))
    second = rng.random(len(chosen))
    samples = (
        (1.0 - root)[:, None] * selected[:, 0]
        + (root * (1.0 - second))[:, None] * selected[:, 1]
        + (root * second)[:, None] * selected[:, 2]
    )
    cad_samples = np.column_stack((samples, np.ones(len(samples)))) @ transform.T
    samples = samples[cad_samples[:, 0] > 8.0]
    stored_normal = np.asarray(alignment["selected_fit"]["plane_normal_glb"], dtype=float)
    stored_normal /= np.linalg.norm(stored_normal)
    stored_offset = float(alignment["selected_fit"]["plane_offset_glb_mm"])
    target = centroids[stable]
    target_tree = cKDTree(target)
    stored_reflections = reflect(samples, stored_normal, stored_offset)
    stored_distances, nearest = target_tree.query(stored_reflections, workers=-1)
    mates = target[nearest]
    keep = stored_distances <= np.quantile(stored_distances, 0.80)
    differences = samples[keep] - mates[keep]
    _, _, directions = np.linalg.svd(differences, full_matrices=False)
    fitted_normal = directions[0]
    if fitted_normal[0] < 0:
        fitted_normal *= -1.0
    midpoints = (samples[keep] + mates[keep]) / 2.0
    fitted_offset = float(np.median(midpoints @ fitted_normal))
    fitted_distances = target_tree.query(reflect(samples, fitted_normal, fitted_offset), workers=-1)[0]
    angle = float(np.degrees(np.arccos(np.clip(fitted_normal @ stored_normal, -1.0, 1.0))))
    offset_delta = abs(fitted_offset - stored_offset)
    stored_metrics = stats(stored_distances)
    fitted_metrics = stats(fitted_distances)
    accepted = (
        angle <= THRESHOLDS["symmetry_plane_angle_deg"]
        and offset_delta <= THRESHOLDS["symmetry_plane_offset_mm"]
        and stored_metrics["p95_mm"] <= THRESHOLDS["reference_reflection_p95_mm"]
        and fitted_metrics["p95_mm"] <= THRESHOLDS["reference_reflection_p95_mm"]
    )
    return {
        "method": "Geometry-only verification fit from deterministic area-weighted reference samples. The cloth/nose mask is excluded, positive-X samples are reflected with the stored plane, nearest opposite-side face centroids establish correspondences, and one robust paired-plane fit is compared with the stored plane.",
        "mask": "Exclude abs(CAD X)<30, CAD Y>8, CAD Z<35; no texture threshold is used by this independent verification.",
        "reference_faces_in_mask": int(np.count_nonzero(stable)),
        "positive_side_samples": int(len(samples)),
        "paired_fit_samples": int(np.count_nonzero(keep)),
        "stored_plane": {"normal_glb": stored_normal.tolist(), "offset_glb_mm": stored_offset},
        "verification_fit": {"normal_glb": fitted_normal.tolist(), "offset_glb_mm": fitted_offset},
        "angle_difference_deg": angle,
        "offset_difference_mm": offset_delta,
        "stored_plane_reflection": stored_metrics,
        "verification_fit_reflection": fitted_metrics,
        "thresholds": {
            "maximum_angle_difference_deg": THRESHOLDS["symmetry_plane_angle_deg"],
            "maximum_offset_difference_mm": THRESHOLDS["symmetry_plane_offset_mm"],
            "maximum_reflection_p95_mm": THRESHOLDS["reference_reflection_p95_mm"],
        },
        "accepted": accepted,
    }


def sample_paths(paths, spacing=0.04):
    points = []
    for path in paths:
        path = np.asarray(path, dtype=float)
        for first, second in zip(path[:-1], path[1:]):
            count = max(1, int(np.ceil(np.linalg.norm(second - first) / spacing)))
            fraction = np.arange(count)[:, None] / count
            points.extend(first + (second - first) * fraction)
    return np.asarray(points)


def section_widths(paths, depth):
    intersections = []
    for path in paths:
        points = np.asarray(path)
        first, second = points[:-1], points[1:]
        delta = second[:, 1] - first[:, 1]
        crossing = (np.abs(delta) > 1e-9) & ((first[:, 1] - depth) * (second[:, 1] - depth) <= 0)
        fraction = (depth - first[crossing, 1]) / delta[crossing]
        values = first[crossing, 0] + fraction * (second[crossing, 0] - first[crossing, 0])
        intersections.extend(values[(values > -10.0) & (values < 16.0)].tolist())
    intersections.sort()
    return intersections[:2] if len(intersections) >= 2 else None


def cad_section_paths(body, station, narrow_data, profile_data):
    right = narrow_data[station]["right"]
    tip = profile_data[station]["paired_tip_local_uv"]
    origin = np.asarray(right["origin"], dtype=float)
    normal = np.asarray(right["toward_vision_pro"], dtype=float)
    inward = np.asarray(right["inward"], dtype=float)
    tangent = np.asarray(right["tangent"], dtype=float)
    section = BRepAlgoAPI_Section(body.wrapped, gp_Pln(gp_Pnt(*origin), gp_Dir(*tangent)), False)
    section.Approximation(True)
    section.Build()
    if not section.IsDone():
        raise RuntimeError(f"CAD section failed at station {station}")
    paths = []
    for edge in Compound(section.Shape()).edges():
        count = max(4, int(np.ceil(edge.length / 0.04)) + 1)
        xyz = np.asarray([tuple(edge.position_at(float(value))) for value in np.linspace(0.0, 1.0, count)])
        uv = np.column_stack(((xyz - origin) @ inward, tip[1] - (xyz - origin) @ normal))
        if np.linalg.norm(uv, axis=1).min() < 16.0:
            paths.append(uv.tolist())
    return paths


def narrow_side_paths(narrow_data, profile_data, station, side):
    record = narrow_data[station][side]
    if not record:
        return None
    tip = profile_data[station]["paired_tip_local_uv"]
    return [
        np.column_stack((np.asarray(path["local"])[:, 0], tip[1] - np.asarray(path["local"])[:, 1])).tolist()
        for path in record["paths"]
    ]


def masked_bidirectional(cad_points, scan_points, low, high):
    def mask(points):
        return (
            (points[:, 0] > -6.0)
            & (points[:, 0] < 8.0)
            & (points[:, 1] >= low)
            & (points[:, 1] <= high)
        )

    cad = cad_points[mask(cad_points)]
    reference = scan_points[mask(scan_points)]
    return {
        "depth_mm": [low, high],
        "cad_to_scan": stats(cKDTree(reference).query(cad)[0]),
        "scan_to_cad": stats(cKDTree(cad).query(reference)[0]),
    }


def projection_from_section(paths):
    values = []
    for depth in np.arange(2.3, 3.51, 0.05):
        bounds = section_widths(paths, depth)
        if bounds:
            values.append((depth, bounds[0]))
    at_two = section_widths(paths, 2.0)
    at_four = section_widths(paths, 4.0)
    if not values or not at_two or not at_four:
        return None
    depths = np.asarray([value[0] for value in values])
    outer = np.asarray([value[1] for value in values])
    baseline = at_two[0] + (at_four[0] - at_two[0]) * (depths - 2.0) / 2.0
    index = int(np.argmax(baseline - outer))
    return float((baseline - outer)[index])


def validate_narrow_interface(body, narrow_data, profile_data):
    stations = []
    for station, label in STATION_LABELS.items():
        cad_paths = cad_section_paths(body, station, narrow_data, profile_data)
        cad_points = sample_paths(cad_paths)
        neck = section_widths(cad_paths, 1.6)
        rim = section_widths(cad_paths, 3.0)
        projection = projection_from_section(cad_paths)
        if not neck or not rim or projection is None:
            stations.append({"station": int(station), "label": label, "accepted": False, "error": "the final STEP section does not contain the required neck, rim, and outer projection", "scan_sides": []})
            continue
        shoulder_gain = (rim[1] - rim[0]) - (neck[1] - neck[0])
        shape_accepted = (
            THRESHOLDS["narrow_projection_min_mm"] <= projection <= THRESHOLDS["narrow_projection_max_mm"]
            and shoulder_gain >= THRESHOLDS["narrow_shoulder_gain_min_mm"]
        )
        sides = []
        for side in ("right", "left"):
            scan_paths = narrow_side_paths(narrow_data, profile_data, station, side)
            if scan_paths is None:
                if side in REQUIRED_SCAN_SIDES[station]:
                    sides.append({"scan_side": side, "accepted": False, "error": "required retained scan side is missing"})
                continue
            scan_points = sample_paths(scan_paths)
            complete = masked_bidirectional(cad_points, scan_points, 0.0, 5.5)
            lip = masked_bidirectional(cad_points, scan_points, 2.2, 4.2)
            accepted = (
                complete["cad_to_scan"]["p95_mm"] <= THRESHOLDS["narrow_complete_p95_mm"]
                and complete["scan_to_cad"]["p95_mm"] <= THRESHOLDS["narrow_complete_p95_mm"]
                and lip["cad_to_scan"]["p95_mm"] <= THRESHOLDS["narrow_lip_p95_mm"]
                and lip["scan_to_cad"]["p95_mm"] <= THRESHOLDS["narrow_lip_p95_mm"]
            )
            sides.append({"scan_side": side, "complete_profile": complete, "inverse_t_lip": lip, "accepted": accepted})
        station_result = {
                "station": int(station),
                "label": label,
                "cad_neck_width_mm_at_depth_1_6": neck[1] - neck[0],
                "cad_rim_width_mm_at_depth_3": rim[1] - rim[0],
                "cad_shoulder_gain_mm": shoulder_gain,
                "cad_outer_projection_mm": projection,
                "inverse_t_shape_accepted": shape_accepted,
                "scan_sides": sides,
                "accepted": shape_accepted and bool(sides) and all(side["accepted"] for side in sides),
            }
        stations.append(station_result)
    return {
        "method": "Intersect the final exported STEP with the four retained local planes. Compare the exact B-rep contour independently with each available aligned scan-side contour; no nearest-side pooling is allowed.",
        "thresholds": {
            "complete_profile_bidirectional_p95_mm": THRESHOLDS["narrow_complete_p95_mm"],
            "inverse_t_lip_bidirectional_p95_mm": THRESHOLDS["narrow_lip_p95_mm"],
            "outer_projection_mm": [THRESHOLDS["narrow_projection_min_mm"], THRESHOLDS["narrow_projection_max_mm"]],
            "minimum_shoulder_gain_mm": THRESHOLDS["narrow_shoulder_gain_min_mm"],
        },
        "stations": stations,
        "accepted": bool(stations) and all(station.get("accepted") is True for station in stations),
    }


def ideal_slot(length, width, count=600):
    radius = width / 2.0
    center = (length - width) / 2.0
    quarter = count // 4
    first = np.column_stack((np.linspace(-center, center, quarter), np.full(quarter, -radius)))
    angle = np.linspace(-np.pi / 2.0, np.pi / 2.0, quarter)
    second = np.column_stack((center + radius * np.cos(angle), radius * np.sin(angle)))
    third = np.column_stack((np.linspace(center, -center, quarter), np.full(quarter, radius)))
    angle = np.linspace(np.pi / 2.0, 3.0 * np.pi / 2.0, quarter)
    fourth = np.column_stack((-center + radius * np.cos(angle), radius * np.sin(angle)))
    return np.vstack((first, second, third, fourth))


def pocket_frame(feature, side):
    if side == "positive_X":
        center = np.asarray(feature["floor_center_mm"], dtype=float)
        normal = np.asarray(feature["outward_normal_low_W"], dtype=float)
        major = np.asarray(feature["major_axis"], dtype=float)
    else:
        center = np.asarray(feature["mirrored_floor_center_mm"], dtype=float)
        normal = np.asarray(feature["mirrored_outward_normal_low_W"], dtype=float)
        major = np.asarray(feature["mirrored_major_axis"], dtype=float)
    normal /= np.linalg.norm(normal)
    major -= normal * (major @ normal)
    major /= np.linalg.norm(major)
    minor = np.cross(normal, major)
    minor /= np.linalg.norm(minor)
    return center, normal, major, minor


def finished_opening(edge_samples, feature, side):
    center, normal, major, minor = pocket_frame(feature, side)
    length = float(feature["depressed_floor_length_mm"])
    width = float(feature["depressed_floor_width_mm"])
    selected_xyz, selected_uv, selected_edges = [], [], 0
    for points in edge_samples:
        local = points - center
        u = local @ major
        v = local @ minor
        depth = local @ normal
        nearby = (
            abs(np.mean(u)) < length / 2.0 + 1.0
            and abs(np.mean(v)) < width / 2.0 + 1.0
            and np.mean(np.abs(u) < length / 2.0 + 1.0) > 0.5
            and np.mean(np.abs(v) < width / 2.0 + 1.0) > 0.5
        )
        # The floor and vertical pocket walls reach depth=0 in this frame. The
        # actual trimmed opening edges remain on the support surface above 0.1 mm.
        if nearby and np.min(depth) > 0.1:
            selected_xyz.append(points)
            selected_uv.append(np.column_stack((u, v)))
            selected_edges += 1
    if not selected_xyz:
        raise RuntimeError(f"No finished opening trim found for {feature['id']} {side}")
    return np.vstack(selected_xyz), np.vstack(selected_uv), selected_edges


def validate_cushion_openings(body, pocket_data):
    edge_samples = []
    for edge in body.edges():
        count = max(5, int(np.ceil(edge.length / 0.04)) + 1)
        edge_samples.append(np.asarray([tuple(edge.position_at(float(value))) for value in np.linspace(0.0, 1.0, count)]))
    features = []
    for feature in pocket_data["features"]:
        ideal = ideal_slot(float(feature["depressed_floor_length_mm"]), float(feature["depressed_floor_width_mm"]))
        sides = []
        xyz = {}
        for side in ("positive_X", "negative_X"):
            actual_xyz, actual_uv, edge_count = finished_opening(edge_samples, feature, side)
            xyz[side] = actual_xyz
            cad_to_measured = stats(cKDTree(ideal).query(actual_uv)[0])
            measured_to_cad = stats(cKDTree(actual_uv).query(ideal)[0])
            accepted = (
                cad_to_measured["p95_mm"] <= THRESHOLDS["cushion_opening_p95_mm"]
                and measured_to_cad["p95_mm"] <= THRESHOLDS["cushion_opening_p95_mm"]
            )
            sides.append(
                {
                    "side": side,
                    "finished_trim_edges": edge_count,
                    "finished_bounds_mm": np.ptp(actual_uv, axis=0).tolist(),
                    "scan_derived_measured_bounds_mm": [feature["depressed_floor_length_mm"], feature["depressed_floor_width_mm"]],
                    "cad_to_scan_derived_contour": cad_to_measured,
                    "scan_derived_contour_to_cad": measured_to_cad,
                    "accepted": accepted,
                }
            )
        positive = xyz["positive_X"].copy()
        positive[:, 0] *= -1.0
        negative = xyz["negative_X"]
        positive_to_negative = stats(cKDTree(negative).query(positive)[0])
        negative_to_positive = stats(cKDTree(positive).query(negative)[0])
        mirror_accepted = (
            positive_to_negative["p95_mm"] <= THRESHOLDS["cushion_pair_mirror_p95_mm"]
            and negative_to_positive["p95_mm"] <= THRESHOLDS["cushion_pair_mirror_p95_mm"]
        )
        pair_offset = float(np.linalg.norm(feature["pair_center_half_difference_mm"]))
        pair_offset_accepted = pair_offset <= float(feature["dimension_uncertainty_mm"])
        feature_result = {
                "id": feature["id"],
                "label": feature["label"],
                "sides": sides,
                "finished_trim_mirror": {
                    "positive_to_negative": positive_to_negative,
                    "negative_to_positive": negative_to_positive,
                    "accepted": mirror_accepted,
                },
                "separate_scan_side_center_half_difference_mm": feature["pair_center_half_difference_mm"],
                "separate_scan_side_center_offset_norm_mm": pair_offset,
                "scan_dimension_uncertainty_mm": feature["dimension_uncertainty_mm"],
                "scan_side_center_offset_accepted": pair_offset_accepted,
                "accepted": all(side["accepted"] for side in sides) and mirror_accepted and pair_offset_accepted,
            }
        features.append(feature_result)
    return {
        "method": "Extract the actual support-surface trim edges from the final STEP on each side and compare them bidirectionally in the measured pocket frame with the paired scan-derived obround contour. Separately enforce the recorded left/right scan-center disagreement against each feature's measurement uncertainty and compare the two finished trim loops after reflection.",
        "thresholds": {
            "opening_contour_bidirectional_p95_mm": THRESHOLDS["cushion_opening_p95_mm"],
            "finished_pair_mirror_p95_mm": THRESHOLDS["cushion_pair_mirror_p95_mm"],
            "scan_side_center_offset": "Feature-specific dimension_uncertainty_mm from face-cushion-wide-pockets.json",
        },
        "features": features,
        "accepted": bool(features) and all(feature["accepted"] for feature in features),
        "limitation": "The retained source measurement stores pair-averaged opening length and width plus separate side-center disagreement, not two independent raw opening polylines. Contour agreement therefore validates the final trimmed CAD against the scan-derived pair measurement; only the center offset is independently side-specific.",
    }


def validate_trimmed_symmetry(body):
    boundary = body.shells()[0]
    edge_errors, face_errors = [], []
    for edge in body.edges():
        for value in np.linspace(0.03, 0.97, 7):
            point = edge.position_at(float(value))
            edge_errors.append(Vertex(-point.X, point.Y, point.Z).distance_to(boundary))
    for face in body.faces():
        surface = BRepAdaptor_Surface(face.wrapped)
        for u in np.linspace(surface.FirstUParameter(), surface.LastUParameter(), 9):
            for v in np.linspace(surface.FirstVParameter(), surface.LastVParameter(), 5):
                point = surface.Value(float(u), float(v))
                vector = Vector(point.X(), point.Y(), point.Z())
                if face.is_inside(vector):
                    face_errors.append(Vertex(-point.X(), point.Y(), point.Z()).distance_to(boundary))
    edge_max = max(edge_errors)
    face_max = max(face_errors)
    accepted = max(edge_max, face_max) <= THRESHOLDS["trimmed_cad_reflection_max_mm"]
    return {
        "plane": "CAD X=0",
        "method": "Reflect samples from every final trim edge and every trimmed face interior, then measure to the final exported STEP boundary shell. Pocket holes are included because this samples the post-boolean body.",
        "edge_samples": len(edge_errors),
        "trimmed_face_samples": len(face_errors),
        "maximum_edge_reflection_error_mm": edge_max,
        "maximum_trimmed_face_reflection_error_mm": face_max,
        "threshold_mm": THRESHOLDS["trimmed_cad_reflection_max_mm"],
        "accepted": accepted,
    }


def write_markdown(result):
    plane = result["reference_symmetry_plane"]
    trimmed = result["finished_trimmed_cad_symmetry"]
    lines = [
        "# Revision-bound Light Seal interface validation",
        "",
        f"Status: **{result['status']}**. Model source `{result['identity']['model_source_sha256'][:12]}`, validator `{result['identity']['validator_sha256'][:12]}`, canonical STEP `{result['identity']['step_canonical_sha256'][:12]}`, reference GLB `{result['identity']['reference_sha256'][:12]}`, default parameters `{result['identity']['parameters_sha256'][:12]}`.",
        "",
        "## Symmetry",
        "",
        f"A geometry-only verification fit from the reference differs from the stored symmetry plane by {plane['angle_difference_deg']:.4f} degrees and {plane['offset_difference_mm']:.4f} mm. The stored plane's reflected-reference p95 is {plane['stored_plane_reflection']['p95_mm']:.3f} mm against a 1.0 mm verification threshold. The final trimmed STEP reflects onto itself with maximum edge and face errors of {trimmed['maximum_edge_reflection_error_mm']:.3g} and {trimmed['maximum_trimmed_face_reflection_error_mm']:.3g} mm.",
        "",
        "## Narrow Vision Pro inverse-T interface",
        "",
        "Each available scan side is evaluated separately. Complete-profile bidirectional p95 must be at most 0.35 mm; the 2.2 to 4.2 mm inverse-T lip interval must be at most 0.30 mm in both directions.",
        "",
        "| Station | Scan side | Complete CAD-to-scan | Complete scan-to-CAD | Lip CAD-to-scan | Lip scan-to-CAD | Projection | Shoulder gain |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for station in result["narrow_vision_pro_interface"]["stations"]:
        for side in station["scan_sides"]:
            lines.append(
                f"| {station['label']} | {side['scan_side']} | {side['complete_profile']['cad_to_scan']['p95_mm']:.3f} | {side['complete_profile']['scan_to_cad']['p95_mm']:.3f} | {side['inverse_t_lip']['cad_to_scan']['p95_mm']:.3f} | {side['inverse_t_lip']['scan_to_cad']['p95_mm']:.3f} | {station['cad_outer_projection_mm']:.3f} | {station['cad_shoulder_gain_mm']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Face-cushion attachment openings",
            "",
            "The actual final STEP trim edges are compared on both sides with the pair-averaged scan-derived obround measurements. Bidirectional p95 must be at most 0.05 mm. The separately observed scan-side center disagreement must remain inside each feature's recorded dimensional uncertainty.",
            "",
            "| Opening | Side | CAD-to-measured contour | Measured contour-to-CAD | Scan-side center offset | Allowed uncertainty |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for feature in result["face_cushion_openings"]["features"]:
        for side in feature["sides"]:
            lines.append(
                f"| {feature['id']} {feature['label']} | {side['side']} | {side['cad_to_scan_derived_contour']['p95_mm']:.3f} | {side['scan_derived_contour_to_cad']['p95_mm']:.3f} | {feature['separate_scan_side_center_offset_norm_mm']:.3f} | {feature['scan_dimension_uncertainty_mm']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Scope and interpretation",
            "",
            "The narrow validation covers the small retaining lip through 5.5 mm depth. The face-cushion validation covers the eight finished shallow attachment openings. Black nose-guard cloth, the deep interior, lining shoulders, magnets, ribs, cosmetic seams, and texture relief remain excluded. Scan agreement is reconstruction evidence, not physical fit certification.",
            "",
            "Run `python references/validate_interfaces.py` after exporting the default STEP, STL, and 3MF. The JSON result contains thresholds, full per-side statistics, methods, hashes, and limitations.",
            "",
        ]
    )
    (REFERENCES / "interface-validation.md").write_text("\n".join(lines))


def collect_findings(geometry, plane, trimmed, narrow, cushion):
    findings = []
    if not geometry["accepted"]:
        findings.append({"code": "geometry.final_step", "message": "the final STEP is not one valid solid", "evidence": geometry})
    if not plane["accepted"]:
        findings.append({"code": "reference.symmetry_plane", "message": "the independently fitted reference plane exceeded its thresholds", "evidence": {"angle_difference_deg": plane["angle_difference_deg"], "offset_difference_mm": plane["offset_difference_mm"], "stored_plane_reflection_p95_mm": plane["stored_plane_reflection"]["p95_mm"], "verification_fit_reflection_p95_mm": plane["verification_fit_reflection"]["p95_mm"]}})
    if not trimmed["accepted"]:
        findings.append({"code": "cad.trimmed_symmetry", "message": "the finished trimmed CAD exceeded its reflection threshold", "evidence": {"maximum_edge_reflection_error_mm": trimmed["maximum_edge_reflection_error_mm"], "maximum_trimmed_face_reflection_error_mm": trimmed["maximum_trimmed_face_reflection_error_mm"], "threshold_mm": trimmed["threshold_mm"]}})
    for station in narrow["stations"]:
        if station.get("accepted") is True:
            continue
        if "error" in station:
            findings.append({"code": "interface.narrow_section", "message": station["error"], "evidence": {"station": station["station"], "label": station["label"]}})
            continue
        if not station["inverse_t_shape_accepted"]:
            findings.append({"code": "interface.inverse_t_shape", "message": "the final inverse-T section did not satisfy its analytic shape thresholds", "evidence": {"station": station["station"], "label": station["label"], "projection_mm": station["cad_outer_projection_mm"], "shoulder_gain_mm": station["cad_shoulder_gain_mm"]}})
        for side in station["scan_sides"]:
            if not side["accepted"]:
                findings.append({"code": "interface.narrow_scan_side", "message": "one retained narrow-interface scan side exceeded its thresholds", "evidence": {"station": station["station"], "label": station["label"], **side}})
    for feature in cushion["features"]:
        if feature["accepted"]:
            continue
        for side in feature["sides"]:
            if not side["accepted"]:
                findings.append({"code": "interface.cushion_opening", "message": "a finished cushion-opening contour exceeded its threshold", "evidence": {"feature": feature["id"], **side}})
        if not feature["finished_trim_mirror"]["accepted"]:
            findings.append({"code": "interface.cushion_mirror", "message": "a finished cushion-opening pair exceeded its mirror threshold", "evidence": {"feature": feature["id"], **feature["finished_trim_mirror"]}})
        if not feature["scan_side_center_offset_accepted"]:
            findings.append({"code": "reference.cushion_side_centers", "message": "the retained scan-side center disagreement exceeds its measurement uncertainty", "evidence": {"feature": feature["id"], "offset_mm": feature["separate_scan_side_center_offset_norm_mm"], "uncertainty_mm": feature["scan_dimension_uncertainty_mm"]}})
    return findings


def validate(write=True):
    watched = (PART, CARD, MEASUREMENTS, STEP, STL, THREE_MF, REFERENCE, ALIGNMENT,
               NARROW_SECTIONS, NARROW_SAMPLES, POCKETS, VALIDATOR,
               REFERENCES / "export_identity.py", REFERENCES / "independent_scan_evidence.py",
               REFERENCES / "face-cushion-wide-seating-measurements.json", ROOT / "build/export-manifest.json")
    started_with = {path: sha256(path) for path in watched}
    spec = importlib.util.spec_from_file_location("lightseal_export_identity", REFERENCES / "export_identity.py")
    exports = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exports)
    if exports.PART.resolve() != PART.resolve() or exports.ROOT.resolve() != ROOT.resolve():
        raise RuntimeError("interface source and export-manifest project disagree")
    current_body, manifest = exports.verify()
    for path in (PART, MEASUREMENTS, STEP, STL, THREE_MF, REFERENCE, ALIGNMENT, NARROW_SECTIONS, NARROW_SAMPLES, POCKETS):
        if not path.is_file():
            raise FileNotFoundError(path)
    alignment = json.loads(ALIGNMENT.read_text())
    target = compare.setting(checks.settings(PART))
    if not target:
        raise ValueError("part card must declare the aligned reference")
    validate_alignment(alignment, target["transform"])
    narrow_data = json.loads(NARROW_SECTIONS.read_text())
    profile_data = json.loads(NARROW_SAMPLES.read_text())
    pocket_data = json.loads(POCKETS.read_text())
    parameters = default_parameters(PART)
    reference_mesh, unit, unit_source = scan.load(REFERENCE, units="mm")
    body = import_step(STEP)
    geometry = {"accepted": unit == "mm" and body.is_valid and len(body.solids()) == 1, "reference_unit": unit, "step_valid": bool(body.is_valid), "step_solids": len(body.solids())}
    plane = verify_reference_symmetry_plane(reference_mesh, alignment)
    require_unchanged_inputs(started_with)
    trimmed = validate_trimmed_symmetry(body)
    narrow = validate_narrow_interface(body, narrow_data, profile_data)
    cushion = validate_cushion_openings(body, pocket_data)
    scan_spec = importlib.util.spec_from_file_location("lightseal_independent_scan", REFERENCES / "independent_scan_evidence.py")
    independent = importlib.util.module_from_spec(scan_spec)
    scan_spec.loader.exec_module(independent)
    aligned_mesh = reference_mesh.copy()
    aligned_mesh.apply_transform(np.asarray(alignment["old_glb_to_symmetric_cad"]))
    findings = collect_findings(geometry, plane, trimmed, narrow, cushion)
    construction_accepted = not findings and all(result["accepted"] for result in (geometry, plane, trimmed, narrow, cushion))
    raw_scan = (independent.evaluate(body, aligned_mesh, pocket_data, narrow_data, profile_data, finished_opening)
                if construction_accepted else {"status": "not_evaluated", "reason": "Earlier geometry or retained-interface requirement failed."})
    if construction_accepted and raw_scan["status"] != "within_scan_uncertainty":
        findings.append({"code": "reference.independent_scan_review", "message": "new independent per-side or between-station evidence is outside the declared uncertainty or unresolved; inspect independent-scan-validation.json"})
    accepted = not findings and all(result["accepted"] for result in (geometry, plane, trimmed, narrow, cushion))
    require_unchanged_inputs(started_with)
    result = {
        "kind": "nurb_validator_evidence",
        "status": "accepted" if accepted else "failed",
        "accepted": accepted,
        "findings": findings,
        "identity": {
            "export_manifest_sha256": sha256(exports.MANIFEST),
            "fresh_built_geometry_sha256": manifest["built_geometry_sha256"],
            "export_inputs": manifest["inputs"],
            "model_source": str(PART.relative_to(ROOT)),
            "model_source_sha256": sha256(PART),
            "card_sha256": sha256(CARD),
            "validator": str(VALIDATOR.relative_to(ROOT)),
            "validator_sha256": sha256(VALIDATOR),
            "measurements": str(MEASUREMENTS.relative_to(ROOT)),
            "measurements_sha256": sha256(MEASUREMENTS),
            "step": str(STEP.relative_to(ROOT)),
            "step_canonical_sha256": canonical_step_sha256(STEP),
            "stl_sha256": sha256(STL),
            "three_mf_canonical_sha256": canonical_three_mf_sha256(THREE_MF),
            "export_hash_normalization": "STEP generation timestamp and 3MF production UUIDs are normalized; STL is hashed byte-for-byte.",
            "reference": str(REFERENCE.relative_to(ROOT)),
            "reference_sha256": sha256(REFERENCE),
            "reference_unit": unit,
            "reference_unit_source": unit_source,
            "alignment_sha256": sha256(ALIGNMENT),
            "narrow_sections_sha256": sha256(NARROW_SECTIONS),
            "narrow_samples_sha256": sha256(NARROW_SAMPLES),
            "pocket_measurements_sha256": sha256(POCKETS),
            "broad_seating_measurements_sha256": sha256(REFERENCES / "face-cushion-wide-seating-measurements.json"),
            "parameters": parameters,
            "parameters_sha256": json_hash(parameters),
            "acceptance_thresholds": THRESHOLDS,
            "acceptance_thresholds_sha256": json_hash(THRESHOLDS),
            "independent_scan_evaluator_sha256": sha256(REFERENCES / "independent_scan_evidence.py"),
        },
        "viewer_evidence": validator_evidence.viewer_contract(
            ROOT,
            [region["feature"]["id"] for region in target.get("regions", []) if "feature" in region],
            [str(path.relative_to(ROOT)) for path in watched],
            environment=manifest["inputs"],
        ),
        "geometry_validity": geometry,
        "source_export_binding": {"accepted": True, "method": manifest["binding"]},
        "reference_symmetry_plane": plane,
        "finished_trimmed_cad_symmetry": trimmed,
        "narrow_vision_pro_interface": narrow,
        "face_cushion_openings": cushion,
        "independent_scan_evidence": {"status": raw_scan["status"], "report": "references/independent-scan-validation.json"},
        "verification_classes": {
            "construction_regression": "accepted" if construction_accepted else "failed",
            "independent_scan_agreement": raw_scan["status"],
            "geometry_validity": ("accepted: final STEP is one valid solid; export topology remains checked by validate_reconstruction.py" if geometry["accepted"] else "failed: final STEP is not one valid solid"),
            "reference_alignment": ("accepted: stored symmetry plane independently verified from reference geometry" if plane["accepted"] else "failed: independent reference-plane verification exceeded its thresholds"),
            "reconstruction_agreement": ("accepted: retained and independently re-extracted interfaces satisfy their requirements" if accepted else "not accepted: inspect current findings and independent scan evidence"),
            "finished_geometry_symmetry": ("accepted: post-boolean STEP trim edges and trimmed face interiors checked" if trimmed["accepted"] else "failed: finished STEP symmetry exceeded its threshold"),
            "physical_fit": "not verified",
        },
        "scope": {
            "included": "small narrow Vision Pro inverse-T retaining lip; broad face-cushion seating side and eight shallow attachment openings",
            "excluded": "black nose-guard cloth, light-seal interior intricacies, deep lining shoulders, magnets, ribs, cosmetic seams, texture relief",
        },
    }
    if write:
        if construction_accepted:
            raw_scan["kind"] = "nurb_validator_evidence"
            raw_scan["identity"] = result["identity"]
            (REFERENCES / "independent-scan-validation.json").write_text(json.dumps(raw_scan, indent=2) + "\n")
            independent.write_summary(raw_scan)
        publish_current(result)
    return result


def publish_current(result):
    """Every discoverable current path reflects failure immediately; history is separate."""
    result = {"kind": "nurb_validator_evidence", **result}
    encoded = json.dumps(result, indent=2) + "\n"
    for name in ("interface-validation-latest.json", "interface-validation.json"):
        path = REFERENCES / name
        temporary = path.with_suffix(".tmp")
        temporary.write_text(encoded)
        temporary.replace(path)
    narrow = {"kind": "nurb_validator_evidence", "status": result["status"], "accepted": result.get("accepted") is True,
              "current_report": "interface-validation-latest.json",
              "identity": result.get("identity"), "validation": result.get("narrow_vision_pro_interface"),
              "scope": "Overall expanded acceptance gates this compatibility path; historical limited acceptance is archived in historical/."}
    (REFERENCES / "vision-pro-narrow-lip-acceptance.json").write_text(json.dumps(narrow, indent=2)+"\n")
    messages = "\n".join("- " + finding["message"] for finding in result.get("findings", []))
    summary = ("# Current Light Seal interface evidence\n\n"
               f"Overall status: **{result['status']}**. Accepted: **{str(result.get('accepted') is True).lower()}**. The canonical machine-readable result is `interface-validation-latest.json`; `interface-validation.json` is its compatibility alias.\n\n"
               "Independent raw-scan measurements and overlays are described in `independent-scan-validation.md`. Their identity must match the current report before reuse. Historical limited acceptance lives only in `historical/` and does not establish current acceptance.\n\n"
               + messages + "\n")
    (REFERENCES / "interface-validation.md").write_text(summary)


def main():
    try:
        result = validate(write=True)
    except Exception as exc:
        result = {"status": "failed", "accepted": False, "findings": [{"code": "validation.error", "message": f"{type(exc).__name__}: {exc}"}]}
        publish_current(result)
    print(json.dumps(result, indent=2))
    return 0 if result.get("accepted") is True else 1


if __name__ == "__main__":
    sys.exit(main())
