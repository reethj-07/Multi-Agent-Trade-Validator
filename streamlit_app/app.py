"""Streamlit UI — calls FastAPI only (no direct graph import)."""

from __future__ import annotations

import os

import httpx
import streamlit as st

API_BASE = os.environ.get("TRADE_VALIDATOR_API_URL", "http://127.0.0.1:8000").rstrip(
    "/"
)

st.set_page_config(page_title="Trade document validation", layout="wide")
st.title("Multi-agent trade document validation")
st.caption("Upload a PDF or image → Gemini extraction → Acme Retail EU rules → router decision.")

if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "nl_answer" not in st.session_state:
    st.session_state.nl_answer = None

def _api_health() -> tuple[bool, str]:
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=3.0)
        r.raise_for_status()
        data = r.json()
        return True, str(data.get("status", "ok"))
    except Exception as e:
        return False, str(e)


with st.sidebar:
    st.header("API")
    st.text(f"Base URL: {API_BASE}")
    ok, detail = _api_health()
    if ok:
        st.success(f"Backend: **{detail}**")
    else:
        st.error("Backend unreachable — start API first:")
        st.code(
            "python -m uvicorn trade_validator.api.main:app "
            "--host 127.0.0.1 --port 8000",
            language="bash",
        )
        st.caption(detail[:200])
    use_pro = st.checkbox(
        "Use Gemini 2.5 Pro for extraction (slower)",
        value=False,
        key="tv_use_pro_extraction",
    )
    st.markdown("---")
    st.markdown("### NL query (stored runs)")
    q = st.text_area(
        "Question",
        placeholder='e.g. How many runs were flagged for human review this week?',
        height=100,
        key="tv_nl_question",
    )
    if st.button("Run query", key="tv_nl_run"):
        if len(q.strip()) < 3:
            st.warning("Enter a longer question.")
        else:
            try:
                r = httpx.post(
                    f"{API_BASE}/api/v1/query",
                    json={"question": q},
                    timeout=120.0,
                )
                r.raise_for_status()
                st.session_state.nl_answer = r.json()
            except Exception as e:
                st.session_state.nl_answer = {"error": str(e)}

uploaded = st.file_uploader(
    "Document",
    type=["pdf", "png", "jpg", "jpeg", "webp"],
    key="tv_document_upload",
)

if st.button("Run pipeline", type="primary", key="tv_run_pipeline"):
    if not uploaded:
        st.error("Upload a document first.")
    else:
        with st.spinner("Running pipeline (LLM calls may take 30–90s)…"):
            try:
                files = {
                    "file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/pdf")
                }
                r = httpx.post(
                    f"{API_BASE}/api/v1/pipeline/run",
                    files=files,
                    params={
                        "customer_id": "acme_retail_eu",
                        "use_pro_extraction": use_pro,
                    },
                    timeout=300.0,
                )
                r.raise_for_status()
                st.session_state.last_result = r.json()
            except httpx.HTTPStatusError as e:
                st.error(f"API error {e.response.status_code}: {e.response.text}")
            except Exception as e:
                st.error(str(e))

if st.session_state.nl_answer:
    st.subheader("NL query result")
    ans = st.session_state.nl_answer
    if ans.get("error"):
        st.error(ans["error"])
    else:
        st.write(ans.get("answer", ""))
        with st.expander("SQL & rows"):
            st.code(ans.get("sql") or "", language="sql")
            st.json(ans.get("rows", []))

res = st.session_state.last_result
if res:
    st.subheader("Pipeline result")
    st.metric("LLM API calls", res.get("llm_calls", 0))
    if res.get("errors"):
        st.error("Pipeline errors:\n" + "\n".join(res["errors"]))

    ext = res.get("extraction") or {}
    val = res.get("validation") or {}
    dec = res.get("router_decision") or {}

    fields = val.get("fields") or []
    st.markdown("### Validation & extraction (per field)")
    for fv in fields:
        name = fv.get("field_name", "")
        verdict = fv.get("verdict", "")
        fe = ext.get(name) or {}
        conf = fe.get("confidence")
        snippet = fe.get("source_snippet") or ""
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.markdown(f"**{name}**")
            if conf is not None:
                c = float(conf)
                if c >= 0.65:
                    st.success(f"confidence: {c:.2f}")
                elif c >= 0.35:
                    st.warning(f"confidence: {c:.2f}")
                else:
                    st.error(f"confidence: {c:.2f}")
        with col2:
            st.caption(f"Verdict: **{verdict}**")
            st.caption(f"Found: `{fv.get('found')}`")
            st.caption(f"Expected: `{fv.get('expected')}`")
        with col3:
            st.caption(fv.get("reason") or "")
            if snippet:
                st.caption(f"Snippet: _{snippet}_")

    st.markdown("### Router")
    st.write(f"**Action:** `{dec.get('action')}`")
    st.write(dec.get("reasoning") or "")
    email = dec.get("draft_amendment_email")
    if email:
        st.text_area(
            "Draft amendment email",
            email,
            height=280,
            key="tv_draft_amendment_email",
            disabled=True,
        )
