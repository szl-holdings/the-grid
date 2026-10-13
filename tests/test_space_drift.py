"""Offline tests for .github/scripts/hf_space_drift.py (no network).

The drift verdict is a pure function of one observation of the Space and the
git blob oids at HEAD, so every red case can be exercised with fixtures.
"""
from __future__ import annotations

import contextlib
import copy
import io
import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "hf_space_drift.py"

spec = importlib.util.spec_from_file_location("hf_space_drift", SCRIPT)
drift = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drift)

PATHS = ["ALIGN.md", "Dockerfile", "README.md", "healthz", "play.html"]
SERVED = {"/": "play.html", "/healthz": "healthz"}
HEAD = "34a11fe5254ee43992eb34319dd22d2057656ee4"
GIT = {p: f"{i:040x}" for i, p in enumerate(PATHS, start=1)}


def healthy() -> dict:
    return {
        "api_status": 200,
        "api": {"sha": HEAD, "host": "https://example.hf.space",
                "runtime": {"stage": "RUNNING", "sha": HEAD}},
        "tree_status": 200,
        "hub_oids": dict(GIT),
        "smoke": {
            "/": {"status": 200, "bytes": 9031, "oid": GIT["play.html"]},
            "/healthz": {"status": 200, "bytes": 63, "oid": GIT["healthz"]},
        },
    }


class Verdict(unittest.TestCase):
    def check(self, obs: dict) -> list[str]:
        return drift.problems(obs, GIT, PATHS, SERVED)

    def test_matching_space_has_no_drift(self) -> None:
        self.assertEqual(self.check(healthy()), [])

    def test_api_unreachable_is_drift(self) -> None:
        self.assertEqual(self.check({"api_status": 503, "api": None}),
                         ["Space API returned HTTP 503"])

    def test_not_running_is_drift(self) -> None:
        for stage in ("BUILDING", "RUNTIME_ERROR", "PAUSED", "SLEEPING", None):
            obs = healthy()
            obs["api"]["runtime"]["stage"] = stage
            with self.subTest(stage=stage):
                self.assertTrue(any("runtime stage" in p for p in self.check(obs)))

    def test_running_an_older_hub_commit_is_drift(self) -> None:
        obs = healthy()
        obs["api"]["runtime"]["sha"] = "0" * 40
        self.assertTrue(any("runtime.sha" in p for p in self.check(obs)))

    def test_hub_file_differs_from_main(self) -> None:
        obs = healthy()
        obs["hub_oids"]["play.html"] = "f" * 40
        self.assertEqual(self.check(obs), [f"play.html: Hub oid {'f' * 40} != main {GIT['play.html']}"])

    def test_hub_file_missing(self) -> None:
        obs = healthy()
        del obs["hub_oids"]["ALIGN.md"]
        self.assertEqual(self.check(obs), ["ALIGN.md: missing on the Hub"])

    def test_tree_unreadable_is_drift(self) -> None:
        obs = healthy()
        obs["tree_status"] = 404
        obs["hub_oids"] = {}
        found = self.check(obs)
        self.assertIn("Hub tree returned HTTP 404", found)
        self.assertEqual(len(found), 1 + len(PATHS))

    def test_route_not_200_or_empty_is_drift(self) -> None:
        obs = healthy()
        obs["smoke"]["/healthz"] = {"status": 502, "bytes": 0, "oid": drift.git_blob_oid(b"")}
        self.assertEqual(self.check(obs), ["GET /healthz returned HTTP 502"])
        obs["smoke"]["/healthz"] = {"status": 200, "bytes": 0, "oid": drift.git_blob_oid(b"")}
        self.assertEqual(self.check(obs), ["GET /healthz returned an empty body"])

    def test_route_serving_stale_bytes_is_drift(self) -> None:
        obs = healthy()
        obs["smoke"]["/"]["oid"] = "e" * 40
        self.assertEqual(len(self.check(obs)), 1)
        self.assertIn("GET / serves blob", self.check(obs)[0])


class BlobOid(unittest.TestCase):
    def test_matches_git_hash_object(self) -> None:
        for name in ("healthz", "play.html"):
            data = (ROOT / name).read_bytes()
            want = subprocess.run(
                ["git", "hash-object", "--no-filters", "--stdin"], input=data,
                cwd=ROOT, check=True, capture_output=True,
            ).stdout.decode().strip()
            with self.subTest(name=name):
                self.assertEqual(drift.git_blob_oid(data), want)

    def test_head_oids_are_read_from_git(self) -> None:
        oids = drift.git_head_oids(["healthz", "Dockerfile"])
        self.assertEqual(set(oids), {"healthz", "Dockerfile"})
        for oid in oids.values():
            self.assertRegex(oid, r"^[0-9a-f]{40}$")


class SettleLoop(unittest.TestCase):
    def test_retries_until_settled_then_passes(self) -> None:
        building = healthy()
        building["api"]["runtime"]["stage"] = "BUILDING"
        seq = [building, healthy()]
        with mock.patch.object(drift, "observe", side_effect=lambda *a: copy.deepcopy(seq.pop(0))), \
             mock.patch.object(drift, "git_head_oids", return_value=dict(GIT)), \
             mock.patch.object(drift.time, "sleep") as sleep, \
             mock.patch.dict("os.environ", {}, clear=False) as env, \
             contextlib.redirect_stdout(io.StringIO()):
            env.pop("GITHUB_STEP_SUMMARY", None)
            rc = drift.main(["--space", "SZLHOLDINGS/the-grid", "--paths", '["ALIGN.md","Dockerfile","README.md","healthz","play.html"]',
                             "--served", '{"/": "play.html", "/healthz": "healthz"}',
                             "--settle-seconds", "600", "--interval", "1"])
        self.assertEqual(rc, 0)
        self.assertEqual(sleep.call_count, 1)

    def test_fails_red_when_drift_persists(self) -> None:
        stale = healthy()
        stale["hub_oids"]["play.html"] = "f" * 40
        with mock.patch.object(drift, "observe", return_value=stale), \
             mock.patch.object(drift, "git_head_oids", return_value=dict(GIT)), \
             mock.patch.object(drift.time, "sleep"), \
             mock.patch.dict("os.environ", {}, clear=False) as env, \
             contextlib.redirect_stdout(io.StringIO()):
            env.pop("GITHUB_STEP_SUMMARY", None)
            rc = drift.main(["--space", "SZLHOLDINGS/the-grid", "--paths", '["play.html"]',
                             "--served", "{}", "--settle-seconds", "0"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
