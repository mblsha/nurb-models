"""Acceptance must reject source/export drift, including equal-volume changes."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[1]


class ExportBinding(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="lightseal-binding-test-")
        self.root = Path(self.temporary.name)
        for directory in ("parts", "build"):
            shutil.copytree(ROOT / directory, self.root / directory, ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "references").mkdir()
        shutil.copy2(ROOT / "measurements.toml", self.root / "measurements.toml")
        source = self.root / "references/export_identity.py"
        shutil.copy2(ROOT / "references/export_identity.py", source)
        spec = importlib.util.spec_from_file_location("test_export_identity_copy", source)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def tearDown(self):
        self.temporary.cleanup()

    def update_source_identity_only(self):
        manifest = json.loads(self.module.MANIFEST.read_text())
        manifest["inputs"] = self.module.inputs()
        self.module.MANIFEST.write_text(json.dumps(manifest))

    def test_current_source_builds_matching_geometry(self):
        body, _ = self.module.verify()
        self.assertTrue(body.is_valid)

    def test_stale_source_is_rejected(self):
        self.module.PART.write_text(self.module.PART.read_text() + "\n# Source changed after export.\n")
        with self.assertRaisesRegex(RuntimeError, "manifest is stale"):
            self.module.verify()

    def test_stale_exports_are_rejected(self):
        for suffix in (".step", ".stl", ".3mf"):
            with self.subTest(suffix=suffix):
                path = self.root / "build" / (self.module.NAME + suffix)
                original = path.read_bytes()
                if suffix == ".3mf":
                    # A translated STL has equal volume, but cannot inherit current evidence.
                    import zipfile
                    with zipfile.ZipFile(path, "a") as archive:
                        data = archive.read("3D/3dmodel.model").replace(b'<model ', b'<model changed="true" ', 1)
                        archive.writestr("3D/3dmodel.model", data)
                else:
                    path.write_bytes(original + b"\nchanged")
                with self.assertRaisesRegex(RuntimeError, "export is stale"):
                    self.module.verify()
                path.write_bytes(original)

    def test_equal_volume_wrong_stl_is_rejected(self):
        path = self.root / "build" / (self.module.NAME + ".stl")
        mesh = trimesh.load_mesh(path)
        before = mesh.volume
        mesh.apply_translation([1, 0, 0])
        self.assertAlmostEqual(before, mesh.volume, places=6)
        mesh.export(path)
        with self.assertRaisesRegex(RuntimeError, "export is stale"):
            self.module.verify()

    def test_unbuildable_source_cannot_be_rebound(self):
        source = self.module.PART.read_text().replace('    if not 1.0 <= wall_mm <= 3.0:', '    raise RuntimeError("deliberately unbuildable model")\n    if not 1.0 <= wall_mm <= 3.0:')
        self.module.PART.write_text(source)
        self.update_source_identity_only()
        with self.assertRaisesRegex(RuntimeError, "unbuildable model"):
            self.module.verify()

    def test_equal_volume_changed_body_cannot_be_rebound(self):
        source = self.module.PART.read_text().replace('    return body\n', '    return Pos(1, 0, 0) * body\n')
        self.module.PART.write_text(source)
        self.update_source_identity_only()
        with self.assertRaisesRegex(RuntimeError, "source geometry differs"):
            self.module.verify()


if __name__ == "__main__":
    unittest.main()
