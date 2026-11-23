# the-grid domain leader study r1 (propose-only)

Date: 2026-11-23. Method: web-verified leader landscape + governing-seat synthesis (Kimi nonce T3-THE-GRID-BRIEF). This card is documentation only; it changes no code, CI, config, or existing PR status. All absorb actions are FUTURE PROPOSALS (non-authorizing); implementation and merges remain separately reviewed and gated.

## Domain: browser-based isometric game exhibit served by a Docker Space (static HTTP)

## Leaders studied (web-verified 2026-11-23)

1. Phaser — mature 2D browser game framework: scene lifecycle, input routing, tweens, asset pipeline; moat is a proven browser-game structure rather than a bespoke loop.
2. three.js — de-facto JavaScript 3D library; battle-tested camera and scene-graph idioms used by countless isometric web experiences; moat is rendering and camera discipline, not game rules.
3. Godot Engine — complete open game engine with deterministic frame loop guidance, export targets, and a large shipped-game corpus; moat is engine-level loop discipline and export practice, not a drop-in static-page replacement.

## Absorb actions (FUTURE PROPOSALS, non-authorizing)

1. (Phaser) Propose a documentation-only scene/input/asset lifecycle map for play.html, identifying where scene transitions, input routing, tween ownership, and asset loading would be separated if a future change is approved. No framework adoption, gameplay change, performance claim, or browser acceptance is claimed; any implementation would require separate review and live browser testing.
2. (three.js) Propose a future camera and scene-graph convention note for the isometric view, covering camera ownership, coordinate transforms, render ordering, and resize behavior without prescribing a 3D rewrite. This is an idiom study only; it does not establish visual correctness, compatibility, or speedup, and browser acceptance remains unmeasured until a live run.
3. (Godot Engine) Propose a future fixed-step/frame-loop and state-transition checklist inspired by deterministic loop guidance, with explicit separation of simulation state, rendering, and winner-state transitions. Godot export is not proposed as a drop-in replacement for the static HTTP exhibit; determinism and gameplay correctness would remain unproven without separately reviewed tests and live runs.
4. (baseline) Propose preserving the existing publish contract as the baseline: tip-of-main refusal, exact Dockerfile COPY source publication, RUNNING verification at the exact Hub commit, per-file sha256 re-fetch comparison, and HTTP 200 checks for / and /healthz. Keep winner=null and /healthz explicitly liveness-only; add no acceptance, winner, performance, energy, or trust claim, and retain an independent external monitor for scheduled-workflow disablement and last-success verification because the daily drift watch is read-only and GitHub may disable schedules after 60 days of repository inactivity.

## Do not do (per governing seat)

Do not merge, bypass the signature wall, or claim implementation beyond this card.
