// ── Extraction de Factures BTP — Frontend JS ──

/**
 * Show a loading spinner, disable a button.
 */
function showLoading(spinnerId, buttonId) {
  const spinner = document.getElementById(spinnerId);
  const btn = document.getElementById(buttonId);
  if (spinner) spinner.classList.remove('hidden');
  if (btn) { btn.disabled = true; btn.classList.add('opacity-50', 'cursor-not-allowed'); }
}

function hideLoading(spinnerId, buttonId) {
  const spinner = document.getElementById(spinnerId);
  const btn = document.getElementById(buttonId);
  if (spinner) spinner.classList.add('hidden');
  if (btn) { btn.disabled = false; btn.classList.remove('opacity-50', 'cursor-not-allowed'); }
}

/**
 * Upload a file to an API endpoint, return JSON.
 */
async function uploadFile(url, file, extraFields = {}) {
  const formData = new FormData();
  formData.append('file', file);
  for (const [key, val] of Object.entries(extraFields)) {
    formData.append(key, val);
  }
  const resp = await fetch(url, { method: 'POST', body: formData });
  if (!resp.ok) throw new Error(`Erreur serveur: ${resp.status}`);
  return resp.json();
}

/**
 * Download an Excel file from the export endpoint.
 */
async function downloadExcel(url, results, filename) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ results }),
  });
  if (!resp.ok) throw new Error(`Erreur export: ${resp.status}`);
  const blob = await resp.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

/**
 * Set a field value with appropriate styling.
 */
function setFieldValue(elementId, value, status) {
  const el = document.getElementById(elementId);
  if (!el) return;

  if (!value || value === 'null' || value === 'None') {
    el.textContent = 'Donnee manquante';
    el.className = el.className.replace(/bg-\S+/g, '').replace(/text-\S+/g, '').trim();
    el.classList.add('text-error', 'italic');
  } else if (status === 'warning') {
    el.textContent = value + ' (a verifier)';
    el.className = el.className.replace(/bg-\S+/g, '').trim();
    el.classList.add('bg-tertiary-fixed', 'text-on-tertiary-fixed-variant');
  } else {
    el.textContent = value;
  }
}

/**
 * Fill all 9 extraction fields from a result object.
 */
function fillFields(prefix, fields, isAvoir) {
  if (!fields) return;
  const aVerifier = fields._a_verifier || [];
  const allKeys = [
    'NUMERO_FACTURE', 'DATE_FACTURE', 'MONTANT_HT', 'TAUX_TVA', 'MONTANT_TTC',
    'NOM_INSTALLATEUR', 'COMMUNE_TRAVAUX', 'CODE_POSTAL', 'ADRESSE_TRAVAUX',
  ];
  for (const key of allKeys) {
    let status = 'ok';
    if (aVerifier.includes(key)) status = 'warning';
    setFieldValue(`${prefix}-${key}`, fields[key], status);
  }
}

/**
 * Populate fournisseur dropdowns from API.
 */
async function loadFournisseurs(selectId) {
  const select = document.getElementById(selectId);
  if (!select) return;
  try {
    const resp = await fetch('/api/fournisseurs');
    const data = await resp.json();
    for (const name of data.fournisseurs) {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name.toUpperCase();
      select.appendChild(opt);
    }
    const defOpt = document.createElement('option');
    defOpt.value = 'DEFAULT';
    defOpt.textContent = 'DEFAULT (generique)';
    select.appendChild(defOpt);
  } catch (e) {
    console.error('Failed to load fournisseurs:', e);
  }
}


// ── PAGE-SPECIFIC LOGIC ──

