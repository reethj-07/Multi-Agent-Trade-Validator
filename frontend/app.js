(function () {
  "use strict";

  function getApiBase() {
    const params = new URLSearchParams(window.location.search);
    const fromQuery = (params.get("api") || "").trim().replace(/\/$/, "");
    if (fromQuery) return fromQuery;
    if (
      window.location.protocol === "file:" ||
      !window.location.origin ||
      window.location.origin === "null"
    ) {
      return "http://127.0.0.1:8000";
    }
    return "";
  }

  const API = getApiBase();

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  const els = {
    apiDisplay: $("#api-base-display"),
    healthPill: $("#health-pill"),
    healthText: $("#health-text"),
    tabPipeline: $("#tab-pipeline"),
    tabAnalytics: $("#tab-analytics"),
    panelPipeline: $("#panel-pipeline"),
    panelAnalytics: $("#panel-analytics"),
    dropzone: $("#dropzone"),
    fileInput: $("#file-input"),
    fileLabel: $("#file-label"),
    usePro: $("#use-pro"),
    btnRun: $("#btn-run"),
    btnClear: $("#btn-clear"),
    runHint: $("#run-hint"),
    pipelinePlaceholder: $("#pipeline-placeholder"),
    pipelineBusy: $("#pipeline-busy"),
    pipelineError: $("#pipeline-error"),
    pipelineOutput: $("#pipeline-output"),
    nlQuestion: $("#nl-question"),
    btnNl: $("#btn-nl"),
    nlPlaceholder: $("#nl-placeholder"),
    nlBusy: $("#nl-busy"),
    nlError: $("#nl-error"),
    nlOutput: $("#nl-output"),
  };

  let selectedFile = null;

  function apiUrl(path) {
    const p = path.startsWith("/") ? path : "/" + path;
    return API + p;
  }

  function setHealth(state, text) {
    els.healthPill.dataset.state = state;
    els.healthText.textContent = text;
  }

  async function checkHealth() {
    try {
      const r = await fetch(apiUrl("/health"), { method: "GET" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const data = await r.json();
      setHealth("ok", "Backend: " + (data.status || "ok"));
    } catch (e) {
      setHealth(
        "error",
        "Unreachable — start API: python -m uvicorn trade_validator.api.main:app --host 127.0.0.1 --port 8000"
      );
    }
  }

  function verdictClass(v) {
    const x = (v || "").toLowerCase();
    if (x === "match") return "verdict--match";
    if (x === "mismatch") return "verdict--mismatch";
    if (x === "uncertain") return "verdict--uncertain";
    return "";
  }

  function confBarClass(c) {
    if (c == null || Number.isNaN(c)) return "conf-bar__fill--mid";
    if (c >= 0.65) return "conf-bar__fill--high";
    if (c >= 0.35) return "conf-bar__fill--mid";
    return "conf-bar__fill--low";
  }

  function actionBadgeClass(action) {
    const a = (action || "").toLowerCase();
    if (a === "auto_approve") return "badge--auto";
    if (a === "human_review") return "badge--review";
    if (a === "draft_amendment_request") return "badge--amend";
    return "badge--default";
  }

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderPipelineResult(data) {
    const ext = data.extraction || {};
    const val = data.validation || {};
    const dec = data.router_decision || {};
    const fields = val.fields || [];

    let errorsHtml = "";
    if (data.errors && data.errors.length) {
      errorsHtml =
        '<div class="alert alert--error" style="margin-bottom:1rem">' +
        escapeHtml(data.errors.join("\n")) +
        "</div>";
    }

    let rowsHtml = fields
      .map((fv) => {
        const name = fv.field_name || "";
        const fe = ext[name] || {};
        const conf =
          fe.confidence != null ? Math.max(0, Math.min(1, Number(fe.confidence))) : null;
        const pct = conf != null ? Math.round(conf * 100) : 0;
        const snippet = fe.source_snippet || "";
        const reason = fv.reason || "";
        return (
          "<tr>" +
          "<td><strong>" +
          escapeHtml(name) +
          "</strong>" +
          (conf != null
            ? '<div class="conf-bar" title="Confidence"><div class="conf-bar__fill ' +
              confBarClass(conf) +
              '" style="width:' +
              pct +
              '%"></div></div>'
            : "") +
          "</td>" +
          '<td><span class="verdict ' +
          verdictClass(fv.verdict) +
          '">' +
          escapeHtml(fv.verdict || "—") +
          "</span></td>" +
          "<td>" +
          escapeHtml(fv.found) +
          "</td>" +
          "<td>" +
          escapeHtml(fv.expected) +
          "</td>" +
          '<td><div class="snippet">' +
          escapeHtml(reason) +
          (snippet
            ? "<div>Snippet: " + escapeHtml(snippet).slice(0, 200) + "</div>"
            : "") +
          "</div></td>" +
          "</tr>"
        );
      })
      .join("");

    const action = dec.action || "—";
    const email = dec.draft_amendment_email || "";

    const emailBlock = email
      ? '<div class="email-preview"><label>Draft amendment email</label><textarea readonly>' +
        escapeHtml(email) +
        "</textarea></div>"
      : "";

    els.pipelineOutput.innerHTML =
      errorsHtml +
      '<div class="metric-row">' +
      '<div class="metric"><span class="metric__label">LLM calls</span>' +
      '<span class="metric__value">' +
      escapeHtml(String(data.llm_calls ?? 0)) +
      "</span></div>" +
      '<div class="metric"><span class="metric__label">Job ID</span>' +
      '<span class="metric__value" style="font-size:0.85rem">' +
      escapeHtml((data.job_id || "").slice(0, 8)) +
      "…</span></div>" +
      "</div>" +
      "<h3 style='margin:1rem 0 0.5rem;font-size:0.85rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em'>Fields</h3>" +
      '<table class="field-table"><thead><tr>' +
      "<th>Field</th><th>Verdict</th><th>Found</th><th>Expected</th><th>Notes</th>" +
      "</tr></thead><tbody>" +
      (rowsHtml || "<tr><td colspan='5'>No field rows</td></tr>") +
      "</tbody></table>" +
      '<div class="router-block"><h3>Router</h3>' +
      '<span class="badge ' +
      actionBadgeClass(action) +
      '">' +
      escapeHtml(action) +
      "</span>" +
      '<p class="router-reason">' +
      escapeHtml(dec.reasoning || "") +
      "</p>" +
      emailBlock +
      "</div>";
  }

  function renderNlResult(data) {
    if (data.error) {
      els.nlError.hidden = false;
      els.nlError.textContent = data.error;
      els.nlOutput.hidden = true;
      els.nlOutput.innerHTML = "";
      return;
    }
    els.nlError.hidden = true;
    const sql = data.sql || "";
    const rows = data.rows || [];
    const keys =
      rows.length > 0
        ? Object.keys(rows[0])
        : [];

    let tableHtml = "";
    if (keys.length && rows.length) {
      const head = keys.map((k) => "<th>" + escapeHtml(k) + "</th>").join("");
      const body = rows
        .map(
          (row) =>
            "<tr>" +
            keys.map((k) => "<td>" + escapeHtml(row[k]) + "</td>").join("") +
            "</tr>"
        )
        .join("");
      tableHtml =
        '<div class="rows-preview"><table><thead><tr>' +
        head +
        "</tr></thead><tbody>" +
        body +
        "</tbody></table></div>";
    }

    els.nlOutput.innerHTML =
      '<div class="nl-answer">' +
      escapeHtml(data.answer || "") +
      "</div>" +
      (data.explanation
        ? '<p style="font-size:0.85rem;color:var(--text-muted)">' +
          escapeHtml(data.explanation) +
          "</p>"
        : "") +
      '<details class="sql-block" open><summary>SQL &amp; rows (' +
      escapeHtml(String(data.row_count ?? rows.length)) +
      ")</summary>" +
      "<pre>" +
      escapeHtml(sql) +
      "</pre>" +
      tableHtml +
      "</details>";
  }

  function showPipelineBusy(on) {
    els.pipelineBusy.hidden = !on;
    if (on) {
      els.pipelineError.hidden = true;
      els.pipelineOutput.hidden = true;
    }
  }

  function tabsActivate(panelId) {
    const isPipe = panelId === "panel-pipeline";
    els.tabPipeline.classList.toggle("is-active", isPipe);
    els.tabPipeline.setAttribute("aria-selected", isPipe);
    els.tabAnalytics.classList.toggle("is-active", !isPipe);
    els.tabAnalytics.setAttribute("aria-selected", !isPipe);
    els.panelPipeline.hidden = !isPipe;
    els.panelAnalytics.hidden = isPipe;
  }

  $$(".tabs__btn").forEach((btn) => {
    btn.addEventListener("click", () => tabsActivate(btn.dataset.panel));
  });

  function updateFileUi() {
    if (selectedFile) {
      els.fileLabel.textContent = selectedFile.name;
      els.btnRun.disabled = false;
      els.runHint.textContent =
        "Ready: " + selectedFile.name + " (" + formatSize(selectedFile.size) + ")";
    } else {
      els.fileLabel.textContent = "Drop a file here or click to browse";
      els.btnRun.disabled = true;
      els.runHint.textContent =
        "Pipeline can take 30–90s depending on document size and model.";
    }
  }

  function formatSize(n) {
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
    return (n / (1024 * 1024)).toFixed(1) + " MB";
  }

  els.dropzone.addEventListener("click", () => els.fileInput.click());
  els.dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      els.fileInput.click();
    }
  });

  els.fileInput.addEventListener("change", () => {
    const f = els.fileInput.files && els.fileInput.files[0];
    selectedFile = f || null;
    updateFileUi();
  });

  ["dragenter", "dragover"].forEach((ev) => {
    els.dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      els.dropzone.classList.add("is-dragover");
    });
  });
  ["dragleave", "drop"].forEach((ev) => {
    els.dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      els.dropzone.classList.remove("is-dragover");
    });
  });
  els.dropzone.addEventListener("drop", (e) => {
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) {
      selectedFile = f;
      els.fileInput.value = "";
      updateFileUi();
    }
  });

  els.btnRun.addEventListener("click", async () => {
    if (!selectedFile) return;
    els.pipelineError.hidden = true;
    els.pipelineOutput.hidden = true;
    els.pipelinePlaceholder.hidden = true;
    showPipelineBusy(true);
    els.btnRun.disabled = true;

    const fd = new FormData();
    fd.append("file", selectedFile, selectedFile.name);

    const params = new URLSearchParams({
      customer_id: "acme_retail_eu",
      use_pro_extraction: els.usePro.checked ? "true" : "false",
    });

    try {
      const r = await fetch(apiUrl("/api/v1/pipeline/run?" + params.toString()), {
        method: "POST",
        body: fd,
      });
      const text = await r.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error(text.slice(0, 500) || "Invalid JSON");
      }
      if (!r.ok) {
        const detail = data.detail != null ? JSON.stringify(data.detail) : text;
        throw new Error("API " + r.status + ": " + detail);
      }
      renderPipelineResult(data);
      els.pipelineOutput.hidden = false;
      els.btnClear.hidden = false;
    } catch (e) {
      els.pipelineError.hidden = false;
      els.pipelineError.textContent = String(e.message || e);
      els.pipelinePlaceholder.hidden = false;
    } finally {
      showPipelineBusy(false);
      els.btnRun.disabled = !selectedFile;
    }
  });

  els.btnClear.addEventListener("click", () => {
    els.pipelineOutput.hidden = true;
    els.pipelineOutput.innerHTML = "";
    els.pipelinePlaceholder.hidden = false;
    els.pipelineError.hidden = true;
    els.btnClear.hidden = true;
  });

  els.btnNl.addEventListener("click", async () => {
    const q = (els.nlQuestion.value || "").trim();
    if (q.length < 3) {
      els.nlError.hidden = false;
      els.nlError.textContent = "Enter a longer question (at least 3 characters).";
      els.nlOutput.hidden = true;
      return;
    }
    els.nlError.hidden = true;
    els.nlPlaceholder.hidden = true;
    els.nlBusy.hidden = false;
    els.nlOutput.hidden = true;
    els.btnNl.disabled = true;

    try {
      const r = await fetch(apiUrl("/api/v1/query"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await r.json();
      if (!r.ok) {
        throw new Error(data.detail ? JSON.stringify(data.detail) : r.statusText);
      }
      renderNlResult(data);
      if (!data.error) {
        els.nlOutput.hidden = false;
      }
    } catch (e) {
      renderNlResult({ error: String(e.message || e) });
      els.nlOutput.hidden = false;
    } finally {
      els.nlBusy.hidden = true;
      els.btnNl.disabled = false;
      if (!els.nlOutput.innerHTML && !els.nlError.textContent) {
        els.nlPlaceholder.hidden = false;
      }
    }
  });

  /* Init */
  const displayBase = API || window.location.origin || "(same origin)";
  els.apiDisplay.textContent = displayBase;
  updateFileUi();
  checkHealth();
  setInterval(checkHealth, 15000);

  if (window.location.protocol === "file:") {
    setHealth("error", "Open this app via the API server (http://127.0.0.1:8000/) not file://");
  }
})();
