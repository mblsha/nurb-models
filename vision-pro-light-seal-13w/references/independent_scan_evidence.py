"""Re-extract scan evidence without consulting CAD dimensions or fitted contours."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from build123d import Compound
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.gp import gp_Dir, gp_Pln, gp_Pnt
from scipy.interpolate import LinearNDInterpolator
from scipy.ndimage import label, binary_erosion
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"


def statistics(values):
    return {"count": len(values), "median_mm": float(np.median(values)),
            "p95_mm": float(np.quantile(values, .95)), "max_mm": float(np.max(values))}


def distances(first, second):
    if len(first) < 10 or len(second) < 10:
        return {"status": "unknown", "reason": "insufficient independent contour samples"}
    return {"status": "measured", "cad_to_scan": statistics(cKDTree(second).query(first)[0]),
            "scan_to_cad": statistics(cKDTree(first).query(second)[0])}


def basis(feature, sign):
    center = np.array(feature["floor_center_mm"], dtype=float)
    normal = np.array(feature["outward_normal_low_W"], dtype=float)
    major = np.array(feature["major_axis"], dtype=float)
    center[0] *= sign; normal[0] *= sign; major[0] *= sign
    normal /= np.linalg.norm(normal)
    major -= normal * np.dot(major, normal); major /= np.linalg.norm(major)
    return center, np.column_stack((major, np.cross(normal, major), normal))


def extract_pocket(mesh, feature, sign):
    center, frame = basis(feature, sign)
    local = (np.asarray(mesh.vertices) - center) @ frame
    # The recorded center only locates a generous scan neighborhood. No measured
    # length, width, ideal slot, mirrored contour or CAD geometry enters extraction.
    keep = (np.abs(local[:, 0]) < 9) & (np.abs(local[:, 1]) < 9) & (local[:, 2] > -2) & (local[:, 2] < 4)
    keep &= np.asarray(mesh.vertex_normals) @ frame[:, 2] > .05
    points = local[keep]
    if len(points) < 80:
        raise ValueError("too few scan vertices around the pocket")
    radius = np.linalg.norm(points[:, :2], axis=1)
    annulus = (radius > 5.2) & (radius < 8.5)
    def terms(xy):
        u, v = xy.T
        return np.column_stack((np.ones(len(xy)), u, v, u*u, u*v, v*v))
    selected = annulus.copy()
    for _ in range(4):
        coefficient = np.linalg.lstsq(terms(points[selected, :2]), points[selected, 2], rcond=None)[0]
        residual = points[:, 2] - terms(points[:, :2]) @ coefficient
        center_residual = np.median(residual[selected])
        selected = annulus & (np.abs(residual - center_residual) < .35)
        if np.count_nonzero(selected) < 30:
            raise ValueError("support surface does not provide a stable independent fit")
    spacing = .1
    u = np.arange(-6, 6 + spacing/2, spacing)
    v = np.arange(-4.5, 4.5 + spacing/2, spacing)
    uu, vv = np.meshgrid(u, v)
    xy = np.column_stack((uu.ravel(), vv.ravel()))
    field = LinearNDInterpolator(points[:, :2], residual)(xy).reshape(uu.shape)
    depressed = np.isfinite(field) & (field < -.22) & (field > -2.5)
    labels, count = label(depressed)
    candidates = []
    for number in range(1, count + 1):
        mask = labels == number
        if np.count_nonzero(mask) < 20:
            continue
        points_xy = xy[mask.ravel()]
        candidates.append((float(np.min(np.linalg.norm(points_xy, axis=1))), mask))
    if not candidates:
        raise ValueError("no geometry-supported recessed contour")
    _, mask = min(candidates, key=lambda row: row[0])
    if np.any(mask[[0, -1], :]) or np.any(mask[:, [0, -1]]):
        raise ValueError("recess reaches extraction boundary; contour is not isolated")
    boundary = mask & ~binary_erosion(mask)
    contour = xy[boundary.ravel()]
    uncertainty = float(feature["dimension_uncertainty_mm"])
    return {"side": "right" if sign == 1 else "left", "contour_local_uv_mm": contour.tolist(),
            "origin_mm": center.tolist(), "basis": frame.tolist(), "raw_scan_vertices": len(points),
            "support_fit_vertices": int(np.count_nonzero(selected)),
            "support_fit_p95_mm": float(np.quantile(np.abs(residual[selected]), .95)),
            "grid_spacing_mm": spacing, "depth_threshold_mm": .22,
            "uncertainty_mm": uncertainty, "bounds_mm": np.ptp(contour, axis=0).tolist(),
            "status": "measured", "interpretation": "Independent depressed-floor boundary at 0.22 mm below a locally fitted support surface; softened opening edge is uncertain."}


def exact_section(body, origin, normal, axes):
    operation = BRepAlgoAPI_Section(body.wrapped, gp_Pln(gp_Pnt(*origin), gp_Dir(*normal)), False)
    operation.Approximation(True); operation.Build()
    if not operation.IsDone():
        raise RuntimeError("exact CAD section failed")
    points = []
    for edge in Compound(operation.Shape()).edges():
        points.extend(tuple(edge.position_at(float(t))) for t in np.linspace(0, 1, max(4, int(edge.length/.04)+1)))
    return (np.asarray(points) - origin) @ axes


def scan_section(mesh, origin, normal, axes):
    section = mesh.section(plane_origin=origin, plane_normal=normal)
    if section is None:
        return np.empty((0, 2))
    points = []
    for entity in section.entities:
        segment = entity.discrete(section.vertices)
        for a, b in zip(segment[:-1], segment[1:]):
            n = max(1, int(np.linalg.norm(b-a)/.04)+1)
            points.extend(a + (b-a)*np.arange(n)[:, None]/n)
    return (np.asarray(points) - origin) @ axes


def section_result(body, mesh, name, origin, normal, axes, limits, uncertainty):
    records = []
    for sign, side in ((1, "right"), (-1, "left")):
        reflection = np.diag([sign, 1, 1])
        o = reflection @ origin; n = reflection @ normal; a = reflection @ axes
        cad = exact_section(body, o, n, a)
        raw = scan_section(mesh, o, n, a)
        def crop(points):
            return points[(points[:, 0] >= limits[0]) & (points[:, 0] <= limits[1]) &
                          (points[:, 1] >= limits[2]) & (points[:, 1] <= limits[3])]
        cad, raw = crop(cad), crop(raw)
        comparison = distances(cad, raw)
        within = comparison["status"] == "measured" and max(comparison[direction]["p95_mm"] for direction in ("cad_to_scan", "scan_to_cad")) <= uncertainty
        records.append({"side": side, "origin_mm": o.tolist(), "normal": n.tolist(), "axes": a.tolist(),
                        "roi_local_uv_mm": limits, "cad_contour_local_uv_mm": cad.tolist(),
                        "scan_contour_local_uv_mm": raw.tolist(), "comparison": comparison,
                        "threshold_mm": uncertainty, "status": "within_scan_uncertainty" if within else "needs_review"})
    return {"name": name, "sides": records}


def evaluate(body, mesh, pocket_data, narrow_data, profile_data, opening_extractor):
    result = {"method": "Raw aligned mesh only for reference extraction. Each side is extracted independently. Existing measurements locate neighborhoods; CAD is evaluated only after extraction.",
              "physical_fit": "not_verified", "cushion_openings": [], "broad_seating": [], "narrow_between_stations": []}
    edge_samples = [np.array([tuple(edge.position_at(float(t))) for t in np.linspace(0, 1, max(5, int(edge.length/.04)+1))]) for edge in body.edges()]
    for feature in pocket_data["features"]:
        records = []
        for sign, side in ((1, "positive_X"), (-1, "negative_X")):
            try:
                raw = extract_pocket(mesh, feature, sign)
                _, cad, _ = opening_extractor(edge_samples, feature, side)
                # The negative-side frame's minor axis reverses under reflection.
                comparison = distances(cad, np.asarray(raw["contour_local_uv_mm"]))
                within = comparison["status"] == "measured" and max(comparison[direction]["p95_mm"] for direction in ("cad_to_scan", "scan_to_cad")) <= raw["uncertainty_mm"]
                records.append({**raw, "cad_contour_local_uv_mm": cad.tolist(), "comparison": comparison, "agreement": "within_scan_uncertainty" if within else "needs_review"})
            except ValueError as exc:
                records.append({"side": side, "status": "unknown", "agreement": "unknown", "reason": str(exc)})
        result["cushion_openings"].append({"id": feature["id"], "sides": records})
    seats = json.loads((REFERENCES / "face-cushion-wide-seating-measurements.json").read_text())["stations"]
    for key in ("2", "4", "6", "8"):
        seat = seats[key]
        origin = np.asarray(seat["seating_face_origin"])
        u = np.asarray(seat["seating_face_transverse_direction"])
        v = np.asarray(seat["seating_face_normal_toward_vision_pro"])
        limits = seat["long_seating_run_span_mm"]
        result["broad_seating"].append(section_result(body, mesh, "seat_"+key, origin, np.cross(u,v), np.column_stack((u,v)), [limits[0]+.75, limits[1]-.75, -1.25, 1.25], .75))
    for first, second in ((2,3), (6,7), (9,10)):
        a, b = narrow_data[str(first)]["right"], narrow_data[str(second)]["right"]
        origin = (np.asarray(a["origin"])+b["origin"])/2
        normal = np.asarray(a["tangent"])+b["tangent"]; normal /= np.linalg.norm(normal)
        u = np.asarray(a["inward"])+b["inward"]; u -= normal*np.dot(u,normal); u /= np.linalg.norm(u)
        v = np.cross(normal,u)
        if np.dot(v, a["toward_vision_pro"]) < 0: v *= -1
        tip = (np.asarray(profile_data[str(first)]["paired_tip_local_uv"])+profile_data[str(second)]["paired_tip_local_uv"])/2
        origin = origin + v*tip[1]
        result["narrow_between_stations"].append(section_result(body, mesh, f"rim_{first}_{second}", origin, normal, np.column_stack((u,-v)), [-6,8,0,5.5], .45))
    statuses = [side.get("agreement", side.get("status")) for category in ("cushion_openings", "broad_seating", "narrow_between_stations") for feature in result[category] for side in feature["sides"]]
    result["status"] = "within_scan_uncertainty" if all(status == "within_scan_uncertainty" for status in statuses) else "needs_review"
    result["independence"] = "Per-side reference contours are never mirrored, pair-averaged, generated from ideal slots, or fitted to CAD. Between-station rim planes were not construction planes; broad planes independently check retained construction sections. Neighborhood frames are retained measurements, not newly independent registration."
    result["source_sha256"] = hashlib.sha256((ROOT / "scans/vision-pro-light-seal-13w-reference.glb").read_bytes()).hexdigest()
    return result


def write_summary(result):
    lines = ["# Independent Light Seal scan evidence", "", f"Current scan-agreement status: **{result['status']}**. Construction regressions and physical fit are separate verdicts. These checks can reject a model whose authored dimensions and symmetry tests pass.", "",
             "Reference contours are independently re-extracted for both sides. Pocket neighborhoods use retained centers and local axes but never use authored slot lengths or widths. A robust quadratic support fit and a 0.22 mm depression threshold define the raw boundary. Soft edge segmentation and registration remain measurement uncertainties. A contour that reaches its neighborhood boundary is unknown, not accepted.", "",
             "Between-guide rim planes sit halfway between construction stations 2/3, 6/7, and 9/10. Broad seating checks use retained measured frames and fresh raw mesh sections. Every CAD contour is an exact B-rep section sampled at 0.04 mm; scan contours are mesh-plane intersections. Thresholds are 0.45 mm for the narrow scan, 0.75 mm for broad seating, and the retained 0.4 or 0.5 mm pocket dimension uncertainty. None is a physical mating tolerance.", "",
             "| Region | Side | CAD to scan p95 mm | Scan to CAD p95 mm | Verdict |", "| --- | --- | ---: | ---: | --- |"]
    for category in ("cushion_openings", "broad_seating", "narrow_between_stations"):
        for record in result[category]:
            for side in record["sides"]:
                comparison = side.get("comparison", {})
                first = comparison.get("cad_to_scan", {}).get("p95_mm")
                second = comparison.get("scan_to_cad", {}).get("p95_mm")
                first = f"{first:.3f}" if first is not None else "unknown"
                second = f"{second:.3f}" if second is not None else "unknown"
                verdict = side.get("agreement", side["status"])
                lines.append(f"| {record.get('id', record.get('name'))} | {side['side']} | {first} | {second} | {verdict} |")
    lines.extend(["", "The new findings require geometric review of the narrow lip between guides and the difference between cushion floor footprints and softened opening boundaries. The retained scan supports these investigations; it does not establish manufactured fit. Do not widen acceptance thresholds merely to make these checks pass.", ""])
    (REFERENCES / "independent-scan-validation.md").write_text("\n".join(lines))
    write_overlays(result["cushion_openings"], "independent-pocket-overlays.svg")
    write_overlays(result["broad_seating"] + result["narrow_between_stations"], "independent-section-overlays.svg")


def write_overlays(records, filename):
    from html import escape
    panels = [(record.get("id", record.get("name")), side) for record in records for side in record["sides"]]
    width, height = 1000, 280 * ((len(panels)+1)//2)
    content = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
               '<rect width="100%" height="100%" fill="#101923"/><style>text{font-family:system-ui,sans-serif;fill:#e6eef4;font-size:13px}</style>']
    for number, (name, side) in enumerate(panels):
        x, y = (number%2)*500, (number//2)*280
        verdict = side.get("agreement", side["status"])
        content.append(f'<text x="{x+20}" y="{y+22}">{escape(name)} {escape(side["side"])}: {escape(verdict)}</text>')
        content.append(f'<text x="{x+20}" y="{y+43}">orange: CAD, cyan: independently extracted scan, mm</text>')
        cad = np.asarray(side.get("cad_contour_local_uv_mm", []))
        raw = np.asarray(side.get("scan_contour_local_uv_mm", side.get("contour_local_uv_mm", [])))
        available = [points for points in (cad,raw) if len(points)]
        if not available:
            content.append(f'<text x="{x+20}" y="{y+90}">{escape(side.get("reason", "No measured contour"))}</text>')
            continue
        points = np.vstack(available); low=points.min(axis=0)-.3; high=points.max(axis=0)+.3
        scale=min(450/(high[0]-low[0]),190/(high[1]-low[1]))
        for points,color in ((raw,"#56d6e4"),(cad,"#ffa64d")):
            for point in points:
                px=x+25+(point[0]-low[0])*scale;py=y+250-(point[1]-low[1])*scale
                content.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.1" fill="{color}"/>')
        content.append(f'<text x="{x+25}" y="{y+269}">U {low[0]:.1f} to {high[0]:.1f}, V {low[1]:.1f} to {high[1]:.1f}</text>')
    content.append('</svg>')
    (REFERENCES / filename).write_text("\n".join(content)+"\n")
