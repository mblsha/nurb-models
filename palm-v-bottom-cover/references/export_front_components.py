"""Export named front components and verify the complete tessellated solids."""

from pathlib import Path
import hashlib
import json
import numpy as np
import trimesh
from build123d import import_step, export_stl

ROOT = Path(__file__).resolve().parents[1]
results = {}
for name in [
    "palm_v_front_cover",
    "palm_v_display",
    "palm_v_button",
    "palm_v_scroll_button",
]:
    step = ROOT / "build" / f"{name}.step"
    stl = step.with_suffix(".stl")
    solid = import_step(step)
    export_stl(solid, stl, tolerance=0.01, angular_tolerance=0.025)
    mesh = trimesh.load_mesh(stl)
    pieces = mesh.split(only_watertight=False, repair=False)
    physical = max(pieces, key=lambda s: len(s.faces))
    discarded = [p for p in pieces if p is not physical]
    for p in discarded:
        if p.area == 0:
            continue
        local = p.copy()
        local.apply_translation(-p.bounds.mean(axis=0))
        if (
            p.extents.max() > 0.1
            or p.area > 1e-7
            or abs(local.volume) > 1e-10
            or np.prod(p.extents) > 1e-10
        ):
            raise ValueError("Material fragment in front export")
    if not physical.is_watertight or not physical.is_winding_consistent:
        raise ValueError(f"{name} mesh is not wholly watertight")
    physical.export(stl)
    results[name] = {
        "valid_solid": solid.is_valid,
        "watertight": physical.is_watertight,
        "consistent_winding": physical.is_winding_consistent,
        "removed_negligible_components": len(discarded),
        "triangles": len(physical.faces),
        "step_sha256": hashlib.sha256(step.read_bytes()).hexdigest(),
        "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
    }
    print(name, results[name], flush=True)
(ROOT / "build/front-export-validation.json").write_text(
    json.dumps(results, indent=2) + "\n"
)
