"""Files published to SZLHOLDINGS/the-grid must not deny that the Space exists.

Every Dockerfile COPY source, the Dockerfile and the README card are published
to the Space by hf-space.yml. A present-tense "does not exist" / "not created"
claim about the canonical Space inside one of those files is false by
construction once the file is on the Space. Dated history may say it *did not*
exist on a given date.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_space_contract import ROOT, SPACE_ID, copy_sources  # noqa: E402

ABSENCE_CLAIM = re.compile(r"\b(does not exist|doesn't exist|not created|not found)\b", re.IGNORECASE)


def published_files() -> list[str]:
    return sorted(set(copy_sources()) | {"Dockerfile", "README.md"})


class PublishedFilesDoNotDenyTheSpace(unittest.TestCase):
    def test_no_present_tense_absence_claim_about_the_canonical_space(self) -> None:
        offenders = []
        for rel in published_files():
            text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                if SPACE_ID in line and ABSENCE_CLAIM.search(line):
                    offenders.append(f"{rel}:{number}: {line.strip()}")
        self.assertEqual(offenders, [], "a published file says the Space it is published to does not exist")

    def test_align_snapshot_is_marked_historical(self) -> None:
        if "ALIGN.md" not in published_files():
            self.skipTest("ALIGN.md is not published")
        head = (ROOT / "ALIGN.md").read_text(encoding="utf-8").split("\n| ", 1)[0]
        self.assertIn("Historical snapshot, measured 2026-09-11. Not current state.", head)


if __name__ == "__main__":
    unittest.main()
