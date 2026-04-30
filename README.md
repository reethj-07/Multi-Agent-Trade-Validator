# Multi-agent trade document validation

Nova DAW Part 1 — **LangGraph** orchestration, **Gemini 2.5** (Flash/Pro) for vision and NL-SQL, **FastAPI** + **Streamlit**, **SQLite** via **SQLModel**.

## What it does

1. **Extractor** — PDF or image → structured fields (8 mandatory trade fields + confidence + source snippet) via Gemini vision + JSON schema.
2. **Validator** — Compares extraction to a bundled customer rule set (**`acme_retail_eu`**, [`src/trade_validator/rules/acme_retail_eu.json`](src/trade_validator/rules/acme_retail_eu.json)): per-field `match` / `mismatch` / `uncertain` (uncertain never auto-approved).
3. **Router** — `auto_approve` (all match), `human_review` (any uncertain), or `draft_amendment_request` (mismatches only) with a draft email listing discrepancies (template + optional Gemini polish within an LLM call budget).
4. **Storage** — Each run is stored in **`trade_validator.db`** (same directory you start the API from unless `TRADE_VALIDATOR_DATABASE_URL` is set).
5. **NL query** — POST a plain-English question; Gemini generates a **read-only `SELECT`**, results are executed, then a **grounded** natural-language answer is returned (no invented counts).

## Quick start (under ~5 minutes)

**Prerequisites:** Python 3.11+, a **Gemini API key** ([Google AI Studio](https://aistudio.google.com/apikey)).

```bash
cd multi-agent-trade-validator
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

copy .env.example .env            # then set GEMINI_API_KEY=
```

**Terminal 1 — API**

```bash
uvicorn trade_validator.api.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — UI**

```bash
set TRADE_VALIDATOR_API_URL=http://127.0.0.1:8000
streamlit run streamlit_app/app.py
```

Open the Streamlit URL, upload a **PDF or image** (invoice / packing list–style), click **Run pipeline**. Use the sidebar NL box after at least one run exists (e.g. *“How many runs have final_action human_review?”*).

**CLI smoke test (stub extractor, no API key needed for graph only):**

```bash
pytest
```

**Health check:** `GET http://127.0.0.1:8000/health`

## API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/pipeline/run` | multipart `file` + query `customer_id`, `use_pro_extraction` |
| POST | `/api/v1/query` | JSON `{"question": "..."}` |
| GET | `/health` | liveness |

## Configuration (environment)

| Variable | Default | Purpose |
|----------|---------|---------|
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | — | Gemini Developer API |
| `TRADE_VALIDATOR_DATABASE_URL` | `sqlite:///./trade_validator.db` | SQLAlchemy URL |
| `TRADE_VALIDATOR_API_URL` | — | Streamlit → API base |
| `TRADE_VALIDATOR_MAX_LLM_CALLS` | `8` | Hard cap per pipeline run |
| `TRADE_VALIDATOR_EXTRACTION_UNCERTAIN_THRESHOLD` | `0.35` | Below this, validator forces `uncertain` |

## Project layout

- [`src/trade_validator/schemas/`](src/trade_validator/schemas/) — Pydantic contracts between agents.
- [`src/trade_validator/agents/`](src/trade_validator/agents/) — Extractor, validator, router.
- [`src/trade_validator/graph/`](src/trade_validator/graph/) — LangGraph `StateGraph` + `MemorySaver`.
- [`src/trade_validator/db/`](src/trade_validator/db/) — SQLModel + SQLite session.
- [`src/trade_validator/services/`](src/trade_validator/services/) — Rules loader, NL query, persistence.
- [`src/trade_validator/api/`](src/trade_validator/api/) — FastAPI app.
- [`streamlit_app/`](streamlit_app/) — UI (HTTP only).
- [`samples/`](samples/) — Add your clean + degraded test PDFs (see `samples/README.md`).

## Verification checklist

| Check | How |
|-------|-----|
| Unit tests | `pytest` — should report all passed. |
| API up | `curl http://127.0.0.1:8000/health` or Streamlit sidebar **Backend: ok**. |
| Full chain | Upload `samples/acme_commercial_invoice_filled.png` or `_degraded.png` → **Run pipeline** → expect field rows + router action. |
| Happy path | Degraded/filled Acme sample → expect **`auto_approve`** when all fields match. |
| Amendment path | Use a doc with wrong HS code or consignee → expect **`draft_amendment_request`** + email body. |
| Human review | Very blurry doc or empty fields → expect **`human_review`** + uncertain fields. |
| NL query | After ≥1 run, sidebar question → grounded answer (check expander for SQL). |
| DB file | `trade_validator.db` appears in the directory where you started **uvicorn** (usually project root). |

**After `git pull` or code edits:** restart `uvicorn` so Python reloads the package (Streamlit can stay running).

## Part 1 submission checklist (GoComet DAW)

Use this table when packaging your submission.

| Requirement | Status | Where / action |
|-------------|--------|----------------|
| **Deliverable 1 — PRD (3–5 pages)** | **In repo (export to PDF)** | [`docs/PRD.md`](docs/PRD.md) — all 8 sections per brief; §1 subsections ≤~200 words each |
| **Deliverable 2A — Extractor** | **Done** | PDF/image → Gemini vision → `ExtractionResult` (8 fields + confidence + snippet) |
| **Deliverable 2B — Validator** | **Done** | `acme_retail_eu` JSON rules; match/mismatch/uncertain; found/expected; uncertain never auto-approved |
| **Deliverable 2C — Router** | **Done** | auto_approve / human_review / draft_amendment_request + reasoning + email |
| **Deliverable 2D — Storage + NL query** | **Done** | SQLite `document_run`; [`docs/SAMPLE_QUERIES.md`](docs/SAMPLE_QUERIES.md) |
| **Deliverable 2E — Minimal UI** | **Done** | [`streamlit_app/app.py`](streamlit_app/app.py) |
| **Deliverable 3 — Technical write-up (1–2)** | **In repo (export to PDF)** | [`docs/TECH_WRITEUP.md`](docs/TECH_WRITEUP.md) |
| **Runnable repo + README** | **Done** | This file + `pyproject.toml` |
| **PRD as PDF or Google Doc** | **You** | Print/export [`docs/PRD.md`](docs/PRD.md) or paste into Docs |
| **Tech write-up as PDF or Google Doc** | **You** | Print/export [`docs/TECH_WRITEUP.md`](docs/TECH_WRITEUP.md) |
| **≥2 sample documents (clean + messy)** | **Done + optional add** | [`samples/acme_commercial_invoice_filled.png`](samples/acme_commercial_invoice_filled.png), [`samples/acme_commercial_invoice_degraded.png`](samples/acme_commercial_invoice_degraded.png); add real PDFs if you want |
| **2–3 min demo video** | **You** | Record pipeline + 1–2 NL queries (see [`docs/SAMPLE_QUERIES.md`](docs/SAMPLE_QUERIES.md)) |
| **Sample queries documented** | **Done** | [`docs/SAMPLE_QUERIES.md`](docs/SAMPLE_QUERIES.md) |

## License

Internal / assignment use unless you add a license.
