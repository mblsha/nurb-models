"""Read-only freshness check for current or historical interface evidence."""
import argparse
import json
from pathlib import Path

import export_identity

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "model_source_sha256": "parts/vision_pro_light_seal_13w.py",
    "card_sha256": "parts/vision_pro_light_seal_13w.md",
    "validator_sha256": "references/validate_interfaces.py",
    "measurements_sha256": "measurements.toml",
    "reference_sha256": "scans/vision-pro-light-seal-13w-reference.glb",
    "alignment_sha256": "references/alignment.json",
    "narrow_sections_sha256": "references/vision-pro-narrow-reference-sections.json",
    "narrow_samples_sha256": "references/vision-pro-narrow-profile-samples.json",
    "pocket_measurements_sha256": "references/face-cushion-wide-pockets.json",
    "broad_seating_measurements_sha256": "references/face-cushion-wide-seating-measurements.json",
    "independent_scan_evaluator_sha256": "references/independent_scan_evidence.py",
    "export_manifest_sha256": "build/export-manifest.json",
}


def check(path):
    report = json.loads(Path(path).read_text())
    identity = report.get("identity", {})
    changed = []
    for key, relative in FILES.items():
        source = ROOT / relative
        if not source.is_file() or identity.get(key) != export_identity.digest(source):
            changed.append(relative)
    for suffix, key in ((".step", "step_canonical_sha256"), (".stl", "stl_sha256"), (".3mf", "three_mf_canonical_sha256")):
        source = ROOT / "build" / (export_identity.NAME + suffix)
        if not source.is_file() or identity.get(key) != export_identity.export_digest(source):
            changed.append(str(source.relative_to(ROOT)))
    if identity.get("export_inputs") != export_identity.inputs():
        changed.append("source/runtime export inputs")
    accepted = report.get("accepted") is True
    return {"status": "stale" if changed else "current_accepted" if accepted else "current_failed",
            "accepted": accepted and not changed, "changed": changed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", nargs="?", default=str(ROOT / "references/interface-validation-latest.json"))
    args = parser.parse_args()
    result = check(args.report)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["accepted"] else 1)
