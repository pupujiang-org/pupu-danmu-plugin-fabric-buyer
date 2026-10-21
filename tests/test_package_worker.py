"""Contracts for the official schema-v2 fabric-buyer Worker package."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import package_worker

ROOT = Path(__file__).resolve().parents[1]
SDK_RELEASE_URL = (
    "https://github.com/pupujiang-org/pupu-danmu-plugin-sdk/releases/download/"
    "v0.3.0/pupu_danmu_plugin_sdk-0.3.0-py3-none-any.whl"
)
SDK_RELEASE_SHA256 = "add62b2baeecb6043a68fca55313f4fe755566b601b6e21fda622a5ea11bb718"


class WorkerPackageTests(unittest.TestCase):
    def test_worker_manifest_targets_a_stable_schema_v2_release(self) -> None:
        manifest = json.loads((ROOT / "worker" / "manifest.json").read_text("utf-8"))

        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(manifest["id"], "org.pupujiang.fabric-buyer")
        self.assertEqual(manifest["version"], "1.3.0")
        self.assertEqual(manifest["runtime_type"], "python-worker")
        self.assertEqual(manifest["plugin_api_version"], 2)
        self.assertEqual(manifest["min_host_version"], "0.5.0b3")
        self.assertEqual(
            set(manifest["capabilities"]),
            {"chat.read", "room.read", "llm.generate", "session.config.read"},
        )

    def test_worker_test_dependency_uses_the_verified_stable_sdk_wheel(self) -> None:
        requirements = (ROOT / "worker" / "requirements.txt").read_text("utf-8")

        self.assertIn(f"pupu-danmu-plugin-sdk @ {SDK_RELEASE_URL}", requirements)
        self.assertIn(f"#sha256={SDK_RELEASE_SHA256}", requirements)
        self.assertNotIn("git+https://", requirements)
        self.assertNotIn("0.3.0.dev0", requirements)

    def test_archive_is_deterministic_and_matches_the_registry_layout(self) -> None:
        first = package_worker.build_worker_archive(expected_version="1.3.0")
        second = package_worker.build_worker_archive(expected_version="1.3.0")

        self.assertEqual(first, second)
        self.assertEqual(
            hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest()
        )
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            names = set(archive.namelist())
            self.assertIn("manifest.json", names)
            self.assertIn("README.md", names)
            self.assertIn("LICENSE", names)
            self.assertIn("worker/fabric_buyer/entrypoint.py", names)
            self.assertIn("worker/fabric_buyer/policy.py", names)
            self.assertNotIn("requirements.txt", names)
            self.assertTrue(
                all(
                    name.startswith(
                        ("manifest.json", "README.md", "LICENSE", "worker/")
                    )
                    for name in names
                )
            )
            self.assertEqual(
                json.loads(archive.read("manifest.json")),
                json.loads((ROOT / "worker" / "manifest.json").read_bytes()),
            )

    def test_builder_parses_source_without_importing_or_executing_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fabric-worker-package-test-") as raw:
            copied_root = Path(raw)
            shutil.copytree(ROOT / "worker", copied_root / "worker")
            shutil.copy2(ROOT / "LICENSE", copied_root / "LICENSE")
            sentinel = copied_root / "executed.txt"
            (copied_root / "worker" / "fabric_buyer" / "sentinel.py").write_text(
                "raise RuntimeError('must not execute')\n", encoding="utf-8"
            )

            archive = package_worker.build_worker_archive(root=copied_root)

            with zipfile.ZipFile(io.BytesIO(archive)):
                pass
            self.assertFalse(sentinel.exists())

    def test_builder_rejects_manifest_version_mismatch_and_invalid_python(self) -> None:
        with self.assertRaises(package_worker.WorkerPackageError):
            package_worker.build_worker_archive(expected_version="1.2.0")

        with tempfile.TemporaryDirectory(prefix="fabric-worker-invalid-source-") as raw:
            copied_root = Path(raw)
            shutil.copytree(ROOT / "worker", copied_root / "worker")
            shutil.copy2(ROOT / "LICENSE", copied_root / "LICENSE")
            (copied_root / "worker" / "fabric_buyer" / "broken.py").write_text(
                "def broken(:\n", encoding="utf-8"
            )

            with self.assertRaises(package_worker.WorkerPackageError):
                package_worker.build_worker_archive(root=copied_root)


if __name__ == "__main__":
    unittest.main()
