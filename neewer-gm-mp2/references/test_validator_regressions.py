"""Deliberate model-specific failures must never produce accepted Neewer evidence."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = Path("references/neewer-current-acceptance.json")
SVG = Path("references/neewer-arca-sections.svg")


class ValidatorFailureRegression(unittest.TestCase):
    def run_failure(self, optimized):
        with tempfile.TemporaryDirectory(prefix="neewer-validator-regression-") as directory:
            project = Path(directory) / "project"
            shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            measurements = project / "measurements.toml"
            changed, count = re.subn(
                r"(\[outer_sleeve_cad_clearance_minimum\]\nvalue = )0\.05",
                r"\g<1>0.10",
                measurements.read_text(),
                count=1,
            )
            self.assertEqual(count, 1)
            measurements.write_text(changed)
            before = {path: (project / path).read_bytes() for path in (ACCEPTANCE, SVG)}
            environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

            stale = subprocess.run(
                [sys.executable, str(project / "references/validate_reconstruction.py"), "--check-report"],
                cwd=project,
                env=environment,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(stale.returncode, 0, stale.stdout + stale.stderr)
            self.assertEqual(json.loads(stale.stdout)["status"], "stale")

            command = [sys.executable]
            if optimized:
                command.append("-O")
            command.append(str(project / "references/validate_reconstruction.py"))
            completed = subprocess.run(command, cwd=project, env=environment, text=True, capture_output=True)
            self.assertNotEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["accepted"])
            self.assertFalse(result["outer_sleeve_fit"]["accepted"])
            self.assertGreater(result["outer_sleeve_fit"]["declared_minimum_mm"], result["outer_sleeve_fit"]["actual_minimum_distance_mm"])
            self.assertTrue(any(finding["code"] == "assembly.outer_sleeve_clearance" for finding in result["findings"]))
            for path, contents in before.items():
                self.assertEqual((project / path).read_bytes(), contents, f"failed validation rewrote {path}")

    def test_bad_clearance_fails_in_normal_python(self):
        self.run_failure(optimized=False)

    def test_bad_clearance_fails_with_assertions_disabled(self):
        self.run_failure(optimized=True)


if __name__ == "__main__":
    unittest.main()
