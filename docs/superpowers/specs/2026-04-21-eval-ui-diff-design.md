# Comparaison A/B — Design (chantier 5.3)

**Date** : 2026-04-21
**Chantier** : 5.3 (UI de diff entre deux runs depuis `/eval-lab`)
**Prérequis** : 5.2 + chantier 2.5 (endpoint diff)
**Statut** : validé, implémentation en cours

---

## Objectif

Permettre à l'utilisateur de sélectionner deux runs depuis le tableau d'historique de `/eval-lab` et voir le diff structuré : delta global, delta par champ, delta par fournisseur, liste des régressions et améliorations par-PDF.

**Backend zéro** : `GET /api/admin/eval/runs/{a}/diff/{b}` existe depuis le chantier 2.6 et renvoie exactement la shape produite par `core.eval.diff.diff_results`.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Sélection | Checkbox dans la 1re colonne du tableau d'historique | Visuellement lisible, pas de clic à la volée. |
| Activation | Bouton "Comparer" actif uniquement quand exactement 2 cochés | UX claire, pas de magie ("oldest removed"). |
| Emplacement du diff | Nouvelle section `#diff-section` sous `#results` | Linear flow, pas de modale pour contenu dense. |
| Limite regressions/improvements | 20 items affichés + compteur "+N autres" | Match le défaut de `render_diff_terminal`. |
| Flèches delta | Unicode ↑↑ ↑ ↓↓ ↓ + couleurs | Portable, lisible, cohérent avec la sortie terminal. |
| Sens A → B | `a` = première coche chronologique (plus ancienne), `b` = seconde | "Comment ai-je évolué" en regardant de gauche à droite. Le serveur calcule `delta = b - a`. |

## Conception

### Template — additions à `eval_lab.html`

Dans la section history, avant la table :

```html
<div class="flex items-center justify-between mb-3">
  <div class="flex items-center gap-2">
    <span class="material-symbols-outlined text-primary">history</span>
    <span class="font-medium text-sm">Runs passés</span>
    <span id="history-count" class="text-xs text-on-surface-variant"></span>
  </div>
  <div class="flex items-center gap-2">
    <span id="diff-hint" class="text-xs text-on-surface-variant">Sélectionne 2 runs pour comparer.</span>
    <button id="btn-diff" type="button" disabled class="bg-primary text-white px-3 py-1.5 rounded-md text-xs font-medium disabled:opacity-40 flex items-center gap-1 hover:bg-primary-container">
      <span class="material-symbols-outlined text-sm">compare_arrows</span>
      Comparer
    </button>
    <button id="btn-refresh-history" ...>Rafraîchir</button>
  </div>
</div>
```

Table : ajout d'une colonne checkbox en 1re position :

```html
<th class="text-left py-2 pl-2"><span class="sr-only">Sélection</span></th>
<!-- puis les autres colonnes -->
```

Chaque `<tr>` dans `renderHistory` reçoit un `<input type="checkbox" class="run-checkbox" data-run-id="...">`.

Nouvelle section après `<section id="results">` :

```html
<section id="diff-section" class="hidden bg-white rounded-xl p-6 border border-outline-variant/50 space-y-6">
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-2">
      <span class="material-symbols-outlined text-primary">compare_arrows</span>
      <h3 id="diff-title" class="font-headline text-xl font-bold"></h3>
    </div>
    <button id="btn-close-diff" type="button" class="text-on-surface-variant hover:text-on-surface">
      <span class="material-symbols-outlined">close</span>
    </button>
  </div>

  <!-- Global deltas: 2 tiles -->
  <div class="grid grid-cols-2 gap-4">
    <div class="bg-surface-container-low rounded-lg p-4" id="diff-global-micro"></div>
    <div class="bg-surface-container-low rounded-lg p-4" id="diff-global-macro"></div>
  </div>

  <!-- Per-field block -->
  <div>
    <div class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Par champ</div>
    <div id="diff-per-field" class="space-y-1 text-xs"></div>
  </div>

  <!-- Per-supplier block -->
  <div>
    <div class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-2">Par fournisseur (partagés)</div>
    <div id="diff-per-supplier" class="space-y-1 text-xs"></div>
  </div>

  <!-- Regressions + Improvements -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div>
      <div class="text-[10px] font-bold text-error uppercase tracking-widest mb-2">
        Régressions <span id="regressions-count"></span>
      </div>
      <div id="regressions-list" class="space-y-1 text-xs font-mono"></div>
    </div>
    <div>
      <div class="text-[10px] font-bold text-[#2e7d32] uppercase tracking-widest mb-2">
        Améliorations <span id="improvements-count"></span>
      </div>
      <div id="improvements-list" class="space-y-1 text-xs font-mono"></div>
    </div>
  </div>
</section>
```

### JS — additions à `eval_lab.js`

```js
// New DOM refs
const btnDiff = $("btn-diff");
const btnCloseDiff = $("btn-close-diff");
const diffSection = $("diff-section");
const diffTitle = $("diff-title");
const diffGlobalMicro = $("diff-global-micro");
const diffGlobalMacro = $("diff-global-macro");
const diffPerField = $("diff-per-field");
const diffPerSupplier = $("diff-per-supplier");
const regressionsList = $("regressions-list");
const improvementsList = $("improvements-list");
const regressionsCount = $("regressions-count");
const improvementsCount = $("improvements-count");

// State
state.selectedRuns = new Set();

// In renderHistory: replace each row's cells to include <input type=checkbox>
// + wire a change handler that updates state.selectedRuns + calls updateDiffButton()

function updateDiffButton() {
    btnDiff.disabled = state.selectedRuns.size !== 2;
}

async function submitDiff() {
    if (state.selectedRuns.size !== 2) return;
    // Sort by ID (which starts with timestamp) so "a" is older, "b" is newer
    const [a, b] = [...state.selectedRuns].sort();
    const res = await fetch(`/api/admin/eval/runs/${a}/diff/${b}`);
    ...
    renderDiff(await res.json(), a, b);
}

function renderDiff(diff, aId, bId) {
    // Populate all diff-* elements
    // Sort per-supplier by delta ASC
    // Limit regressions/improvements to 20, show +N more
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
```

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | Sans run coché → bouton "Comparer" disabled | OK |
| 2 | 1 run coché → bouton disabled | OK |
| 3 | 2 runs cochés → bouton actif | OK |
| 4 | 3 runs cochés → bouton disabled | OK |
| 5 | Clic "Comparer" avec 2 runs → appel `/api/admin/eval/runs/{a}/diff/{b}` (a = ID alphabétiquement inférieur) | OK |
| 6 | `#diff-section` contient tous les sous-éléments (global, per-field, per-supplier, regressions, improvements) | OK |
| 7 | Bouton "Close" cache la section | OK |
| 8 | /admin et /admin-lab ne contiennent pas les nouveaux IDs | OK |
| 9 | eval_lab.js contient `submitDiff`, `renderDiff`, `updateDiffButton` | OK |
| 10 | Aucune régression | Tous 200 |

## Hors scope

- 5.4 — SSE progress
- Sauvegarde/export du diff
- Diff de plus de 2 runs (matrix view)
- Persistance de la sélection entre rechargements
