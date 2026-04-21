# Auto-test du brouillon généré — Design (chantier 4.4)

**Date** : 2026-04-21
**Chantier** : 4.4 (feedback immédiat sur la qualité du prompt généré)
**Prérequis** : 4.1 + 4.2 + 4.3
**Statut** : validé, implémentation en cours

---

## Objectif

Après génération d'un brouillon de prompt, lancer **immédiatement** une extraction sur les mêmes échantillons avec ce nouveau prompt, comparer aux valeurs attendues, et afficher les métriques dans l'UI avant la validation humaine. Le métier voit en un coup d'œil si le prompt produit par Gemma2 fonctionne déjà correctement ou s'il faut l'éditer.

**Boucle livrée (dans la foulée de 4.3)** : upload → OCR + génération + **auto-test** → draft + score affiché dans l'éditeur → review → save.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Emplacement | Intégré dans `/api/admin/prompts/generate` | Évite un 2e roundtrip HTTP. Les OCR sont déjà faits, réutilisables. |
| Opt-in | Non, toujours activé | 30s de plus pour un feedback qui évite une sauvegarde inutile. ROI clair. |
| Fonction extraction avec prompt inline | Nouveau `extraire_champs_with_prompt(ocr_text, prompt)` | `extraire_champs` existant lit le dict global par clé ; pas adapté pour tester un prompt pas encore sauvegardé. |
| Affichage UI | Panneau dans l'éditeur (pas dans la modale) | La modale se ferme après génération, le focus passe à l'éditeur où l'utilisateur va travailler. Le panneau y est pertinent. |
| Métriques | Même schéma que chantier 2 (per_field / global) | Consistance + réutilisation de `compare_fields` + `aggregate`. |
| Échec du self-test | Non-fatal : le draft est retourné avec `self_test = null` + message d'erreur dans les logs | L'utilisateur n'est pas bloqué par un échec secondaire. |

## Contrat HTTP (évolution de 4.2)

`POST /api/admin/prompts/generate` renvoie maintenant en plus :

```json
{
  "key": "acme_sarl",
  "detecter": [...],
  "prompt": "...",
  "self_test": {
    "metrics": {
      "per_field": { "NUMERO_FACTURE": { "match": 3, "mismatch": 0, "missing": 0, "unexpected": 0, "total": 3, "accuracy": 1.0 }, ... },
      "global": { "match": 24, "total": 27, "accuracy": 0.889, "accuracy_macro": 0.889 }
    },
    "per_pdf": [
      { "filename": "sample_a.pdf", "verdicts": { "NUMERO_FACTURE": "match", ... } },
      ...
    ]
  }
}
```

Si self-test échoue (exception Ollama / JSON sur une extraction) → `"self_test": null` + un warning loggué serveur. Le draft reste valide.

## Design backend

### Nouvelle fonction `extraire_champs_with_prompt`

Dans `core/extraction.py` :

```python
def extraire_champs_with_prompt(texte: str, prompt_text: str) -> dict:
    """Variant of extraire_champs that accepts the prompt inline (not by
    supplier key). Used by chantier 4.4 to self-test a draft prompt before
    it's saved to disk."""
    prompt = prompt_text + texte
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        options=OLLAMA_OPTIONS,
    )
    raw = clean_json(response["message"]["content"])
    try:
        result = json.loads(raw)
        result = verifier_coherence_montants(result)
        return _apply_sip_cleanup(result)
    except json.JSONDecodeError:
        return {champ: None for champ in ALL_FIELD_KEYS}
```

C'est un sous-ensemble de `extraire_champs` (pas de `nettoyer_adresse_nvins` parce qu'un nouveau fournisseur n'est pas `nvins_*`).

### Endpoint modifié

Dans `api/admin.py`, après `draft = generate_prompt_from_samples(samples)` :

