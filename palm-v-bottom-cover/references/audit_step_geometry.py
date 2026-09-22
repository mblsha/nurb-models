"""Independent reopened-STEP probes; does not import the part's fitting code."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from build123d import import_step, Vertex
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt


def intersections(shape, origin, direction, low=-20.0, high=20.0):
    query = IntCurvesFace_ShapeIntersector()
    query.Load(shape.wrapped, 1e-7)
    query.Perform(gp_Lin(gp_Pnt(*origin), gp_Dir(*direction)), low, high)
    hits = []
    for i in range(1, query.NbPnt() + 1):
        p = query.Pnt(i)
        surface = BRepAdaptor_Surface(query.Face(i))
        props = BRepLProp_SLProps(surface, query.UParameter(i), query.VParameter(i), 1, 1e-8)
        n = props.Normal()
        hits.append((query.WParameter(i), [p.X(), p.Y(), p.Z()], [n.X(), n.Y(), n.Z()]))
    hits.sort()
    unique = []
    for hit in hits:
        if not unique or abs(hit[0] - unique[-1][0]) > 1e-5:
            unique.append(hit)
    return unique


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    shape = import_step(args.step)
    rows = []
    for x in [0.0, 12.0, 24.0, 35.0, 38.0]:
        for y in [-48.0, -40.0, -25.0, -10.0, 5.0, 14.5, 18.0, 25.0, 40.0, 52.0, 55.0]:
            hits = intersections(shape, (x, y, 0.0), (0.0, 0.0, 1.0))
            row = {"x_mm": x, "y_mm": y, "vertical_hits_mm": [h[0] for h in hits]}
            if hits:
                _, point, normal = hits[0]
                normal_hits = intersections(shape, point, normal, -2, 2)
                nonzero = [abs(h[0]) for h in normal_hits if abs(h[0]) > 1e-4]
                row["normal_gauge_mm"] = min(nonzero) if nonzero else None
                row["mirror_error_mm"] = Vertex(-point[0], point[1], point[2]).distance_to(shape.shells()[0])
            rows.append(row)
    gauges = [r["normal_gauge_mm"] for r in rows if r.get("normal_gauge_mm") is not None]
    report = {
        "source": args.step.name,
        "source_sha256": hashlib.sha256(args.step.read_bytes()).hexdigest(),
        "valid": shape.is_valid,
        "solids": len(shape.solids()),
        "default_kernel_volume_mm3_not_adaptively_integrated": shape.volume,
        "bounds_mm": [list(shape.bounding_box().min), list(shape.bounding_box().max)],
        "gauge_quantiles_mm": np.quantile(gauges, [0, .5, .95, 1]).tolist() if gauges else [],
        "multiple_material_layers": [r for r in rows if len(r["vertical_hits_mm"]) > 2],
        "maximum_sampled_mirror_error_mm": max(r.get("mirror_error_mm", 0) for r in rows),
        "probes": rows,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k:v for k,v in report.items() if k != "probes"}, indent=2))


if __name__ == "__main__":
    main()
