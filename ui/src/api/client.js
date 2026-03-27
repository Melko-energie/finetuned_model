const BASE_URL = "http://localhost:8000/api";

async function fetchJSON(url, options = {}) {
  const res = await fetch(`${BASE_URL}${url}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Erreur serveur");
  }
  return res.json();
}

async function fetchBlob(url, options = {}) {
  const res = await fetch(`${BASE_URL}${url}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Erreur serveur");
  }
  return res.blob();
}

// Upload a file and extract with Gemma2 Texte (tab 1 — uses pre-computed OCR)
export async function extractTexte(file) {
  const form = new FormData();
  form.append("file", file);
  return fetchJSON("/extract-texte", { method: "POST", body: form });
}

// Upload a file and extract with Gemma2 Smart (tab 2 — uses pre-computed OCR)
export async function extractSmart(file, fournisseur = "Auto-detect") {
  const form = new FormData();
  form.append("file", file);
  form.append("fournisseur", fournisseur);
  return fetchJSON("/extract-smart", { method: "POST", body: form });
}

// Upload a file and run full pipeline: OCR DocTR + Gemma2 Smart (tab 3)
export async function ocrExtract(file, fournisseur = "Auto-detect") {
  const form = new FormData();
  form.append("file", file);
  form.append("fournisseur", fournisseur);
  return fetchJSON("/ocr-extract", { method: "POST", body: form });
}

// Upload a ZIP and run batch processing (tab 4)
export async function batchZip(file) {
  const form = new FormData();
  form.append("file", file);
  return fetchJSON("/batch-zip", { method: "POST", body: form });
}

// Get list of available installateurs
export async function getInstallateurs() {
  return fetchJSON("/installateurs");
}

// Export results as Excel (returns blob)
export async function exportExcel(results) {
  return fetchBlob("/export-excel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(results),
  });
}

// Export batch results as multi-sheet Excel (returns blob)
export async function exportExcelMulti(results) {
  return fetchBlob("/export-excel-multi", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(results),
  });
}

// Get file preview URL (for uploaded files stored temporarily)
export function getPreviewUrl(fileId) {
  return `${BASE_URL}/preview/${fileId}`;
}
