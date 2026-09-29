"""PAYLOAD-01-ALIGN-PUSH.md must describe the pinned deployer as it is.

The retirement note maps each guard of the retired local publisher to the
committed writer. The expected-parent guard (create_commit(parent_commit=...))
is the one the reusable deployer may or may not provide, so this test reads the
deployer source at the exact SHA hf-space.yml pins and requires the note's row
to agree with it: "DROPPED" while no create_commit call passes parent_commit,
and not "DROPPED" once one does.

publication-contract.yml checks that deployer revision out and exports its
path as TOOLS. Outside CI, run with TOOLS pointing at a checkout of
szl-holdings/.github at the pinned SHA. Without TOOLS the test is skipped
locally, and fails in GitHub Actions.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTE = ROOT / "PAYLOAD-01-ALIGN-PUSH.md"
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "hf-space.yml"
DEPLOYER_REL = Path(".github") / "scripts" / "hf_deploy_from_dockerfile.py"
PIN = re.compile(r"reusable-hf-deploy\.yml@([0-9a-f]{40})")
ROW_KEY = "Expected-parent guard"


def pinned_sha() -> str:
    pins = PIN.findall(DEPLOY_WORKFLOW.read_text(encoding="utf-8"))
    if len(set(pins)) != 1:
        raise AssertionError(f"hf-space.yml must pin exactly one deployer SHA, found {pins}")
    return pins[0]


def create_commit_calls(source: str) -> list[ast.Call]:
    calls = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name == "create_commit":
            calls.append(node)
    return calls


def passes_parent_commit(call: ast.Call) -> bool:
    return any(k.arg == "parent_commit" for k in call.keywords)


def note_row(key: str) -> list[str]:
    for line in NOTE.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 2 and cells[0].startswith(key):
            return cells
    raise AssertionError(f"{NOTE.name} has no table row starting with {key!r}")


class RetirementNoteMatchesPinnedDeployer(unittest.TestCase):
    def setUp(self) -> None:
        tools = os.environ.get("TOOLS", "")
        if not tools:
            if os.environ.get("GITHUB_ACTIONS") == "true":
                self.fail("TOOLS is unset; publication-contract.yml must export the deployer checkout")
            self.skipTest("set TOOLS to a checkout of szl-holdings/.github at the pinned SHA")
        self.tools = Path(tools)
        head = subprocess.run(
            ["git", "-C", str(self.tools), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        self.assertEqual(head, pinned_sha(), "TOOLS is not the deployer revision hf-space.yml pins")
        self.calls = create_commit_calls((self.tools / DEPLOYER_REL).read_text(encoding="utf-8"))
        self.assertTrue(self.calls, "the pinned deployer has no create_commit call")

    def test_expected_parent_row_states_what_the_deployer_does(self) -> None:
        _, workflow_cell = note_row(ROW_KEY)
        guarded = all(passes_parent_commit(c) for c in self.calls)
        if guarded:
            self.assertNotIn(
                "DROPPED", workflow_cell,
                "the pinned deployer now passes parent_commit; update the note",
            )
        else:
            self.assertTrue(
                workflow_cell.startswith("**DROPPED.**"),
                "the pinned deployer passes no parent_commit; the note must say the guard is DROPPED",
            )

    def test_prose_does_not_claim_every_guarantee_is_kept(self) -> None:
        guarded = all(passes_parent_commit(c) for c in self.calls)
        prose = NOTE.read_text(encoding="utf-8").split("\n| ", 1)[0]
        if not guarded:
            self.assertIn("One is dropped: the expected-parent guard.", prose)


if __name__ == "__main__":
    unittest.main()
