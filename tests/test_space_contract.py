"""Contract for the Hugging Face Space SZLHOLDINGS/the-grid.

These checks keep the committed writer, the image and the card consistent with
each other. They read only files in this repository; nothing here talks to the
Hub. PyYAML is installed in CI from the same hash-locked closure the reusable
deployer uses (see .github/workflows/publication-contract.yml).
"""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
README = ROOT / "README.md"
HEALTHZ = ROOT / "healthz"
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "hf-space.yml"
DRIFT_WORKFLOW = ROOT / ".github" / "workflows" / "hf-space-drift.yml"
DRIFT_SCRIPT = ROOT / ".github" / "scripts" / "hf_space_drift.py"

SPACE_ID = "SZLHOLDINGS/the-grid"
SOURCE_URL = "https://github.com/szl-holdings/the-grid"
REUSABLE = "szl-holdings/.github/.github/workflows/reusable-hf-deploy.yml"
LOCK_GROUP = f"hf-write/space/{SPACE_ID}"
# Hugging Face Space card colors (huggingface.co/docs/hub/spaces-config-reference).
HF_CARD_COLORS = {"red", "yellow", "green", "blue", "indigo", "purple", "pink", "gray"}
# Provider write calls that would make a second writer for the Space.
HUB_WRITE_CALL = re.compile(
    r"\b(create_commit|upload_file|upload_folder|create_repo|delete_file|"
    r"add_space_secret|add_space_variable|restart_space)\s*\("
)


def dockerfile_instructions() -> list[str]:
    """Logical Dockerfile instructions: comments dropped, continuations joined."""
    logical, buf = [], ""
    for raw in DOCKERFILE.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not buf and (not stripped or stripped.startswith("#")):
            continue
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
            continue
        logical.append(buf + stripped)
        buf = ""
    if buf:
        logical.append(buf)
    return logical


def copy_sources() -> list[str]:
    """Build-context sources of COPY/ADD (multi-stage --from excluded)."""
    sources = []
    for line in dockerfile_instructions():
        match = re.match(r"^(COPY|ADD)\s+(.*)$", line, re.IGNORECASE)
        if not match:
            continue
        rest = match.group(2).strip()
        if rest.startswith("["):
            sources.extend(json.loads(rest)[:-1])
            continue
        tokens = rest.split()
        if any(t.lower().startswith("--from") for t in tokens):
            continue
        args = [t for t in tokens if not t.startswith("--")]
        sources.extend(args[:-1])
    return [s[2:] if s.startswith("./") else s for s in sources]


def card() -> tuple[dict, str]:
    text = README.read_text(encoding="utf-8")
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.DOTALL)
    if not match:
        raise AssertionError("README.md has no YAML front matter")
    meta = yaml.safe_load(match.group(1))
    if not isinstance(meta, dict):
        raise AssertionError("README.md front matter is not a mapping")
    return meta, match.group(2)


def deploy_workflow() -> dict:
    data = yaml.safe_load(DEPLOY_WORKFLOW.read_text(encoding="utf-8"))
    # YAML 1.1 reads a bare `on` key as boolean True; the file quotes it.
    if "on" not in data:
        raise AssertionError('hf-space.yml must quote its "on" key')
    return data


class DockerfileContract(unittest.TestCase):
    def test_every_base_image_is_digest_pinned(self) -> None:
        froms = [l for l in dockerfile_instructions() if re.match(r"^FROM\s", l, re.I)]
        self.assertTrue(froms, "Dockerfile has no FROM")
        for line in froms:
            with self.subTest(line=line):
                self.assertRegex(line, r"^FROM\s+(--platform=\S+\s+)?\S+@sha256:[0-9a-f]{64}(\s|$)")

    def test_healthcheck_probes_healthz_on_the_served_port(self) -> None:
        checks = [l for l in dockerfile_instructions() if l.upper().startswith("HEALTHCHECK")]
        self.assertEqual(len(checks), 1, "exactly one HEALTHCHECK is required")
        exposed = re.findall(r"^EXPOSE\s+(\d+)", "\n".join(dockerfile_instructions()), re.M)
        self.assertEqual(exposed, ["7860"])
        self.assertIn("127.0.0.1:7860/healthz", checks[0])

    def test_healthz_is_served_and_is_a_json_liveness_body(self) -> None:
        self.assertIn("healthz", copy_sources())
        body = json.loads(HEALTHZ.read_text(encoding="utf-8"))
        self.assertEqual(body.get("status"), "ok")
        self.assertEqual(body.get("service"), "the-grid")

    def test_no_whole_context_copy(self) -> None:
        # The reusable deployer refuses `COPY . <dest>`; fail here first.
        self.assertNotIn(".", copy_sources())
        for src in copy_sources():
            self.assertTrue((ROOT / src).exists(), f"COPY source missing: {src}")


