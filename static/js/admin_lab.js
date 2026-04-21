// Admin page — CRUD UI on /api/admin/prompts
(function () {
  "use strict";

  const API = "/api/admin/prompts";
  const KEY_PATTERN = /^[a-z][a-z0-9_]*$/;
  const RESERVED_KEYS = new Set(["texte", "default"]);

  const state = {
    items: [],          // from GET /api/admin/prompts
    currentKey: null,
    isNew: false,
    isDirty: false,
    lastLoaded: { detecter: "", prompt: "" },  // snapshot to detect dirty
  };

  // ─── DOM refs ───
  const $ = (id) => document.getElementById(id);
  const listContainer = $("list-container");
  const listCount = $("list-count");
  const searchInput = $("search-input");
  const emptyState = $("empty-state");
  const editor = $("editor");
  const inputKey = $("input-key");
  const inputDetecter = $("input-detecter");
  const inputPrompt = $("input-prompt");
  const detecterSection = $("detecter-section");
  const typeBadge = $("type-badge");
  const dirtyDot = $("dirty-dot");
  const btnNew = $("btn-new");
  const btnSave = $("btn-save");
  const btnCancel = $("btn-cancel");
  const btnDelete = $("btn-delete");
  const toast = $("toast");
  const modalDelete = $("modal-delete");
  const modalDeleteKey = $("modal-delete-key");
  const btnModalCancel = $("btn-modal-cancel");
  const btnModalConfirm = $("btn-modal-confirm");

  // Generate-from-samples modal (chantier 4.3)
  const btnGenerate = $("btn-generate");
  const modalGenerate = $("modal-generate");
  const genForm = $("gen-form");
  const genKey = $("gen-key");
  const genPdfs = $("gen-pdfs");
  const genPdfsList = $("gen-pdfs-list");
  const genTruth = $("gen-truth");
  const btnGenSubmit = $("btn-gen-submit");
  const btnGenCancel = $("btn-gen-cancel");
  const genLoading = $("gen-loading");

  // ─── Toast helper ───
  let toastTimer = null;
  function showToast(message, kind) {
    toast.textContent = message;
    toast.className = "fixed bottom-6 right-6 px-4 py-3 rounded-lg shadow-lg text-white text-sm font-medium z-50";
    toast.classList.add(kind === "error" ? "bg-error" : "bg-primary");
    toast.classList.remove("hidden");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.add("hidden"), 3500);
  }

  // ─── API helpers ───
  async function api(method, path, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    let data = null;
    try { data = await res.json(); } catch (_) { /* non-json */ }
    if (!res.ok) {
      const detail = (data && (data.detail || data.error)) || `HTTP ${res.status}`;
      const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      err.status = res.status;
      throw err;
    }
    return data;
  }

  // ─── Dirty tracking ───
  function markDirty() {
    state.isDirty = true;
    dirtyDot.classList.remove("hidden");
  }
  function clearDirty() {
    state.isDirty = false;
    dirtyDot.classList.add("hidden");
  }
  function confirmDiscardChanges() {
    if (!state.isDirty) return true;
    return window.confirm("Modifications non sauvegardées. Continuer et les perdre ?");
  }

  // ─── Detecter serialization: list <-> textarea ───
  function detecterToText(arr) {
    return (arr || []).join("\n");
  }
  function detecterFromText(text) {
    return text.split("\n").map((s) => s.trim()).filter((s) => s.length > 0);
  }

  // ─── List rendering ───
  function renderList(filter) {
    const q = (filter || "").toLowerCase();
    const filtered = state.items.filter((it) => it.key.toLowerCase().includes(q));
    const suppliers = filtered.filter((it) => it.type === "supplier");
    const system = filtered.filter((it) => it.type === "system");

    listCount.textContent = state.items.length;

    const parts = [];
    if (suppliers.length > 0) {
      parts.push(`<div><p class="text-[10px] font-bold text-on-surface-variant/70 uppercase tracking-widest mb-1 px-1">Fournisseurs</p><ul class="space-y-0.5">`);
      for (const it of suppliers) parts.push(renderListItem(it));
      parts.push(`</ul></div>`);
    }
    if (system.length > 0) {
      parts.push(`<div><p class="text-[10px] font-bold text-on-surface-variant/70 uppercase tracking-widest mb-1 px-1">Système</p><ul class="space-y-0.5">`);
      for (const it of system) parts.push(renderListItem(it));
      parts.push(`</ul></div>`);
    }
    if (parts.length === 0) {
      listContainer.innerHTML = `<p class="text-xs text-on-surface-variant italic px-1">Aucun résultat.</p>`;
      return;
    }
    listContainer.innerHTML = parts.join("");
    for (const li of listContainer.querySelectorAll("li[data-key]")) {
      li.addEventListener("click", () => selectPrompt(li.dataset.key));
    }
  }
  function renderListItem(it) {
    const active = it.key === state.currentKey && !state.isNew;
    const classes = active
      ? "bg-white text-[#003d9b] font-semibold border-l-4 border-[#003d9b]"
      : "text-slate-700 hover:bg-slate-200/40";
    return `<li data-key="${it.key}" class="cursor-pointer px-3 py-2 rounded text-sm ${classes}">
      <span class="font-mono">${it.key}</span>
      <span class="ml-2 text-[10px] text-on-surface-variant">${it.detecter_count} kw · ${it.prompt_chars} ch</span>
    </li>`;
  }

  // ─── Editor state ───
  function showEditor() {
    emptyState.classList.add("hidden");
    editor.classList.remove("hidden");
  }
  function hideEditor() {
    emptyState.classList.remove("hidden");
    editor.classList.add("hidden");
  }

  async function selectPrompt(key) {
    if (!confirmDiscardChanges()) return;
    try {
      const data = await api("GET", `${API}/${encodeURIComponent(key)}`);
      state.currentKey = key;
      state.isNew = false;
      fillForm(data);
      renderList(searchInput.value);
      showEditor();
    } catch (e) {
      showToast(`Erreur chargement : ${e.message}`, "error");
    }
  }

  function fillForm(data) {
    inputKey.value = data.key;
    inputKey.disabled = true;
    inputDetecter.value = detecterToText(data.detecter);
    inputPrompt.value = data.prompt;

    const isSystem = data.type === "system";
    typeBadge.textContent = data.type;
    typeBadge.classList.toggle("bg-tertiary-fixed", isSystem);
    typeBadge.classList.toggle("bg-secondary-fixed", !isSystem);

    // Hide detecter section for `texte` (the generic prompt has no supplier detection)
    detecterSection.classList.toggle("hidden", data.key === "texte");

    // Delete button: disabled for reserved keys
    btnDelete.disabled = RESERVED_KEYS.has(data.key);
    btnDelete.classList.toggle("hidden", state.isNew);

    state.lastLoaded = {
      detecter: inputDetecter.value,
      prompt: inputPrompt.value,
    };
    clearDirty();
  }

  function startNew() {
    if (!confirmDiscardChanges()) return;
    state.currentKey = null;
    state.isNew = true;
    inputKey.disabled = false;
    inputKey.value = "";
    inputDetecter.value = "";
    inputPrompt.value = "";
    typeBadge.textContent = "nouveau";
    typeBadge.className = "inline-block mt-2 text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-tertiary-container text-on-tertiary-container";
    detecterSection.classList.remove("hidden");
    btnDelete.classList.add("hidden");
    state.lastLoaded = { detecter: "", prompt: "" };
    clearDirty();
    renderList(searchInput.value);
    showEditor();
    inputKey.focus();
  }

  // ─── Save ───
  async function save() {
    const promptText = inputPrompt.value;
    if (!promptText.trim()) {
      showToast("Le prompt ne peut pas être vide.", "error");
      return;
    }
    const detecter = detecterFromText(inputDetecter.value);

    btnSave.disabled = true;
    try {
      if (state.isNew) {
        const key = inputKey.value.trim();
        if (!KEY_PATTERN.test(key)) {
          showToast("Clé invalide : minuscules, chiffres et _ uniquement, démarre par une lettre.", "error");
          return;
        }
        if (RESERVED_KEYS.has(key)) {
          showToast(`'${key}' est une clé réservée.`, "error");
          return;
        }
        const created = await api("POST", API, { key, detecter, prompt: promptText });
        state.isNew = false;
        state.currentKey = created.key;
        await refreshList();
        fillForm(created);
        showToast(`Prompt '${created.key}' créé.`, "ok");
      } else {
        const key = state.currentKey;
        const updated = await api("PUT", `${API}/${encodeURIComponent(key)}`, { detecter, prompt: promptText });
        await refreshList();
        fillForm(updated);
        showToast(`Prompt '${key}' sauvegardé.`, "ok");
      }
    } catch (e) {
      showToast(`Erreur : ${e.message}`, "error");
    } finally {
      btnSave.disabled = false;
    }
  }

  async function refreshList() {
    const data = await api("GET", API);
    state.items = data.prompts || [];
    renderList(searchInput.value);
  }

  // ─── Delete ───
  function openDeleteModal() {
    if (!state.currentKey || RESERVED_KEYS.has(state.currentKey)) return;
    modalDeleteKey.textContent = state.currentKey;
    modalDelete.classList.remove("hidden");
  }
  function closeDeleteModal() {
    modalDelete.classList.add("hidden");
  }
  async function confirmDelete() {
    const key = state.currentKey;
    closeDeleteModal();
    try {
      await api("DELETE", `${API}/${encodeURIComponent(key)}`);
      state.currentKey = null;
      state.isNew = false;
      clearDirty();
      hideEditor();
      await refreshList();
      showToast(`Prompt '${key}' supprimé.`, "ok");
    } catch (e) {
      showToast(`Erreur suppression : ${e.message}`, "error");
    }
  }

  // ─── Cancel: reload from server to discard changes ───
  async function cancelEdit() {
    if (state.isNew) {
      state.isNew = false;
      state.currentKey = null;
      clearDirty();
      hideEditor();
      renderList(searchInput.value);
      return;
    }
    if (!state.currentKey) return;
    if (!state.isDirty) return;
    if (!window.confirm("Annuler les modifications et recharger depuis le serveur ?")) return;
    try {
      const data = await api("GET", `${API}/${encodeURIComponent(state.currentKey)}`);
      fillForm(data);
    } catch (e) {
      showToast(`Erreur rechargement : ${e.message}`, "error");
    }
  }

  // ─── Generate-from-samples flow (chantier 4.3) ───
  function openGenerateModal() {
    if (!confirmDiscardChanges()) return;
    genKey.value = "";
    genPdfs.value = "";
    genTruth.value = "";
    genPdfsList.innerHTML = "";
    genLoading.classList.add("hidden");
    btnGenSubmit.disabled = false;
    modalGenerate.classList.remove("hidden");
    setTimeout(() => genKey.focus(), 50);
  }
  function closeGenerateModal() {
    modalGenerate.classList.add("hidden");
  }
  function updatePdfsList() {
    const files = Array.from(genPdfs.files || []);
    if (files.length === 0) {
      genPdfsList.innerHTML = "";
      return;
    }
    genPdfsList.innerHTML = files.map(f =>
      `<li>• <span class="font-mono">${f.name}</span> <span class="text-on-surface-variant/70">(${Math.round(f.size / 1024)} KB)</span></li>`
    ).join("");
  }
  async function submitGenerate(event) {
    event.preventDefault();
    const key = genKey.value.trim();
    const pdfs = Array.from(genPdfs.files || []);
    const truth = genTruth.files && genTruth.files[0];

    if (!KEY_PATTERN.test(key)) {
      showToast("Clé invalide : minuscules, chiffres, _ seulement, commence par une lettre.", "error");
      return;
    }
    if (RESERVED_KEYS.has(key)) {
      showToast(`'${key}' est une clé réservée.`, "error");
      return;
    }
    if (pdfs.length < 2) {
      showToast("Dépose au moins 2 factures échantillons.", "error");
      return;
    }
    if (pdfs.length > 5) {
      showToast("Maximum 5 factures échantillons.", "error");
      return;
    }
    if (!truth) {
      showToast("Fournis le fichier Excel ground truth.", "error");
      return;
    }

    const fd = new FormData();
    fd.append("key", key);
    for (const pdf of pdfs) fd.append("pdfs", pdf);
    fd.append("truth_xlsx", truth);

    btnGenSubmit.disabled = true;
    genLoading.classList.remove("hidden");
    try {
      const res = await fetch("/api/admin/prompts/generate", { method: "POST", body: fd });
      let data = null;
      try { data = await res.json(); } catch (_) { /* non-json */ }
      if (!res.ok) {
        const detail = (data && (data.detail || data.error)) || `HTTP ${res.status}`;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      closeGenerateModal();
      loadDraft(data);
      showToast(`Brouillon généré pour '${data.key}' — relis et sauvegarde.`, "ok");
    } catch (e) {
      showToast(`Erreur génération : ${e.message}`, "error");
    } finally {
      btnGenSubmit.disabled = false;
      genLoading.classList.add("hidden");
    }
  }

  function loadDraft(draft) {
    state.currentKey = null;
    state.isNew = true;
    inputKey.disabled = false;
    inputKey.value = draft.key;
    inputDetecter.value = detecterToText(draft.detecter);
    inputPrompt.value = draft.prompt;
    typeBadge.textContent = "brouillon";
    typeBadge.className = "inline-block mt-2 text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-tertiary-container text-on-tertiary-container";
    detecterSection.classList.remove("hidden");
    btnDelete.classList.add("hidden");
    state.lastLoaded = { detecter: inputDetecter.value, prompt: inputPrompt.value };
    markDirty();
    renderList(searchInput.value);
    showEditor();
  }

  // ─── Event wiring ───
  function onTextareaChange() {
    // New prompts (from "+ Nouveau" or from a generated draft) are always
    // dirty until saved — there's no server-side baseline to compare against.
    if (state.isNew) {
      if (!state.isDirty) markDirty();
      return;
    }
    const cur = { detecter: inputDetecter.value, prompt: inputPrompt.value };
    const changed = cur.detecter !== state.lastLoaded.detecter || cur.prompt !== state.lastLoaded.prompt;
    if (changed && !state.isDirty) markDirty();
    if (!changed && state.isDirty) clearDirty();
  }

  inputDetecter.addEventListener("input", onTextareaChange);
  inputPrompt.addEventListener("input", onTextareaChange);
  inputKey.addEventListener("input", () => { if (state.isNew) markDirty(); });
  btnNew.addEventListener("click", startNew);
  btnSave.addEventListener("click", save);
  btnCancel.addEventListener("click", cancelEdit);
  btnDelete.addEventListener("click", openDeleteModal);
  btnModalCancel.addEventListener("click", closeDeleteModal);
  btnModalConfirm.addEventListener("click", confirmDelete);
  searchInput.addEventListener("input", (e) => renderList(e.target.value));

  // Generate-from-samples wiring (chantier 4.3)
  btnGenerate.addEventListener("click", openGenerateModal);
  btnGenCancel.addEventListener("click", closeGenerateModal);
  genPdfs.addEventListener("change", updatePdfsList);
  genForm.addEventListener("submit", submitGenerate);

  window.addEventListener("beforeunload", (e) => {
    if (state.isDirty) {
      e.preventDefault();
      e.returnValue = "";
    }
  });

  // ─── Init ───
  refreshList().catch((e) => {
    listContainer.innerHTML = `<p class="text-xs text-error px-1">Erreur de chargement : ${e.message}</p>`;
  });
})();
