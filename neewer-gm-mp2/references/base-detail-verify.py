"""Check the reconstructed lower web without rewriting canonical evidence."""
from pathlib import Path
import json
import sys
import numpy as np
from build123d import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_reconstruction as inherited

ROOT = Path(__file__).resolve().parents[1]


def slots(mesh, z=2.5, lower=17, upper=20):
    section = mesh.section((0, 0, 1), (0, 0, z))
    contours = [e.discrete(section.vertices)[:, :2] for e in section.entities]
    found = [q for q in contours if lower < np.ptp(q[:, 0]) < upper and 27 < np.ptp(q[:, 1]) < 30]
    return sorted(found, key=lambda q: q[:, 0].min())


def sample(polyline):
    return np.concatenate([np.linspace(a, b, max(2, int(np.linalg.norm(b-a) / .05))) for a, b in zip(polyline, polyline[1:])])


def distance(points, polyline):
    starts, ends = polyline[:-1], polyline[1:]
    vectors = ends - starts
    norm = np.sum(vectors * vectors, axis=1)
    keep = norm > 1e-12
    starts, vectors, norm = starts[keep], vectors[keep], norm[keep]
    delta = points[:, None] - starts
    t = np.clip(np.sum(delta * vectors, axis=2) / norm, 0, 1)
    return np.sqrt(np.min(np.sum((delta - t[:, :, None] * vectors) ** 2, axis=2), axis=1))


def main():
    shape, _, _ = inherited.builder.build(inherited.PART, overrides=inherited.POSE)
    base = inherited.components(shape)["bottom Arca plate"]
    reference, _, _ = inherited.scan.load(inherited.REFERENCE, units="mm")
    reference_slots, cad_slots = slots(reference), slots(inherited.shape_mesh(base, .01))
    if len(reference_slots) != 6 or len(cad_slots) != 6:
        raise RuntimeError("Expected six independent lower-web openings")
    rows = []
    for index, (cad, scan) in enumerate(zip(cad_slots, reference_slots)):
        forward, reverse = distance(sample(cad), scan), distance(sample(scan), cad)
        rows.append({"slot": index + 1, "cad_to_scan_p95_mm": float(np.percentile(forward, 95)),
                     "scan_to_cad_p95_mm": float(np.percentile(reverse, 95))})
    upper_scan = slots(reference, 7.5, 55, 62)
    upper_cad = slots(inherited.shape_mesh(base, .01), 7.5, 55, 62)
    if len(upper_scan) != 2 or len(upper_cad) != 2:
        raise RuntimeError("Expected two upper lightening windows")
    windows = []
    for index, (cad, scan) in enumerate(zip(upper_cad, upper_scan)):
        forward, reverse = distance(sample(cad), scan), distance(sample(scan), cad)
        windows.append({"window": index + 1, "cad_to_scan_p95_mm": float(np.percentile(forward, 95)),
                        "scan_to_cad_p95_mm": float(np.percentile(reverse, 95))})
    voids = [(54.4, 22.1, 2.5), (72.5, 22.1, 2.5), (90.6, 22.1, 2.5),
             (116.2, 22.1, 2.5), (134.3, 22.1, 2.5), (152.4, 22.1, 2.5)]
    ribs = [(34, 22.1, 2.5), (63.4, 22.1, 2.5), (81.5, 22.1, 2.5),
            (103.4, 10, 2.5), (125.3, 22.1, 2.5), (143.4, 22.1, 2.5), (172, 22.1, 2.5)]
    bounds = base.bounding_box()
    results = {"pose": inherited.POSE, "valid": bool(base.is_valid), "solids": len(base.solids()),
               "slot_contours": rows, "upper_window_contours": windows, "all_six_void_probes_empty": all(not base.is_inside(Vector(*p)) for p in voids),
               "all_seven_web_probes_solid": all(base.is_inside(Vector(*p)) for p in ribs),
               "bounds_mm": [inherited.vector_list(bounds.min), inherited.vector_list(bounds.max)],
               "method": "Both directions use continuous distances to mesh-plane intersection segments, with perimeter samples spaced at most 0.05 mm. These are local scan-fit checks, not physical verification."}
    results["accepted"] = results["valid"] and results["solids"] == 1 and results["all_six_void_probes_empty"] and results["all_seven_web_probes_solid"] and all(max(row["cad_to_scan_p95_mm"], row["scan_to_cad_p95_mm"]) < .2 for row in rows + windows)
    (ROOT / "references/base-detail-verification.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    if not results["accepted"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
