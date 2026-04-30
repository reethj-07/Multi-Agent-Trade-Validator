# Multi-agent trade document validation

A reference implementation of a **three-stage** pipeline for trade paperwork: **multimodal extraction** (PDF or image) with per-field confidence, **rule-based validation** against a customer profile, and a **routing** step that proposes the next action (including optional draft supplier communication). Orchestration uses **LangGraph**; the default LLM stack is **Google Gemini 2.5** (Flash / Pro). A small **FastAPI** service exposes the pipeline and a **grounded natural-language → SQL** interface over stored runs; **Streamlit** provides an operator-oriented UI.

## Features

- **Extractor** — Structured output for eight core trade fields (consignee, HS code, ports, Incoterms, goods description, gross weight, invoice number) with **confidence** and **source snippets**.
- **Validator** — Per-field `match` / `mismatch` / `uncertain` against a JSON rule pack ([`acme_retail_eu`](src/trade_validator/rules/acme_retail_eu.json)); uncertain fields are never auto-approved.
- **Router** — `auto_approve`, `human_review`, or `draft_amendment_request` with reasoning and a structured discrepancy list.
- **Persistence** — SQLite (`SQLModel`) for run history; configurable URL for portability to Postgres-style deployments.
- **NL analytics** — Plain-English questions translated to **read-only** `SELECT` statements, with answers grounded in query results.

## Requirements

- Python **3.11+**
- [Gemini API key](https://aistudio.google.com/apikey) (`GEMINI_API_KEY` or `GOOGLE_API_KEY`)

## Quick start

```bash
git clone https://github.com/reethj-07/Multi-Agent-Trade-Validator.git
cd Multi-Agent-Trade-Validator
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows
pip install -e ".[dev]"
cp .env.example .env                 # set GEMINI_API_KEY
```

**API** (terminal 1):

```bash
python -m uvicorn trade_validator.api.main:app --host 127.0.0.1 --port 8000
```

**UI** (terminal 2):

```bash
export TRADE_VALIDATOR_API_URL=http://127.0.0.1:8000   # Linux / macOS
# set TRADE_VALIDATOR_API_URL=http://127.0.0.1:8000    # Windows CMD
python -m streamlit run streamlit_app/app.py
```

Upload a PDF or image under **Document**, then **Run pipeline**. The sidebar shows API reachability and supports NL questions after at least one run has been stored.

**Tests:**

```bash
pytest
```

**Health:** `GET /health`

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/pipeline/run` | Multipart `file`; query params `customer_id`, `use_pro_extraction` |
| `POST` | `/api/v1/query` | JSON body `{"question": "..."}` |
| `GET` | `/health` | Liveness |

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | — | Gemini Developer API |
| `TRADE_VALIDATOR_DATABASE_URL` | `sqlite:///./trade_validator.db` | Database URL |
| `TRADE_VALIDATOR_API_URL` | — | Streamlit → API base URL |
| `TRADE_VALIDATOR_MAX_LLM_CALLS` | `8` | Max LLM round-trips per pipeline run |
| `TRADE_VALIDATOR_EXTRACTION_UNCERTAIN_THRESHOLD` | `0.35` | Extraction confidence below → validator `uncertain` |

## Repository layout

| Path | Role |
|------|------|
| `src/trade_validator/schemas/` | Pydantic contracts between stages |
| `src/trade_validator/agents/` | Extractor, validator, router |
| `src/trade_validator/graph/` | LangGraph `StateGraph`, checkpoints |
| `src/trade_validator/db/` | SQLModel models and session |
| `src/trade_validator/services/` | Rules, storage, NL query |
| `src/trade_validator/api/` | FastAPI application |
| `streamlit_app/` | Web UI (HTTP client only) |
| `samples/` | Example inputs and generator script |
| `tests/` | Pytest suite |
| `docs/` | Product and technical documentation |

## Documentation

| Document | Contents |
|----------|----------|
| [docs/PRD.md](docs/PRD.md) | Product context, personas, architecture rationale, metrics |
| [docs/TECH_WRITEUP.md](docs/TECH_WRITEUP.md) | System diagram, failure handling, cost/latency, operations |
| [docs/SAMPLE_QUERIES.md](docs/SAMPLE_QUERIES.md) | Example NL questions over `document_run` |

## Development notes

- Use the **same** Python environment for `pip install -e .` and `python -m uvicorn` (avoid mixing system `uvicorn` with a different interpreter).
- After code changes, **restart** the API process so imports reload.
- Sample PNGs can be regenerated: `python scripts/generate_acme_sample_invoice.py`.

## License

See [LICENSE](LICENSE).
