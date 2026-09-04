#!/usr/bin/env python3
"""PAYLOAD-01 — founder-machine only.

Creates HF Docker Spaces SZLHOLDINGS/the-grid + betterwithage/the-grid
when tokens exist. Fail closed. Does not mint keys. Does not glow constellation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def die(msg: str, code: int = 2) -> None:
    print(f"FAIL_CLOSED {msg}", file=sys.stderr)
    raise SystemExit(code)


def main() -> None:
    gh = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    hf = os.environ.get("HF_TOKEN")
    if not gh:
        die("GITHUB_TOKEN unset. Export on founder machine. Do not paste into chat.")
    if not hf:
        die("HF_TOKEN unset. Cannot create Spaces. GitHub source stays the live surface.")

    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        die("pip install huggingface_hub first")

    api = HfApi(token=hf)
    spaces = [
        ("SZLHOLDINGS/the-grid", "org exhibit"),
        ("betterwithage/the-grid", "founder pin"),
    ]
    files = [
        "play.html",
        "index.html",
        "Dockerfile",
        "README.md",
        "ALIGN.md",
        "docs/FRONTIER.md",
        "docs/OPERATIONAL.md",
    ]
    for repo_id, label in spaces:
        print(f"create_or_exists {repo_id} ({label})")
        create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            exist_ok=True,
            token=hf,
            private=False,
        )
        for rel in files:
            path = ROOT / rel
            if not path.exists():
                print(f"skip missing {rel}")
                continue
            api.upload_file(
                path_or_fileobj=str(path),
                path_in_repo=rel,
                repo_id=repo_id,
                repo_type="space",
                token=hf,
            )
            print(f"  uploaded {rel}")
    print("DONE. Do not glow constellation until the Space serves port 7860.")
    print("  https://huggingface.co/spaces/SZLHOLDINGS/the-grid")
    print("  https://huggingface.co/spaces/betterwithage/the-grid")


if __name__ == "__main__":
    main()
