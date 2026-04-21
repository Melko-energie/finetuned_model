# Endpoint HTTP de génération — Design (chantier 4.2)

**Date** : 2026-04-21
**Chantier** : 4.2 (endpoint HTTP qui enveloppe 4.1)
**Prérequis** : 4.1 (generator backend)
**Statut** : validé, implémentation en cours

---

## Objectif

Exposer la fonction `generate_prompt_from_samples` de 4.1 derrière un endpoint HTTP multipart, pour que la future UI `/admin-lab` (chantier 4.3) puisse la consommer simplement depuis le navigateur.

**Flux cible** : upload multipart (clé + 2-5 PDFs + Excel ground truth) → OCR live sur chaque PDF → appariement avec le truth → génération → JSON draft retourné.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Module | `api/admin.py` (endroit existant des endpoints prompts) | Cohérence topologique. Split si ça gonfle plus tard. |
| URL | `POST /api/admin/prompts/generate` | Sémantiquement `prompts/*`. |
| Protection | `Depends(_require_localhost)` existant | Idem tous les admins. |
| Input PDFs | Liste de `UploadFile` (multipart plain, pas de ZIP) | L'UI a naturellement N inputs file. ZIP inutile pour 2-5 fichiers. |
| Input truth | Excel upload (pas un JSON inline) | Le métier sait déjà produire cet Excel (export `/batch` + corrections). |
| Collision de clé | Pas de vérif ici — la clé peut exister | On génère un **draft** ; c'est l'étape `POST /api/admin/prompts` (save) qui tranche. |
| OCR | Live DocTR via `run_doctr_ocr` | Les PDFs sont nouveaux, pas de pré-calcul dispo. |

## Contrat HTTP

`POST /api/admin/prompts/generate`

Body : `multipart/form-data`
- `key` (string, required) — regex `^[a-z][a-z0-9_]*$`, max 50 chars, pas dans `{texte, default}`.
- `pdfs` (file, required, 2-5 fichiers) — les échantillons.
- `truth_xlsx` (file, required) — Excel avec feuille `Extractions` ou `TOUTES_FACTURES`, colonne `Nom du PDF` pour le matching.

**Réponse 200** :
```json
{
  "key": "acme_sarl",
  "detecter": ["ACME SARL", "FA-2026", "80000"],
  "prompt": "Tu es un extracteur de données de factures BTP..."
}
```

**Erreurs** :

| Code | Cause |
|---|---|
| 400 | clé invalide (regex), clé réservée, PDF non apparié dans le truth, Excel sans feuille attendue |
| 422 | champs multipart manquants |
| 500 | `PromptGenerationError` remontée depuis 4.1 |

## Flux de traitement

```
1. Valider key (regex + réservé)
2. Valider nombre de PDFs (2-5)
3. Lire truth_xlsx (bytes) → temp file → load_ground_truth()
4. Construire pdf_filename → expected_fields (par nom de fichier sans extension)
5. Pour chaque UploadFile :
     - filename = uploaded_file.filename
     - lookup dans le truth → si absent, 400
     - ocr_text = run_doctr_ocr(file_bytes, suffix=".pdf")
     - samples.append({"ocr_text": ocr_text, "expected": expected_fields})
6. draft = generate_prompt_from_samples(samples)
7. return {"key": key, "detecter": draft["detecter"], "prompt": draft["prompt"]}
```

## Validation dès que possible

L'ordre des validations est conçu pour **rater vite** (pas d'OCR si la clé est mauvaise, pas d'OCR si un PDF manque dans le truth). Les OCR sont ce qu'il y a de plus lent (~5-10s par PDF), donc on ne les lance qu'après toutes les vérifs cheap.

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | Happy path (mocks OCR + generator) | 200 + shape `{key, detecter, prompt}` |
| 2 | Clé invalide `Bad-Key` | 422 Pydantic (regex) |
| 3 | Clé réservée `texte` | 400 "reserved" |
| 4 | 1 seul PDF | 400 "at least 2" |
| 5 | 6 PDFs | 400 "max 5" |
| 6 | PDF absent du truth | 400 nommant le PDF |
| 7 | Excel sans feuille attendue | 400 listant les feuilles trouvées |
| 8 | `PromptGenerationError` depuis 4.1 | 500 avec le message |
| 9 | Non-localhost (mock) | 403 |
| 10 | Aucune régression sur les autres endpoints | tous 200 |

## Hors scope

- 4.3 — UI (branche ce endpoint)
- 4.4 — Auto-test du prompt généré
- Streaming de progression SSE (tous les OCR d'un coup) — YAGNI, 3 PDFs tiennent en ~30s
- Support de formats d'images autres que PDF — YAGNI
