# API CRUD prompts — Design

**Date** : 2026-04-21
**Chantier** : 1.4 (CRUD REST sur les fichiers `config/prompts/*.yaml`)
**Prérequis** : 1.1 (YAML) + 1.2 (validation Pydantic) + 1.3 (hot-reload endpoint)
**Statut** : design validé, en attente d'implémentation

---

## Contexte

Après 1.1-1.3, les prompts sont éditables sur disque et le serveur peut recharger sans redémarrer. Mais éditer reste manuel : ouvrir un fichier YAML dans un éditeur de texte, écrire, sauvegarder, puis curl pour reload.

1.4 expose une **API REST** sur ces fichiers. Sans elle, l'UI d'édition (1.5) n'aurait rien à consommer.

## Objectif

Cinq endpoints REST sur `/api/admin/prompts` couvrant les opérations standards : list, read, create, update, delete. Chaque mutation déclenche le `reload()` de 1.3 pour propager immédiatement le changement à l'extraction.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Clés réservées (`texte`, `default`) | Visibles + éditables (PUT), non créables (POST refusé) ni supprimables (DELETE refusé) | Le métier doit pouvoir affiner le prompt générique et le fallback ; mais leur absence casserait le loader. |
| Auto-reload après mutation | Oui, automatique après chaque POST/PUT/DELETE | UX naturelle ; sauvegarder sans activer n'a aucun sens. `?reload=false` ajoutable plus tard si besoin batch. |
| Versioning / historique | Aucun | Out of scope : git pour les devs, hors périmètre métier. Si on veut un historique métier-friendly, ce sera un chantier dédié (rétention, restauration, UI). |
| Module | Nouveau `api/admin.py` | Sépare clairement les endpoints d'administration des endpoints d'extraction publique. Y déplace aussi `_require_localhost` et `/admin/reload-prompts` de 1.3. |
| Écriture sur disque | Atomique via `os.replace(tmp, path)` | Évite qu'un crash en plein write laisse un YAML corrompu. |

## Conception

### URL space

```
GET    /api/admin/prompts            → liste (métadonnées seules)
GET    /api/admin/prompts/{key}      → détail complet
POST   /api/admin/prompts            → création (key dans le body)
PUT    /api/admin/prompts/{key}      → modification
DELETE /api/admin/prompts/{key}      → suppression
```

Toutes les routes derrière `Depends(_require_localhost)` jusqu'à chantier 3 (auth).

### Schémas Pydantic

```python
KEY_PATTERN = r"^[a-z][a-z0-9_]*$"

class PromptCreate(BaseModel):
    key: str = Field(pattern=KEY_PATTERN, max_length=50)
    detecter: list[str] = Field(default_factory=list)
    prompt: str = Field(min_length=1)

class PromptUpdate(BaseModel):
    detecter: list[str] = Field(default_factory=list)
    prompt: str = Field(min_length=1)

class PromptDetail(BaseModel):
    key: str
    type: Literal["supplier", "system"]
    detecter: list[str]
    prompt: str

class PromptListItem(BaseModel):
    key: str
    type: Literal["supplier", "system"]
    detecter_count: int
    prompt_chars: int
```

### Règles métier