```python
# Self-test on the same samples
from core.eval.compare import compare_fields
from core.eval.metrics import aggregate
from core.extraction import extraire_champs_with_prompt

self_test = None
try:
    per_pdf = []
    for sample_plan, sample in zip(samples_plan, samples):
        extracted = extraire_champs_with_prompt(sample["ocr_text"], draft["prompt"])
        verdicts = compare_fields(extracted, sample["expected"])
        per_pdf.append({
            "filename": sample_plan[0].filename,
            "verdicts": verdicts,
        })
    self_test = {
        "metrics": aggregate(per_pdf),
        "per_pdf": per_pdf,
    }
except Exception as e:
    # Self-test is a bonus; don't fail the generation if it breaks
    import logging
    logging.warning(f"Self-test failed after generation: {e}")

return {
    "key": key,
    "detecter": draft["detecter"],
    "prompt": draft["prompt"],
    "self_test": self_test,
}
```

## Design UI (`/admin-lab`)

### Nouveau panneau dans l'éditeur

Placé entre le champ `prompt` et les boutons d'action, visible uniquement quand `state.selfTest` est non-null (c.-à-d. après un loadDraft de 4.4).

Structure HTML (ajoutée à `admin_lab.html` par Jinja2, mais le JS la remplit/cache à la volée) :

```html
<div id="self-test-panel" class="hidden border border-outline-variant/50 rounded-lg p-4 bg-surface-container-low">
  <div class="flex items-center justify-between mb-3">
    <div class="flex items-center gap-2">
      <span class="material-symbols-outlined text-primary">verified</span>
      <span class="font-medium text-sm">Auto-test sur les échantillons fournis</span>
    </div>
    <span id="self-test-global" class="text-sm font-bold"></span>
  </div>
  <div id="self-test-fields" class="grid grid-cols-2 gap-1 text-xs"></div>
</div>
```

`self-test-fields` affiche une grille 2 colonnes avec une ligne par champ :
- Nom du champ
- Barre colorée (vert/orange/rouge selon accuracy) + %
- Détail `(match/total)`

Exemple :
```
NUMERO_FACTURE     ██████████  100%  (3/3)
DATE_FACTURE       ██████░░░░   66%  (2/3)
MONTANT_HT         ░░░░░░░░░░    0%  (0/3)   ← rouge, à corriger
```

### JS `admin_lab.js`

- `loadDraft` reçoit désormais un objet avec `self_test` en option.
- Nouveau helper `renderSelfTest(selfTest)` qui remplit le panneau.
- Quand l'utilisateur sauvegarde ou annule le draft, le panneau se cache (dans `cancelEdit`, dans le flow post-save).
- Quand l'utilisateur sélectionne un autre prompt dans la liste, le panneau se cache.

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | `extraire_champs_with_prompt` avec mock Ollama renvoyant JSON valide | Dict avec les 9 clés |
| 2 | `extraire_champs_with_prompt` avec mock Ollama renvoyant JSON cassé | `{k: None for k in ALL_FIELD_KEYS}` |
| 3 | Endpoint `generate` avec mocks sur OCR, gen, `extraire_champs_with_prompt` retournant pile le ground truth | `self_test.metrics.global.accuracy == 1.0` |
| 4 | Endpoint `generate` avec self-test qui lève une Exception | 200 + `self_test: null` (le draft est renvoyé) |
| 5 | Template `/admin-lab` contient `#self-test-panel`, `#self-test-global`, `#self-test-fields` | OK |
| 6 | Template `/admin` (stable) n'a PAS ces éléments | OK |
| 7 | `admin_lab.js` a la fonction `renderSelfTest` | OK |
| 8 | `admin.js` ne l'a PAS | OK |
| 9 | Aucune régression HTTP | Tous 200 |

## Hors scope

- Re-test après édition manuelle du prompt dans l'éditeur (nécessiterait un endpoint séparé) → YAGNI maintenant
- Drill-down par PDF/champ dans l'UI (cliquer sur un champ rouge pour voir le détail) → enhancement, pas MVP
- Parallélisation des appels Gemma2 pour le self-test → micro-optimisation
