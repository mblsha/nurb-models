"""Independent rear/body occupancy grid across the inner long-seat boundary."""
import argparse
import hashlib
import json
from pathlib import Path

from build123d import Axis, import_step

parser = argparse.ArgumentParser()
parser.add_argument('--rear', type=Path, required=True)
parser.add_argument('--body', type=Path, required=True)
parser.add_argument('--poses', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
from audit_step_geometry import intersections

rear = import_step(args.rear)
body = import_step(args.body)
pose = json.loads(args.poses.read_text())['rear_cover']
body = body.translate((0, 0, -0.8))
body = body.translate(tuple(-v for v in pose['translation_mm']))
body = body.rotate(Axis.X, -pose['rotation_x_degrees'])
xs = [33.5, 33.75, 34.0, 34.25, 34.5, 34.75, 35.0, 35.5, 36.0, 37.0, 38.0]
# Avoid rays exactly on the y=45 and x=32 CAD seams; probe both sides of the x seam.
ys = [-35.0, -30.0, -20.0, -10.0, 0.0, 10.0, 19.0, 25.0, 30.0, 37.0, 42.0, 44.0, 44.999]
upper_xs = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 28.0, 30.0, 31.0, 31.999, 32.001, 33.0, 34.0, 35.0]
upper_ys = [54.5, 54.75, 54.9, 55.0, 55.1, 55.25, 55.5]
ray_points = [('long_seat', sign * x0, y) for sign in (-1, 1) for x0 in xs for y in ys]
ray_points.extend(('upper_return', sign * x0, y) for sign in (-1, 1) for x0 in upper_xs for y in upper_ys if x0 or sign == 1)
results = []
failures = []
for region, x, y in ray_points:
    try:
        rear_hits = intersections(rear, (x, y, 0), (0, 0, 1))
        body_hits = intersections(body, (x, y, 0), (0, 0, 1))
    except Exception as exc:
        failures.append({'region': region, 'x_mm': x, 'y_mm': y, 'error': type(exc).__name__ + ': ' + str(exc)})
        print('RAY_ERROR', region, x, y, type(exc).__name__, flush=True)
        continue
    zs = sorted({float(hit[0]) for hit in rear_hits + body_hits})
    intervals = []
    for z0, z1 in zip(zs[:-1], zs[1:]):
        if z1 - z0 < 1e-5:
            continue
        point = (x, y, (z0 + z1) / 2)
        if rear.is_inside(point, 1e-9) and body.is_inside(point, 1e-9):
            intervals.append([z0, z1])
    depth = sum(z1 - z0 for z0, z1 in intervals)
    if depth > 1e-5:
        results.append({
            'region': region,
            'x_mm': x, 'y_mm': y,
            'co_occupied_depth_mm': depth,
            'co_occupied_z_intervals_mm': intervals,
            'rear_hit_z_mm': [float(h[0]) for h in rear_hits],
            'body_hit_z_mm': [float(h[0]) for h in body_hits],
        })
    if y == ys[-1] and region == 'long_seat' and x in (-xs[-1], xs[-1]):
        print('done long_seat x', x, flush=True)
report = {
    'method': 'Reopened STEP solids in rear frame; dense long-seat boundary rays at |x|=33.5–38 mm,y=-35..44.999 plus upper-return rays at |x|=0..35,y=54.5..55.5. Each interval midpoint strictly classified inside both solids at 1e-9 mm tolerance. This probes physical co-occupancy independently of OCCT Common topology. The intended upper seat contacts the cover up to physical y≈55; the upturned outer lip beyond that is deliberately free of body contact.',
    'source_sha256': {label: hashlib.sha256(path.read_bytes()).hexdigest() for label, path in [('rear', args.rear), ('body', args.body), ('poses', args.poses)]},
    'edge_perturbations_mm': {'long_seat_y_45_nominal': 44.999, 'upper_return_x_32_nominal': [31.999, 32.001]},
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'rays_attempted': len(ray_points),
    'rays_tested': len(ray_points) - len(failures),
    'ray_errors': failures,
    'rays_with_errors': len(failures),
    'rays_with_co_occupancy_over_0_005_mm': sum(v['co_occupied_depth_mm'] > 0.005 for v in results),
    'max_co_occupied_depth_mm': max((v['co_occupied_depth_mm'] for v in results), default=0),
    'by_sign': {str(sign): {'rays_with_co_occupancy_over_0_005_mm': sum(v['co_occupied_depth_mm'] > 0.005 and (1 if v['x_mm'] > 0 else -1) == sign for v in results), 'max_depth_mm': max((v['co_occupied_depth_mm'] for v in results if (1 if v['x_mm'] > 0 else -1) == sign), default=0)} for sign in (-1, 1)},
    'by_region': {region: {'rays_tested': sum(q[0] == region for q in ray_points), 'rays_with_co_occupancy_over_0_005_mm': sum(v['region'] == region and v['co_occupied_depth_mm'] > 0.005 for v in results), 'max_depth_mm': max((v['co_occupied_depth_mm'] for v in results if v['region'] == region), default=0)} for region in ('long_seat', 'upper_return')},
    'hotspots': sorted(results, key=lambda v: v['co_occupied_depth_mm'], reverse=True)[:40],
}
args.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'hotspots'}, indent=2), flush=True)
print('top_hotspots', report['hotspots'][:8], flush=True)

if failures:
    raise RuntimeError(f'{len(failures)} occupancy rays failed; inspect report')
