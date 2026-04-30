# Product Requirements Document (PRD)

**Product:** Multi-agent trade document validation pipeline (Nova DAW — Part 1)  
**Audience:** Engineers implementing the POC; reviewers evaluating Nova understanding  
**Format:** Execution-oriented (not a vision deck). **Export this file to PDF (3–5 pages)** for submission.

---

## 1 | Nova, FDE, and System of Outcomes

### 1.1 What is Nova? What problem is it solving that traditional SaaS can’t?

**Nova** (in GoComet’s framing) is a bet that global trade operations need **automation that reaches an outcome**—a **verified** document set and a clear next action—not just another place to store files or chat. Traditional **SaaS** excels at **systems of record** (databases) and **engagement** (inbox, tasks), but it rarely combines **multimodal reading** of messy PDFs, **customer-specific rule logic**, and **safe escalation** in one loop. Humans still re-key fields, rules live in heads, and amendment cycles multiply. Nova targets that gap: **extract → validate → decide** with explicit trust boundaries, so operators handle **exceptions**, not every cell. *(~165 words)*

### 1.2 What is the FDE (Forward Deployed Engineer) model, and why does GoComet use it for Nova?

**Forward Deployed Engineers** work **inside** the customer’s reality—workflows, edge cases, and integrations—rather than shipping generic features from afar. Trade validation is **high-variance**: customer A requires chapter 8471 HS rules; customer B cares about consignee legal name parity; CG teams tolerate 2–4 email loops as “normal.” An FDE model fits Nova because **outcomes are defined locally** (pilot metrics, rule packs, approval policy), and the product must be **tuned** until those outcomes improve. GoComet uses FDEs to shorten the loop from **messy truth** to **working automation**, which generic product cycles rarely match. *(~115 words)*

### 1.3 What does “System of Outcomes” mean? How is it different from System of Record or System of Engagement?

A **System of Record** answers “What do we know?” (stored facts). A **System of Engagement** answers “How do we coordinate people?” (tasks, messages, workflows). A **System of Outcomes** answers “Did we **get to the right end state**?”—e.g., documents that **pass** customer rules, **auditability** of who approved what, and **time-to-clear** improving. Nova’s POC optimizes for **outcome signals**: per-field **match/mismatch/uncertain**, **router decisions** with reasoning, **persisted runs** for queries—not just filing another PDF. Engagement and record matter, but the **north star** is **verified trade readiness**, not inbox zero. *(~120 words)*

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

Within **five minutes** of opening the tool, the CG operator can: **upload** a trade PDF or image; see **every required field** with **confidence** and **source snippet**; see **validation** as match / mismatch / uncertain with **found vs expected**; see a **router decision** with **plain-language reasoning**; and, when rules fail cleanly, receive a **draft amendment** listing discrepancies by field. They can run a **natural-language question** over **stored runs** (e.g., counts by `final_action`) and get an answer **grounded** in query results—not invented numbers.

---

## 3 | Users and jobs-to-be-done (JTBD)

### 3.1 Personas

| Persona | Role | Core concern |
|---------|------|----------------|
| **CG (Cargo / Control Group)** | Validator at customer or forwarder | Correctness vs customer rules; speed; defensible audit; safe escalation when unsure. |
| **SU (Shipping Unit / supplier)** | Shipper / doc issuer | Clear, **field-level** feedback when something is wrong; fewer back-and-forth emails. |

### 3.2 JTBD (≥5, testable)

1. **When** a shipment PDF arrives, **I want** structured extraction without re-keying, **so that** I can validate in minutes, not hours.  
2. **When** extraction is noisy, **I want** the field marked **uncertain** (not “green”), **so that** we **never silently approve** bad data.  
3. **When** a field violates customer rules, **I want** **found vs expected** on screen, **so that** I can defend the decision to the customer or SU.  
4. **When** multiple fields fail, **I want** a **draft amendment email** listing each discrepancy, **so that** I edit once and send a consistent message.  
5. **When** my lead asks for status, **I want** to query stored runs in **plain English**, **so that** I report counts (e.g., flagged this week) without SQL.  
6. **When** the pipeline crashes mid-run, **I want** resumable state, **so that** we don’t pay twice or lose correlation IDs.  

---

## 4 | Agent architecture (technical core)

### 4.1 Why three agents—not one prompt, not five?

- **One mega-prompt** mixes **perception** (what’s on the page), **governance** (what the customer requires), and **policy** (what we do next). Failures become **un-debuggable** (“was extraction wrong or the rule wrong?”), and you can’t swap models or tests per concern.  
- **Five+ agents** without crisp I/O contracts (e.g. micro “normalize port” agents) adds **orchestration debt** and **silent state drift** for marginal gain in a time-boxed POC.  
- **Three agents** mirror the **real CG mental model**: **read the doc** → **check rules** → **decide the action**. Each stage has a **Pydantic contract**; the next stage **validates** input—**loud** failure on schema mismatch.

### 4.2 Responsibilities, inputs, outputs (executor / verifier / policy framing)

| Agent | Role | Input | Output |
|-------|------|--------|--------|
| **Extractor** | **Executor** (perception) | PDF/image bytes, MIME type | `ExtractionResult`: 8 fields × `{value, confidence, source_snippet}` |
| **Validator** | **Verifier** (rules) | `ExtractionResult` + customer JSON rules (`acme_retail_eu`) | `ValidationReport`: per-field `match` / `mismatch` / `uncertain` + found/expected/reason |
| **Router** | **Policy + comms** | `ValidationReport` | `RouterDecision`: `auto_approve` \| `human_review` \| `draft_amendment_request` + reasoning + optional draft email |

### 4.3 How agents communicate

**Structured handoff via LangGraph state:** each node writes `model_dump(mode="json")` into `GraphState`; the next node calls `model_validate(...)`. No ad-hoc string passing. Optional **`errors[]`** list for operator-visible failures.

### 4.4 Crash recovery

**LangGraph `MemorySaver`** checkpoints after each node. **`thread_id`** is stable per job (UUID aligned with `job_id`). On retry with the same `thread_id`, execution can resume from the last checkpoint (same process in POC; production would use a durable checkpointer).

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

**Go** if: uncertain rate below agreed threshold; **zero** silent-pass incidents on golden set; cost per doc within budget; CG lead signs off “would use weekly”; p95 latency acceptable for their volume. **No-Go** if: repeated wrong **auto_approve** on audit; cost or latency **unbounded**; operators distrust snippets/confidence.

---

## 8 | What’s next (after Part 1 ships)

**Next two weeks (priority order):** (1) **Email / folder trigger** and multi-attachment ingestion; (2) **cross-document consistency** (B/L vs invoice field parity—Part 2 theme); (3) **offline eval harness** + dashboard for golden-set regression; (4) **rule versioning** per customer and **human review queue** UI. **Why not something else first:** without **trigger + multi-doc**, the system doesn’t sit in the real CG loop; without **eval**, quality regresses silently as prompts/models change.

---

## Appendix — Mapping to implemented POC

| PRD section | Code / artifact |
|-------------|------------------|
| Extractor | `src/trade_validator/agents/extractor.py`, schemas `ExtractionResult` |
| Validator | `src/trade_validator/agents/validator.py`, `rules/acme_retail_eu.json` |
| Router | `src/trade_validator/agents/router.py` |
| Orchestration | `src/trade_validator/graph/pipeline.py`, `MemorySaver` |
| Storage + NL | `src/trade_validator/db/`, `services/nl_query.py`, `services/storage.py` |
| UI + API | `streamlit_app/app.py`, `src/trade_validator/api/` |
