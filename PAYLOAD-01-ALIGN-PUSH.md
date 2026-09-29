# PAYLOAD-01 — Publish THE GRID from exact GitHub source to the canonical Hugging Face Space

**Id:** `SZL-GRID-CONVERGENCE-2026-09-04`
**GitHub source authority:** `szl-holdings/the-grid`
**Canonical provider projection:** `SZLHOLDINGS/the-grid`
**State:** RETIRED 2026-09-29. Superseded by the committed workflow below.

The founder-machine publisher `scripts/payload01_align_push.py` published `SZLHOLDINGS/the-grid` once (Hub commit `745dded6`, "Publish THE GRID from GitHub 06c7f8e5…", 2026-09-26). It is removed so the Space has exactly one writer. Its last version is in git history at `4978d68`.

The only writer is now [`.github/workflows/hf-space.yml`](.github/workflows/hf-space.yml), which calls the org's reusable deployer (`szl-holdings/.github/.github/workflows/reusable-hf-deploy.yml`, pinned by commit SHA). The guarantees the local script gave are kept or tightened:

| Local script (retired) | Committed workflow |
|---|---|
| `HEAD` must equal `THE_GRID_SOURCE_SHA` and the tree must be clean | CI checks out `github.sha`; the deployer refuses unless it is the current tip of `main` at the moment of the Hub commit |
| Hand-listed file set | File set derived from the `Dockerfile` `COPY` sources (plus `Dockerfile`, its ignore file and `README.md`) |
| Expected-parent guard | One lock per asset (`hf-write/space/SZLHOLDINGS/the-grid`) and the default-branch-tip guard |
| Readback: Hub `sha` equals the returned commit | Readback: the Space API reports that exact commit `RUNNING`, every published file matches by sha256 at that commit, and `/` and `/healthz` return HTTP 200 |
| Fails when `HF_TOKEN` is unset | Fails when the `HF_TOKEN` repository secret is absent |

Neither path creates a Space. A green deploy still does **not** establish browser acceptance, product promotion, or proof-site qualification.

Demo exhibit. Not a kernel. Not a11oy. Not Λ.
