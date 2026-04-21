# Historique + comparaison de runs — Design (chantier 2.5)

**Date** : 2026-04-21
**Chantier** : 2.5 (sauvegarde de runs + diff A/B)
**Prérequis** : 2.1 → 2.4
**Statut** : validé, implémentation en cours

---

## Objectif

Transformer `run_eval.py` d'outil ponctuel en outil de **boucle qualité** : chaque run est sauvegardé automatiquement, et on peut diffuser deux runs pour mesurer objectivement l'effet d'une modification de prompt.

Le flux cible :

```
1. run_eval --pdfs X --truth Y              → run A (baseline)
2. [édition d'un prompt via /admin]
3. run_eval --pdfs X --truth Y              → run B (after change)
4. run_eval diff A B                         → delta per-field / per-supplier / per-PDF
```

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Format CLI | Subcommands : `run`, `list`, `diff` | Cohérence (un seul binaire), séparation claire des modes. Rupture de l'API `--pdfs/--truth` en root, acceptable à ce stade (5 commits). |
| Stockage | `data/eval_runs/<YYYY-MM-DD_HHMMSS>/result.json` | Lisible, trié par nom = trié chrono, pas de DB nécessaire. |
| Gitignore | Ajouter `data/eval_runs/` | Gros fichiers JSON, pas du code. |
| Alias "latest" | Résout au dernier run (listing trié DESC) | UX : `diff latest previous` / `diff <specific> latest`. |
| Regressions affichées | Top 20 par défaut, configurable via `--limit` | Pas d'explosion de sortie sur gros dataset. |

## Conception

### Structure disque

```
data/eval_runs/
├── 2026-04-21_170245/
│   └── result.json
├── 2026-04-21_172030/
│   └── result.json
└── ...
```

Nom du dossier = timestamp UTC compact.

### `core/eval/history.py` (nouveau)

```python
RUNS_DIR = DATA_DIR / "eval_runs"

def save_run(result, run_name=None) -> Path: ...
def list_runs() -> list[dict]: ...         # [{id, started_at, pdfs_dir, accuracy, ...}]
def load_run(run_id) -> dict: ...          # 'latest' resolves to the newest
```

### `core/eval/diff.py` (nouveau)

```python
def diff_results(a: dict, b: dict) -> dict:
    """Compute structured diff between two run results.
    Returns:
      {
        'meta': {a_id, b_id, a_started_at, b_started_at, a_model, b_model},
        'global': {micro: {a, b, delta}, macro: {a, b, delta}},
        'per_field': {field: {a, b, delta}},
        'per_supplier': {supplier: {n_a, n_b, a, b, delta}},   # only shared
        'regressions': [{filename, field, verdict_a, verdict_b}],  # match→not-match
        'improvements': [{filename, field, verdict_a, verdict_b}], # not-match→match
      }
    """

def render_diff_terminal(diff, limit=20): ...
```

### `scripts/run_eval.py` — subcommands

```bash
python scripts/run_eval.py run    --pdfs X --truth Y [--excel Z] [--output W]
                                   [--no-save] [--run-name NAME]
python scripts/run_eval.py list
python scripts/run_eval.py diff   <run_a> <run_b> [--limit N]
```

### Mode `run`

- Lance l'éval comme avant.
- Auto-sauvegarde dans `data/eval_runs/<timestamp>/result.json` (sauf `--no-save`).
- Affiche `Saved run: <run_id>` à la fin.

### Mode `list`

```
=== Saved eval runs ===

  ID                     Started            Dataset                  Global acc.
  ─────────────────────  ─────────────────  ───────────────────────  ───────────
  2026-04-21_172030      2026-04-21 17:20   data/echantillon         78.2%
  2026-04-21_170245      2026-04-21 17:02   data/echantillon         72.5%
  2026-04-20_153045      2026-04-20 15:30   data/echantillon         68.1%
```

Tri : plus récent en haut.

### Mode `diff`

Affiche :

```
=== Diff: 2026-04-20_153045 → 2026-04-21_172030 ===
Model:   gemma2:9b → gemma2:9b
Dataset: data/echantillon (same)

Global:
  micro   68.1% → 78.2%   (+10.1pp)  ↑
  macro   65.4% → 74.3%   ( +8.9pp)  ↑

Per-field:
  DATE_FACTURE      45.0% →  95.0%  (+50.0pp)  ↑↑
  MONTANT_HT        40.0% →  85.0%  (+45.0pp)  ↑↑
  NOM_INSTALLATEUR  80.0% →  75.0%  ( -5.0pp)  ↓   ← regression

Per-supplier (shared):
  a2m       100.0% → 100.0%   ( 0.0pp)
  dila       22.2% →  55.5%   (+33.3pp)  ↑
  ternel     66.7% →  88.9%   (+22.2pp)  ↑

Regressions (3 verdicts match → not-match):
  S1120630.PDF    NOM_INSTALLATEUR   match → mismatch
  S1120318.PDF    COMMUNE_TRAVAUX    match → missing
  ...

Improvements (42 verdicts not-match → match):
  S1120317.PDF    MONTANT_HT         mismatch → match
  ...
```

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | `run` CLI avec défaut `--no-save` absent | Sauvegarde automatique dans `data/eval_runs/<timestamp>/` |
| 2 | `run --no-save` | Aucun dossier créé |
| 3 | `list` sur `data/eval_runs/` vide | Message "No saved runs" |
| 4 | `list` avec 2 runs | Tableau trié DESC |
| 5 | `diff a b` avec IDs valides | Render terminal complet |
| 6 | `diff latest previous` | Résolu correctement |
| 7 | `diff x y` avec ID inexistant | Erreur claire |
| 8 | Détection des régressions | Verdicts match→mismatch détectés |
| 9 | Détection des améliorations | Verdicts mismatch→match détectés |
| 10 | Per-supplier diff | Seuls les fournisseurs présents dans les deux runs |

## Hors scope

- 2.6 : Endpoint HTTP
- UI de listing/diff (viendra avec 2.6 et/ou une extension de /admin)
- Comparaison >2 runs (YAGNI)
- Alerting automatique sur régression (YAGNI)
- Déduplication des runs identiques (YAGNI)
