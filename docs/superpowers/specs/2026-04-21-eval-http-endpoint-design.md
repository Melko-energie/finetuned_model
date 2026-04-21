# Endpoint HTTP d'évaluation — Design (chantier 2.6)

**Date** : 2026-04-21
**Chantier** : 2.6 (API REST pour le banc d'évaluation)
**Prérequis** : 2.1 → 2.5
**Statut** : validé, implémentation en cours

---

## Objectif

Exposer le banc d'évaluation (aujourd'hui CLI-only) via HTTP pour préparer l'UI "Tester un fournisseur" du chantier 5 (big plan). Le métier n'appellera pas directement ces endpoints — ils seront consommés par une page web plus tard.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Module | Nouveau `api/admin_eval.py` | `api/admin.py` commence à gonfler (prompts CRUD + reload). Les eval sont un domaine distinct. |
| Protection | Même `_require_localhost` (partagée via import) | Idem chantier 1.4. |
| Upload | Deux fichiers multipart : `pdfs_zip` + `truth_xlsx` | Plus simple qu'un ZIP contenant les deux. |
| Traitement | Synchrone pour MVP | Un eval de 50 PDFs prend quelques minutes. On documente "timeout long" pour l'UI 5. L'asynchrone arrivera si besoin. |
| Stockage résultat | Réutilise `save_run()` de 2.5 | Chaque éval HTTP créé un run comme les runs CLI. Même historique, même `list_runs()`. |
| Format Excel | Généré + stocké sous `data/eval_runs/<id>/report.xlsx` | Téléchargeable ensuite via un endpoint GET dédié. |

## URL space

```
POST   /api/admin/eval                            lance un run (multipart)
GET    /api/admin/eval/runs                       liste les runs
GET    /api/admin/eval/runs/{id}                  détail d'un run (result.json)
GET    /api/admin/eval/runs/{id}/download         télécharge le XLSX
GET    /api/admin/eval/runs/{a}/diff/{b}          diff structuré (JSON)
```

Tous derrière `Depends(_require_localhost)`.

## Contrats

### `POST /api/admin/eval`

Body : `multipart/form-data`
- `pdfs_zip` : fichier `.zip` contenant les PDFs à l'unité (arborescence libre, scan récursif côté serveur).
- `truth_xlsx` : le fichier Excel ground truth.

Réponse 200 :

```json
{
  "run_id": "2026-04-21_172030",
  "result": { /* même structure que run_eval.run_eval() */ },
  "download_url": "/api/admin/eval/runs/2026-04-21_172030/download"
}
```

Erreurs :
- 400 si ZIP/XLSX mal formés.
- 400 si aucun PDF ne matche le ground truth.

### `GET /api/admin/eval/runs`

Réponse 200 :
```json
{"runs": [ /* list_runs() format */ ]}
```

### `GET /api/admin/eval/runs/{id}`

Réponse 200 : le `result` complet. 404 si inconnu.

### `GET /api/admin/eval/runs/{id}/download`

Réponse 200 : le fichier `report.xlsx` du run (stream). 404 si inconnu ou si pas d'Excel.

### `GET /api/admin/eval/runs/{a}/diff/{b}`

Réponse 200 : le dict renvoyé par `diff_results(a, b)`. 404 si l'un des runs est inconnu.

## Implémentation — flux du POST

1. Réception multipart : `UploadFile` pour les deux.
2. Création d'un `tempfile.TemporaryDirectory()`.
3. `pdfs_zip` extrait dans `<tmp>/pdfs/`.
4. `truth_xlsx` sauvé en `<tmp>/truth.xlsx`.
5. `result = run_eval(Path(<tmp>/pdfs), Path(<tmp>/truth.xlsx))`.
6. `run_dir = save_run(result)`.
7. `dump_excel(result, run_dir / "report.xlsx")`.
8. Suppression du tempdir (automatique par context manager).
9. Renvoi du JSON.

## Critères d'acceptation

| # | Test | Attendu |
|---|---|---|
| 1 | POST avec ZIP + XLSX valides | 200 + run_id + result + download_url |
| 2 | POST sans `pdfs_zip` | 422 Pydantic |
| 3 | POST avec ZIP corrompu | 400 avec message clair |
| 4 | POST depuis non-localhost (mock) | 403 |
| 5 | GET /eval/runs après POST | Le nouveau run apparaît en tête |
| 6 | GET /eval/runs/{id} existant | 200 + full result |
| 7 | GET /eval/runs/{id} inconnu | 404 |
| 8 | GET /eval/runs/{id}/download | 200 + `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` + body non vide |
| 9 | GET /eval/runs/{id}/download sur run sans XLSX | 404 |
| 10 | GET /diff/{a}/{b} | 200 + structure du diff |
| 11 | GET /diff/{a}/{b} avec IDs inconnus | 404 |
| 12 | Aucune régression sur les routes existantes | Toutes 200 |

## Hors scope

- Streaming de progression (SSE) : ajouterai si l'UI 5 en a besoin
- Annulation d'un run en cours : YAGNI
- Notifications webhooks : YAGNI
- Upload de datasets stockés côté serveur (data/echantillon déjà sur disque) : YAGNI
