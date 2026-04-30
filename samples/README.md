# Sample documents

## Bundled generated samples (Acme rules–aligned)

Regenerate anytime:

```bash
python scripts/generate_acme_sample_invoice.py
```

| File | Purpose |
|------|---------|
| `acme_commercial_invoice_filled.png` | **Clean** — filled commercial invoice (values match [`acme_retail_eu`](../src/trade_validator/rules/acme_retail_eu.json) for a happy-path test). |
| `acme_commercial_invoice_degraded.png` | **Degraded** — half resolution + heavier PNG compression (harder for vision). |

Upload either in Streamlit or:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/pipeline/run" -F "file=@samples/acme_commercial_invoice_filled.png"
```

---

Part 1 also expects **your own** real-world tests:

1. **Clean** — readable scan or native PDF (invoice or packing list with the usual fields).
2. **Degraded** — low resolution, skew, fax, or heavy compression.

Place extra files in this folder (any names) and run the pipeline from the UI or API. Example API:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/pipeline/run" -F "file=@samples/your_invoice.pdf"
```

Customer rule set bundled in the repo: **`acme_retail_eu`** (see `src/trade_validator/rules/acme_retail_eu.json`). Adjust extracted values in tests or use documents that intentionally violate rules to exercise **mismatch** and **draft amendment** paths.
