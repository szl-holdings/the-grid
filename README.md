---
title: THE GRID
emoji: 🟦
colorFrom: cyan
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: Isometric extraction protocol. Survive the Convergence.
---

# THE GRID

Isometric extraction protocol. Loot the lattice. Outrun the Convergence.

**L4 exhibit. GitHub is source authority. Not a kernel. Not a11oy. Not Λ. `winner=null`.**

Play source: [play.html](./play.html)

The canonical provider projection is `SZLHOLDINGS/the-grid`. Provider existence, publication, runtime health, and browser acceptance are separate evidence lanes; this repository does not treat organization membership or a token as proof that any of them passed. Do not host this exhibit on `a-11-oy.com` or `a11oy.net`, and do not hijack an unrelated Space.

## Play

JACK IN → VESPER NYX QUILL RIVEN SABLE HELIX WRAITH AEGIS → loot cyan → Q/E EXTRACTOR → F on gold ≥20 juice before heat 100.

WASD · Q/E · R scan · F extract · Space overclock · C Convergence

## Publication contract

`scripts/payload01_align_push.py` is founder-machine-only and fail-closed. It **does not create a Space**. Before any provider write it requires:

1. an exact clean Git checkout whose `HEAD` equals `THE_GRID_SOURCE_SHA`;
2. the existing canonical target `SZLHOLDINGS/the-grid` to be readable;
3. `HF_EXPECTED_PARENT_SHA` to equal that target's current Hub revision; and
4. an `HF_TOKEN` that can perform the already-authorized write.

The publisher uploads the source-owned file set as one Hub commit with an expected-parent guard, then verifies provider readback. Product/runtime and proof-site promotion remain separate.

```bash
python3 -m pip install --user huggingface_hub
export HF_TOKEN='set-locally-do-not-paste-into-chat'
export THE_GRID_SOURCE_SHA="$(git rev-parse HEAD)"
export HF_EXPECTED_PARENT_SHA='<current existing SZLHOLDINGS/the-grid revision>'
python3 scripts/payload01_align_push.py
```

If the canonical Space does not exist or cannot be read, stop. Target creation/access resolution is a separate provider-administration action and is not performed by this script.

Apache-2.0.