class CardContract(unittest.TestCase):
    def test_front_matter_is_a_valid_docker_space_card(self) -> None:
        meta, _ = card()
        self.assertEqual(meta.get("sdk"), "docker")
        self.assertEqual(meta.get("app_port"), 7860)
        self.assertIn(meta.get("colorFrom"), HF_CARD_COLORS)
        self.assertIn(meta.get("colorTo"), HF_CARD_COLORS)
        self.assertIsInstance(meta.get("title"), str)
        short = meta.get("short_description", "")
        self.assertLessEqual(len(short), 60, "HF rejects short_description over 60 chars")

    def test_license_matches_the_repository_license(self) -> None:
        meta, _ = card()
        self.assertEqual(meta.get("license"), "apache-2.0")
        self.assertIn("Apache License", (ROOT / "LICENSE").read_text(encoding="utf-8-sig"))
        self.assertIn("Version 2.0", (ROOT / "LICENSE").read_text(encoding="utf-8-sig"))

    def test_card_links_its_github_source(self) -> None:
        _, body = card()
        self.assertIn(f"({SOURCE_URL})", body)


class DeployWorkflowContract(unittest.TestCase):
    def setUp(self) -> None:
        self.wf = deploy_workflow()
        self.job = self.wf["jobs"]["deploy"]
        self.inputs = self.job["with"]

    def test_calls_the_reusable_deployer_pinned_by_commit_sha(self) -> None:
        self.assertRegex(self.job["uses"], rf"^{re.escape(REUSABLE)}@[0-9a-f]{{40}}$")

    def test_targets_the_canonical_space_from_the_exact_main_tip(self) -> None:
        self.assertEqual(self.inputs["hf-repo"], SPACE_ID)
        self.assertEqual(self.inputs["ref"], "${{ github.sha }}")
        self.assertIs(self.inputs["require-default-branch-tip"], True)
        self.assertEqual(self.inputs["dockerfile-path"], "Dockerfile")
        self.assertIs(self.inputs["include-readme"], True)

    def test_attests_root_and_healthz(self) -> None:
        paths = json.loads(self.inputs["smoke-paths"])
        self.assertIn("/", paths)
        self.assertIn("/healthz", paths)
        self.assertGreater(int(self.inputs["wait-running"]), 0)

    def test_one_lock_per_asset_not_per_event(self) -> None:
        conc = self.wf["concurrency"]
        self.assertEqual(conc["group"], LOCK_GROUP)
        self.assertIs(conc["cancel-in-progress"], False)

    def test_only_main_pushes_and_manual_dispatch_can_publish(self) -> None:
        triggers = self.wf["on"]
        self.assertEqual(set(triggers), {"push", "workflow_dispatch"})
        self.assertEqual(triggers["push"]["branches"], ["main"])

    def test_single_declared_credential(self) -> None:
        # The deployer receives exactly one credential: the first candidate the
        # credential job proved can write (organization HF_ORG_TOKEN, else the
        # repository HF_TOKEN that would otherwise shadow the organization one).
        self.assertEqual(
            self.job["secrets"],
            {"HF_TOKEN": "${{ needs.credential.outputs.pick == 'HF_ORG_TOKEN' "
                         "&& secrets.HF_ORG_TOKEN || secrets.HF_TOKEN }}"},
        )
        self.assertEqual(self.job["needs"], "credential")
        self.assertEqual(self.wf["permissions"], {"contents": "read"})

    def test_credential_job_only_reads_authorization_metadata(self) -> None:
        cred = self.wf["jobs"]["credential"]
        self.assertNotIn("permissions", cred)  # inherits contents: read
        (step,) = cred["steps"]
        self.assertEqual(set(step["env"]) - {"HUB_ORG", "HUB_SPACE"}, {"CANDIDATE_HF_ORG_TOKEN", "CANDIDATE_HF_TOKEN"})
        script = step["run"]
        self.assertIn("https://huggingface.co/api/whoami-v2", script)
        self.assertIn("?expand=resourceGroup", script)
        self.assertEqual(step["env"]["HUB_SPACE"], SPACE_ID)
        self.assertNotRegex(script, HUB_WRITE_CALL)
        # Candidates are tried organization-first and the job fails closed.
        self.assertLess(script.index('"HF_ORG_TOKEN"'), script.index('"HF_TOKEN")'))
        self.assertIn("raise SystemExit", script)
        # The summary records validity and kind, never the credential value.
        self.assertNotIn("print(token", script)
        self.assertNotIn("{token}\"", script.replace('f"Bearer {token}"', ""))

    def test_push_paths_cover_every_published_input(self) -> None:
        paths = set(self.wf["on"]["push"]["paths"])
        published = set(copy_sources()) | {
            "Dockerfile",
            "Dockerfile.dockerignore",
            ".dockerignore",
            "README.md",
            ".github/workflows/hf-space.yml",
        }
        self.assertEqual(sorted(published - paths), [], "published inputs missing from push.paths")
        self.assertEqual(sorted(paths - published), [], "push.paths lists an unpublished file")


