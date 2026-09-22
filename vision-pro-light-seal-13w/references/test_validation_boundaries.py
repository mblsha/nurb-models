"""Acceptance boundaries: concurrent replacement, runtime identity and rigid datum."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from nurb import builder, checks, compare

ROOT = Path(__file__).resolve().parents[1]


def load(root, name):
    spec = importlib.util.spec_from_file_location("boundary_"+name, root / "references" / (name+".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReplacementBoundary(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="lightseal-boundary-")
        self.root = Path(self.directory.name) / "project"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def tearDown(self):
        self.directory.cleanup()

    def exercise(self, entry):
        original_build = builder.build
        for filename in ("export-manifest.json", "vision_pro_light_seal_13w.step", "vision_pro_light_seal_13w.stl", "vision_pro_light_seal_13w.3mf"):
            with self.subTest(entry=entry, replacement=filename):
                path = self.root / "build" / filename
                before = path.read_bytes()
                replaced = []
                def build_and_replace(*args, **kwargs):
                    result = original_build(*args, **kwargs)
                    if not replaced:
                        temporary = path.with_suffix(path.suffix+".replacement")
                        temporary.write_bytes(before+b"\n")
                        temporary.replace(path)
                        replaced.append(True)
                    return result
                try:
                    with patch.object(builder, "build", build_and_replace):
                        with self.assertRaisesRegex(RuntimeError, "manifest or exports changed during validation"):
                            module = load(self.root, entry)
                            if entry == "export_identity":
                                module.verify()
                            elif entry == "validate_interfaces":
                                module.validate(write=False)
                            else:
                                module.main()
                    self.assertTrue(replaced)
                finally:
                    path.write_bytes(before)

    def test_direct_verify_rejects_every_replacement(self):
        self.exercise("export_identity")

    def test_interface_path_rejects_every_replacement(self):
        self.exercise("validate_interfaces")

    def test_reconstruction_path_rejects_every_replacement(self):
        self.exercise("validate_reconstruction")

    def test_interface_watches_manifest_after_source_verification(self):
        module = load(self.root, "validate_interfaces")
        manifest = self.root / "build/export-manifest.json"
        def replace_during_measurement(*args):
            manifest.write_bytes(manifest.read_bytes()+b"\n")
            return {"accepted":True}
        with patch.object(module, "verify_reference_symmetry_plane", replace_during_measurement):
            with self.assertRaisesRegex(RuntimeError, "validation inputs changed"):
                module.validate(write=False)

    def test_reconstruction_watches_manifest_after_source_verification(self):
        module = load(self.root, "validate_reconstruction")
        original = module.import_step
        manifest = self.root / "build/export-manifest.json"
        def replace_after_step_read(*args):
            body = original(*args)
            manifest.write_bytes(manifest.read_bytes()+b"\n")
            return body
        with patch.object(module, "import_step", replace_after_step_read):
            with self.assertRaisesRegex(RuntimeError, "manifest or exports changed"):
                module.main()

    def test_runtime_dependency_change_expires_manifest(self):
        module = load(self.root, "export_identity")
        original = module.importlib.metadata.version
        def changed(package):
            return "changed-scipy" if package == "scipy" else original(package)
        with patch.object(module.importlib.metadata, "version", changed):
            with self.assertRaisesRegex(RuntimeError, "manifest is stale"):
                module.verify()
        with patch.object(module, "nurb_source_digest", return_value="changed-editable-source"):
            with self.assertRaisesRegex(RuntimeError, "manifest is stale"):
                module.verify()


class DatumAndDiscovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load(ROOT, "validate_interfaces")
        cls.alignment = json.loads((ROOT / "references/alignment.json").read_text())
        cls.card = compare.setting(checks.settings(ROOT / "parts/vision_pro_light_seal_13w.py"))["transform"]

    def test_card_and_alignment_match(self):
        self.validator.validate_alignment(self.alignment, self.card)

    def test_scale_shear_reflection_projective_and_nonfinite_rejected(self):
        original = np.asarray(self.alignment["old_glb_to_symmetric_cad"])
        for kind in ("scale", "shear", "reflection", "projective", "nan"):
            matrix = original.copy()
            if kind == "scale": matrix[:3,0] *= 1.01
            if kind == "shear": matrix[0,1] += .1
            if kind == "reflection": matrix[:3,0] *= -1
            if kind == "projective": matrix[3,0] = .1
            if kind == "nan": matrix[0,0] = float("nan")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.validator.validate_alignment({"old_glb_to_symmetric_cad": matrix.tolist()}, matrix.ravel().tolist())

    def test_different_rigid_card_datum_rejected(self):
        card = np.asarray(self.card).reshape(4,4).copy()
        card[0,3] += .001
        with self.assertRaisesRegex(ValueError, "exactly match"):
            self.validator.validate_alignment(self.alignment, card.ravel().tolist())

    def test_runtime_content_hash_tracks_editable_source(self):
        module = load(ROOT, "export_identity")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "builder.py"
            source.write_text("geometry = 1\n")
            before = module.nurb_source_digest(directory)
            source.write_text("geometry = 2\n")
            self.assertNotEqual(before, module.nurb_source_digest(directory))
        versions = module.inputs()["runtime_versions"]
        self.assertTrue(all(name in versions for name in ("numpy","scipy","lib3mf","build123d","cadquery-ocp","trimesh","nurb","python")))

    def test_exception_publication_closes_every_current_discovery_path(self):
        import tomllib
        settings = tomllib.loads((ROOT / "measurements.toml").read_text())["vision_pro_narrow_lip"]
        self.assertEqual(settings["acceptance"], "references/interface-validation-latest.json")
        self.assertEqual(settings["acceptance_json_pointer"], "/accepted")
        with tempfile.TemporaryDirectory() as directory:
            references = Path(directory)
            module = load(ROOT, "validate_interfaces")
            module.REFERENCES = references
            for name in ("interface-validation-latest.json","interface-validation.json","vision-pro-narrow-lip-acceptance.json"):
                (references / name).write_text('{"accepted":true,"status":"accepted"}')
            failure = {"status":"failed","accepted":False,"findings":[{"code":"test","message":"source was replaced"}]}
            module.publish_current(failure)
            for name in ("interface-validation-latest.json","interface-validation.json","vision-pro-narrow-lip-acceptance.json"):
                value = json.loads((references / name).read_text())
                self.assertFalse(value["accepted"])
                self.assertEqual(value["status"], "failed")
        for path in (ROOT / "references/historical").glob("*.json"):
            history = json.loads(path.read_text())
            self.assertFalse(history["accepted"])
            self.assertEqual(history["status"], "historical_superseded")


if __name__ == "__main__":
    unittest.main()
