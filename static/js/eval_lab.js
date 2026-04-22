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
  const btnDownload = $("btn-download");
  const toast = $("toast");

  // Hero card + insights + per-field/supplier cards (results redesign)
  const heroPct = $("hero-pct");
  const heroDonutCircle = $("hero-donut-circle");
  const heroMicroDetail = $("hero-micro-detail");
  const statMacro = $("stat-macro");
  const statMatched = $("stat-matched");
  const statMatchedDetail = $("stat-matched-detail");
  const statFieldsOk = $("stat-fields-ok");
  const statFieldsBad = $("stat-fields-bad");
  const insightsContainer = $("insights");
  const perFieldCards = $("per-field-cards");
  const perSupplierCards = $("per-supplier-cards");
  // Donut circle radius is 52 → circumference = 2π·52 ≈ 326.7
  const DONUT_CIRC = 2 * Math.PI * 52;

  // SSE progress (chantier 5.4)
  const progressBar = $("progress-bar");
  const progressPercent = $("progress-percent");
  const progressSummary = $("progress-summary");
  const progressLast = $("progress-last");

  // History (chantier 5.2)
  const historySection = $("history-section");
  const historyCount = $("history-count");
  const historyTbody = $("history-tbody");
  const btnRefreshHistory = $("btn-refresh-history");

  // Diff (chantier 5.3)
  const btnDiff = $("btn-diff");
  const btnCloseDiff = $("btn-close-diff");
  const diffSection = $("diff-section");
  const diffTitle = $("diff-title");
  const diffGlobalMicro = $("diff-global-micro");
  const diffGlobalMacro = $("diff-global-macro");
  const diffPerField = $("diff-per-field");
  const diffPerSupplier = $("diff-per-supplier");
  const regressionsList = $("regressions-list");
  const regressionsCount = $("regressions-count");
  const improvementsList = $("improvements-list");
  const improvementsCount = $("improvements-count");

  state.selectedRuns = new Set();

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

  function resetProgress() {
    progressBar.style.width = "0%";
    progressPercent.textContent = "0%";
    progressSummary.textContent = "Initialisation…";
    progressLast.textContent = "";
  }

  function updateProgress(index, total, filename, installateur) {
    const pct = total > 0 ? Math.round((index / total) * 100) : 0;
    progressBar.style.width = pct + "%";
    progressPercent.textContent = pct + "%";
    progressSummary.textContent = `${index} / ${total} PDFs traités`;
    if (filename) {
      const short = filename.length > 60 ? "…" + filename.slice(-59) : filename;
      progressLast.textContent = `${short}   (${installateur || "?"})`;
    }
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
    resetProgress();
    loading.classList.remove("hidden");
    results.classList.add("hidden");

    let finalPayload = null;

    try {
      const res = await fetch("/api/admin/eval/stream", { method: "POST", body: fd });
      if (!res.ok) {
        // Fail-fast errors (bad ZIP extension, validation) come back as plain JSON.
        let detail = `HTTP ${res.status}`;
        try {
          const body = await res.json();
          detail = body.detail || body.error || detail;
        } catch (_) { /* non-json */ }
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let streamError = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sep;
        while ((sep = buffer.indexOf("\n\n")) !== -1) {
          const chunk = buffer.slice(0, sep).trim();
          buffer = buffer.slice(sep + 2);
          if (!chunk.startsWith("data: ")) continue;
          let payload;
          try {
            payload = JSON.parse(chunk.slice(6));
          } catch (_) {
            continue;
          }
          if (payload.type === "init") {
            updateProgress(0, payload.total, null, null);
          } else if (payload.type === "progress") {
            updateProgress(payload.index, payload.total, payload.filename, payload.installateur);
          } else if (payload.type === "done") {
            finalPayload = {
              run_id: payload.run_id,
              result: payload.result,
              download_url: payload.download_url,
            };
          } else if (payload.type === "error") {
            streamError = payload.error || "unknown server error";
          }
        }
      }

      if (streamError) {
        throw new Error(streamError);
      }
      if (!finalPayload || !finalPayload.result) {
        throw new Error("le serveur n'a pas envoyé d'événement 'done'");
      }
      state.currentRun = finalPayload;
      renderResults(finalPayload);
      const label = finalPayload.run_id ? `Run '${finalPayload.run_id}' terminé.`
                                        : "Évaluation terminée (aucun PDF apparié, rien sauvegardé).";
      showToast(label, "ok");
    } catch (e) {
      showToast(`Erreur éval : ${e.message}`, "error");
    } finally {
      state.isRunning = false;
      btnRun.disabled = false;
      loading.classList.add("hidden");
    }
  }

  // ─── Results renderer (refonte design) ───

  // Color/CSS helpers shared by the cards
  function accBgClass(acc) {
    if (acc >= 0.9) return "bg-[#2e7d32]";
    if (acc >= 0.6) return "bg-[#e65100]";
    return "bg-error";
  }
  function accBorderClass(acc) {
    if (acc >= 0.9) return "border-l-[#2e7d32]";
    if (acc >= 0.6) return "border-l-[#e65100]";
    return "border-l-error";
  }
  function accDonutColor(acc) {
    if (acc >= 0.9) return "#2e7d32";
    if (acc >= 0.6) return "#e65100";
    return "#ba1a1a";
  }
  function accLabel(acc) {
    if (acc >= 0.9) return "excellent";
    if (acc >= 0.75) return "bon";
    if (acc >= 0.6) return "à améliorer";
    return "critique";
  }

  function renderResults(payload) {
    const result = payload.result;
    const meta = result.meta || {};
    const metrics = result.metrics || {};
    const perField = metrics.per_field || {};
    const g = metrics.global || {};
    const bySupplier = result.metrics_by_supplier || {};

    // ─── Header ───
    runId.textContent = payload.run_id;
    const startedAt = (meta.started_at || "").replace("T", " ").slice(0, 16);
    const durSec = Math.round(meta.duration_seconds || 0);
    const durStr = durSec < 60 ? `${durSec}s` : `${Math.floor(durSec / 60)}m ${durSec % 60}s`;
    runMeta.textContent =
      `démarré ${startedAt} UTC · durée ${durStr} · modèle ${meta.model || "?"}`;

    // ─── Hero donut ───
    const microAcc = g.accuracy || 0;
    const microPct = microAcc * 100;
    heroPct.textContent = `${microPct.toFixed(1)}%`;
    heroPct.className = "font-headline text-2xl font-extrabold leading-none " + accClass(microAcc);
    heroDonutCircle.style.strokeDashoffset = String(DONUT_CIRC * (1 - microAcc));
    heroDonutCircle.style.stroke = accDonutColor(microAcc);
    heroMicroDetail.textContent = `${g.match || 0} / ${g.total || 0} cellules correctes`;

    // ─── Quick stats ───
    const macroAcc = g.accuracy_macro || 0;
    statMacro.textContent = `${(macroAcc * 100).toFixed(1)}%`;
    statMacro.className = "font-headline text-2xl font-extrabold mt-1 " + accClass(macroAcc);

    statMatched.textContent = String(meta.matched || 0);
    const skipped = (meta.missing_on_disk || 0) + (meta.skipped_no_truth || 0);
    statMatchedDetail.textContent = skipped > 0
      ? `évalués · ${skipped} ignoré(s)`
      : "évalués";

    const fieldEntries = Object.entries(perField);
    const okCount = fieldEntries.filter(([k, v]) => (v.accuracy || 0) >= 0.9).length;
    const badCount = fieldEntries.filter(([k, v]) => (v.accuracy || 0) < 0.6).length;
    statFieldsOk.textContent = String(okCount);
    statFieldsBad.textContent = String(badCount);

    // ─── Insights (auto-generated) ───
    renderInsights(perField, bySupplier, microAcc);

    // ─── Per-field cards (sorted DESC by accuracy) ───
    perFieldCards.innerHTML = "";
    const sortedFields = [...FIELD_KEYS].sort((a, b) => {
      const aa = (perField[a] || {}).accuracy || 0;
      const bb = (perField[b] || {}).accuracy || 0;
      return bb - aa;
    });
    for (const field of sortedFields) {
      perFieldCards.appendChild(renderFieldCard(field, perField[field] || {}));
    }

    // ─── Per-supplier rows (sorted ASC by accuracy = worst first) ───
    perSupplierCards.innerHTML = "";
    const sortedSuppliers = Object.keys(bySupplier).sort((a, b) =>
      ((bySupplier[a].global || {}).accuracy || 0) - ((bySupplier[b].global || {}).accuracy || 0)
    );
    for (const sup of sortedSuppliers) {
      perSupplierCards.appendChild(renderSupplierRow(sup, bySupplier[sup]));
    }

    btnDownload.href = payload.download_url || "#";

    results.classList.remove("hidden");
  }

  function renderInsights(perField, bySupplier, microAcc) {
    insightsContainer.innerHTML = "";
    const items = [];

    // Best 3 fields
    const sortedFieldsDesc = Object.entries(perField)
      .sort(([, a], [, b]) => (b.accuracy || 0) - (a.accuracy || 0));
    if (sortedFieldsDesc.length && (sortedFieldsDesc[0][1].accuracy || 0) >= 0.9) {
      const top = sortedFieldsDesc.slice(0, 3).map(([k]) => k).join(", ");
      items.push({
        type: "good",
        icon: "trending_up",
        text: "Champs les plus fiables",
        detail: top,
      });
    }

    // Worst field
    const sortedFieldsAsc = Object.entries(perField)
      .sort(([, a], [, b]) => (a.accuracy || 0) - (b.accuracy || 0));
    if (sortedFieldsAsc.length && (sortedFieldsAsc[0][1].accuracy || 0) < 0.6) {
      const [worstField, worstStats] = sortedFieldsAsc[0];
      items.push({
        type: "bad",
        icon: "priority_high",
        text: `Champ à travailler : ${worstField}`,
        detail: `${((worstStats.accuracy || 0) * 100).toFixed(1)} % seulement`,
      });
    }

    // Worst supplier
    const sortedSupAsc = Object.entries(bySupplier)
      .sort(([, a], [, b]) => ((a.global || {}).accuracy || 0) - ((b.global || {}).accuracy || 0));
    if (sortedSupAsc.length && ((sortedSupAsc[0][1].global || {}).accuracy || 0) < 0.6) {
      const [worstSup, worstM] = sortedSupAsc[0];
      items.push({
        type: "bad",
        icon: "factory",
        text: `Fournisseur prioritaire : ${worstSup}`,
        detail: `${((worstM.global.accuracy || 0) * 100).toFixed(1)} % sur ${worstM.n_pdfs || 0} PDFs`,
      });
    }

    // Overall posture
    if (microAcc >= 0.9) {
      items.unshift({
        type: "good",
        icon: "check_circle",
        text: "Très bonne qualité d'extraction",
        detail: `${(microAcc * 100).toFixed(1)} % de cellules correctes — prêt pour usage`,
      });
    } else if (microAcc < 0.6) {
      items.unshift({
        type: "bad",
        icon: "warning",
        text: "Qualité globale insuffisante",
        detail: "Vérifier les prompts des fournisseurs problématiques",
      });
    }

    if (items.length === 0) {
      insightsContainer.classList.add("hidden");
      return;
    }
    insightsContainer.classList.remove("hidden");
    for (const it of items) {
      const div = document.createElement("div");
      const palette = it.type === "good"
        ? "border-l-[#2e7d32] bg-[#E6F4EA]/40"
        : "border-l-error bg-[#FDE8E8]/40";
      const iconColor = it.type === "good" ? "text-[#2e7d32]" : "text-error";
      div.className = `rounded-xl p-4 border border-outline-variant/30 border-l-4 ${palette} flex items-start gap-3`;
      div.innerHTML = `
        <span class="material-symbols-outlined ${iconColor}">${it.icon}</span>
        <div class="flex-1 min-w-0">
          <div class="font-medium text-sm text-on-surface">${it.text}</div>
          <div class="text-xs text-on-surface-variant mt-0.5">${it.detail}</div>
        </div>
      `;
      insightsContainer.appendChild(div);
    }
  }

  function renderFieldCard(field, c) {
    const acc = c.accuracy || 0;
    const pct = (acc * 100).toFixed(1);
    const card = document.createElement("div");
    card.className = `bg-surface-container-low rounded-xl p-4 border border-outline-variant/20 border-l-4 ${accBorderClass(acc)}`;

    const chips = [];
    if (c.match)      chips.push(`<span class="px-2 py-0.5 bg-[#E6F4EA] text-[#2e7d32] rounded font-medium">${c.match} OK</span>`);
    if (c.mismatch)   chips.push(`<span class="px-2 py-0.5 bg-[#FDE8E8] text-error rounded font-medium">${c.mismatch} faux</span>`);
    if (c.missing)    chips.push(`<span class="px-2 py-0.5 bg-[#FFE5CC] text-[#e65100] rounded font-medium">${c.missing} manquant</span>`);
    if (c.unexpected) chips.push(`<span class="px-2 py-0.5 bg-[#FFF9C4] text-[#665900] rounded font-medium">${c.unexpected} inattendu</span>`);
    if (chips.length === 0) chips.push(`<span class="text-on-surface-variant italic">aucune donnée</span>`);

    card.innerHTML = `
      <div class="flex items-center justify-between mb-2">
        <span class="font-mono text-sm font-semibold text-on-surface">${field}</span>
        <div class="flex items-baseline gap-2">
          <span class="font-headline text-xl font-extrabold ${accClass(acc)}">${pct}%</span>
          <span class="text-[10px] uppercase tracking-widest font-bold ${accClass(acc)}">${accLabel(acc)}</span>
        </div>
      </div>
      <div class="w-full h-2 bg-white rounded-full overflow-hidden">
        <div class="h-full ${accBgClass(acc)} rounded-full transition-all duration-500" style="width: ${pct}%"></div>
      </div>
      <div class="flex flex-wrap gap-1.5 mt-2.5 text-[11px]">
        ${chips.join("")}
      </div>
    `;
    return card;
  }

  function renderSupplierRow(sup, m) {
    const gg = m.global || {};
    const acc = gg.accuracy || 0;
    const pct = (acc * 100).toFixed(1);
    const row = document.createElement("div");
    row.className = "flex items-center gap-3 p-3 bg-surface-container-low rounded-xl";
    row.innerHTML = `
      <div class="w-1.5 h-12 rounded-full ${accBgClass(acc)} flex-shrink-0"></div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center justify-between gap-2 mb-1">
          <div class="flex items-center gap-2 min-w-0">
            <span class="font-mono text-sm font-semibold text-on-surface truncate">${sup}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-white/60 text-on-surface-variant flex-shrink-0">
              ${m.n_pdfs || 0} PDF${(m.n_pdfs || 0) > 1 ? "s" : ""}
            </span>
          </div>
          <div class="flex items-baseline gap-2 flex-shrink-0">
            <span class="font-headline text-lg font-extrabold ${accClass(acc)}">${pct}%</span>
            <span class="text-[10px] text-on-surface-variant">${gg.match || 0}/${gg.total || 0}</span>
          </div>
        </div>
        <div class="w-full h-1.5 bg-white rounded-full overflow-hidden">
          <div class="h-full ${accBgClass(acc)} rounded-full transition-all duration-500" style="width: ${pct}%"></div>
        </div>
      </div>
    `;
    return row;
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
        <td class="py-2 pl-2 text-center">
          <input type="checkbox" class="run-checkbox" data-run-id="${run.id}"/>
        </td>
        <td class="py-2 font-mono">${run.id}</td>
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
    for (const cb of historyTbody.querySelectorAll(".run-checkbox")) {
      if (state.selectedRuns.has(cb.dataset.runId)) cb.checked = true;
      cb.addEventListener("change", onRunSelectionChange);
    }
    updateDiffButton();
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

  // ─── Diff (chantier 5.3) ───
  function onRunSelectionChange(event) {
    const cb = event.target;
    const id = cb.dataset.runId;
    if (cb.checked) state.selectedRuns.add(id);
    else state.selectedRuns.delete(id);
    updateDiffButton();
  }

  function updateDiffButton() {
    btnDiff.disabled = state.selectedRuns.size !== 2;
  }

  async function submitDiff() {
    if (state.selectedRuns.size !== 2) return;
    // Sort by ID (timestamp-prefixed) so 'a' is older, 'b' is newer.
    const [a, b] = [...state.selectedRuns].sort();
    btnDiff.disabled = true;
    try {
      const res = await fetch(`/api/admin/eval/runs/${encodeURIComponent(a)}/diff/${encodeURIComponent(b)}`);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const detail = (body && (body.detail || body.error)) || `HTTP ${res.status}`;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      const diff = await res.json();
      renderDiff(diff, a, b);
      diffSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      showToast(`Erreur comparaison : ${e.message}`, "error");
    } finally {
      updateDiffButton();
    }
  }

  function arrow(delta) {
    if (delta > 0.05) return "↑↑";
    if (delta > 0.005) return "↑";
    if (delta < -0.05) return "↓↓";
    if (delta < -0.005) return "↓";
    return "=";
  }
  function deltaClass(delta) {
    if (delta > 0.005) return "text-[#2e7d32]";
    if (delta < -0.005) return "text-error";
    return "text-on-surface-variant";
  }
  function fmtPct(x) { return ((x || 0) * 100).toFixed(1) + "%"; }
  function fmtPp(d)  { return (d >= 0 ? "+" : "") + ((d || 0) * 100).toFixed(1) + "pp"; }

  function renderDiff(diff, aId, bId) {
    diffTitle.textContent = `Diff : ${aId}  →  ${bId}`;

    const g = diff.global || {};
    const micro = g.micro || { a: 0, b: 0, delta: 0 };
    const macro = g.macro || { a: 0, b: 0, delta: 0 };
    diffGlobalMicro.innerHTML = `
      <div class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Global micro</div>
      <div class="font-headline text-2xl font-extrabold mt-1">${fmtPct(micro.a)} → ${fmtPct(micro.b)}</div>
      <div class="text-sm font-bold ${deltaClass(micro.delta)} mt-1">${fmtPp(micro.delta)}  ${arrow(micro.delta)}</div>
    `;
    diffGlobalMacro.innerHTML = `
      <div class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Global macro</div>
      <div class="font-headline text-2xl font-extrabold mt-1">${fmtPct(macro.a)} → ${fmtPct(macro.b)}</div>
      <div class="text-sm font-bold ${deltaClass(macro.delta)} mt-1">${fmtPp(macro.delta)}  ${arrow(macro.delta)}</div>
    `;

    diffPerField.innerHTML = "";
    for (const field of Object.keys(diff.per_field || {})) {
      const v = diff.per_field[field];
      const row = document.createElement("div");
      row.className = "grid grid-cols-[1.2fr_auto_auto_auto_auto] gap-3 items-center";
      row.innerHTML = `
        <span class="font-mono text-on-surface-variant">${field}</span>
        <span class="font-mono">${fmtPct(v.a)}</span>
        <span class="font-mono text-on-surface-variant">→</span>
        <span class="font-mono">${fmtPct(v.b)}</span>
        <span class="font-mono font-bold ${deltaClass(v.delta)}">${fmtPp(v.delta)} ${arrow(v.delta)}</span>
      `;
      diffPerField.appendChild(row);
    }

    diffPerSupplier.innerHTML = "";
    const sups = diff.per_supplier || {};
    const supKeys = Object.keys(sups).sort((x, y) => (sups[x].delta || 0) - (sups[y].delta || 0));
    if (supKeys.length === 0) {
      diffPerSupplier.innerHTML = `<p class="text-on-surface-variant italic">Aucun fournisseur commun entre les deux runs.</p>`;
    } else {
      for (const sup of supKeys) {
        const v = sups[sup];
        const row = document.createElement("div");
        row.className = "grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-3 items-center";
        row.innerHTML = `
          <span class="font-mono text-on-surface-variant">${sup}</span>
          <span class="font-mono">${fmtPct(v.a)}</span>
          <span class="font-mono text-on-surface-variant">→</span>
          <span class="font-mono">${fmtPct(v.b)}</span>
          <span class="font-mono font-bold ${deltaClass(v.delta)}">${fmtPp(v.delta)} ${arrow(v.delta)}</span>
          <span class="text-on-surface-variant/70">(${v.n_a || 0} → ${v.n_b || 0} PDFs)</span>
        `;
        diffPerSupplier.appendChild(row);
      }
    }

    const LIMIT = 20;
    renderVerdictChanges(regressionsList, regressionsCount, diff.regressions || [], LIMIT, "→");
    renderVerdictChanges(improvementsList, improvementsCount, diff.improvements || [], LIMIT, "→ match");

    diffSection.classList.remove("hidden");
  }

  function renderVerdictChanges(listEl, countEl, items, limit, arrowText) {
    countEl.textContent = `(${items.length})`;
    listEl.innerHTML = "";
    if (items.length === 0) {
      listEl.innerHTML = `<p class="text-on-surface-variant italic">Aucun</p>`;
      return;
    }
    const shown = items.slice(0, limit);
    for (const r of shown) {
      const div = document.createElement("div");
      div.className = "text-on-surface-variant";
      // Keep filename truncated visually but preserve full on hover
      div.innerHTML = `
        <span class="inline-block max-w-[260px] truncate align-bottom" title="${r.filename}">${r.filename}</span>
        <span class="mx-2 text-on-surface-variant/60">·</span>
        <span class="text-on-surface">${r.field}</span>
        <span class="mx-2 text-on-surface-variant/60">${r.verdict_a} → ${r.verdict_b}</span>
      `;
      listEl.appendChild(div);
    }
    if (items.length > limit) {
      const more = document.createElement("div");
      more.className = "text-on-surface-variant/70 italic mt-1";
      more.textContent = `… et ${items.length - limit} de plus`;
      listEl.appendChild(more);
    }
  }

  btnDiff.addEventListener("click", submitDiff);
  btnCloseDiff.addEventListener("click", () => diffSection.classList.add("hidden"));

  // Single submit handler: run the eval, then refresh history so the new run
  // appears at the top of the table.
  form.addEventListener("submit", async (event) => {
    await submitEval(event);
    refreshHistory();
  });

  // Initial load
  refreshHistory();
})();
