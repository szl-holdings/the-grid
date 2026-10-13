"""Read-only drift check: does the public Space SZLHOLDINGS/the-grid serve main?

Run by .github/workflows/hf-space-drift.yml on a schedule, so a Space that has
drifted from main (a failed or skipped deploy, a hand edit on the Hub, a stuck
build, a stale edge) turns red between pushes instead of staying invisible.

It holds no credential. It reads main through Git object fetches and uses
anonymous HTTP GETs for the Space:
  1. GET /api/spaces/<id>: the runtime must be RUNNING on the Hub head
     (runtime.sha == sha).
  2. GET /api/spaces/<id>/tree/<sha>: for every published path the Hub blob
     oid must equal `git ls-tree <fresh main SHA>` (a git blob oid; these files are not LFS).
  3. GET <host><path> for every served path: HTTP 200 with a body whose git
     blob oid equals the committed source file the Dockerfile serves there.

A deploy can be in flight when the schedule fires, so the checks are repeated
until they pass or the settle window ends. Every attempt re-resolves main and
compares the Space only with the blobs of that one main commit, and only when
main did not move while the Space was being read.

Exit status 0 means a coherent main snapshot was compared and matched. Exit
status 1 is either DRIFT (the last attempt compared a coherent main snapshot
and found differences) or INCONCLUSIVE (the last attempt could not compare one:
main was unreadable, moved during the observation, or changed the monitor's own
configuration). An inconclusive run is never reported as a pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HUB = "https://huggingface.co"
USER_AGENT = "szl-holdings/the-grid hf-space-drift (read-only)"


def git_blob_oid(data: bytes) -> str:
    """The git blob object id of `data` (what the Hub reports as a file oid)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def git_head_oids(paths: list[str], ref: str = "HEAD") -> dict[str, str]:
    out = subprocess.run(
        ["git", "ls-tree", "-z", ref, "--", *paths],
        check=True, capture_output=True, timeout=30,
    ).stdout.decode("utf-8")
    oids = {}
    for entry in filter(None, out.split("\0")):
        meta, path = entry.split("\t", 1)
        _mode, kind, oid = meta.split()
        if kind == "blob":
            oids[path] = oid
    return oids


def refresh_main() -> str:
    """Fetch objects only; do not replace or execute the checked-out monitor."""
    subprocess.run(["git", "fetch", "--quiet", "--no-tags", "--depth=1", "origin", "refs/heads/main"],
                   check=True, capture_output=True, timeout=30)
    sha = subprocess.run(["git", "rev-parse", "--verify", "FETCH_HEAD^{commit}"],
                         check=True, capture_output=True, text=True, timeout=30).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("main revision is not a commit SHA")
    return sha


def get(url: str, timeout: float = 30) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read() or b""
    except OSError as err:
        return 0, type(err).__name__.encode()


def observe(space: str, paths: list[str], served: dict[str, str]) -> dict:
    """One read-only observation of the Space, its Hub files and its served bytes."""
    status, body = get(f"{HUB}/api/spaces/{space}")
    obs: dict = {"api_status": status, "api": None, "hub_oids": {}, "smoke": {}}
    if status != 200:
        return obs
    api = json.loads(body)
    obs["api"] = api
    if api.get("sha"):
        tree_url = f"{HUB}/api/spaces/{space}/tree/{api['sha']}?recursive=true"
        status, body = get(tree_url)
        obs["tree_status"] = status
        if status == 200:
            wanted = set(paths)
            obs["hub_oids"] = {
                e["path"]: e.get("oid")
                for e in json.loads(body)
                if e.get("type") == "file" and e.get("path") in wanted
            }
    host = (api.get("host") or "").rstrip("/")
    for route in served:
        status, data = get(host + route) if host else (0, b"")
        obs["smoke"][route] = {"status": status, "bytes": len(data), "oid": git_blob_oid(data)}
    return obs


