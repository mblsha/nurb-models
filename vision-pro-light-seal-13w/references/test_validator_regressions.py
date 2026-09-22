"""Deliberate per-side failures must never produce accepted Light Seal evidence."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = tuple(path.relative_to(ROOT) for path in (ROOT / "references/historical").glob("*"))


class ValidatorFailureRegression(unittest.TestCase):
    def run_failure(self, optimized):
        with tempfile.TemporaryDirectory(prefix="lightseal-validator-regression-") as directory:
            project = Path(directory) / "project"
            shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            sections = project / "references/vision-pro-narrow-reference-sections.json"
            data = json.loads(sections.read_text())
            for path in data["5"]["left"]["paths"]:
                for point in path["local"]:
                    point[0] += 2.0
            sections.write_text(json.dumps(data, indent=2) + "\n")
            before = {path: (project / path).read_bytes() for path in HISTORICAL}
            environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable]
            if optimized:
                command.append("-O")
            command.append(str(project / "references/validate_interfaces.py"))
            completed = subprocess.run(command, cwd=project, env=environment, text=True, capture_output=True)
            self.assertNotEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["accepted"])
            self.assertFalse(result["narrow_vision_pro_interface"]["accepted"])
            station = next(station for station in result["narrow_vision_pro_interface"]["stations"] if station["station"] == 5)
            left = next(side for side in station["scan_sides"] if side["scan_side"] == "left")
            self.assertFalse(left["accepted"])
            self.assertTrue(any(finding["code"] == "interface.narrow_scan_side" for finding in result["findings"]))
            for path, contents in before.items():
                self.assertEqual((project / path).read_bytes(), contents, f"failed validation rewrote {path}")
            import tomllib
            settings = tomllib.loads((project / "measurements.toml").read_text())["vision_pro_narrow_lip"]
            self.assertEqual(settings["acceptance_json_pointer"], "/accepted")
            declared = json.loads((project / settings["acceptance"]).read_text())
            self.assertFalse(declared["accepted"])
            self.assertEqual(declared["status"], "failed")
            for path in ("interface-validation.json", "vision-pro-narrow-lip-acceptance.json"):
                current = json.loads((project / "references" / path).read_text())
                self.assertFalse(current["accepted"])
                self.assertEqual(current["status"], "failed")

    def test_bad_scan_side_fails_in_normal_python(self):
        self.run_failure(optimized=False)

    def test_bad_scan_side_fails_with_assertions_disabled(self):
        self.run_failure(optimized=True)


if __name__ == "__main__":
    unittest.main()
