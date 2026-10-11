# The Grid interface source and verification

`play.html` is the playable source of record. The Dockerfile copies it to the served `index.html`; the repository's separate `index.html` is not the game. The existing main-only `hf-space.yml` remains the sole publisher, with its exact-source, credential, Docker-derived file set, RUNNING and immutable-readback gates unchanged.

The interface uses a scoped native KANCHAY palette projection and the exact small Orbit suite artwork from accepted `szl-brand@27d12e77fc0f9f1a0e5fae8b34adf2380d51d070`. The SVG SHA-256 is `6e2b7d72a3af3d9602b79de41df0194ede6496a9661f057108ec224c0efc92e6`. Artwork is CC BY 4.0 with visible source and license links; code remains Apache-2.0. It does not load a full KANCHAY bundle or a runtime font/CDN.

The entry/results panels and controls use opaque surfaces, native focus, forced colors and a responsive two/four-column operator menu. The isometric projection fits the space between the HUD and controls. The current operator has a visible outline. On-screen held controls and keyboard controls operate the existing local key state. Native buttons retain Space activation; only a focused active lattice captures game keys. Pause freezes the local tick, clears held input and resumes without accumulated clock time. Losing the window or hiding the tab pauses the run. Storage denial leaves the game playable for the current visit.

Operator constants, seeding, convergence, heat, movement, scoring and extraction logic are preserved. The tick's only new condition is the local pause guard. The game is a visual canvas without a complete nonvisual equivalent. This remains an L4 exhibit: no kernel, receipt, model or product/proof-site admission; `winner=null`, `BLOCKED_NO_METAL` and the reconstruction limits remain visible.

## Verification

With the publisher repository checked out at the revision pinned by `hf-space.yml`:

```sh
TOOLS=/path/to/exact-publisher python -m unittest discover -s tests -v
CHROME_PATH=/path/to/chromium python tools/verify_grid_browser.py --output /new/evidence-directory
```

The 20 existing contracts pass. The standalone verifier serves only the exact local `play.html` and blocks all external requests and non-GET requests. Five widths (320, 390, 768, 1280, 1920) cover actual Space deployment by native key, movement, tool/scan controls, touch hold/release, projection bounds, 44px targets, pause timing, Escape, result/restart focus, forced colors, exact icon bytes and denied storage. Its end-screen fixture is a local presentation transition, not evidence of a successful extraction or published runtime. Final source browser qualification had zero page errors, attempted writes or external requests.
