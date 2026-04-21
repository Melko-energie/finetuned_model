# Breakdown par fournisseur — Design (chantier 2.4)

**Date** : 2026-04-21
**Chantier** : 2.4 (regroupement des métriques par fournisseur détecté)
**Prérequis** : 2.1 + 2.2 + 2.3
**Statut** : validé, implémentation en cours

---

## Objectif

Ajouter un regroupement des résultats d'évaluation **par fournisseur détecté** (`installateur` retourné par `extract_smart`). Le métier obtient ainsi la réponse opérationnelle à sa vraie question : **"quel fournisseur dois-je travailler en priorité ?"**.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Clé de groupage | `installateur` renvoyé par l'extraction (auto-detect ou DEFAULT) | C'est la valeur produite par le système, donc la vraie réalité d'usage. Les PDFs où la détection échoue → bucket `unknown`. |
| Métriques par groupe | Même structure que le global (`per_field` + `global`) | Réutilise `aggregate()` existant. Rien à inventer. |
| Tri par défaut | Accuracy croissante (pires en premier) | Actionnable : le métier voit en haut de liste ceux à améliorer. |
| Affichage terminal | Tous les fournisseurs avec leurs PDFs | < 30 lignes en pratique, pas besoin de limiter. |
| Affichage Excel | Nouvelle feuille `Per-Supplier` | Évite de surcharger la feuille `Summary`. |
| Seuils couleur Excel | ≥90 % vert, 60-90 % orange, <60 % rouge | Cohérent avec la palette 2.2. |

## Conception

### Nouvelle fonction `aggregate_by_supplier`

```python
# metrics.py
def aggregate_by_supplier(per_pdf: list[dict]) -> dict[str, dict]:
    groups: dict[str, list[dict]] = {}
    for row in per_pdf:
        supplier = (row.get("installateur") or "unknown").lower()
        groups.setdefault(supplier, []).append(row)
    return {s: aggregate(rows) for s, rows in groups.items()}
```

Stockée dans `result["metrics_by_supplier"]`, côte à côte avec `result["metrics"]` (global).

### Terminal report

Nouveau bloc après "Global accuracy" :

```
  Per-supplier accuracy (worst first):

    unknown         ██░░░░░░░░  23.5%  (17 / 72 cells)    (8 PDFs)
    dila            ████░░░░░░  42.2%  (19 / 45 cells)    (5 PDFs)
    ternel          ██████░░░░  64.4%  (29 / 45 cells)    (5 PDFs)
    a2m             █████████░  92.6%  (50 / 54 cells)    (6 PDFs)
    ...
```

### Excel — nouvelle feuille `Per-Supplier`

| Col | Colonne |
|---|---|
| A | Fournisseur |
| B | N PDFs |
| C | Global micro | ← coloré par seuil |
| D | Global macro |
| E-M | Accuracy par champ (9 colonnes) | ← colorées par seuil |

Tri par ligne : micro accuracy ASC (pires en haut).

### Seuils de couleur Excel

```python
def _acc_fill(acc: float) -> PatternFill:
    if acc >= 0.9: return GREEN
    if acc >= 0.6: return ORANGE
    return RED
```

Applied to accuracy cells (not count cells).

## Critères d'acceptation

1. Lancer une éval → `result["metrics_by_supplier"]` est peuplé avec une clé par fournisseur détecté.
2. Chaque clé a une structure `{per_field, global}` identique au global.
3. PDFs avec `installateur=None` tombent dans `unknown`.
4. Terminal : bloc "Per-supplier accuracy" affiche chaque fournisseur avec barre + % + compteur.
5. Excel `--excel` produit désormais **3 feuilles** : `Summary`, `Details`, `Per-Supplier`.
6. Dans la feuille `Per-Supplier`, les lignes sont triées par accuracy croissante.
7. Les cellules d'accuracy sont colorées selon les seuils (vert/orange/rouge).
8. JSON `--output` inclut `metrics_by_supplier`.

## Hors scope (chantiers ultérieurs)

- 2.5 : historique de runs + diff
- 2.6 : endpoint HTTP
- Regroupement par tranche de montant, type (facture vs avoir), date — YAGNI.
- Drill-down cliquable dans Excel — overkill.
