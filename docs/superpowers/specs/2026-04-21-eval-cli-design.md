# Banc d'évaluation CLI — Design (chantier 2.1)

**Date** : 2026-04-21
**Chantier** : 2.1 (MVP banc d'évaluation — CLI + normalisation basique)
**Prérequis** : chantier 1 complet (prompts fonctionnels)
**Statut** : validé, implémentation en cours

---

## Objectif

CLI `scripts/run_eval.py` qui prend un dossier de PDFs + un fichier Excel de ground truth, lance l'extraction Smart sur chaque PDF, compare avec la vérité, et affiche des métriques par champ + globales en terminal.

**Réussite** : un développeur peut en une commande mesurer objectivement la qualité de l'extraction sur un lot.

## Interface

```bash
python scripts/run_eval.py --pdfs <dir> --truth <xlsx> [--output <json>]
```

## Ground truth

- Format = sortie actuelle de `/batch` (feuilles `Extractions` ou `TOUTES_FACTURES`).
- Colonne `Nom du PDF` = clé de matching avec le filename (case-insensitive).
- 9 champs métier comparés + `Type` (facture/avoir).

## Normalisation (niveau 2.1)

```python
def normalize_basic(v):
    if v is None: return ""
    s = str(v).strip().lower()
    if s in {"", "null", "non detecte", "—", "-"}: return ""
    return s.rstrip(".,;")
```

Exact match après normalisation. Pas de dates/nombres intelligents (c'est 2.3).

## Pipeline

1. Charger ground truth (feuille `Extractions` ou `TOUTES_FACTURES`).
2. Scanner `--pdfs` récursivement pour les `*.pdf`, `*.PDF`.
3. Pour chaque ligne du truth : trouver le PDF correspondant, lancer `extract_smart()` (fallback `process_file_live()` si pas d'OCR pré-calculé — comme `iter_batch_zip`).
4. Comparer champ par champ, compter match/mismatch/missing.
5. Afficher un rapport terminal avec barres ASCII.
6. Si `--output` : dump JSON complet.

## Architecture

```
core/eval/                  ← nouveau sous-package, aucune dépendance à api/
├── __init__.py
├── normalize.py            ← normalize_basic()
├── dataset.py              ← load_ground_truth(), find_pdf_for(key, pdfs_dir)
├── compare.py              ← compare_fields(extracted, expected)
├── metrics.py              ← aggregate_by_field(), global_accuracy()
├── report.py               ← render_terminal(), dump_json()
└── runner.py               ← run_eval() — orchestration top-level

scripts/run_eval.py         ← CLI wrapper argparse → runner.run_eval()
```

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | CLI sans args | Affiche usage, exit 1 |
| 2 | `--truth` inexistant | Erreur explicite |
| 3 | Excel sans feuille attendue | Erreur listant les feuilles trouvées |
| 4 | Dataset 2 PDF + truth 2 lignes | Rapport avec 9 champs + global |
| 5 | PDF dans truth mais absent sur disque | Warning `[missing]`, compté dans le total |
| 6 | PDF sur disque absent du truth | Warning `[skip]` |
| 7 | `--output report.json` | Fichier JSON valide avec `{meta, per_field, global, per_pdf}` |
| 8 | Aucun import depuis `api.*` | `core.eval` isolé |

## Hors scope (déjà noté dans le découpage)

- 2.2 — Rapport Excel coloré
- 2.3 — Normalisation dates/montants
- 2.4 — Breakdown par fournisseur
- 2.5 — Historique + comparaison de runs
- 2.6 — Endpoint HTTP