document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;

  // ── PAGE: /texte ──
  if (path === '/texte') {
    const input = document.getElementById('upload-texte');
    const btnExport = document.getElementById('btn-export-texte');
    let lastResult = null;

    if (input) {
      input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        showLoading('loading-texte', 'btn-export-texte');
        document.getElementById('results-texte')?.classList.add('hidden');
        try {
          const data = await uploadFile('/api/extract-texte', file);
          lastResult = data;
          if (data.error) {
            alert('Erreur: ' + data.error);
          } else {
            fillFields('field', data.fields, data.is_avoir);
            document.getElementById('json-raw-texte').textContent = JSON.stringify(data.fields, null, 2);
            document.getElementById('results-texte')?.classList.remove('hidden');
          }
        } catch (err) {
          alert('Erreur: ' + err.message);
        } finally {
          hideLoading('loading-texte', 'btn-export-texte');
        }
      });
    }

    if (btnExport) {
      btnExport.addEventListener('click', () => {
        if (!lastResult?.fields) return;
        downloadExcel('/api/export-excel', [{
          filename: document.getElementById('upload-texte')?.files[0]?.name || 'facture',
          fields: lastResult.fields,
          installateur: 'gemma2-texte',
          is_avoir: lastResult.is_avoir,
        }], 'extraction.xlsx');
      });
    }
  }

  // ── PAGE: /smart ──
  if (path === '/smart') {
    loadFournisseurs('select-fournisseur-smart');
    const input = document.getElementById('upload-smart');
    const btnExport = document.getElementById('btn-export-smart');
    let lastResult = null;

    if (input) {
      input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const fournisseur = document.getElementById('select-fournisseur-smart')?.value || 'Auto-detect';
        showLoading('loading-smart', 'btn-export-smart');
        document.getElementById('results-smart')?.classList.add('hidden');
        try {
          const data = await uploadFile('/api/extract-smart', file, { fournisseur });
          lastResult = data;
          if (data.error) {
            alert('Erreur: ' + data.error);
          } else {
            const detEl = document.getElementById('detected-fournisseur');
            if (detEl) detEl.textContent = (data.installateur || '?').toUpperCase();

            fillFields('smart-field', data.fields, data.is_avoir);
            document.getElementById('json-raw-smart').textContent = JSON.stringify(data.fields, null, 2);
            document.getElementById('results-smart')?.classList.remove('hidden');
          }
        } catch (err) {
          alert('Erreur: ' + err.message);
        } finally {
          hideLoading('loading-smart', 'btn-export-smart');
        }
      });
    }

    if (btnExport) {
      btnExport.addEventListener('click', () => {
        if (!lastResult?.fields) return;
        downloadExcel('/api/export-excel', [{
          filename: document.getElementById('upload-smart')?.files[0]?.name || 'facture',
          fields: lastResult.fields,
          installateur: lastResult.installateur || '',
          is_avoir: lastResult.is_avoir,
        }], 'extraction_smart.xlsx');
      });
    }
  }

  // ── PAGE: /nouvelle ──
  if (path === '/nouvelle') {
    loadFournisseurs('select-fournisseur-nouvelle');
    const inputFile = document.getElementById('upload-nouvelle');
    const inputZip = document.getElementById('upload-zip-nouvelle');
    const btnExport = document.getElementById('btn-export-nouvelle');
    let batchResults = [];

    // Mode toggle
    const modeUnique = document.getElementById('mode-unique');
    const modeZip = document.getElementById('mode-zip');
    const zoneUnique = document.getElementById('zone-unique');
    const zoneZip = document.getElementById('zone-zip');

    if (modeUnique && modeZip) {
      modeUnique.addEventListener('change', () => {
        if (zoneUnique) zoneUnique.classList.remove('hidden');
        if (zoneZip) zoneZip.classList.add('hidden');
      });
      modeZip.addEventListener('change', () => {
        if (zoneUnique) zoneUnique.classList.add('hidden');
        if (zoneZip) zoneZip.classList.remove('hidden');
      });
    }

    // Single file upload
    if (inputFile) {
      inputFile.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const fournisseur = document.getElementById('select-fournisseur-nouvelle')?.value || 'Auto-detect';
        showLoading('loading-nouvelle', 'btn-export-nouvelle');
        try {
          const data = await uploadFile('/api/extract-ocr', file, { fournisseur });
          batchResults = [{
            filename: file.name,
            fields: data.fields,
            installateur: data.installateur || 'DEFAULT',
            is_avoir: data.is_avoir,
          }];
          renderResultsList('results-nouvelle', batchResults);
          updateStats(batchResults);
        } catch (err) {
          alert('Erreur: ' + err.message);
        } finally {
          hideLoading('loading-nouvelle', 'btn-export-nouvelle');
        }
      });
    }

    // ZIP upload
    if (inputZip) {
      inputZip.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        showLoading('loading-nouvelle', 'btn-export-nouvelle');
        try {
          const data = await uploadFile('/api/batch', file);
          batchResults = data.results;
          renderResultsList('results-nouvelle', batchResults);
          updateStats(batchResults);
        } catch (err) {
          alert('Erreur: ' + err.message);
        } finally {
          hideLoading('loading-nouvelle', 'btn-export-nouvelle');
        }
      });
    }

    if (btnExport) {
      btnExport.addEventListener('click', () => {
        if (!batchResults.length) return;
        downloadExcel('/api/export-excel', batchResults, 'extraction_nouvelle.xlsx');
      });
    }
  }

  // ── PAGE: /batch ──
  if (path === '/batch') {
    const input = document.getElementById('upload-batch');
    const btnExport = document.getElementById('btn-export-batch');
    let batchResults = [];

    if (input) {
      input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        showLoading('loading-batch', 'btn-export-batch');
        try {
          const data = await uploadFile('/api/batch', file);
          batchResults = data.results;
          renderResultsList('results-batch', batchResults);
          updateBatchStats(batchResults);
          renderBatchTable('table-preview-batch', batchResults);
        } catch (err) {
          alert('Erreur: ' + err.message);
        } finally {
          hideLoading('loading-batch', 'btn-export-batch');
        }
      });
    }

    if (btnExport) {
      btnExport.addEventListener('click', () => {
        if (!batchResults.length) return;
        downloadExcel('/api/export-excel-multi', batchResults, 'extraction_multi.xlsx');
      });
    }
  }
});


