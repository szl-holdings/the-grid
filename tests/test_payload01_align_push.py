from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "payload01_align_push.py"
spec = importlib.util.spec_from_file_location("grid_publisher", SCRIPT)
assert spec and spec.loader
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublicationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_root = publisher.ROOT
        self._old_files = publisher.FILES
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Grid Contract Test"], check=True)
        (self.root / "README.md").write_text("grid\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-q", "-m", "fixture"], check=True)
        publisher.ROOT = self.root
        publisher.FILES = ("README.md",)
        self.head = subprocess.check_output(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True
        ).strip()

    def tearDown(self) -> None:
        publisher.ROOT = self._old_root
        publisher.FILES = self._old_files
        self.tempdir.cleanup()

    def test_exact_clean_source_is_accepted(self) -> None:
        self.assertEqual(publisher.require_exact_clean_source(self.head), self.head)

    def test_source_movement_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            publisher.require_exact_clean_source("0" * 40)

    def test_dirty_tracked_file_is_rejected(self) -> None:
        (self.root / "README.md").write_text("changed\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            publisher.require_exact_clean_source(self.head)

    def test_untracked_file_is_rejected(self) -> None:
        (self.root / "UNTRACKED").write_text("unexpected\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            publisher.require_exact_clean_source(self.head)

    def test_parent_sha_must_be_exact_lowercase_sha1(self) -> None:
        self.assertEqual(publisher.require_parent_sha("a" * 40), "a" * 40)
        for invalid in ("", "A" * 40, "a" * 39, "g" * 40):
            with self.subTest(invalid=invalid), self.assertRaises(SystemExit):
                publisher.require_parent_sha(invalid)


if __name__ == "__main__":
    unittest.main()
