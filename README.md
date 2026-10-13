---
title: THE GRID
emoji: 🟦
colorFrom: blue
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: Isometric extraction protocol. Survive the Convergence.
---

<!-- Native identity: szl-brand@4309f6fce89179331b0b3ed8c99494e76c5be256; Orbit v2 icon sha256 6e2b7d72a3af3d9602b79de41df0194ede6496a9661f057108ec224c0efc92e6. -->
<p><a href="https://github.com/szl-holdings"><img src="https://raw.githubusercontent.com/szl-holdings/szl-brand/4309f6fce89179331b0b3ed8c99494e76c5be256/kit/logos/orbit-v2/suite/szl-icon-32.svg" alt="SZL Holdings — Orbit v2" width="32" height="32" /></a></p>

<p><small>Orbit v2 artwork © SZL Holdings · <a href="https://github.com/szl-holdings/szl-brand/blob/4309f6fce89179331b0b3ed8c99494e76c5be256/kit/LICENSE">CC BY 4.0</a>. The SZL name and mark remain trademarks; source-code and data licenses remain as declared.</small></p>

# The Grid · Interactive Exhibit

Play an isometric extraction game: explore the grid, collect resources and escape before convergence.

**Artifact:** Browser game served by a Docker Space · **Stage:** L4 exhibit · software

[Explore in Command Lab](https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab) · [Build](https://github.com/szl-holdings/the-grid) · [Evidence](https://github.com/szl-holdings/the-grid/blob/0cd569099660f5c5ef347e8d506fff793cbfefa1/README.md)

## Before you use it

- Game mechanics and in-world language belong to this exhibit; they do not establish a kernel result or a qualified A11oy product.
- The static health endpoint confirms server liveness only. Browser acceptance and publication evidence remain separate.
- The exhibit retains winner=null, its own source namespace and its existing publication checks. No model capability or Λ result is claimed.

<details>
<summary>Technical details and original evidence</summary>

The retained source below is exact and may contain historical observations. Its dates, use restrictions, licenses and evidence boundaries continue to apply.

<!-- SZL-PRESERVED-TECHNICAL-BODY:START -->

# THE GRID

Isometric extraction protocol. Loot the lattice. Outrun the Convergence.

**L4 exhibit. GitHub is source authority. Not a kernel. Not a11oy. Not Λ. `winner=null`.**

Source: [github.com/szl-holdings/the-grid](https://github.com/szl-holdings/the-grid)

Play source: [play.html](./play.html)

The canonical provider projection is `SZLHOLDINGS/the-grid`. Provider existence, publication, runtime health, and browser acceptance are separate evidence lanes; this repository does not treat organization membership or a token as proof that any of them passed. Do not host this exhibit on `a-11-oy.com` or `a11oy.net`, and do not hijack an unrelated Space.

## Play

JACK IN → VESPER NYX QUILL RIVEN SABLE HELIX WRAITH AEGIS → loot cyan → Q/E EXTRACTOR → F on gold ≥20 juice before heat 100.

WASD · Q/E · R scan · F extract · Space overclock · C Convergence

## Publication

The Space `SZLHOLDINGS/the-grid` has one writer: [`.github/workflows/hf-space.yml`](https://github.com/szl-holdings/the-grid/blob/main/.github/workflows/hf-space.yml). On a push to `main` that changes a published input, or a manual dispatch from `main`, it calls the org's reusable deployer, which:

1. refuses to publish unless the checked-out commit is the current tip of `main`;
2. publishes exactly the `Dockerfile` `COPY` sources, the `Dockerfile`, its build-context ignore file and this card as one Hub commit whose title names the source commit;
3. waits until the Space API reports that exact Hub commit `RUNNING`, then re-fetches every published file at that commit and compares sha256; and
4. requires `/` and `/healthz` to return HTTP 200 with a body.

It fails closed when the `HF_TOKEN` repository secret is absent, and it never creates a Space. `/healthz` is a static file served by the same `http.server` process: it shows the server answers, not browser acceptance, product promotion or proof-site qualification.

The founder-machine publisher `scripts/payload01_align_push.py` is retired in favor of that workflow; its last version is in git history at `4978d68`.

Apache-2.0.

<!-- SZL-PRESERVED-TECHNICAL-BODY:END -->

</details>

### Read-only drift monitor

The daily `HF Space drift watch` workflow checks current token authorization
metadata and the public Space without publishing. Each observation refreshes
main and compares immutable source blob IDs; an advance during observation is
retried. A changed Dockerfile or monitor configuration requires a fresh run so
old route/path declarations cannot certify new deployment configuration.

GitHub can disable scheduled workflows after 60 days of repository inactivity.
The existing external SZL runtime monitor must independently inspect this
repository's `.github/workflows/hf-space-drift.yml` state and latest successful
run. It must report disabled state, failures, and a success older than 48 hours
as an operational alert. Recovery is to re-enable this exact workflow and
manually dispatch it on trusted `main`, then verify both credential and public
drift jobs. The daily cron alone does not provide this external coverage;
continuous idle monitoring remains unverified until that integration is active.
