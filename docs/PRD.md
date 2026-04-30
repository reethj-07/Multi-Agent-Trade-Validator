# Product Requirements Document (PRD)

**What this is:** A working picture of the multi-agent trade document pipeline for Nova DAW (Part 1).  
**Who it’s for:** Anyone building it, reviewing it, or grading it.  
**Length:** You can export this to PDF (roughly three to five pages) if you need a formal handoff.

---

## 1 | Nova, FDE, and “system of outcomes”

### 1.1 What Nova is trying to do

Nova isn’t really about building “one more place to stash PDFs.” The uncomfortable truth in operations is that you need something you can defend later: did we actually check this paperwork, what did we find, and what did we decide to do? When a shipment goes sideways, “I think we looked at it” doesn’t cut it.

Regular SaaS is fine at storing rows and moving tickets. It’s much weaker at squinting at a bad scan, applying rules that change from customer to customer, and knowing when automation should back off. In the wild, people still retype fields by hand, the scary-smart senior keeps half the rules in their head, and every amendment costs half a day of email. This POC is a small step toward **read the doc → check it → decide**, so operators spend their time on the weird cases instead of on copy-paste.

### 1.2 Why “forward deployed” shows up in this world

Trade validation doesn’t normalize across accounts. One customer obsesses over HS chapter 8471; another cares that the consignee legal name matches exactly. In plenty of shops, two to four email rounds per shipment is just “how it works.” Forward deployed engineers sit in that reality—lanes, exceptions, integrations—and the definition of “good enough” gets negotiated in the room: pilot metrics, which rule pack ships, who signs off. If the product only moves when a distant roadmap says so, you’ll never tune it fast enough. That’s the FDE story in one sentence.

### 1.3 System of outcomes vs record vs engagement

- **System of record:** “What do we believe is true?”  
- **System of engagement:** “How does work move between people?”  
- **System of outcomes:** “Did we actually reach the state we said we wanted?”

This build leans on things you can poke at: each field tagged match / mismatch / uncertain, a router that says what it would do next (in plain language), and runs stored so someone can ask questions later. The PDF still has to land in the filing cabinet; what we care about here is whether you’d stand behind the shipment *after* the tool had its say.

---

## 2 | Problem statement

### 2.1 Where the current flow hurts

**Tribal rules.** Customer quirks live in someone’s head; new hires mis-validate for weeks.

**Manual re-keying.** Fields get typed from the PDF into checks by hand—slow, easy to get wrong, doesn’t scale.

**Amendment loops.** Two to four email cycles per shipment isn’t rare, and each cycle often costs hours.

**Thin audit trail.** When there’s a dispute, nobody has a clean “found vs expected” story per field.

**Silent errors.** A wrong HS code or consignee can slip through a casual glance and turn into holds, fines, or angry customers.

**No visibility.** “How much is stuck in review this week?” shouldn’t require a spreadsheet marathon.

### 2.2 What “good” feels like in the first five minutes

Someone drops in a PDF or a phone photo. They get back the fields that matter, each with a confidence score and a short quote from the page—so they’re not staring at a black box. Validation is readable: matched, mismatched, or uncertain, with found vs expected when something’s wrong. The router explains what it would do next. If several fields are off, there’s a draft amendment email they can edit instead of rewriting from zero. If their manager asks how many runs landed in human review, they can ask in normal language and get an answer tied to real rows in the database, not a vibe.

---

## 3 | Users and jobs-to-be-done

### 3.1 Who we’re picturing

**CG (cargo / control group)** — the person at the customer or forwarder who has to be right. They care about matching the customer’s rules, moving fast, and having an audit trail they can point to. When the model is unsure, they want a safe escalation, not a fake green checkmark.

**SU (supplier / shipper)** — the side that issued the docs. They want **field-level** feedback when something’s wrong, so they’re not playing email ping-pong with vague “please fix” notes.

### 3.2 Jobs we’re trying to cover (testable)

1. A shipment PDF shows up → turn it into structured fields without retyping the whole page; validation should be minutes, not an afternoon.  
2. The model is wobbly on a field → mark it **uncertain**, not “probably fine.” Nothing auto-approves on thin evidence.  
3. A rule fires → show **found vs expected** on screen so CG can explain it to the customer or supplier without reopening the PDF.  
4. Several fields are wrong → one draft email that lists the gaps, so they edit once instead of sending five contradictory messages.  
5. A manager asks “how many stuck in review this week?” → ask in plain English over stored runs; the answer should map to actual query results.  
6. **Checkpoints (honest scope):** LangGraph keeps in-memory checkpoints after each node. In development, you could replay from the last checkpoint **in the same process** if you re-invoked with the same `thread_id`. The HTTP API, as shipped, runs one full `invoke` per upload—so durable “resume this job after a crash” would mean a persisted checkpointer plus a resume API. Worth saying out loud so nobody expects magic across separate requests.

---

## 4 | Agent architecture

### 4.1 Why three steps, not one giant prompt and not fifteen tiny agents

Stuffing everything into one prompt mixes “what’s on the page,” “what this customer allows,” and “what we do next.” When it fails, you can’t tell which layer lied. Exploding into a dozen micro-agents without hard contracts means you spend the sprint plumbing state instead of shipping behavior.

