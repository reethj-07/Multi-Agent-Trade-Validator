# Sample natural-language queries (Part 1 submission)

Run these in the **Streamlit sidebar** (“NL query”) after at least one pipeline run, or via API:

```http
POST http://127.0.0.1:8000/api/v1/query
Content-Type: application/json

{"question": "YOUR_QUESTION_HERE"}
```

**Prerequisite:** API and DB exist; `trade_validator.db` is in the working directory where **uvicorn** was started (so NL query uses the same SQLite file).

## Queries to try

1. **How many document runs are stored in the database?**  
   *Expect:* A count grounded in `SELECT COUNT(*) FROM document_run`.

2. **How many runs have final_action equal to human_review?**  
   *Expect:* Count filtered on `final_action` (exact string from schema: `auto_approve`, `human_review`, `draft_amendment_request`).

3. **How many runs were auto-approved?**  
   *Expect:* `WHERE final_action = 'auto_approve'`.

4. **List the last 5 runs with their customer_id and final_action.**  
   *Expect:* Small result set; answer summarizes rows only.

5. **How many runs have at least one mismatch (mismatch_count greater than zero)?**  
   *Expect:* Filter on `mismatch_count > 0`.

6. **What is the average llm_calls_used across all runs?**  
   *Expect:* `AVG(llm_calls_used)` — may be empty if no rows.

## For your demo video

Screen-record: run pipeline once → open sidebar → run **(1)** and **(2)** → expand **SQL & rows** in the UI to show grounded behavior.

## Note

Answers must come **only** from executed SQL results; if the model generates invalid SQL, the API returns an `error` field—include that in your write-up as honest failure handling.
