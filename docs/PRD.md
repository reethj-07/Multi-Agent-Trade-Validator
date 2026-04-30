# Product Requirements Document (PRD)

**Product:** Multi-agent trade document validation pipeline (Nova DAW — Part 1)  
**Audience:** Whoever implements or grades the POC  
**Format:** Execution-oriented; export to PDF (about 3–5 pages) if they want a formal drop.

---

## 1 | Nova, FDE, and System of Outcomes

### 1.1 What is Nova? What problem is it solving that traditional SaaS can’t?

GoComet frames Nova as pushing past “another inbox for PDFs.” The point is to land somewhere defensible: a checked document set, a clear call on what happens next, and enough trace that you’re not arguing from memory when a shipment blows up. Ordinary SaaS is good at storing facts and nudging people through tasks; it’s weak at reading ugly scans, applying rules that differ per customer, and knowing when to stop automating. In practice people still copy fields by hand, senior cargo staff carry the rules in their heads, and every amendment adds another half day. Nova tries to close that loop with extract → validate → decide, so humans spend time on exceptions instead of retyping every line.

### 1.2 What is the FDE (Forward Deployed Engineer) model, and why does GoComet use it for Nova?

Forward deployed engineers sit with the customer: their lanes, their exceptions, their integrations. Trade validation isn’t one-size-fits-all—one account cares about HS chapter 8471, another about legal name matching on consignee, and “two or four email rounds per shipment” is treated as normal in a lot of shops. Outcomes get defined in the room (pilot metrics, which rule pack ships, who signs off). The product has to be tuned until those numbers move; that’s a bad fit for a purely distant roadmap cycle, which is why the FDE model shows up here.

### 1.3 What does “System of Outcomes” mean? How is it different from System of Record or System of Engagement?

Record systems answer “what do we know?” Engagement systems answer “how do we move work between people?” An outcomes framing asks whether we actually reached the state we wanted—docs that clear the customer’s bar, an audit trail for who said yes, time-to-clear trending the right way. This POC leans on signals you can inspect: per-field match/mismatch/uncertain, a router call with plain reasoning, runs stored so you can ask questions later. Filing the PDF still matters; the part we care about is whether the shipment is in a state you’d stand behind.

---

## 2 | Problem statement

### 2.1 Where does the current trade-doc validation flow break? (Failure modes)

| Failure mode | What happens |
|--------------|----------------|
| **Tribal rules** | Customer-specific requirements live in senior CG memory; new hires mis-validate for weeks. |
| **Manual re-keying** | Every field is typed from PDF into checks; slow, error-prone, not scalable. |
| **Amendment loops** | 2–4 email cycles per shipment are “normal”; each cycle adds **4–24h+** latency. |
| **No audit trail** | Disputes lack a structured record of **found vs expected** per field. |
| **Silent errors** | Wrong HS or consignee can pass informal review and cause **holds, fines, or customer penalties**. |
| **No visibility** | Leadership can’t answer “how many pending / flagged this week?” without a spreadsheet sprint. |

### 2.2 What does success look like for a CG operator in the first 5 minutes?

They drop in a PDF or photo and get back the fields that matter, each with a confidence score and a short quote from the page so they’re not trusting a black box. Validation reads in plain English: matched, mismatched, or uncertain, with found vs expected when it’s wrong. The router says what it would do next and why. If several fields are off, there’s a draft amendment they can trim and send instead of rewriting from scratch. If their manager pings them for numbers, they can ask a plain-English question over past runs and get an answer tied to actual query rows, not a guess.

---

## 3 | Users and jobs-to-be-done (JTBD)

### 3.1 Personas

| Persona | Role | Core concern |
|---------|------|----------------|
| **CG (Cargo / Control Group)** | Validator at customer or forwarder | Correctness vs customer rules; speed; defensible audit; safe escalation when unsure. |
| **SU (Shipping Unit / supplier)** | Shipper / doc issuer | Clear, **field-level** feedback when something is wrong; fewer back-and-forth emails. |

### 3.2 JTBD (≥5, testable)

1. Shipment PDF lands → get structured fields without retyping the whole page; validation should take minutes, not an afternoon.  
2. Model output is shaky → mark the field uncertain instead of green-washing it; nothing auto-approved on thin evidence.  
3. Rule violation → show found vs expected on screen so the CG person can explain it to the customer or the supplier without digging back into the PDF.  
4. Several fields wrong → one draft email that lists each gap so they edit once instead of sending five contradictory notes.  
5. Manager asks “how many stuck in review this week?” → ask in normal language over stored runs, get counts that map to real rows.  
6. Job dies halfway → in dev, LangGraph can reload from the last in-memory checkpoint if you re-invoke with the same `thread_id` in the **same process**; the HTTP API runs one full `invoke` per upload (durable replay would need a persisted checkpointer + resume endpoint).  

---

## 4 | Agent architecture (technical core)

### 4.1 Why three agents—not one prompt, not five?

One huge prompt blends “what’s on the page,” “what this customer allows,” and “what we do next.” When it goes wrong you can’t tell which layer failed, and you can’t swap the vision model or tighten the rules without touching everything. Spraying the problem into a dozen micro-agents without hard contracts is worse: you spend the sprint wiring state, not shipping behavior. Three steps line up with how cargo people actually talk about the work: read the doc, check it against the rule pack, decide the action. Each hop has a Pydantic payload; the next hop validates it so bad shapes fail loudly instead of drifting downstream.

### 4.2 Responsibilities, inputs, outputs (executor / verifier / policy framing)

