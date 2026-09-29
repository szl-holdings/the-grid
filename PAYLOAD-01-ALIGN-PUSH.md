# PAYLOAD-01 — Publish THE GRID from exact GitHub source to the canonical Hugging Face Space

**Id:** `SZL-GRID-CONVERGENCE-2026-09-04`
**GitHub source authority:** `szl-holdings/the-grid`
**Canonical provider projection:** `SZLHOLDINGS/the-grid`
**State:** RETIRED 2026-09-29. Superseded by the committed workflow below.

The founder-machine publisher `scripts/payload01_align_push.py` published `SZLHOLDINGS/the-grid` once (Hub commit `745dded6`, "Publish THE GRID from GitHub 06c7f8e5…", 2026-09-26). It is removed so the Space has exactly one writer. Its last version is in git history at `4978d68`.

The only writer is now [`.github/workflows/hf-space.yml`](.github/workflows/hf-space.yml), which calls the org's reusable deployer (`szl-holdings/.github/.github/workflows/reusable-hf-deploy.yml`, pinned by commit SHA). Four of the local script's guarantees are kept or tightened. **One is dropped: the expected-parent guard.**

| Local script (retired) | Committed workflow |
|---|---|
| `HEAD` must equal `THE_GRID_SOURCE_SHA` and the tree must be clean | Kept. CI checks out `github.sha`. Immediately before the Hub commit, the deployer refuses unless that commit is the current tip of `main`. |
| Hand-listed file set | Tightened. The file set is derived from the `Dockerfile` `COPY` sources, plus `Dockerfile`, its ignore file and `README.md`. |
| Expected-parent guard: refuse unless the Hub head equals the operator-supplied `HF_EXPECTED_PARENT_SHA`, then pass it as `create_commit(parent_commit=…)` so the Hub rejects a head that moved | **DROPPED.** The pinned deployer (`.github/scripts/hf_deploy_from_dockerfile.py`) calls `create_commit` with no `parent_commit` and does not read the Hub head before writing. A Hub commit that anyone else made since the last deploy is not detected. The deploy commits on top of it: files in the deploy set are overwritten, and other files are left in place. The per-asset lock (`hf-write/space/SZLHOLDINGS/the-grid`) serializes only runs inside this repository. The tip guard binds the GitHub source, not the Hub parent. Neither one replaces this guard. |
| Readback: Hub `sha` equals the returned commit | Tightened. The Space API must report that exact commit `RUNNING`. Every published file must match by sha256 at that commit. `/` and `/healthz` must return HTTP 200. As a side effect, a foreign Hub commit that lands *after* this run's commit, but before the Space reports it `RUNNING`, fails the run. One that lands *before* the write is still not detected. |
| Fails when `HF_TOKEN` is unset | Kept. The deploy fails when the `HF_TOKEN` repository secret is absent. |

Restoring the expected-parent guard needs a change in `szl-holdings/.github` (`hf_deploy_from_dockerfile.py`), not in this repository. That change must read the Hub head before the write, refuse unless it is the expected parent, and pass `parent_commit`. `tests/test_retirement_note.py` fails when the pinned deployer's behavior and this row disagree, so it forces this note to change when the pin moves to a deployer that restores the guard.

Neither path creates a Space. A green deploy still does **not** establish browser acceptance, product promotion, or proof-site qualification.

Demo exhibit. Not a kernel. Not a11oy. Not Λ.
