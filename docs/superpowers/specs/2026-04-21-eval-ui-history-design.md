# Historique des runs — Design (chantier 5.2)

**Date** : 2026-04-21
**Chantier** : 5.2 (navigation dans les runs passés depuis `/eval-lab`)
**Prérequis** : 5.1 + chantier 2.6 (endpoints list/detail)
**Statut** : validé, implémentation en cours

---

## Objectif

Permettre à l'utilisateur de consulter les runs passés depuis la page `/eval-lab` sans relancer une évaluation. Clic sur un run → détail complet affiché dans la même section résultats qu'une éval fraîche.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Emplacement | Section inline entre l'upload form et le loading | Always-visible, pas de clic supplémentaire, donne immédiatement le contexte. |
| Vide vs liste | Section cachée s'il n'y a pas de run | Pas de bruit quand on arrive pour la première fois. |
| Rafraîchissement | Au chargement de la page + après chaque POST réussi | Évite de manquer un run fraîchement créé. |
| Affichage | Tableau avec ID, date, dataset (tronqué), accuracy micro colorée, durée, bouton "Voir" | Calqué sur la sortie `run_eval.py list`. |
| Réutilisation | `renderResults` existant, wrappé dans `viewRun` qui fetch le détail | Zéro duplication de rendu. |
| Bouton "Comparer" | Placeholder pour 5.3 — pas implémenté ici | Garde le scope serré. |

## Conception

### Template : nouvelle section `templates/eval_lab.html`

Insérée entre `</form>` et `<div id="loading">`. Structure :

```html
<section id="history-section" class="hidden bg-white rounded-xl p-5 border border-outline-variant/50">
  <div class="flex items-center justify-between mb-3">
    <div class="flex items-center gap-2">
      <span class="material-symbols-outlined text-primary">history</span>
      <span class="font-medium text-sm">Runs passés</span>
      <span id="history-count" class="text-xs text-on-surface-variant"></span>
    </div>
    <button id="btn-refresh-history" class="text-xs text-primary hover:underline">Rafraîchir</button>
  </div>
  <table class="w-full text-xs">
    <thead class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest border-b border-outline-variant/50">
      <tr>
        <th class="text-left py-2 pl-2">ID</th>
        <th class="text-left py-2">Démarré</th>
        <th class="text-left py-2">Dataset</th>
        <th class="text-right py-2">Accuracy</th>
        <th class="text-right py-2">Durée</th>
        <th class="text-right py-2 pr-2">Action</th>
      </tr>
    </thead>
    <tbody id="history-tbody"></tbody>
  </table>
</section>
```

### JS : extensions dans `static/js/eval_lab.js`

Nouveaux DOM refs :
```js
const historySection = $("history-section");
const historyCount = $("history-count");
const historyTbody = $("history-tbody");
const btnRefreshHistory = $("btn-refresh-history");
```

Nouvelles fonctions :
```js
async function refreshHistory() {
    // GET /api/admin/eval/runs, render if any, hide if none
}

function renderHistory(runs) {
    // Populate tbody, one row per run, each with a "Voir" button
}

async function viewRun(runId) {
    // GET /api/admin/eval/runs/{runId}, wrap as POST-shape payload,
    // call renderResults().
}
```

### Dans `submitEval` (existant)

Après un POST réussi, appeler `refreshHistory()` pour que le run fraîchement créé apparaisse en tête.

### Au chargement

Appeler `refreshHistory()` à la fin de l'IIFE.

### Format d'une ligne du tableau

```
2026-04-21_172030   2026-04-21 17:20   data/echantillon         78.2%   8m    [Voir]
```

La cellule accuracy est colorée selon les seuils déjà définis (≥90 vert, 60-90 orange, <60 rouge).

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | Au chargement de `/eval-lab` sans runs | `#history-section` reste `hidden` |
| 2 | Au chargement avec ≥1 run | `#history-section` devient visible, lignes rendues |
| 3 | Tableau contient N lignes pour N runs | OK |
| 4 | Tri : plus récent en haut (délégué au serveur qui renvoie déjà trié) | OK |
| 5 | Clic sur "Voir" déclenche `viewRun(id)` → le `#results` se remplit | OK |
| 6 | Bouton "Rafraîchir" refait l'appel | OK |
| 7 | Après un POST éval réussi, le nouveau run apparaît en tête | OK |
| 8 | `#btn-download` dans `#results` pointe correctement sur `/api/admin/eval/runs/{id}/download` après `viewRun` | OK |
| 9 | Aucune régression sur `/admin`, `/admin-lab`, `/batch` etc. | Tous 200 |

## Hors scope

- 5.3 — Comparaison A/B (le bouton viendra ici même)
- 5.4 — SSE progress
- Pagination (YAGNI — 10-20 runs attendus dans l'horizon visible)
- Suppression d'un run depuis l'UI (YAGNI)
- Renommage / tag d'un run (YAGNI)
