// Éval Lab — UI for POST /api/admin/eval + results rendering (chantier 5.1)
(function () {
  "use strict";

  const API_EVAL = "/api/admin/eval";

  const FIELD_KEYS = [
    "NUMERO_FACTURE", "DATE_FACTURE", "MONTANT_HT", "TAUX_TVA", "MONTANT_TTC",
    "NOM_INSTALLATEUR", "COMMUNE_TRAVAUX", "CODE_POSTAL", "ADRESSE_TRAVAUX",
  ];

  const state = {
    currentRun: null,
    isRunning: false,
  };

  const $ = (id) => document.getElementById(id);
  const form = $("form-eval");
  const inputZip = $("input-pdfs-zip");
  const inputTruth = $("input-truth-xlsx");
  const btnRun = $("btn-run");
  const loading = $("loading");
  const results = $("results");
  const runId = $("run-id");
  const runMeta = $("run-meta");
  const globalMicro = $("global-micro");
  const globalMicroDetail = $("global-micro-detail");
  const globalMacro = $("global-macro");
  const perFieldTable = $("per-field-table");
  const perSupplierList = $("per-supplier-list");
  const btnDownload = $("btn-download");
  const toast = $("toast");

  // History (chantier 5.2)
  const historySection = $("history-section");
  const historyCount = $("history-count");
  const historyTbody = $("history-tbody");
  const btnRefreshHistory = $("btn-refresh-history");

  let toastTimer = null;
  function showToast(message, kind) {
    toast.textContent = message;
    toast.className = "fixed bottom-6 right-6 px-4 py-3 rounded-lg shadow-lg text-white text-sm font-medium z-50";
    toast.classList.add(kind === "error" ? "bg-error" : "bg-primary");
    toast.classList.remove("hidden");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.add("hidden"), 4000);
  }

  function accClass(acc) {
    if (acc >= 0.9) return "text-[#2e7d32]";
    if (acc >= 0.6) return "text-[#e65100]";
    return "text-error";
  }

  function renderBar(acc, width) {
    width = width || 10;
    const filled = Math.round(acc * width);
    return "█".repeat(filled) + "░".repeat(width - filled);
  }

  async function submitEval(event) {
    event.preventDefault();
    if (state.isRunning) return;

    const zip = inputZip.files && inputZip.files[0];
    const truth = inputTruth.files && inputTruth.files[0];
    if (!zip) { showToast("Dépose un ZIP de PDFs.", "error"); return; }
    if (!truth) { showToast("Dépose un fichier Excel ground truth.", "error"); return; }

    const fd = new FormData();
    fd.append("pdfs_zip", zip);
    fd.append("truth_xlsx", truth);

    state.isRunning = true;
    btnRun.disabled = true;
    loading.classList.remove("hidden");
    results.classList.add("hidden");

    try {
      const res = await fetch(API_EVAL, { method: "POST", body: fd });
      let data = null;
      try { data = await res.json(); } catch (_) { /* non-json */ }
      if (!res.ok) {
        const detail = (data && (data.detail || data.error)) || `HTTP ${res.status}`;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      state.currentRun = data;
      renderResults(data);
      showToast(`Run '${data.run_id}' terminé.`, "ok");
    } catch (e) {
      showToast(`Erreur éval : ${e.message}`, "error");
    } finally {
      state.isRunning = false;
      btnRun.disabled = false;
      loading.classList.add("hidden");
    }
  }

  function renderResults(payload) {
    const result = payload.result;
    const meta = result.meta || {};
    const metrics = result.metrics || {};
    const perField = metrics.per_field || {};
    const g = metrics.global || {};
    const bySupplier = result.metrics_by_supplier || {};

    runId.textContent = payload.run_id;

    const startedAt = (meta.started_at || "").replace("T", " ").slice(0, 19);
    const durStr = meta.duration_seconds ? `${Math.round(meta.duration_seconds)}s` : "?";
    runMeta.textContent =
      `${meta.matched || 0} PDFs évalués · ${meta.missing_on_disk || 0} manquant(s) sur disque · `
      + `${meta.skipped_no_truth || 0} hors ground truth · modèle ${meta.model || "?"} · `
      + `démarré ${startedAt} UTC · durée ${durStr}`;

    const microPct = (g.accuracy || 0) * 100;
    const macroPct = (g.accuracy_macro || 0) * 100;
    globalMicro.textContent = `${microPct.toFixed(1)}%`;
    globalMicro.className = "font-headline text-3xl font-extrabold mt-1 " + accClass(g.accuracy || 0);
    globalMicroDetail.textContent = `${g.match || 0} / ${g.total || 0} cellules correctes`;
    globalMacro.textContent = `${macroPct.toFixed(1)}%`;
    globalMacro.className = "font-headline text-3xl font-extrabold mt-1 " + accClass(g.accuracy_macro || 0);

    perFieldTable.innerHTML = "";
    for (const field of FIELD_KEYS) {
      const c = perField[field] || {};
      const acc = c.accuracy || 0;
      const row = document.createElement("div");
      row.className = "grid grid-cols-[1.2fr_auto_auto_auto] gap-3 items-center";
      row.innerHTML = `
        <span class="font-mono text-on-surface-variant">${field}</span>
        <span class="font-mono ${accClass(acc)}">${renderBar(acc)}</span>
        <span class="font-mono ${accClass(acc)}">${(acc * 100).toFixed(1)}%</span>
        <span class="text-on-surface-variant/70">
          (${c.match || 0} ok / ${c.mismatch || 0} mis / ${c.missing || 0} miss / ${c.unexpected || 0} unex)
        </span>
      `;
      perFieldTable.appendChild(row);
    }

    perSupplierList.innerHTML = "";
    const sortedSuppliers = Object.keys(bySupplier).sort((a, b) => {
      return (bySupplier[a].global.accuracy || 0) - (bySupplier[b].global.accuracy || 0);
    });
    for (const sup of sortedSuppliers) {
      const m = bySupplier[sup];
      const gg = m.global || {};
      const acc = gg.accuracy || 0;
      const row = document.createElement("div");
      row.className = "grid grid-cols-[1fr_auto_auto_auto] gap-3 items-center";
      row.innerHTML = `
        <span class="font-mono text-on-surface-variant">${sup}</span>
        <span class="font-mono ${accClass(acc)}">${renderBar(acc)}</span>
        <span class="font-mono ${accClass(acc)}">${(acc * 100).toFixed(1)}%</span>
        <span class="text-on-surface-variant/70">(${m.n_pdfs || 0} PDFs, ${gg.match || 0}/${gg.total || 0} cells)</span>
      `;
      perSupplierList.appendChild(row);
    }

    btnDownload.href = payload.download_url || "#";

    results.classList.remove("hidden");
  }

  // ─── History (chantier 5.2) ───
  async function refreshHistory() {
    try {
      const res = await fetch("/api/admin/eval/runs");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = await res.json();
      renderHistory(body.runs || []);
    } catch (e) {
      // History failures are non-blocking; just hide the section.
      historySection.classList.add("hidden");
    }
  }

  function renderHistory(runs) {
    if (!runs || runs.length === 0) {
      historySection.classList.add("hidden");
      historyTbody.innerHTML = "";
      historyCount.textContent = "";
      return;
    }
    historyCount.textContent = `(${runs.length})`;
    historyTbody.innerHTML = "";
    for (const run of runs) {
      const tr = document.createElement("tr");
      tr.className = "border-b border-outline-variant/30 hover:bg-surface-container-low";
      const started = (run.started_at || "").replace("T", " ").slice(0, 16);
      const acc = run.accuracy_micro || 0;
      const dataset = run.pdfs_dir || "";
      const datasetShort = dataset.length > 34 ? "…" + dataset.slice(-33) : dataset;
      const dur = Math.round(run.duration_seconds || 0);
      const durStr = dur < 60 ? `${dur}s` : `${Math.floor(dur / 60)}m ${dur % 60}s`;
      tr.innerHTML = `
        <td class="py-2 pl-2 font-mono">${run.id}</td>
        <td class="py-2 text-on-surface-variant">${started}</td>
        <td class="py-2 text-on-surface-variant font-mono">${datasetShort}</td>
        <td class="py-2 text-right font-bold ${accClass(acc)}">${(acc * 100).toFixed(1)}%</td>
        <td class="py-2 text-right text-on-surface-variant">${durStr}</td>
        <td class="py-2 pr-2 text-right">
          <button type="button" class="text-primary hover:underline btn-view-run" data-run-id="${run.id}">Voir</button>
        </td>
      `;
      historyTbody.appendChild(tr);
    }
    historySection.classList.remove("hidden");
    for (const btn of historyTbody.querySelectorAll(".btn-view-run")) {
      btn.addEventListener("click", () => viewRun(btn.dataset.runId));
    }
  }

  async function viewRun(runId) {
    btnRefreshHistory.disabled = true;
    try {
      const res = await fetch(`/api/admin/eval/runs/${encodeURIComponent(runId)}`);
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        const detail = (data && (data.detail || data.error)) || `HTTP ${res.status}`;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      const result = await res.json();
      renderResults({
        run_id: runId,
        result: result,
        download_url: `/api/admin/eval/runs/${encodeURIComponent(runId)}/download`,
      });
      showToast(`Run '${runId}' chargé.`, "ok");
      results.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      showToast(`Erreur chargement : ${e.message}`, "error");
    } finally {
      btnRefreshHistory.disabled = false;
    }
  }

  btnRefreshHistory.addEventListener("click", refreshHistory);

  // Single submit handler: run the eval, then refresh history so the new run
  // appears at the top of the table.
  form.addEventListener("submit", async (event) => {
    await submitEval(event);
    refreshHistory();
  });

  // Initial load
  refreshHistory();
})();
