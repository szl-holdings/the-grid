# PAYLOAD-01 — Align GitHub org + push THE GRID to HF vertical

**Id:** `SZL-GRID-CONVERGENCE-2026-09-04`  
**Owner:** SZL Holdings (`szl-holdings` / `SZLHOLDINGS`)  
**Operator GitHub:** `stephenlutar2-hash`  
**GitHub repo:** https://github.com/szl-holdings/the-grid  
**HF Space (vertical exhibit):** https://huggingface.co/spaces/SZLHOLDINGS/the-grid  
**Related catalog:** https://huggingface.co/spaces/SZLHOLDINGS/SZL-Vertical-Services  
**Constellation mirror:** https://github.com/stephenlutar2-hash/szl-constellation

This payload does three things and then stops:

1. Confirm / create `szl-holdings/the-grid` on GitHub.
2. Commit this working tree (no `node_modules`, no secrets) and push `main`.
3. Create / update Hugging Face Space `SZLHOLDINGS/the-grid` (Docker, port 7860) and upload the same tree.

Tokens stay in the environment. The script never writes them to disk.

## Tokens (terminal only)

```bash
export GITHUB_TOKEN=ghp_REPLACE_ME
export HF_TOKEN=hf_REPLACE_ME
```

```bash
python3 scripts/payload01_align_push.py
```