class DriftWatchContract(unittest.TestCase):
    """hf-space-drift.yml: a scheduled, read-only watch that is never a writer."""

    def setUp(self) -> None:
        text = DRIFT_WORKFLOW.read_text(encoding="utf-8")
        self.text = text
        self.wf = yaml.safe_load(text)
        self.assertIn("on", self.wf, 'hf-space-drift.yml must quote its "on" key')
        self.jobs = self.wf["jobs"]

    def test_runs_on_a_schedule_and_by_hand_only(self) -> None:
        triggers = self.wf["on"]
        self.assertEqual(set(triggers), {"schedule", "workflow_dispatch"})
        crons = [entry["cron"] for entry in triggers["schedule"]]
        self.assertTrue(crons, "the watch needs at least one cron")

    def test_contents_read_only(self) -> None:
        self.assertEqual(self.wf["permissions"], {"contents": "read"})
        for name, job in self.jobs.items():
            with self.subTest(job=name):
                self.assertNotIn("permissions", job)

    def test_never_publishes(self) -> None:
        self.assertNotIn("reusable-hf-deploy", self.text)
        self.assertNotIn("hf_deploy_from_dockerfile", self.text)
        for name, job in self.jobs.items():
            with self.subTest(job=name):
                self.assertNotIn("uses", job)  # no reusable workflow at all
                self.assertNotIn("secrets", job)  # nothing handed to a callee
                self.assertNotIn("outputs", job)  # the census pick goes nowhere
                self.assertNotIn("needs", job)
                for step in job["steps"]:
                    self.assertNotIn("uses", step)

    def test_does_not_share_the_write_lock(self) -> None:
        # A pending run in the same group would displace a pending deploy.
        self.assertNotEqual(self.wf["concurrency"]["group"], LOCK_GROUP)
        self.assertFalse(self.wf["concurrency"]["group"].startswith("hf-write/"))

    def test_census_is_the_deploy_census_verbatim(self) -> None:
        (census,) = self.jobs["credential"]["steps"]
        (deploy_census,) = deploy_workflow()["jobs"]["credential"]["steps"]
        self.assertEqual(census["run"], deploy_census["run"])
        self.assertEqual(census["env"], deploy_census["env"])
        self.assertEqual(census.get("shell"), "python")
        self.assertIn("raise SystemExit", census["run"])  # red when nothing can write

    def test_secrets_reach_only_the_census_step(self) -> None:
        drift = yaml.safe_dump(self.jobs["drift"])
        self.assertNotIn("secrets.", drift)
        self.assertNotIn("github.token", drift)
        script = DRIFT_SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("Authorization", script)
        self.assertNotIn("HF_TOKEN", script)
        self.assertNotRegex(script, r"method\s*=")  # GET only

    def test_checked_paths_equal_the_deploy_set(self) -> None:
        env = self.jobs["drift"]["env"]
        self.assertEqual(env["SPACE_ID"], SPACE_ID)
        checked = json.loads(env["PUBLISHED_PATHS"])
        self.assertEqual(len(checked), len(set(checked)))
        self.assertEqual(set(checked), set(copy_sources()) | {"Dockerfile", "README.md"})
        for path in checked:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_served_routes_are_the_deploy_smoke_paths(self) -> None:
        served = json.loads(self.jobs["drift"]["env"]["SERVED_PATHS"])
        smoke = json.loads(deploy_workflow()["jobs"]["deploy"]["with"]["smoke-paths"])
        self.assertEqual(sorted(served), sorted(smoke))
        # Each route's source is the file the Dockerfile copies to that route.
        copies = {}
        for line in dockerfile_instructions():
            match = re.match(r"^COPY\s+(\S+)\s+(\S+)$", line, re.IGNORECASE)
            if match:
                copies[match.group(1)] = match.group(2)
        self.assertEqual(copies.get(served["/"]), "index.html")
        self.assertEqual(copies.get(served["/healthz"]), "./healthz")

    def test_runs_the_committed_drift_script(self) -> None:
        steps = self.jobs["drift"]["steps"]
        self.assertIn('test "$(git rev-parse HEAD)" = "${GITHUB_SHA}"', steps[0]["run"])
        self.assertIn(".github/scripts/hf_space_drift.py", steps[-1]["run"])
        self.assertIn("--settle-seconds", steps[-1]["run"])


class SingleWriter(unittest.TestCase):
    def test_no_other_tracked_file_writes_to_the_hub(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
        ).stdout.decode("utf-8").split("\0")
        offenders = []
        for rel in filter(None, tracked):
            if rel.startswith("tests/"):
                continue
            path = ROOT / rel
            if path.suffix not in {".py", ".sh", ".js", ".mjs", ".ts", ".yml", ".yaml"}:
                continue
            if HUB_WRITE_CALL.search(path.read_text(encoding="utf-8", errors="replace")):
                offenders.append(rel)
        self.assertEqual(offenders, [], "the Space must have one writer: hf-space.yml")


if __name__ == "__main__":
    unittest.main()