- `RESERVED_KEYS = {"texte", "default"}` — un set en tête du module.
- `type` est calculé : `"system"` si la clé est dans `RESERVED_KEYS`, `"supplier"` sinon.
- `POST` avec une clé réservée → 400 (`"reserved key"`).
- `DELETE` avec une clé réservée → 400 (`"reserved key, cannot delete"`).
- `POST` avec une clé qui correspond à un fichier existant → 409 (`"already exists"`).
- `PUT` sur `texte` : on ignore le champ `detecter` (toujours forcé à `[]` car la clé n'a aucun sens pour le prompt générique).
- Validation regex de la clé via Pydantic `Field(pattern=...)` → erreur 422 automatique.

### Format des réponses

`GET /prompts` :
```json
{
  "prompts": [
    {"key": "a2m", "type": "supplier", "detecter_count": 4, "prompt_chars": 1234},
    {"key": "default", "type": "system", "detecter_count": 0, "prompt_chars": 567},
    {"key": "texte", "type": "system", "detecter_count": 0, "prompt_chars": 910}
  ]
}
```

Triée par `key` ASC.

`GET /prompts/{key}` :
```json
{
  "key": "a2m",
  "type": "supplier",
  "detecter": ["a2m elec", "..."],
  "prompt": "Tu es un extracteur..."
}
```

`POST /prompts` (201) : même shape que GET détail.

`PUT /prompts/{key}` (200) : même shape.

`DELETE /prompts/{key}` (200) :
```json
{"status": "deleted", "key": "acme_test"}
```

### Helper d'écriture atomique

```python
def _write_yaml_atomic(path: Path, payload: dict) -> None:
    """Dump payload to YAML, write atomically via tmp + replace."""
    rendered = yaml.dump(
        payload,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=10_000,
    )
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(rendered, encoding="utf-8")
    os.replace(tmp, path)
```

Multi-line strings (le `prompt`) sont sérialisés via le custom `_BlockStr` representer (même technique que `scripts/migrate_prompts.py` à l'origine — réutilisable).

### Flux d'une mutation

1. Pydantic valide le body (regex de la clé, `prompt` non vide).
2. Vérifications métier : clé réservée ? doublon ? clé existante ?
3. Construction du payload YAML (avec normalisation `detecter=[]` pour `texte`).
4. Écriture atomique sur disque.
5. Appel à `core.prompts.reload()`.
   - Si reload échoue (cas pathologique : édition concurrente d'un autre fichier) → réponse 500 avec le message d'erreur, fichier laissé en place pour investigation.
6. Retour de la réponse 200/201 avec le contenu sauvé.

## Critères d'acceptation

| # | Test | Résultat attendu |
|---|---|---|
| 1 | `GET /api/admin/prompts` | 200, liste de 32 éléments (30 supplier + 2 system), triée par key |
| 2 | `GET /api/admin/prompts/a2m` | 200, contenu identique au YAML sur disque |
| 3 | `GET /api/admin/prompts/inexistant` | 404 |
| 4 | `POST` créer `acme_test` puis `GET /api/fournisseurs` | acme_test dans la liste (auto-reload effectif) |
| 5 | `POST /api/admin/prompts` avec `key=texte` | 400, message "reserved key" |
| 6 | `POST /api/admin/prompts` avec `key=a2m` (doublon) | 409 |
| 7 | `POST /api/admin/prompts` avec `key="Bad-Key"` | 422 (Pydantic regex) |
| 8 | `PUT /api/admin/prompts/texte` avec `detecter=["junk"]` | 200, fichier sur disque a `detecter` absent ou vide |
| 9 | `DELETE /api/admin/prompts/default` | 400, "reserved key, cannot delete" |
| 10 | `DELETE /api/admin/prompts/inexistant` | 404 |
| 11 | `DELETE /api/admin/prompts/acme_test` (créé en #4) puis `GET /api/fournisseurs` | acme_test absent (auto-reload effectif) |
| 12 | Aucun fichier `.yaml.tmp` ne traîne après tous les tests | Atomicité confirmée |

## Hors scope

| Chantier | Apport | Repoussé pourquoi |
|---|---|---|
| 1.5 | UI d'édition (consomme cette API) | Suite logique, design à part. |
| 3 | Auth réelle | Remplacera `_require_localhost`. |
| Futur | Versioning / historique | Décisions lourdes (rétention, restauration), pas urgent. |
| Futur | Bulk operations / import multiple | YAGNI tant qu'on ajoute les fournisseurs un par un. |

## Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Race condition : deux PUT simultanés sur le même fichier | Faible (1 utilisateur à ce stade) | Le dernier gagne (perte silencieuse) | Acceptable. À traiter avec un lock ou ETag si plusieurs admins concurrents. |
| Reload échoue après écriture (autre fichier corrompu) | Très faible | L'API renvoie 500 mais le fichier est sauvegardé | Documenter : si 500 sur write, regarder les logs et appeler manuellement reload après correction du fichier fautif. |
| Suppression accidentelle d'un fournisseur en production | Moyenne (UX manuelle) | Critique tant qu'il n'y a ni confirmation UI ni historique | Out of scope 1.4. UI 1.5 ajoutera une confirmation modale. |
| Fichier `.yaml.tmp` laissé en place après crash en plein write | Très faible | Pollution du dossier, pas chargé par le loader (filtre `.yaml`) | Le loader ignore `.yaml.tmp` (extension différente). Au prochain write, `os.replace` écrase. |

## Plan de bascule

1. Créer `api/admin.py` avec :
   - Imports (yaml, fastapi, pydantic, core.prompts).
   - `RESERVED_KEYS`, `KEY_PATTERN`.
   - `_require_localhost` (déplacé depuis `api/routes.py`).
   - Helpers : `_write_yaml_atomic`, `_classify`, `_path_for(key)`.
   - Modèles Pydantic.
   - Router avec prefix `/api/admin` et les 6 endpoints (5 CRUD + reload-prompts existant).
2. Retirer de `api/routes.py` : `_require_localhost`, l'endpoint `/admin/reload-prompts`, et les imports devenus inutiles (`Request`, `JSONResponse`, `datetime`, `Depends`, `HTTPException`, `PromptConfigError`, `reload as reload_prompts`).
3. Inclure le nouveau router dans `main.py` : `app.include_router(admin_router)`.
4. Smoke tests manuels (les 12 critères ci-dessus).
5. Commit unique : `feat(prompts): CRUD REST API on /api/admin/prompts`.