Three stages line up with how people in cargo actually describe the work: read the document, check it against the rule pack, decide what happens. Each handoff uses a **Pydantic** payload; the next stage validates it so garbage doesn’t drift downstream quietly.

### 4.2 What each agent owns

**Extractor (executor / perception)**  
Takes PDF or image bytes plus MIME type. Produces `ExtractionResult`: eight core fields, each with value, confidence, and a short source snippet.

**Validator (verifier / rules)**  
Takes the extraction plus the customer JSON (`acme_retail_eu` in the repo). Produces `ValidationReport`: per field, `match` / `mismatch` / `uncertain`, plus found, expected, and a human-readable reason.

**Router (policy + comms)**  
Takes the validation report. Produces `RouterDecision`: `auto_approve`, `human_review`, or `draft_amendment_request`, with reasoning, a discrepancy list, and an optional draft email when amendments make sense.

### 4.3 How they talk to each other

LangGraph holds a typed state dict. After each node we serialize with `model_dump(mode="json")` and the next node parses with `model_validate(...)`. No loose strings between stages. There’s also an `errors[]` list so operators can see stack traces or guard failures without losing the rest of the run.

### 4.4 Crash recovery (what we actually have)

We use LangGraph’s `MemorySaver` after each node. `thread_id` is the same UUID as `job_id`, so you can correlate API → graph → database row. Mid-graph resume only lasts as long as that in-memory checkpointer exists; it doesn’t automatically survive a new HTTP request. Production shape would be a durable store and an explicit “resume job” path.

---

## 5 | LLM and tooling

**Gemini 2.5 Flash** is the default for extraction: vision, speed, cost, structured JSON via `response_schema`.

**Gemini 2.5 Pro** is for harder moments: one retry if Flash fails, NL→SQL generation, and summarizing query results. The idea is to use it **sparingly**.

**When the document is ugly:** low confidence flows to the validator as uncertain → router picks **human_review**. Extraction retries once with Pro if Flash throws. If we’re out of LLM budget, the amendment email falls back to a template instead of a polished draft.

**LangGraph** gives typed state, checkpoints, and a straight line: extract → validate → route, with obvious places to test.

**Structured output** matters where contracts matter: extraction (`ExtractionResult`), NL SQL helper (`SqlAnswer`), email polish (`_AmendmentEmailBody`).

**Why the validator isn’t an LLM:** rules are deterministic and debuggable. Router policy is code-first; the model helps draft text when it’s safe, not when we need a verdict we can explain in an audit.

---

## 6 | Trust, failure handling, and evaluation

**Hallucinated fields:** the extractor prompt pushes “only visible text,” null + low confidence when missing, snippet when claiming a value; the validator can mark uncertain below a confidence threshold.

**Low confidence:** we never route to **auto_approve** if any field is **uncertain**—that goes to **human_review**.

**Runaway cost:** `TRADE_VALIDATOR_MAX_LLM_CALLS` caps round-trips per run; the router checks cumulative `llm_calls` before optional polish; no infinite retry loops.

**Offline eval (where you’d go next):** a small golden set of labeled PDFs—precision/recall on extraction, rule accuracy on the validator, router vs human labels.

**Online:** share of uploads that reach `auto_approve` without override, sampled audits on auto-approved rows, p95 latency per stage.

---

## 7 | Metrics and success

### North star (one number)

**Median minutes from upload to a CG decision** (approve, amendment, or escalate) on pilot traffic—lower weekly is better.

### Supporting metrics that actually help

Uncertain field rate. Auto-approve precision from spot checks. Amendment cycles per shipment (email thread as a proxy). LLM cost and tokens per doc. p95 latency end-to-end and per node. NL answers that contradict the SQL result (you want that near zero). A simple “would you use this weekly?” from operators.

### Go / no-go for a two-week pilot

You’d **go** if uncertain rate stays in the band you agreed with the customer, you’re not seeing silent passes on a golden set, cost per doc fits the budget, the CG lead will really use it, and latency doesn’t fall over at their volume.

You’d **stop** if auto-approve keeps failing audits, spend or latency has no ceiling, or people stop trusting the snippets and scores.

---

## 8 | If Part 1 worked, what I’d do next

I’d chase real ingestion first—email or a watched folder, more than one attachment—because until traffic hits the system it’s still a demo. Cross-document checks (B/L vs invoice) are the natural Part 2. I’d want a tiny golden set in CI so prompt edits don’t silently trash extraction, versioned rule packs, and a thin queue UI for human review. Triggers and multi-doc before polish; evaluation before you believe the headline metrics.

---

## Appendix — Where this lives in the repo

| PRD topic | Location |
|-----------|----------|
| Extractor | `src/trade_validator/agents/extractor.py`, `schemas/extraction.py` |
| Validator | `src/trade_validator/agents/validator.py`, `rules/acme_retail_eu.json` |
| Router | `src/trade_validator/agents/router.py` |
| Orchestration | `src/trade_validator/graph/pipeline.py`, `MemorySaver` |
| Storage + NL | `src/trade_validator/db/`, `services/nl_query.py`, `services/storage.py` |
| UI + API | `frontend/`, optional `streamlit_app/app.py`, `src/trade_validator/api/` |
