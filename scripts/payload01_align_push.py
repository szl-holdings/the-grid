#!/usr/bin/env python3
"""Publish THE GRID to the canonical SZLHOLDINGS Space, fail closed.

Founder-machine only. The publisher never creates a Space, never mints credentials,
and never treats organization membership as publication qualification. It publishes
only an exact clean Git commit to an already-existing canonical target whose current
Hub parent revision is supplied explicitly by the operator.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_REPO = "SZLHOLDINGS/the-grid"
SOURCE_SHA_ENV = "THE_GRID_SOURCE_SHA"
TARGET_PARENT_ENV = "HF_EXPECTED_PARENT_SHA"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
FILES = (
    "play.html",
    "index.html",
    "Dockerfile",
    "README.md",
    "ALIGN.md",
    "docs/FRONTIER.md",
    "docs/OPERATIONAL.md",
)


def die(msg: str, code: int = 2) -> None:
    print(f"FAIL_CLOSED {msg}", file=sys.stderr)
    raise SystemExit(code)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        die(f"git {' '.join(args)}: {detail}")
    return result.stdout.strip()


def require_exact_clean_source(expected_sha: str) -> str:
    if not SHA40.fullmatch(expected_sha):
        die(f"{SOURCE_SHA_ENV} must be a lowercase 40-hex Git commit SHA")

    observed_root = Path(git("rev-parse", "--show-toplevel")).resolve()
    if observed_root != ROOT.resolve():
        die(f"repository root mismatch: expected {ROOT}, observed {observed_root}")

    observed_sha = git("rev-parse", "HEAD")
    if observed_sha != expected_sha:
        die(f"source moved: expected {expected_sha}, observed {observed_sha}")

    if git("status", "--porcelain"):
        die("working tree is not clean; publication requires exact committed bytes")

    for rel in FILES:
        path = ROOT / rel
        if path.is_symlink() or not path.is_file():
            die(f"required source file is missing, non-file, or symlink: {rel}")
        git("ls-files", "--error-unmatch", rel)

    return observed_sha


def require_parent_sha(value: str) -> str:
    if not SHA40.fullmatch(value):
        die(f"{TARGET_PARENT_ENV} must be the lowercase 40-hex current Hub revision")
    return value


def main() -> None:
    hf = os.environ.get("HF_TOKEN")
    if not hf:
        die("HF_TOKEN unset. No provider mutation attempted.")

    expected_source = os.environ.get(SOURCE_SHA_ENV, "")
    source_sha = require_exact_clean_source(expected_source)
    expected_parent = require_parent_sha(os.environ.get(TARGET_PARENT_ENV, ""))

    try:
        from huggingface_hub import CommitOperationAdd, HfApi
    except ImportError:
        die("huggingface_hub is required; install it in an isolated operator environment")

    api = HfApi(token=hf)
    try:
        before = api.repo_info(repo_id=TARGET_REPO, repo_type="space")
    except Exception as exc:  # provider/network/auth errors must fail before write
        die(f"cannot read existing canonical target {TARGET_REPO}: {exc}")

    observed_parent = getattr(before, "sha", None)
    if observed_parent != expected_parent:
        die(
            f"target moved or expected parent is stale: expected {expected_parent}, "
            f"observed {observed_parent!r}"
        )

    operations = [
        CommitOperationAdd(path_in_repo=rel, path_or_fileobj=str(ROOT / rel))
        for rel in FILES
    ]

    print(f"publishing exact source {source_sha} to {TARGET_REPO} from parent {expected_parent}")
    try:
        commit = api.create_commit(
            repo_id=TARGET_REPO,
            repo_type="space",
            operations=operations,
            commit_message=f"Publish THE GRID from GitHub {source_sha}",
            parent_commit=expected_parent,
        )
    except Exception as exc:
        die(f"Hub commit failed; do not retry until target/source state is re-read: {exc}")

    commit_sha = getattr(commit, "oid", None) or getattr(commit, "commit_id", None)
    if not commit_sha:
        die("Hub returned no commit identity; publication cannot be qualified")

    try:
        after = api.repo_info(repo_id=TARGET_REPO, repo_type="space")
    except Exception as exc:
        die(f"Hub commit returned but readback failed: {exc}")

    if getattr(after, "sha", None) != commit_sha:
        die(
            "Hub readback does not match the returned publication commit; "
            "treat provider state as unqualified"
        )

    print(f"QUALIFIED_PROVIDER_WRITE target={TARGET_REPO} hub_sha={commit_sha} source_sha={source_sha}")
    print("Runtime/browser qualification remains separate. Do not promote product or proof surfaces here.")


if __name__ == "__main__":
    main()
