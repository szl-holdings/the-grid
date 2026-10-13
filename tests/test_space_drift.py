"""Offline tests for .github/scripts/hf_space_drift.py (no network).

The drift verdict is a pure function of one observation of the Space and the
git blob oids at HEAD, so every red case can be exercised with fixtures.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import importlib.util
import subprocess
import unittest.mock
from pathlib import Path

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
        with unittest.mock.patch.object(drift, "observe", side_effect=lambda *a: copy.deepcopy(seq.pop(0))), \
             unittest.mock.patch.object(drift, "git_head_oids", return_value=dict(GIT)), \
             unittest.mock.patch.object(drift, "refresh_main", return_value=HEAD), \
             unittest.mock.patch.object(drift.time, "sleep") as sleep, \
             unittest.mock.patch.dict("os.environ", {}, clear=False) as env, \
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
        with unittest.mock.patch.object(drift, "observe", return_value=stale), \
             unittest.mock.patch.object(drift, "git_head_oids", return_value=dict(GIT)), \
             unittest.mock.patch.object(drift, "refresh_main", return_value=HEAD), \
             unittest.mock.patch.object(drift.time, "sleep"), \
             unittest.mock.patch.dict("os.environ", {}, clear=False) as env, \
             contextlib.redirect_stdout(io.StringIO()):
            env.pop("GITHUB_STEP_SUMMARY", None)
            rc = drift.main(["--space", "SZLHOLDINGS/the-grid", "--paths", '["play.html"]',
                             "--served", "{}", "--settle-seconds", "0"])
        self.assertEqual(rc, 1)


class MovingMain(unittest.TestCase):
    def run_with(self, refresh, observe, oids, settle=600):
        output = io.StringIO()
        with unittest.mock.patch.object(drift, "refresh_main", side_effect=refresh), \
             unittest.mock.patch.object(drift, "observe", side_effect=observe), \
             unittest.mock.patch.object(drift, "git_head_oids", side_effect=oids), \
             unittest.mock.patch.object(drift.time, "sleep"), \
             unittest.mock.patch.dict("os.environ", {}, clear=True), contextlib.redirect_stdout(output):
            rc = drift.main(["--space", "SZLHOLDINGS/the-grid", "--paths", '["play.html"]',
                             "--served", '{"/": "play.html"}', "--settle-seconds", str(settle), "--interval", "1"])
        return rc, output.getvalue()

    def test_source_advance_during_observation_is_retried_against_new_main(self):
        new = "b" * 40
        new_git = {**GIT, "play.html": "c" * 40}
        newer = healthy()
        newer["hub_oids"] = new_git
        newer["smoke"]["/"]["oid"] = new_git["play.html"]
        def oids(paths, ref="HEAD"):
            if "Dockerfile" in paths:
                return {"Dockerfile": "1", ".github/workflows/hf-space-drift.yml": "2"}
            return new_git if ref == new else GIT
        rc, output = self.run_with([HEAD, new, new, new], [newer, newer], oids)
        self.assertEqual(rc, 0, output)
        self.assertIn("main advanced during observation", output)
        self.assertIn(f"observed main `{new}`", output)
        self.assertIn("**Result:** no drift", output)

    def test_failed_main_refresh_is_not_a_stale_success(self):
        rc, output = self.run_with([subprocess.TimeoutExpired("git", 30)], [], lambda *a: GIT, settle=0)
        self.assertEqual(rc, 1)
        self.assertIn("observation failed: TimeoutExpired", output)

    def test_changed_monitor_configuration_requires_fresh_run(self):
        rc, output = self.run_with([HEAD], [], lambda paths, ref="HEAD": {"Dockerfile": ref}, settle=0)
        self.assertEqual(rc, 1)
        self.assertIn("fresh workflow run is required", output)
        self.assertIn("**Result:** INCONCLUSIVE", output)

    def test_refresh_fetches_main_objects_without_checkout(self):
        responses = [unittest.mock.Mock(), unittest.mock.Mock(stdout=HEAD + "\n")]
        with unittest.mock.patch.object(drift.subprocess, "run", side_effect=responses) as run:
            self.assertEqual(drift.refresh_main(), HEAD)
        self.assertIn("refs/heads/main", run.call_args_list[0].args[0])
        self.assertEqual(run.call_args_list[0].kwargs["timeout"], 30)
        self.assertFalse(any("checkout" in c.args[0] for c in run.call_args_list))


class MovingMainAcceptance(unittest.TestCase):
    """X65 acceptance case 3: main moves A -> B while the scheduled watch runs.

    The checkout (HEAD) is commit A. Main B changes play.html only, so the
    monitor's own configuration is the same at A and B. Time is simulated, so
    the bounded settle window is exercised without sleeping.
    """

    A, B = HEAD, "b" * 40
    GIT_A = dict(GIT)
    GIT_B = {**GIT, "play.html": "c" * 40}
    CONTROLS = {"Dockerfile": GIT["Dockerfile"], ".github/workflows/hf-space-drift.yml": "d" * 40}

    def oids(self, paths, ref="HEAD"):
        if ".github/workflows/hf-space-drift.yml" in paths:
            return dict(self.CONTROLS)
        return dict(self.GIT_B if ref == self.B else self.GIT_A)

    @staticmethod
    def space_serving(git: dict, stage: str = "RUNNING") -> dict:
        obs = healthy()
        obs["api"]["runtime"]["stage"] = stage
        obs["hub_oids"] = dict(git)
        obs["smoke"]["/"]["oid"] = git["play.html"]
        obs["smoke"]["/healthz"]["oid"] = git["healthz"]
        return obs

    def run_watch(self, refresh, observations, oids=None, settle=1200, interval=60):
        """Run main() with main tips `refresh` (consumed per fetch) and Space states `observations`."""
        clock = [0.0]
        refresh, observations = list(refresh), [copy.deepcopy(o) for o in observations]

        def next_tip():
            tip = refresh.pop(0) if len(refresh) > 1 else refresh[0]
            if isinstance(tip, BaseException):
                raise tip
            return tip

        def next_observation(*_args):
            return observations.pop(0) if len(observations) > 1 else copy.deepcopy(observations[0])

        def sleep(seconds):
            clock[0] += seconds

        output = io.StringIO()
        with unittest.mock.patch.object(drift, "refresh_main", side_effect=next_tip), \
             unittest.mock.patch.object(drift, "observe", side_effect=next_observation) as observe, \
             unittest.mock.patch.object(drift, "git_head_oids", side_effect=oids or self.oids), \
             unittest.mock.patch.object(drift.time, "monotonic", side_effect=lambda: clock[0]), \
             unittest.mock.patch.object(drift.time, "sleep", side_effect=sleep) as slept, \
             unittest.mock.patch.dict("os.environ", {}, clear=True), contextlib.redirect_stdout(output):
            rc = drift.main(["--space", "SZLHOLDINGS/the-grid", "--paths", json.dumps(PATHS),
                             "--served", json.dumps(SERVED), "--settle-seconds", str(settle),
                             "--interval", str(interval)])
        return rc, output.getvalue(), observe.call_count, slept.call_count

    def test_main_moved_before_first_observation_is_compared_against_new_main(self) -> None:
        # The run was triggered at A, but main is already B when the script starts
        # and the Space already serves B: compare with B, never with the checkout.
        rc, output, observed, slept = self.run_watch([self.B], [self.space_serving(self.GIT_B)])
        self.assertEqual(rc, 0, output)
        self.assertIn(f"observed main `{self.B}`", output)
        self.assertIn("**Result:** no drift", output)
        self.assertNotIn(self.GIT_A["play.html"], output)
        self.assertEqual((observed, slept), (1, 0))

    def test_main_moved_during_settling_ends_on_new_main_not_drift_against_old(self) -> None:
        # Attempt 1: main A, Space still building A. Attempt 2: main B, the deploy
        # of B is in flight so the Space serves A. Attempt 3: the Space serves B.
        tips = [self.A, self.A, self.B, self.B, self.B, self.B]
        spaces = [self.space_serving(self.GIT_A, "BUILDING"), self.space_serving(self.GIT_A),
                  self.space_serving(self.GIT_B)]
        rc, output, observed, slept = self.run_watch(tips, spaces)
        self.assertEqual(rc, 0, output)
        self.assertIn(f"Hub oid {self.GIT_A['play.html']} != main {self.GIT_B['play.html']}", output)
        self.assertIn(f"observed main `{self.B}`", output)
        self.assertIn("**Result:** no drift", output)
        self.assertEqual((observed, slept), (3, 2))

    def test_space_matching_old_main_while_main_moves_is_not_a_pass(self) -> None:
        # The Space matches A exactly, but main became B during that observation:
        # that apparent success is superseded and B is assessed next.
        tips = [self.A, self.B, self.B, self.B]
        spaces = [self.space_serving(self.GIT_A), self.space_serving(self.GIT_B)]
        rc, output, observed, slept = self.run_watch(tips, spaces)
        self.assertEqual(rc, 0, output)
        self.assertIn("main advanced during observation", output)
        self.assertIn(f"observed main `{self.B}`", output)
        self.assertEqual((observed, slept), (2, 1))

    def test_drift_persisting_against_stable_new_main_still_fails_after_window(self) -> None:
        # The deploy of B never lands: the Space keeps serving A while main stays
        # B. The watch must end red against B once the bounded window closes.
        rc, output, observed, slept = self.run_watch(
            [self.A, self.B], [self.space_serving(self.GIT_A)], settle=600, interval=60)
        self.assertEqual(rc, 1, output)
        self.assertIn("**Result:** DRIFT", output)
        self.assertIn(f"observed main `{self.B}`\n", output)
        self.assertIn(f"- play.html: Hub oid {self.GIT_A['play.html']} != main {self.GIT_B['play.html']}", output)
        self.assertIn(f"- GET / serves blob {self.GIT_A['play.html']}, main play.html is {self.GIT_B['play.html']}",
                      output)
        self.assertEqual((observed, slept), (11, 10))  # attempts at t=0,60,...,600, then stop

    def test_unreadable_main_is_inconclusive_never_drift_or_pass(self) -> None:
        unreadable_tree = subprocess.CalledProcessError(128, ["git", "ls-tree"])

        def tree_unreadable_at_b(paths, ref="HEAD"):
            if ref == self.B:
                raise unreadable_tree
            return self.oids(paths, ref)

        cases = (("fetch fails", [subprocess.CalledProcessError(128, ["git", "fetch"])], None, "CalledProcessError"),
                 ("fetch times out", [subprocess.TimeoutExpired("git", 30)], None, "TimeoutExpired"),
                 ("fetched tree unreadable", [self.B], tree_unreadable_at_b, "CalledProcessError"))
        for name, tips, oids, error in cases:
            with self.subTest(name):
                rc, output, observed, slept = self.run_watch(
                    tips, [self.space_serving(self.GIT_B)], oids=oids, settle=120, interval=60)
                self.assertEqual(rc, 1, output)
                self.assertIn(f"source or provider observation failed: {error}", output)
                self.assertIn("**Result:** INCONCLUSIVE", output)
                self.assertNotIn("**Result:** DRIFT", output)
                self.assertNotIn("**Result:** no drift", output)
                self.assertIn("(not compared)", output)
                self.assertEqual((observed, slept), (0, 2))

    def test_main_still_moving_when_window_closes_is_inconclusive(self) -> None:
        rc, output, observed, slept = self.run_watch(
            [self.A, self.B], [self.space_serving(self.GIT_A)], settle=0)
        self.assertEqual(rc, 1, output)
        self.assertIn("main advanced during observation", output)
        self.assertIn(f"observed main `{self.A}` (not compared)", output)
        self.assertIn("**Result:** INCONCLUSIVE", output)
        self.assertEqual((observed, slept), (1, 0))


if __name__ == "__main__":
    unittest.main()