// ── BATCH RENDERING HELPERS ──

function renderResultsList(containerId, results) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';

  for (const res of results) {
    const isError = res.installateur === 'ERREUR';
    const isAvoir = res.is_avoir;

    const div = document.createElement('div');
    div.className = isAvoir
      ? 'bg-tertiary-fixed/30 rounded-xl overflow-hidden border-l-4 border-tertiary mb-2'
      : isError
        ? 'bg-surface-container-lowest rounded-xl overflow-hidden border-l-4 border-error mb-2'
        : 'bg-surface-container-lowest rounded-xl overflow-hidden mb-2';

    const icon = isError ? 'error' : 'check_circle';
    const iconColor = isError ? 'text-error' : 'text-green-600';
    const typeLabel = isAvoir ? 'AVOIR' : 'FACTURE';
    const typeBg = isAvoir ? 'bg-tertiary-fixed text-on-tertiary-fixed-variant' : 'bg-blue-50 text-blue-700';

    div.innerHTML = `
      <div class="p-4 flex items-center justify-between hover:bg-surface-container-low cursor-pointer transition-colors">
        <div class="flex items-center gap-4">
          <span class="material-symbols-outlined ${iconColor}" style="font-variation-settings: 'FILL' 1;">${icon}</span>
          <div>
            <div class="font-bold text-sm">${res.filename}</div>
            <div class="text-xs text-on-surface-variant">Fournisseur: <span class="font-semibold">${(res.installateur || '?').toUpperCase()}</span></div>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <span class="text-[10px] px-2 py-0.5 rounded ${typeBg} font-bold">${typeLabel}</span>
          ${res.fields?.MONTANT_TTC ? `<span class="font-headline font-bold text-sm ${isAvoir ? 'text-error' : ''}">${res.fields.MONTANT_TTC} &euro;</span>` : ''}
        </div>
      </div>
    `;
    container.appendChild(div);
  }
}

function updateStats(results) {
  const ok = results.filter(r => r.installateur !== 'ERREUR').length;
  const errors = results.length - ok;
  const el1 = document.getElementById('stat-extraites');
  const el2 = document.getElementById('stat-erreurs');
  if (el1) el1.textContent = `${ok}/${results.length}`;
  if (el2) el2.textContent = errors;
}

function updateBatchStats(results) {
  const ok = results.filter(r => r.installateur !== 'ERREUR').length;
  const errors = results.length - ok;
  const installateurs = new Set(results.filter(r => r.installateur !== 'ERREUR').map(r => r.installateur)).size;
  const preCalc = results.filter(r => r.source === 'OCR pre-calcule').length;
  const live = results.filter(r => r.source === 'DocTR live').length;

  const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  setText('stat-traitees', `${ok} / ${results.length}`);
  setText('stat-ocr-precalc', preCalc);
  setText('stat-doctr-live', live);
  setText('stat-installateurs', installateurs);
  setText('stat-erreurs-batch', errors);

  // Update progress bar
  const pct = results.length > 0 ? 100 : 0;
  const bar = document.getElementById('progress-batch');
  const txt = document.getElementById('progress-text-batch');
  if (bar) bar.style.width = pct + '%';
  if (txt) txt.textContent = pct + '%';
}

function renderBatchTable(containerId, results) {
  const container = document.getElementById(containerId);
  if (!container) return;

  let html = `<table class="w-full text-left border-collapse">
    <thead><tr class="bg-surface-container-low">
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Fichier</th>
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Date</th>
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Fournisseur</th>
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Type</th>
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">HT</th>
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">TTC</th>
    </tr></thead><tbody class="divide-y divide-outline-variant/10">`;

  for (const res of results) {
    const isAvoir = res.is_avoir;
    const typeBg = isAvoir ? 'bg-tertiary-fixed text-on-tertiary-fixed-variant' : 'bg-blue-50 text-blue-700';
    const amountClass = isAvoir ? 'text-error' : '';
    html += `<tr class="hover:bg-surface-container-low/30">
      <td class="px-6 py-4 font-mono text-xs">${res.filename}</td>
      <td class="px-6 py-4 text-xs">${res.fields?.DATE_FACTURE || '-'}</td>
      <td class="px-6 py-4 text-xs font-semibold">${(res.installateur || '?').toUpperCase()}</td>
      <td class="px-6 py-4"><span class="text-[10px] px-2 py-0.5 rounded ${typeBg} font-bold">${isAvoir ? 'AVOIR' : 'FACTURE'}</span></td>
      <td class="px-6 py-4 font-headline text-xs font-bold ${amountClass}">${res.fields?.MONTANT_HT || '-'}</td>
      <td class="px-6 py-4 font-headline text-xs font-bold ${amountClass}">${res.fields?.MONTANT_TTC || '-'}</td>
    </tr>`;
  }
  html += '</tbody></table>';
  container.innerHTML = html;
}
