# Generator backend — Design (chantier 4.1)

**Date** : 2026-04-21
**Chantier** : 4.1 (cœur de la génération assistée — fonction pure)
**Prérequis** : chantiers 1 complet (prompts externalisés)
**Statut** : validé, implémentation en cours

---

## Contexte

Première marche du chantier 4. Ce module fait **une seule chose** : prendre des échantillons de factures (texte OCR + valeurs attendues) et produire un brouillon de prompt spécialisé via Gemma2:9b. Pas d'HTTP, pas d'UI, pas de stockage. Les couches au-dessus (4.2 HTTP, 4.3 UI) bâtiront dessus.

## Objectif

Exposer **une fonction pure** :

```python
generate_prompt_from_samples(samples) -> {"detecter": [...], "prompt": "..."}
```

où `samples = [{"ocr_text": str, "expected": {field: str | None}}, ...]` (2 à 5 échantillons).

**Ruéssite** : un humain peut appeler cette fonction avec 2-3 factures d'un fournisseur inconnu et récupérer un prompt **directement compatible** avec `PROMPTS_INSTALLATEURS[key]["prompt"]` + une liste de mots-clés directement utilisable dans `detect_installateur`.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| LLM | Gemma2:9b (le même qui fait l'extraction) | Zéro nouvelle dépendance. La qualité sera imparfaite mais la boucle d'édition humaine rattrape — c'était déjà acté. |
| Module | `core/prompt_gen.py` (fichier unique) | Petit, focalisé, évite un sous-package prématuré. |
| Meta-prompt | Inline dans le module | Versionné avec le code. Facile à ajuster. |
| Format de sortie | JSON `{"detecter": [str], "prompt": str}` | Strictement aligné avec le schéma Pydantic de `core/prompts.py`. |
| Errors | `PromptGenerationError` (RuntimeError) avec message explicite | Les appelants HTTP/UI traduisent en 500/toast. |
| Limites | 2-5 samples, OCR tronqué à 2000 chars chacun | Évite la saturation du contexte Gemma2. |

## Meta-prompt design

Le meta-prompt demande à Gemma2 d'analyser les échantillons et de produire :

1. **3-5 mots-clés de détection** présents littéralement dans le texte OCR (nom d'entreprise, SIRET, email, préfixe de numéro).
2. **Un prompt d'extraction** dans le même style stylistique que les prompts existants :
   - ouverture "Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de <NOM>…"
   - section "PARTICULARITÉS <NOM> :" avec des règles par champ
   - rappels sur le null et le JSON strict
   - template JSON inclus
   - fin sur "TEXTE OCR :\n"

Réponse JSON strict imposée. `core.postprocess.clean_json` gère le cas où Gemma2 encapsule sa réponse dans des ```json``` blocks.

## API publique

```python
# core/prompt_gen.py

class PromptGenerationError(RuntimeError):
    """Raised when the LLM fails to produce a valid prompt draft."""

def generate_prompt_from_samples(samples: list[dict]) -> dict:
    """Generate a supplier prompt draft from 2-5 (ocr_text, expected) samples.

    Returns {"detecter": list[str], "prompt": str}. Both fields are
    guaranteed non-empty on success. Raises PromptGenerationError on
    invalid input or on any LLM / JSON failure.
    """
```

## Validation du résultat

Avant de renvoyer, on vérifie que le LLM a produit :
- un dict top-level,
- une clé `detecter` = liste non vide de chaînes,
- une clé `prompt` = chaîne non vide,
- les éléments de `detecter` strippés.

Si n'importe quelle condition échoue → `PromptGenerationError` avec un message concret.

## Non-garanties (volontaires)

- On **ne valide pas** que le prompt généré extrait correctement les échantillons. C'est le rôle du 4.4 (auto-test) — out of scope 4.1.
- On **ne stocke pas** le résultat dans `config/prompts/`. L'utilisateur humain doit relire et valider via `/admin` → qui appellera ensuite l'API CRUD existante.
- On **n'essaie pas** plusieurs fois en cas d'échec JSON. Le appelant relance s'il veut.

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | Samples valides + mock Ollama renvoyant JSON bien formé | Résultat `{detecter, prompt}` avec bonnes valeurs |
| 2 | Mock Ollama renvoie du JSON entouré de ```json``` fences | Parsé correctement (via clean_json) |
| 3 | Mock Ollama renvoie une string non-JSON | `PromptGenerationError` |
| 4 | Mock Ollama renvoie un dict sans `detecter` | `PromptGenerationError` avec mention de la clé |
| 5 | Mock Ollama renvoie un `prompt` vide | `PromptGenerationError` |
| 6 | samples = [] | `PromptGenerationError` |
| 7 | samples manque `ocr_text` | `PromptGenerationError` |
| 8 | Le meta-prompt envoyé à Ollama contient les 2 blocs "ÉCHANTILLON 1" / "ÉCHANTILLON 2" | Vérifié en inspectant l'appel mocké |
| 9 | OCR de 5000 chars est tronqué à 2000 | Vérifié dans le meta-prompt envoyé |
| 10 | Aucun import depuis `api.*` ni `scripts.*` | `core.prompt_gen` reste backend-pur |

## Plan de bascule

1. Créer `core/prompt_gen.py` (META_PROMPT + fonction + erreur).
2. Batterie de tests mocks (unittest.mock.patch sur `ollama.chat`).
3. Commit.
