# Progression SSE sur l'éval — Design (chantier 5.4)

**Date** : 2026-04-21
**Chantier** : 5.4 (progress streaming pendant les longs évals)
**Prérequis** : 5.1 + 5.2 + 5.3 + chantier 2.6 (endpoint sync existant)
**Statut** : validé, implémentation en cours

---

## Objectif

Remplacer le spinner immobile de `/eval-lab` par une vraie barre de progression qui reflète l'avancement PDF par PDF en temps réel. Même mécanisme que `/batch` (déjà SSE).

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Endpoint | Nouveau `POST /api/admin/eval/stream` | Ne casse pas le endpoint JSON existant. Les deux coexistent. |
| Protocole | Server-Sent Events (`text/event-stream`) | Déjà utilisé par `/api/batch`, pattern connu du projet. |
| Refactor runner | Extraire `iter_run_eval()` générateur, garder `run_eval()` en wrapper | Même pattern que `iter_batch_zip` / `process_batch_zip`. `run_eval()` drain le générateur → zéro régression CLI. |
| Format events | `{type: init \| progress \| done \| error, ...}` | Simple et extensible. |
| UI : fallback | L'ancien endpoint JSON reste disponible, pas touché | Safety net en cas de bug SSE. |
| Client SSE | `fetch()` + `ReadableStream` (EventSource ne gère pas POST multipart) | Même technique que `static/js/app.js` pour `/batch`. |
| Barre de progression | Pourcentage + barre + compteur + dernier PDF affiché | Informatif sans être bruyant. |

## Contrat SSE

`POST /api/admin/eval/stream` (multipart : `pdfs_zip`, `truth_xlsx`) → `text/event-stream`

Events :

```json
{ "type": "init",     "total": 42, "pdfs_dir": "...", "truth_file": "..." }
{ "type": "progress", "index": 1, "total": 42, "filename": "S1120630.pdf",
                      "installateur": "a2m", "verdicts": {...}, "error": null }
...
{ "type": "done",     "result": {...full result dict...},
                      "run_id": "2026-04-21_172030",
                      "download_url": "/api/admin/eval/runs/.../download" }
```

Erreur en cours de stream :

```json
{ "type": "error", "error": "message explicite" }
```

Les erreurs fatales **avant** le démarrage du stream (ZIP cassé, Excel sans feuille attendue) restent gérées par du 400 JSON synchrone (avant le premier SSE envoyé).

## Refactor `core/eval/runner.py`

Avant :
```python
def run_eval(pdfs_dir, truth_file) -> dict:
    # 1. load truth
    # 2. for each row: extract + compare + append
    # 3. aggregate + return
```

Après :
```python
def iter_run_eval(pdfs_dir, truth_file):
    """Generator. Yields events (init, progress, done).

    The 'done' event carries the full result dict (shape identical to what
    run_eval() returned). Callers that want a single value drain the
    generator.
    """
    # init event
    yield {"type": "init", "total": ..., ...}

    per_pdf = []
    for idx, row in enumerate(truth_rows):
        # extract + compare + append
        yield {"type": "progress", "index": idx+1, "total": ..., ...}

    # final aggregate
    result = {"meta": ..., "per_pdf": per_pdf,
              "metrics": aggregate(per_pdf),
              "metrics_by_supplier": aggregate_by_supplier(per_pdf)}
    yield {"type": "done", "result": result}


def run_eval(pdfs_dir, truth_file) -> dict:
    """Wrapper that drains iter_run_eval and returns the final result."""
    final = None
    for event in iter_run_eval(pdfs_dir, truth_file):
        if event["type"] == "done":
            final = event["result"]
    return final
```

La CLI (`scripts/run_eval.py`) et l'endpoint JSON existant (`POST /api/admin/eval`) continuent d'appeler `run_eval()` sans modification.

## Endpoint streaming

