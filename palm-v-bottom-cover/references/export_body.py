"""Rebuild and export the exact nominal body STEP; does not claim printable STL."""

import argparse
import hashlib
import json
from pathlib import Path
from build123d import export_step, import_step
from nurb.builder import load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    root = args.project
    source = root / "parts/palm_v_body.py"
    shape = load(source)()
    if not shape.is_valid or len(shape.solids()) != 1:
        raise ValueError("Body must build as one valid B-rep solid")
    path = root / "build/palm_v_body.step"
    path.parent.mkdir(exist_ok=True)
    export_step(shape, path)
    reopened = import_step(path)
    if not reopened.is_valid or len(reopened.solids()) != 1:
        raise ValueError("Reopened body STEP is not one valid solid")

    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    report = {
        "source_sha256": sha(source),
        "profile_fit_sha256": sha(root / "references/palm-body-profile-fit.json"),
        "assembly_pose_sha256": sha(root / "references/palm-assembly-poses.json"),
        "step_sha256": sha(path),
        "step_valid": True,
        "step_solids": 1,
        "stl_delivered": False,
        "stl_limitation": "Coarse OCCT tessellation produced zero-thickness artifacts and open boundary edges. No welded or hole-filled STL is supplied. Exact B-rep STEP is the validated CAD deliverable.",
        "audit_note": "Re-run independent mating/interface reports after regenerating STEP so their artifact hashes match.",
    }
    (root / "build/palm-body-export.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
