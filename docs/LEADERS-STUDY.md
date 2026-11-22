# Domain Leader Study — the-grid (isometric extraction protocol)

OUROBOROS phase-3, cohort-02 tranche-1, Kimi ruling W26-C2T1-KIMI-20261123-ASK (GO, custody gate satisfied pre-write: fresh probe 2026-11-23 measured no open sibling study branches or PRs on this repo, no existing docs/LEADERS-STUDY.md; sibling custody object was the HF Space surface, not this GitHub repo — receipts vibe_w26_collision_probe.txt). PROPOSE-ONLY study card: documentation only, no implementation in this PR.

## Current state (repo inspection 2026-11-23)
Python repo; description: THE GRID isometric extraction protocol, convergence ring collapse; canonical source for the HF Space (spaces census measured it live). Topics: dashboard, demo, huggingface, isometric, python, spaces.

## Domain leaders studied
| Leader | What they have | Key sources |
| --- | --- | --- |
| deck.gl aggregation layers (visgl) | GPU-side binning/aggregation as a first-class primitive; HexagonLayer demonstrates grid aggregation with resolution control and coverage trimming upstream of rendering | deck.gl/docs/api-reference/aggregation-layers/hexagon-layer + gallery hexagon-layer (accessed 2026-11-23) |
| Uber H3 hexagonal indexing | The reference hierarchical hexagonal/isometric grid indexing system with python bindings: resolution-parameterized cells, reproducible aggregation — the canonical way to make grid claims replayable | H3HexagonLayer lineage (deck.gl geo-layers h3-hexagon-layer, references H3 papers) (accessed 2026-11-23) |

## What the leaders do better
- Aggregation is defined by resolution parameters, not ad hoc geometry: two runs at the same resolution provably cover the same cells — the leader version of receipt-verifiable extraction.
- Aggregation happens on the GPU with declared upper bounds (coverage, radius), so scaling is parameterized, not discovered at runtime.
- The hexagon is the leaders' chosen isometric primitive for a reason: indexable, hierarchical, visualizable — same shape class as the grid's convergence rings.

## Gaps
- Extraction protocol currently defines its own isometric semantics; card found no documented resolution-parameterized cell indexing that an external verifier could reproduce.

## Ranked #1 absorb proposal (NOT implemented in this PR)
Define convergence-ring cells as resolution-parameterized hierarchical hexagonal cells (H3-style, pure-python indexing sublayer), so each extraction receipt cites the cell set + resolution, externally replayable. Expected benefit: ring-collapse claims become reproducible by third parties; visualization stays compatible with hexagon aggregation primitives. Cost/risk: low-medium; additive indexing layer, protocol semantics unchanged. Validation: identical cell sets across two independent extractions at fixed resolution. Rollback: indexing layer optional; legacy semantics untouched.

## Sources
- deck.gl HexagonLayer: https://deck.gl/next/docs/api-reference/aggregation-layers/hexagon-layer (accessed 2026-11-23)
- deck.gl H3HexagonLayer: https://deck.gl/next/docs/api-reference/geo-layers/h3-hexagon-layer (accessed 2026-11-23)
- deck.gl hexagon gallery: https://deck.gl/gallery/hexagon-layer (accessed 2026-11-23)