def problems(obs: dict, git_oids: dict[str, str], paths: list[str], served: dict[str, str]) -> list[str]:
    """Every way the observation differs from main; empty means no drift."""
    found = []
    if obs.get("api_status") != 200 or not obs.get("api"):
        return [f"Space API returned HTTP {obs.get('api_status')}"]
    api = obs["api"]
    runtime = api.get("runtime") or {}
    if runtime.get("stage") != "RUNNING":
        found.append(f"runtime stage is {runtime.get('stage')!r}, not 'RUNNING'")
    if not api.get("sha") or runtime.get("sha") != api.get("sha"):
        found.append(f"runtime.sha {runtime.get('sha')!r} is not the Hub head {api.get('sha')!r}")
    if obs.get("tree_status", 200) != 200:
        found.append(f"Hub tree returned HTTP {obs.get('tree_status')}")
    for path in paths:
        want = git_oids.get(path)
        have = obs.get("hub_oids", {}).get(path)
        if want is None:
            found.append(f"{path}: not tracked at HEAD")
        elif have is None:
            found.append(f"{path}: missing on the Hub")
        elif have != want:
            found.append(f"{path}: Hub oid {have} != main {want}")
    for route, source in served.items():
        got = obs.get("smoke", {}).get(route) or {}
        if got.get("status") != 200:
            found.append(f"GET {route} returned HTTP {got.get('status')}")
        elif not got.get("bytes"):
            found.append(f"GET {route} returned an empty body")
        elif got.get("oid") != git_oids.get(source):
            found.append(f"GET {route} serves blob {got.get('oid')}, main {source} is {git_oids.get(source)}")
    return found


def verdict(found: list[str], compared: bool) -> str:
    """'no drift' only for a passing comparison; an uncompared attempt is never drift or a pass."""
    if compared:
        return "DRIFT" if found else "no drift"
    return "INCONCLUSIVE (no coherent main snapshot was compared; not a pass)"


def summarize(space: str, obs: dict, git_oids: dict, paths: list[str], found: list[str], source_sha: str,
              compared: bool = True) -> str:
    api = obs.get("api") or {}
    runtime = api.get("runtime") or {}
    lines = [
        f"### Space drift: {space}\n",
        f"- Hub head `{api.get('sha')}`, runtime `{runtime.get('sha')}`, stage `{runtime.get('stage')}`",
        f"- observed main `{source_sha}`" + ("" if compared else " (not compared)") + "\n",
        "| path | main oid | Hub oid | match |",
        "|---|---|---|---|",
    ]
    for path in paths:
        want, have = git_oids.get(path), obs.get("hub_oids", {}).get(path)
        lines.append(f"| {path} | {want} | {have} | {want is not None and want == have} |")
    lines += ["", "| route | HTTP | bytes | served blob |", "|---|---|---|---|"]
    for route, got in obs.get("smoke", {}).items():
        lines.append(f"| {route} | {got['status']} | {got['bytes']} | {got['oid']} |")
    lines += ["", "**Result:** " + verdict(found, compared)]
    lines += [f"- {p}" for p in found]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--space", required=True)
    ap.add_argument("--paths", required=True, help="JSON list of published repository paths")
    ap.add_argument("--served", required=True, help="JSON map of served route -> source path")
    ap.add_argument("--settle-seconds", type=int, default=0)
    ap.add_argument("--interval", type=int, default=60)
    args = ap.parse_args(argv)

    paths = json.loads(args.paths)
    served = json.loads(args.served)
    if args.settle_seconds < 0 or args.interval <= 0:
        ap.error("settle-seconds must be nonnegative and interval must be positive")
    wanted = sorted(set(paths) | set(served.values()))
    # Configuration changes require a fresh workflow run with its reviewed
    # paths/routes; a content-only main advance can settle within this run.
    controls = ["Dockerfile", ".github/workflows/hf-space-drift.yml"]
    admitted_controls = git_head_oids(controls)
    deadline = time.monotonic() + args.settle_seconds
    while True:
        # `compared` is set only when this attempt's verdict came from one main
        # commit that stayed the tip for the whole observation.
        source_sha, git_oids, obs, compared = "unavailable", {}, {}, False
        try:
            source_sha = refresh_main()
            if git_head_oids(controls, source_sha) != admitted_controls:
                found = ["monitor configuration changed on main; a fresh workflow run is required"]
            else:
                git_oids = git_head_oids(wanted, source_sha)
                obs = observe(args.space, paths, served)
                after_sha = refresh_main()
                if after_sha != source_sha:
                    found = ["main advanced during observation; retrying a fresh snapshot"]
                else:
                    found, compared = problems(obs, git_oids, paths, served), True
        except (OSError, subprocess.SubprocessError, ValueError, TypeError) as exc:
            found = [f"source or provider observation failed: {type(exc).__name__}"]
        if not found or time.monotonic() + args.interval > deadline:
            break
        print("not settled yet: " + "; ".join(found), flush=True)
        time.sleep(args.interval)

    report = summarize(args.space, obs, git_oids, paths, found, source_sha, compared)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(report)
    return 0 if compared and not found else 1


if __name__ == "__main__":
    sys.exit(main())
