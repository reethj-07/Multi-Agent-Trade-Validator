# Sample natural-language queries (Part 1 submission)

You can run these from the Analytics tab in the browser UI (`http://127.0.0.1:8000/`), from Streamlit’s sidebar if you’re using that client, or with curl/Postman:

```http
POST http://127.0.0.1:8000/api/v1/query
Content-Type: application/json

{"question": "YOUR_QUESTION_HERE"}
```

Have the API up and at least one pipeline run in the bank. NL query reads whatever SQLite file you get from starting uvicorn—usually `trade_validator.db` in the cwd—so don’t start the server from a random folder unless you mean to.

## Queries to try

1. How many document runs are stored? (You want a straight `COUNT(*)` on `document_run`.)  
2. How many runs ended in `human_review`? (`final_action` is one of `auto_approve`, `human_review`, `draft_amendment_request`.)  
3. How many were auto-approved?  
4. Last five runs with `customer_id` and `final_action`—small enough to eyeball in the UI.  
5. How many runs have `mismatch_count > 0`?  
6. Average `llm_calls_used` across runs (empty table if you haven’t stored anything yet).

## Demo video

Quick recipe: run the pipeline once on a sample invoice, flip to Analytics, fire questions 1 and 2, then open the SQL/rows panel so whoever’s grading can see the answer came from the query, not thin air.

## Honest note

If the model emits bad SQL you’ll get an `error` field back—that’s fine to show in a write-up; it’s part of how the thing behaves under guardrails.
