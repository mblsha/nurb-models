"""Export the complete named Palm exterior and preserve component materials in GLB."""

from pathlib import Path
import hashlib
import json
import numpy as np
import trimesh
from build123d import export_step
from nurb.builder import build, to_mesh

ROOT = Path(__file__).resolve().parents[1]


def main():
    shape = build(ROOT / "parts/palm_v.py")[0]
    components = shape._nurb_scene.components
    if len(components) != 9 or not all(
        c.solid.is_valid and len(c.solid.solids()) == 1 for c in components
    ):
        raise ValueError("Expected nine individually valid Palm components")
    target = ROOT / "build/palm_v.step"
    target.parent.mkdir(parents=True, exist_ok=True)
    export_step(shape, target)
    scene = trimesh.Scene()
    for c in components:
        mesh = to_mesh(c.solid, tolerance=0.05)
        if c.solid.color is not None:
            mesh.visual.vertex_colors = np.tile(
                np.round(np.array(tuple(c.solid.color)) * 255).astype("u1"),
                (len(mesh.vertices), 1),
            )
        scene.add_geometry(
            mesh, node_name=c.label, geom_name=c.label, metadata={"component": c.label}
        )
    glb = ROOT / "build/palm_v.glb"
    glb.write_bytes(scene.export(file_type="glb"))
    reopened = trimesh.load(glb)
    if len(reopened.geometry) != 9:
        raise ValueError("GLB lost named components")
    inputs = [
        ROOT / "palm_front_geometry.py",
        *sorted((ROOT / "parts").glob("palm_v*.py")),
        *[
            ROOT / "references" / name
            for name in [
                "surface-fit.json",
                "straight-rim-fit.json",
                "front-fit.json",
                "palm-body-profile-fit.json",
                "palm-assembly-poses.json",
            ]
        ],
    ]
    report = {
        "components": [
            {
                "name": c.label,
                "valid": c.solid.is_valid,
                "solids": len(c.solid.solids()),
            }
            for c in components
        ],
        "assembly_valid": shape.is_valid,
        "step_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "glb_sha256": hashlib.sha256(glb.read_bytes()).hexdigest(),
        "glb_component_count": len(reopened.geometry),
        "source_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in inputs
        },
        "note": "Named separate solids preserve editable component identity. Pairwise contacts/overlaps are audited in the dedicated interface reports. The GLB explicitly preserves material colors; the current NURB live viewer may render its own neutral material.",
    }
    (ROOT / "build/palm-assembly-export-validation.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
