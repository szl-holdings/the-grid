# PAYLOAD-01 — Publish THE GRID from exact GitHub source to the canonical Hugging Face Space

**Id:** `SZL-GRID-CONVERGENCE-2026-09-04`
**GitHub source authority:** `szl-holdings/the-grid`
**Canonical provider projection:** `SZLHOLDINGS/the-grid`

This publisher is founder-machine-only and fail-closed. It does **not** create a Hugging Face Space, does not mint credentials, and does not publish a second founder mirror. Target creation/access resolution is a separate provider-administration action.

Before running, independently read the existing canonical Space and record its exact current Hub revision. Run only from the exact clean Git commit intended for publication.

```bash
python3 -m pip install --user huggingface_hub
export HF_TOKEN='set-locally-do-not-paste-into-chat'
export THE_GRID_SOURCE_SHA="$(git rev-parse HEAD)"
export HF_EXPECTED_PARENT_SHA='<current existing SZLHOLDINGS/the-grid revision>'
python3 scripts/payload01_align_push.py
```

The script refuses to write unless:

- `HEAD` exactly equals `THE_GRID_SOURCE_SHA`;
- the Git working tree is clean, including no untracked files;
- every publication input is a tracked regular file, not a symlink;
- the existing `SZLHOLDINGS/the-grid` Space is readable; and
- its current Hub SHA exactly equals `HF_EXPECTED_PARENT_SHA`.

The publication itself is one Hub commit guarded by the expected parent, followed by exact Hub revision readback. A successful provider write still does **not** establish Space runtime health, browser acceptance, product promotion, or proof-site qualification.

If the canonical target is absent or unreadable, stop. Do not substitute `betterwithage/the-grid`, create a new target, or reinterpret organization membership as publication authority.

Demo exhibit. Not a kernel. Not a11oy. Not Λ.