```python
@router.post("/stream")
async def run_evaluation_stream(
    pdfs_zip: UploadFile = File(...),
    truth_xlsx: UploadFile = File(...),
):
    # Same pre-checks as /api/admin/eval (extension, ZIP validity)
    # fail-fast 400 before ANY event is emitted

    zip_bytes = await pdfs_zip.read()
    truth_bytes = await truth_xlsx.read()

    def event_stream():
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            pdfs_dir = tmp / "pdfs"
            pdfs_dir.mkdir()
            try:
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                    zf.extractall(pdfs_dir)
            except zipfile.BadZipFile:
                yield f"data: {json.dumps({'type': 'error', 'error': 'pdfs_zip is not a valid ZIP archive'})}\n\n"
                return

            truth_path = tmp / "truth.xlsx"
            truth_path.write_bytes(truth_bytes)

            try:
                for event in iter_run_eval(pdfs_dir, truth_path):
                    if event["type"] == "done":
                        result = event["result"]
                        if result["meta"]["matched"] > 0:
                            run_dir = save_run(result)
                            dump_excel(result, run_dir / "report.xlsx")
                            event["run_id"] = run_dir.name
                            event["download_url"] = f"/api/admin/eval/runs/{run_dir.name}/download"
                    yield f"data: {json.dumps(event, default=str, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

## UI `/eval-lab`

### Template — loading block enrichi

```html
<div id="loading" class="hidden p-4 bg-tertiary-fixed/40 rounded-xl space-y-3">
  <div class="flex items-center gap-3">
    <span class="material-symbols-outlined text-tertiary animate-spin">progress_activity</span>
    <div class="flex-1 text-sm text-on-surface">
      <div class="font-medium">Évaluation en cours…</div>
      <div id="progress-summary" class="text-xs text-on-surface-variant">Initialisation…</div>
    </div>
    <div id="progress-percent" class="font-mono text-lg font-bold">0%</div>
  </div>
  <div class="w-full h-2 bg-surface-container-high rounded-full overflow-hidden">
    <div id="progress-bar" class="h-full bg-primary transition-all duration-200" style="width: 0%"></div>
  </div>
  <div id="progress-last" class="text-[11px] text-on-surface-variant font-mono truncate"></div>
</div>
```

### JS — remplacer le POST actuel par un SSE reader

```js
async function submitEval(event) {
    event.preventDefault();
    // ... existing validation ...
    const fd = new FormData();
    fd.append("pdfs_zip", zip);
    fd.append("truth_xlsx", truth);

    state.isRunning = true;
    btnRun.disabled = true;
    loading.classList.remove("hidden");
    resetProgress();
    results.classList.add("hidden");

    try {
        const res = await fetch("/api/admin/eval/stream", { method: "POST", body: fd });
        if (!res.ok) {
            const txt = await res.text();
            throw new Error(`HTTP ${res.status}: ${txt.slice(0, 200)}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            let sep;
            while ((sep = buffer.indexOf("\n\n")) !== -1) {
                const chunk = buffer.slice(0, sep);
                buffer = buffer.slice(sep + 2);
                const line = chunk.trim();
                if (!line.startsWith("data: ")) continue;
                const event = JSON.parse(line.slice(6));
                handleEvent(event);
            }
        }
    } catch (e) {
        showToast(`Erreur éval : ${e.message}`, "error");
    } finally {
        state.isRunning = false;
        btnRun.disabled = false;
        loading.classList.add("hidden");
    }
}

function handleEvent(ev) {
    if (ev.type === "init") {
        state.total = ev.total;
        progressSummary.textContent = `0 / ${ev.total} PDFs traités`;
    } else if (ev.type === "progress") {
        const pct = Math.round((ev.index / ev.total) * 100);
        progressBar.style.width = pct + "%";
        progressPercent.textContent = pct + "%";
        progressSummary.textContent = `${ev.index} / ${ev.total} PDFs traités`;
        const short = ev.filename.length > 60 ? "…" + ev.filename.slice(-59) : ev.filename;
        progressLast.textContent = `${short}   (${ev.installateur || "?"})`;
    } else if (ev.type === "done") {
        renderResults({ run_id: ev.run_id, result: ev.result, download_url: ev.download_url });
        showToast(`Run '${ev.run_id}' terminé.`, "ok");
    } else if (ev.type === "error") {
        showToast(`Erreur serveur : ${ev.error}`, "error");
    }
}
```

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | `iter_run_eval` avec 2 samples (mocks) | yield 1 init + 2 progress + 1 done avec result.meta.matched == 2 |
| 2 | `run_eval` wrapper retourne le même dict qu'avant | Forme inchangée (tests existants 2.1 passent toujours) |
| 3 | Endpoint `/api/admin/eval/stream` : réponse `Content-Type: text/event-stream` | OK |
| 4 | Endpoint streaming avec mocks : stream contient init + N progress + done | OK |
| 5 | Endpoint streaming avec ZIP corrompu : stream envoie un seul event `{type: error, ...}` | OK |
| 6 | Endpoint JSON existant `/api/admin/eval` toujours fonctionnel | OK |
| 7 | `/eval-lab` a les nouveaux DOM IDs (progress-bar, progress-percent, progress-summary, progress-last) | OK |
| 8 | `eval_lab.js` contient `handleEvent` et parse SSE | OK |
| 9 | Aucune régression | Tous 200 |

## Hors scope

- Annulation d'un eval en cours côté client (cancel button)
- Reconnexion automatique si la connexion tombe
- Persistance côté serveur du dernier event pour reprise
