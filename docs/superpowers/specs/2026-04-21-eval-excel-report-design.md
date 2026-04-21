# Rapport Excel détaillé — Design (chantier 2.2)

**Date** : 2026-04-21
**Chantier** : 2.2 (rapport Excel coloré, une ligne par PDF, mismatches visibles)
**Prérequis** : 2.1 (pipeline eval CLI)
**Statut** : validé, implémentation en cours

---

## Objectif

Ajouter à `run_eval.py` une option `--excel <path>` qui génère un fichier `.xlsx` avec :

1. Feuille **Summary** : mêmes métriques que le terminal, présentées verticalement.
2. Feuille **Details** : une ligne par PDF, colonnes `expected` / `extracted` côte à côte pour chaque champ, cellules colorées selon le verdict.

Le métier peut ainsi **repérer visuellement** les cellules à corriger d'un coup d'œil, sans plonger dans un JSON.

## Interface CLI

```bash
python scripts/run_eval.py --pdfs <dir> --truth <xlsx> --excel report.xlsx
```

`--excel`, `--output` (JSON) et le rendu terminal sont indépendants — on peut tous les combiner.

## Palette (cohérente avec `core/excel.py`)

| Verdict | Couleur de fond | Usage |
|---|---|---|
| match | `E6F4EA` (vert clair) | Cellule extracted identique à expected |
| mismatch | `FDE8E8` (rouge clair) | Valeurs divergent |
| missing | `FFE5CC` (orange doux) | Attendu non vide, extrait vide/null |
| unexpected | `FFF9C4` (jaune) | Extrait non vide, attendu vide |
| neutre (métadonnées) | `F2F4F6` (gris clair) | filename, installateur, type |

## Feuille Details — structure

| Col | Colonne | Source |
|---|---|---|
| A | Nom du PDF | per_pdf[i].filename |
| B | Type | per_pdf[i].expected.Type (facture/avoir) |
| C | Installateur détecté | per_pdf[i].installateur |
| D | Erreur | per_pdf[i].error (ou vide) |
| E-F | NUMERO_FACTURE expected / extracted | ... |
| G-H | DATE_FACTURE expected / extracted | |
| ... | les 9 champs × 2 colonnes = 18 colonnes | |

Total : **22 colonnes**.

**Coloration** : les paires de cellules (expected + extracted) prennent la couleur du verdict. Les colonnes métadonnées (A-D) restent en gris neutre.

Ligne d'en-tête figée (`freeze_panes`).

## Feuille Summary — structure

- Bloc 1 : métadonnées du run (dataset, truth, model, durée, date).
- Bloc 2 : tableau per-field (field, match, mismatch, missing, unexpected, total, accuracy %).
- Bloc 3 : accuracy globale micro + macro.

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | `--excel report.xlsx` génère un fichier | Fichier .xlsx valide, 2 feuilles |
| 2 | Cellule match → fond vert | Vérifié via openpyxl après lecture |
| 3 | Cellule mismatch → fond rouge | Idem |
| 4 | Cellule missing → fond orange | Idem |
| 5 | Cellule unexpected → fond jaune | Idem |
| 6 | Sans `--excel` | Aucun fichier généré, CLI inchangé |
| 7 | `--excel` + `--output json` + terminal | Les trois outputs produits |

## Structure code

```
core/eval/excel_report.py      ← nouveau
scripts/run_eval.py            ← ajout du flag --excel
```

Pas de changement sur les autres modules eval.

## Hors scope

- 2.3 — Normalisation avancée (dates/nombres)
- 2.4 — Breakdown par fournisseur (feuille par fournisseur)
- 2.5 — Historique
- 2.6 — Endpoint HTTP
