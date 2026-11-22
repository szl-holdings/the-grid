"""Offline Python-stdlib regression: the advertised /play.html must exist in the image."""
from pathlib import Path
import shlex
import unittest

ROOT = Path(__file__).resolve().parents[1]


def has_play_route_copy(dockerfile: str) -> bool:
    for line in dockerfile.splitlines():
        line = line.strip()
        if not line.startswith("COPY "):
            continue
        args = shlex.split(line)
        if len(args) == 3 and args[0] == "COPY" and args[1] == "play.html":
            if args[2] in {"play.html", "./play.html", "/app/play.html"}:
                return True
    return False


class PlayDeepLinkContract(unittest.TestCase):
    def test_alias_to_index_does_not_preserve_play_route(self):
        self.assertFalse(has_play_route_copy("COPY play.html index.html\n"))
        self.assertTrue(has_play_route_copy("COPY play.html index.html\nCOPY play.html ./play.html\n"))

    def test_advertised_play_html_is_copied_as_play_html(self):
        card = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("[play.html](./play.html)", card)
        self.assertTrue((ROOT / "play.html").is_file())
        self.assertTrue(
            has_play_route_copy((ROOT / "Dockerfile").read_text(encoding="utf-8")),
            "COPY play.html index.html aliases only the root file; /play.html remains 404",
        )


if __name__ == "__main__":
    unittest.main()
