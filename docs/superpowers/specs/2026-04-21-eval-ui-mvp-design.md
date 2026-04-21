# UI évaluation MVP — Design (chantier 5.1)

**Date** : 2026-04-21
**Chantier** : 5.1 (page `/eval-lab`, lancer un run + voir les métriques)
**Prérequis** : chantier 2 complet (API REST eval déjà en place)
**Statut** : validé, implémentation en cours

---

## Objectif

Permettre au métier de lancer une évaluation depuis le navigateur : upload d'un ZIP de PDFs + d'un Excel ground truth → barre de progression → affichage des métriques par champ et par fournisseur → bouton pour télécharger le rapport XLSX détaillé.

**Backend zéro** : tous les endpoints nécessaires (`POST /api/admin/eval`, `GET /api/admin/eval/runs/{id}/download`) sont déjà livrés en chantier 2.6. 5.1 est purement frontend.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| URL | `/eval-lab` | Aligné avec la convention `lab` de chantier 4. Séparé de `/admin-lab` parce que le domaine est distinct (prompts vs eval). |
| Entrée sidebar | "Éval Lab" avec icône `analytics` | Discoverable à côté de Admin Lab. |
| Layout | Linéaire top-down (upload → loading → results) | Pas de master-detail ni de tabs ; simple pour un MVP. |
| Upload | Deux inputs file séparés (ZIP + XLSX), pas de drag-drop | Cohérent avec `/admin-lab/generate`. Enhancement plus tard. |
| Loading state | Spinner + texte "~5-10 min, selon le nombre de PDFs" | Les évals réels sur 50-100 PDFs prennent longtemps. L'utilisateur doit comprendre. |
| Affichage résultats | Section qui apparaît sous l'upload, avec 3 blocs : métadonnées, per-field (barres + %), per-supplier (triés ASC) | Calqué sur la sortie terminal de `run_eval.py` — cohérence mentale. |
| Téléchargement XLSX | Bouton dans le bloc résultats → `GET /api/admin/eval/runs/{id}/download` | Même palette que les autres "Exporter vers Excel". |

## Conception

### Structure de fichiers

```
templates/eval_lab.html      ← nouveau
static/js/eval_lab.js        ← nouveau
main.py                      ← + GET /eval-lab route
templates/base.html          ← + sidebar entry "Éval Lab"
```

Aucune modif sur `admin_lab.html` / `admin.js` / `admin_lab.js` / les endpoints backend.

### Layout

```
┌──────────────────────────────────────────────┐
│  Évaluation (lab)                            │
│                                              │
│  Upload :                                    │
│    [ZIP de PDFs]                             │
│    [Excel ground truth]                      │
│    [Lancer l'évaluation]                     │
│                                              │
│  (loading state avec spinner + description)  │
│                                              │
│  (section résultats cachée tant qu'aucun run)│
│  ─────────────────────────────────────────   │
│    ✓ Run #2026-04-21_172030                  │
│    Dataset: X PDFs matched, Y missing        │
│    Model: gemma2:9b, durée: 8m 14s           │
│                                              │
│    Global micro: 78.2%  macro: 73.4%         │
│                                              │
│    Per-field:                                │
│    NUMERO_FACTURE    ████████  82.1%         │
│    DATE_FACTURE      ██████    61.9%         │
│    ...                                       │
│                                              │
│    Per-supplier (pires en premier):          │
│    unknown  ░░░░░  23.5%  (8 PDFs)           │
│    dila     ███░░  42.2%  (5 PDFs)           │
│    ...                                       │
│                                              │
│    [Télécharger rapport Excel]               │
│    (slot réservé 5.3 : [Comparer avec...])   │
└──────────────────────────────────────────────┘
```

### Contrat JS (`eval_lab.js`)

```js
const state = {
  currentRun: null,   // full result dict from POST /api/admin/eval
  isRunning: false,
};

function submitEval(event) {
  // 1. validate inputs present
  // 2. POST /api/admin/eval with FormData(pdfs_zip, truth_xlsx)
  // 3. toggle loading
  // 4. on success : state.currentRun = body.result; renderResults()
  // 5. on error : toast
}

function renderResults() {
  // Populates:
  //  - #run-id, #run-meta (matched, missing, model, duration)
  //  - #global-micro, #global-macro
  //  - #per-field-table (loop ALL_FIELD_KEYS client-side too)
  //  - #per-supplier-list (sorted by accuracy ASC)
  //  - #btn-download → href = result.download_url
}
```

### Couleurs (barres par champ, pastilles par fournisseur)

Mêmes seuils que chantier 2.4 (feu tricolore) et 4.4 (self-test) :
- ≥90 % vert
- 60-90 % orange
- <60 % rouge

Helper `accClass(acc)` partagé par copier-coller (pas de module JS commun pour garder la page autonome).

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | `GET /eval-lab` | 200 avec tous les IDs DOM attendus (`form-eval`, `input-pdfs-zip`, `input-truth-xlsx`, `btn-run`, `loading`, `results`, `run-id`, `global-micro`, `per-field-table`, `per-supplier-list`, `btn-download`) |
| 2 | `/eval-lab` référence `eval_lab.js`, pas `admin*.js` | OK |
| 3 | JS syntaxiquement valide (braces/parens balanced) | OK |
| 4 | Sidebar contient l'entrée "Éval Lab" | OK |
| 5 | `/admin` et `/admin-lab` ne référencent pas `eval_lab.js` | OK |
| 6 | POST `/api/admin/eval` avec mock renvoyant un result synthétique + TestClient → la page JS en faisant `renderResults` affiche les 9 champs et le bouton download est actif | (Test de rendu JS faisable en unit via jsdom ? Trop lourd pour MVP. On valide uniquement côté template + API côté backend, le rendu se teste à la main.) |
| 7 | Aucune régression sur `/admin`, `/admin-lab`, `/texte`, `/smart`, `/nouvelle`, `/batch` | Tous 200 |

## Hors scope

- 5.2 — Historique navigable
- 5.3 — Comparaison A/B dans l'UI
- 5.4 — Progression SSE pendant l'éval
- Drag-drop upload
- Sauvegarde côté client du dernier run vu (localStorage)
- Graphiques / charts (on reste sur des barres ASCII + tableaux)
