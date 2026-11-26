import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from bootstrap_project import bootstrap


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        # Keep disposable data within the explicitly selected test workspace.
        self.test_workspace = Path.cwd().resolve()
        self.temp = tempfile.TemporaryDirectory(prefix="bootstrap-test-", dir=self.test_workspace)
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(self.cleanup_workspace)
        self.skill = self.root / "skill"
        engine = self.skill / "assets" / "engine"
        (engine / "tools").mkdir(parents=True)
        data = b"print('source engine')\n"
        (engine / "tools" / "example.py").write_bytes(data)
        self.manifest = self.skill / "assets" / "engine-manifest.json"
        self.manifest.write_text(json.dumps({"files": {"tools/example.py": hashlib.sha256(data).hexdigest()}}))
        self.dest = self.root / "output"

    def cleanup_workspace(self):
        if not self.root.is_relative_to(self.test_workspace) or self.root == self.test_workspace:
            raise RuntimeError("Refusing cleanup outside test workspace")
        self.temp.cleanup()

    def test_copy_is_byte_identical_and_no_implicit_runtime(self):
        result = bootstrap(self.dest, skill_root=self.skill)
        self.assertEqual(result["copied_files"], 1)
        self.assertEqual((self.dest / "tools/example.py").read_bytes(), b"print('source engine')\n")
        self.assertFalse((self.dest / ".venv").exists())
        self.assertIsNone(result["python_executable"])

    def test_nonempty_destination_is_not_overwritten(self):
        self.dest.mkdir()
        marker = self.dest / "user.txt"
        marker.write_text("keep")
        with self.assertRaisesRegex(ValueError, "empty directory"):
            bootstrap(self.dest, skill_root=self.skill)
        self.assertEqual(marker.read_text(), "keep")
        self.assertEqual(len(list(self.dest.iterdir())), 1)

    def test_tampered_bundle_fails_before_writes(self):
        (self.skill / "assets/engine/tools/example.py").write_text("changed")
        with self.assertRaisesRegex(ValueError, "integrity failure"):
            bootstrap(self.dest, skill_root=self.skill)
        self.assertFalse(self.dest.exists())

    def test_skill_cannot_be_output(self):
        with self.assertRaisesRegex(ValueError, "separate"):
            bootstrap(self.skill / "run", skill_root=self.skill)

    def test_manifest_path_cannot_escape(self):
        self.manifest.write_text(json.dumps({"files": {"../escape.py": "a" * 64}}))
        with self.assertRaisesRegex(ValueError, "escapes"):
            bootstrap(self.dest, skill_root=self.skill)
        self.assertFalse(self.dest.exists())

    def raw_fixture(self):
        source = self.root / "runtime"
        raw = source / "raw" / "test_tank"
        raw.mkdir(parents=True)
        data = b"glTF\x02\x00test"
        (raw / "tank.glb").write_bytes(data)
        (raw / "geometry_inventory.json").write_text("{}")
        manifest = {"vehicle_id": "test_tank", "glb_file": "tank.glb", "sha256": hashlib.sha256(data).hexdigest()}
        (raw / "extraction_manifest.json").write_text(json.dumps(manifest))
        return source, raw

    def test_raw_snapshot_copy_verifies_and_preserves_source(self):
        source, raw = self.raw_fixture()
        result = bootstrap(self.dest, source_project=source, source_vehicle="test_tank", skill_root=self.skill)
        self.assertEqual(result["copied_files"], 4)
        self.assertEqual((self.dest / "raw/test_tank/tank.glb").read_bytes(), (raw / "tank.glb").read_bytes())
        self.assertEqual(len(list(raw.iterdir())), 3)

    def test_wrong_raw_hash_fails_before_writes(self):
        source, raw = self.raw_fixture()
        (raw / "tank.glb").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            bootstrap(self.dest, source_project=source, source_vehicle="test_tank", skill_root=self.skill)
        self.assertFalse(self.dest.exists())

    def test_missing_runtime_fails_before_writes(self):
        with self.assertRaisesRegex(ValueError, "interpreter missing"):
            bootstrap(self.dest, runtime_project=self.root / "missing", skill_root=self.skill)
        self.assertFalse(self.dest.exists())


if __name__ == "__main__":
    unittest.main()
