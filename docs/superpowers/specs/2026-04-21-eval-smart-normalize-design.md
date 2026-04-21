# Normalisation avancée — Design (chantier 2.3)

**Date** : 2026-04-21
**Chantier** : 2.3 (normalisation par type de champ : dates, nombres, accents)
**Prérequis** : 2.1 (pipeline eval) + 2.2 (rapport Excel)
**Statut** : validé, implémentation en cours

---

## Objectif

Remplacer la normalisation unique `normalize_basic` par un dispatch **champ-par-champ** qui applique la bonne transformation selon le type métier (date, nombre, pourcentage, texte). Objectif : éliminer les faux négatifs dus à des formats divergents mais équivalents.

**Exemples** actuellement comptés comme mismatch, qui doivent passer en match après 2.3 :

| Champ | Expected | Extracted | Actuel | Après 2.3 |
|---|---|---|---|---|
| DATE_FACTURE | `21/04/2026` | `2026-04-21` | mismatch | **match** |
| DATE_FACTURE | `21/04/2026` | `21 avril 2026` | mismatch | **match** |
| MONTANT_HT | `1 234,56` | `1234.56` | mismatch | **match** |
| MONTANT_HT | `100,00 €` | `100` | mismatch | **match** |
| TAUX_TVA | `20%` | `20.0 %` | mismatch | **match** |
| COMMUNE_TRAVAUX | `Amiens` | `AMIENS` | match (déjà via lowercase) | match |
| NOM_INSTALLATEUR | `Société A2M` | `societe a2m` | mismatch | **match** |

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Dispatch | Dict `FIELD_NORMALIZERS: {field: fn}` dans `normalize.py` | Explicite, testable, maintenable. |
| Dates : canonique | `YYYY-MM-DD` via `dateutil.parser` + traduction des mois français | `dateutil` déjà transitive (via pandas). Mois FR pas supportés nativement. |
| Nombres : canonique | `float` arrondi à 2 décimales, `str(x)` avec `.` comme séparateur | Stable, comparable. |
| Pourcentages | Parse comme nombre, strip du `%` avant | `"20%"` et `"20.0"` convergent vers `20.0`. |
| Texte (noms, adresses) | Strip accents + lowercase + collapse whitespace | Rend `Société` == `societe`. |
| Fallback | Si la normalisation spécialisée échoue, tomber sur `normalize_basic` | Pas de crash sur données bizarres, juste moins performant. |

## Design détaillé

### `core/eval/normalize.py` — structure nouvelle

```python
def normalize_basic(value) -> str: ...       # inchangé, fallback
def normalize_text(value) -> str: ...        # strip accents + lowercase + collapse
def normalize_date(value) -> str: ...        # → 'YYYY-MM-DD' ou normalize_basic(value) en fallback
def normalize_number(value) -> str: ...      # → '123.45' ou fallback
def normalize_percent(value) -> str: ...     # strip '%' puis normalize_number
def normalize(value, field_key=None) -> str: # dispatch
```

### `FIELD_NORMALIZERS`

```python
FIELD_NORMALIZERS = {
    "NUMERO_FACTURE":   normalize_text,
    "DATE_FACTURE":     normalize_date,
    "MONTANT_HT":       normalize_number,
    "TAUX_TVA":         normalize_percent,
    "MONTANT_TTC":      normalize_number,
    "NOM_INSTALLATEUR": normalize_text,
    "COMMUNE_TRAVAUX":  normalize_text,
    "CODE_POSTAL":      normalize_text,  # digits but text-strip suffit
    "ADRESSE_TRAVAUX":  normalize_text,
}
```

### Dates françaises

Pré-traitement avant `dateutil.parser.parse` :

```python
_FRENCH_MONTHS = {
    "janvier": "01", "février": "02", "fevrier": "02", "mars": "03",
    "avril": "04", "mai": "05", "juin": "06", "juillet": "07",
    "août": "08", "aout": "08", "septembre": "09", "octobre": "10",
    "novembre": "11", "décembre": "12", "decembre": "12",
}
# regex \b(janvier|...)\b → chiffre, puis parse(..., dayfirst=True)
```

Si le parse échoue (chaîne trop courte, incohérente) → retour au `normalize_basic`.

Excel peut renvoyer un `datetime` / `Timestamp` directement → traité en premier (strftime).

### Nombres

Étapes :

1. `str(v).strip()`
2. Strip currency : `€`, `EUR`, `$`, `£`, ` eur `
3. Strip `%` (pour `normalize_percent`)
4. Détermination du séparateur décimal :
   - Si `.` et `,` présents : le **dernier** est décimal, l'autre est milliers → retirer l'autre
   - Si seulement `,` : remplacer par `.`
   - Si seulement `.` : garder tel quel (fallback natif)
5. Retirer tous les séparateurs de milliers (espaces, `_`)
6. `float(...)` → `round(x, 2)` → `str(x)` sans zéro superflu (`"1234.5"` pas `"1234.50"`)
7. Si `ValueError` → `normalize_basic`

### Texte

```python
import unicodedata

def normalize_text(value):
    s = normalize_basic(value)
    if not s: return s
    # strip accents
    s = "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )
    s = " ".join(s.split())  # collapse whitespace
    return s
```

### Compatibilité avec 2.1

`compare.py` appelle actuellement `normalize_basic(x)`. On remplace par `normalize(x, field_key=key)`. Aucune autre modif.

## Critères d'acceptation

Batterie de tests unitaires couvrant au moins :

1. Dates : `21/04/2026` = `2026-04-21` = `21 avril 2026` = `21-04-2026` = `Timestamp(2026,4,21)` → tous donnent `"2026-04-21"`.
2. Nombres : `1 234,56` = `1,234.56` = `1234.56` = `1234,56` → tous donnent `"1234.56"`.
3. Nombres sans décimales : `100` = `100,00` = `100.00` = `100 €` → tous donnent `"100.0"`.
4. Pourcentages : `20%` = `20,0 %` = `20.0%` = `20` → tous donnent `"20.0"`.
5. Texte : `Société` = `societe` = `SOCIÉTÉ  ` = `société` → tous donnent `"societe"`.
6. Fallback : une date invalide ("foobar") via `normalize_date` ne crashe pas, retombe sur `"foobar"`.
7. None / "" / "null" → `""` pour tous les types.
8. Dispatch : `normalize("1 234,56", "MONTANT_HT")` == `"1234.56"`.
9. Intégration : `compare_fields` reconnaît comme match deux valeurs équivalentes mais de format différent.

## Hors scope

- 2.4 — Breakdown par fournisseur
- 2.5 — Historique + diff runs
- 2.6 — Endpoint HTTP
- Autodétection du type de champ (on reste sur le dict statique)
- Tolérance floue style Levenshtein pour le texte (overkill à ce stade)
