"""Check optional exterior geometry, mounting clearance and commanded motion."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from nurb import builder
import validate_reconstruction as validator
from clamp_detail_evidence import overlap_volume

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/exterior-detail-validation.json'


def run():
    failures = []
    rows = []
    for feet_deployed in (False, True):
        baseline_shape, _, _ = builder.build(validator.PART, overrides={**validator.POSE, 'camera_plate_installed': True, 'include_sleeve': False, 'feet_deployed': feet_deployed})
        baseline = validator.components(baseline_shape)
        for detent in range(4):
            for travel in (0.0, validator.SCAN_TRAVEL_MM, 140.0):
                parameters = {'arca_detent': detent, 'carriage_position_mm': travel, 'camera_plate_installed': True, 'include_sleeve': False, 'feet_deployed': feet_deployed}
                shape, _, _ = builder.build(validator.PART, overrides=parameters)
                found = validator.components(shape)
                motion = validator.commanded_pose_check(found, baseline, detent, travel)
                pairs = []
                for first, second, contact in (
                    ('removable camera plate', 'fixed top Arca clamp', True),
                    ('removable camera plate', 'movable top Arca jaw', False),
                    ('removable camera plate', 'quarter-inch camera stud', True),
                    ('sliding carriage', 'end blocks', False),
                    ('sliding carriage', 'bottom Arca plate', False),
                    ('left folding foot', 'sliding carriage', False),
                    ('right folding foot', 'sliding carriage', False),
                ):
                    volume = overlap_volume(found[first], found[second])
                    gap = float(found[first].distance_to(found[second]))
                    accepted = volume < 1e-6 and (not contact or gap < 1e-6)
                    pairs.append({'components': [first, second], 'overlap_mm3': volume, 'gap_mm': gap, 'accepted': accepted})
                plate_group = ['removable camera plate', 'quarter-inch camera stud', *(f'camera plate pad {column}-{row}' for column in (1,2,3) for row in (1,2))]
                for pad in plate_group[2:]:
                    volume = overlap_volume(found['removable camera plate'], found[pad])
                    gap = float(found['removable camera plate'].distance_to(found[pad]))
                    pairs.append({'components': ['removable camera plate', pad], 'overlap_mm3': volume, 'gap_mm': gap, 'accepted': volume < 1e-6 and gap < 1e-6})
                valid = all(component.is_valid and len(component.solids()) == 1 for name, component in found.items() if name in plate_group or 'screw head' in name or name == 'focus knob dark end cap')
                accepted = motion['accepted'] and valid and all(pair['accepted'] for pair in pairs)
                row = {'parameters': parameters, 'accepted': accepted, 'motion_accepted': motion['accepted'], 'geometry_valid': valid, 'interfaces': pairs}
                rows.append(row)
                print(f"Exterior pose: feet={feet_deployed}, detent={detent}, travel={travel}: {'accepted' if accepted else 'FAILED'}", flush=True)
                if not accepted:
                    failures.append(row)
    # Hardware is stationary and checked once against the rebuilt control bodies.
    hardware = []
    for name in baseline:
        target = 'end blocks' if 'screw head' in name else 'large focus knob' if name == 'focus knob dark end cap' else None
        if target is None:
            continue
        volume = overlap_volume(baseline[name], baseline[target])
        gap = float(baseline[name].distance_to(baseline[target]))
        row = {'component': name, 'seat': target, 'overlap_mm3': volume, 'gap_mm': gap, 'accepted': volume < 1e-6 and gap < 1e-6}
        hardware.append(row)
        if not row['accepted']:
            failures.append(row)
    # GLB reopening verifies that the appearance and named accessory geometry export.
    import trimesh
    target = ROOT / 'build/exterior-detail-photo.glb'
    target.write_bytes(builder.to_glb(baseline_shape))
    reopened = trimesh.load(target, force='scene', process=False)
    exported_names = sorted(reopened.geometry)
    export_ok = len(exported_names) == len(baseline)
    if not export_ok:
        failures.append({'export_geometry_count': len(exported_names), 'expected': len(baseline)})
    report = {'status': 'accepted' if not failures else 'failed', 'identity': {'model_sha256': hashlib.sha256(validator.PART.read_bytes()).hexdigest(), 'helper_sha256': hashlib.sha256((ROOT/'parts/_neewer_exterior.py').read_bytes()).hexdigest(), 'feet_helper_sha256': hashlib.sha256(validator.FEET_HELPER.read_bytes()).hexdigest(), 'scan_travel_mm': validator.SCAN_TRAVEL_MM}, 'pose_matrix': rows, 'stationary_hardware': hardware, 'reopened_glb_geometry_count': len(exported_names), 'failures': failures, 'limitations': ['Camera plate dimensions and all concealed retention details are provisional photo-based reconstruction choices.', 'Camera stud uses a nominal 1/4-20 depiction; the lead-screw pitch remains unknown and is not modeled.', 'The approximately 0.03 mm nominal end gaps are below scan uncertainty and do not validate physical stop clearance.']}
    OUTPUT.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'poses': len(rows), 'hardware': hardware, 'failures': failures}, indent=2))
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(run())