| Agent | Role | Input | Output |
|-------|------|--------|--------|
| **Extractor** | **Executor** (perception) | PDF/image bytes, MIME type | `ExtractionResult`: 8 fields × `{value, confidence, source_snippet}` |
| **Validator** | **Verifier** (rules) | `ExtractionResult` + customer JSON rules (`acme_retail_eu`) | `ValidationReport`: per-field `match` / `mismatch` / `uncertain` + found/expected/reason |
| **Router** | **Policy + comms** | `ValidationReport` | `RouterDecision`: `auto_approve` \| `human_review` \| `draft_amendment_request` + reasoning + optional draft email |

### 4.3 How agents communicate

LangGraph carries a typed state dict. After each node we stash `model_dump(mode="json")` and the following node pulls it back through `model_validate(...)`. No free-form strings between stages. There’s also an `errors[]` list for things an operator should see (stack traces, guard failures) without losing the rest of the run.

### 4.4 Crash recovery

Checkpoints use LangGraph’s `MemorySaver` after each node. `thread_id` is the job id (UUID) so state is correlated end-to-end; resuming mid-graph is possible only while that checkpointer instance still exists (not across separate API requests today). For production you’d swap in a durable checkpointer and expose explicit resume.

---

## 5 | LLM and tooling choices

| Choice | Rationale |
|--------|-----------|
| **Gemini 2.5 Flash** — extraction (default) | **Vision + speed + cost**; structured JSON via `response_schema`. |
| **Gemini 2.5 Pro** — extraction retry, NL→SQL, answer summarization | **Higher quality** on degraded scans and harder reasoning; use **sparingly**. |
| **Fallback on bad docs** | **Low confidence** → validator → **uncertain** → **human_review**; extraction **retries once** with Pro on failure; amendment body **template** if polish blocked by budget. |
| **LangGraph** | **Typed state**, **checkpoints**, **linear** `extract→validate→route` with clear test seams. |
| **Structured output** | **Extraction** (`ExtractionResult`), **NL SQL helper** (`SqlAnswer`), **email polish** (`_AmendmentEmailBody`)—schema enforcement where contracts matter. |
| **Avoid tool use** | Validator is **deterministic** on rules (debuggable); router policy is **code-first**; LLM used for **drafting** only when safe. |

---

## 6 | Trust, failure handling, and evals

| Topic | Approach |
|-------|----------|
| **Hallucinated fields** | Prompt: extract only **visible** text; **null + low confidence** if absent; **snippet** required when claiming a value; validator **uncertain** below confidence threshold. |
| **Low-confidence extraction** | **Never** maps to **auto_approve**; router sends **`human_review`** if **any** field is **uncertain**. |
| **Loops / runaway cost** | **`TRADE_VALIDATOR_MAX_LLM_CALLS`** hard cap per run; router checks cumulative **`llm_calls`** before optional polish; **no** unbounded retries. |
| **Offline eval** | **Golden set** (N labeled PDFs): field-level **precision/recall** on extraction; **rule accuracy** on validator; **confusion matrix** on router vs CG labels. |
| **Online metric** | **% of uploads** reaching **`auto_approve`** without CG override; **sampled audit** of auto-approved rows for **precision**; **p95 latency** per stage. |

---

## 7 | Metrics and success criteria

### 7.1 North-star (one number, one sentence)

**Median minutes from document upload to CG decision** (approve, send amendment, or escalate) on pilot traffic—**lower is better**, measured weekly.

### 7.2 Supporting metrics (5–8)

1. **Uncertain field rate** (% of fields marked uncertain).  
2. **Auto-approve precision** (sampled audit: % of auto-approved runs CG agrees with).  
3. **Amendment cycles per shipment** (email thread count proxy).  
4. **LLM cost per document** ($) and **tokens per stage**.  
5. **p95 pipeline latency** (total + per node).  
6. **NL query grounding errors** (answers inconsistent with SQL result—target ~0).  
7. **Operator CSAT / “would use weekly”** (qualitative, 1–5).  

### 7.3 Go / No-Go for a 2-week pilot (one customer)

Green light if uncertain rate stays inside what you agreed with the customer, you see zero silent passes on the golden set, cost per doc is inside budget, the CG lead will actually use it weekly, and p95 latency doesn’t embarrass you at their volume. Pull the plug if auto-approve keeps failing spot checks, spend or latency has no ceiling, or people stop trusting the snippets and confidence scores.

---

## 8 | What’s next (after Part 1 ships)

If I had two more weeks I’d chase ingestion first—email or folder drop, more than one attachment—because until the thing fires on real traffic it stays a demo. Cross-doc checks (B/L vs invoice) are the obvious Part 2 thread. I’d also want a small golden set in CI so prompt tweaks don’t quietly wreck extraction, plus versioned rule packs and a thin queue UI for human review. Triggers and multi-doc matter before polish; eval matters before you trust the headline metrics.

---

## Appendix — Mapping to implemented POC

| PRD section | Code / artifact |
|-------------|------------------|
| Extractor | `src/trade_validator/agents/extractor.py`, schemas `ExtractionResult` |
| Validator | `src/trade_validator/agents/validator.py`, `rules/acme_retail_eu.json` |
| Router | `src/trade_validator/agents/router.py` |
| Orchestration | `src/trade_validator/graph/pipeline.py`, `MemorySaver` |
| Storage + NL | `src/trade_validator/db/`, `services/nl_query.py`, `services/storage.py` |
| UI + API | `frontend/` (static UI mounted by FastAPI), `streamlit_app/app.py` (optional), `src/trade_validator/api/` |
