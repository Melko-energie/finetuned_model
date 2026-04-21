# Hot-reload des prompts — Design

**Date** : 2026-04-21
**Chantier** : 1.3 (rechargement à chaud des fichiers YAML sans redémarrage du serveur)
**Prérequis** : chantiers 1.1 + 1.2 (prompts externalisés en YAML + validation Pydantic)
**Statut** : design validé, en attente d'implémentation

---

## Contexte

Après 1.1 + 1.2, les prompts vivent dans `config/prompts/*.yaml` et sont chargés au démarrage du serveur FastAPI. Modifier un prompt reste donc impossible sans redéploiement (ou au moins redémarrage d'Uvicorn).

Objectif de 1.3 : permettre la prise en compte d'une modification d'un YAML **sans interrompre le service**.

## Objectif

Exposer un endpoint HTTP qui relit `config/prompts/*.yaml` et remplace atomiquement l'état en mémoire. Si la validation 1.2 échoue, l'état précédent doit rester intact.

**Critère de réussite ultime** : un développeur (puis plus tard le métier via l'UI 1.5) édite un YAML, appelle l'endpoint, et la requête suivante d'extraction utilise la nouvelle version — sans avoir redémarré le serveur.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Trigger | Endpoint HTTP explicite `POST /api/admin/reload-prompts` | Déterministe, zéro dépendance ajoutée, réutilisable par l'UI 1.5. Un file-watcher peut être ajouté plus tard si besoin. |
| Mécanisme de propagation | Mutation en place du dict `PROMPTS_INSTALLATEURS` | Pas besoin de modifier les consommateurs (`detection.py`, `extraction.py`, `batch.py`) qui importent le dict. |
| `PROMPT_TEXTE` (immutable) | Consommateur bascule sur `from core import prompts` + `prompts.PROMPT_TEXTE` | Une ligne à changer dans `core/extraction.py`. Alternative plus lourde évitée. |
| Protection | Check localhost-only (`127.0.0.1` et `::1`) | Sécurité minimale tant que l'auth (chantier 3) n'existe pas. À remplacer par une vraie dépendance d'auth ensuite. |
| Atomicité | Charger-puis-swap : `_load_all()` doit réussir avant de toucher l'état en mémoire | Un YAML cassé ne doit pas laisser l'application dans un état moitié-vide. |

## Conception

### Contrat de l'endpoint

`POST /api/admin/reload-prompts`

**Succès (200)** :
```json
{
  "status": "ok",
  "loaded_at": "2026-04-21T15:23:45Z",
  "prompts_count": 30,
  "files": ["a2m.yaml", "arcana.yaml", "default.yaml", "..."]
}
```

- `prompts_count` : nombre d'entrées dans `PROMPTS_INSTALLATEURS` (hors `PROMPT_TEXTE`).
- `files` : liste triée des fichiers effectivement chargés.
- `loaded_at` : timestamp ISO-8601 UTC.

**Échec validation (400)** :
```json
{
  "status": "error",
  "error": "default.yaml: schema validation failed — prompt: Field required"
}
```

État précédent **préservé** : le prochain appel à `/api/extract-smart` utilise encore les prompts pré-reload.

**Hors localhost (403)** :
```json
{
  "detail": "Reload endpoint is localhost-only"
}
```

### Fonction `reload()` dans `core/prompts.py`

```python
def reload():
    """Re-read config/prompts/*.yaml and swap the in-memory state atomically.
    Raises PromptConfigError if the new state fails validation; in that case
    the existing PROMPTS_INSTALLATEURS and PROMPT_TEXTE remain unchanged."""
    new_prompts, new_texte = _load_all()   # can raise; state still intact
    PROMPTS_INSTALLATEURS.clear()
    PROMPTS_INSTALLATEURS.update(new_prompts)
    global PROMPT_TEXTE
    PROMPT_TEXTE = new_texte
```

Le dict `PROMPTS_INSTALLATEURS` reste **le même objet en mémoire** — seul son contenu change. Tous les consommateurs voient automatiquement la nouvelle version au prochain accès.

### Bascule du pattern d'accès pour `PROMPT_TEXTE`

`core/extraction.py` actuel :

```python
from core.prompts import PROMPTS_INSTALLATEURS, PROMPT_TEXTE
...
prompt = PROMPT_TEXTE.format(texte=...)
```

Après 1.3 :

```python
from core.prompts import PROMPTS_INSTALLATEURS
from core import prompts as _prompts
...
prompt = _prompts.PROMPT_TEXTE.format(texte=...)
```

Raison : la chaîne `PROMPT_TEXTE` est immutable. Si on faisait `PROMPT_TEXTE = new_texte` dans `core/prompts.py`, l'import `from ... import PROMPT_TEXTE` du consommateur conserverait l'ancienne référence. L'accès via `_prompts.PROMPT_TEXTE` lit toujours la valeur courante du module.

### Protection localhost

```python
def _require_localhost(request: Request):
    if request.client.host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=403, detail="Reload endpoint is localhost-only")
```

Appliqué à l'endpoint de reload uniquement via `Depends(_require_localhost)`.

**À retirer/remplacer** quand chantier 3 (auth) ajoutera une vraie dépendance `Depends(current_admin_user)`.

## Critères d'acceptation

1. **Hot-reload fonctionnel** : éditer `config/prompts/a2m.yaml` (par exemple ajouter un mot-clé `detecter`), appeler `POST /api/admin/reload-prompts`, puis vérifier via une introspection du dict que le nouveau mot-clé est bien présent.
2. **Échec de reload = état conservé** : introduire un YAML invalide, appeler l'endpoint → 400 avec message nommant le fichier fautif. Un appel subséquent à `/api/fournisseurs` retourne toujours la liste complète (état d'avant reload).
3. **Atomicité** : pendant qu'une requête d'extraction tourne, un reload en parallèle ne fait pas crasher l'extraction en cours (le dict reste le même objet Python).
4. **Protection localhost** : requête depuis `127.0.0.1` → 200 ; requête simulée depuis une autre IP → 403.
5. **Aucune régression** : `scripts/extract_cli.py` produit la même sortie qu'avant 1.3 (le comportement par défaut est identique, seul un endpoint est ajouté).

## Hors scope (chantiers ultérieurs)

| Chantier | Apport | Repoussé pourquoi |
|---|---|---|
| 1.3.B (éventuel) | File watcher automatique | Sur-ingénierie pour le besoin actuel. L'endpoint suffit et l'UI 1.5 l'utilisera directement. |
| 1.4 | API CRUD (lecture/écriture des YAML via REST) | Chantier distinct, nécessite un plan propre. |
| 1.5 | UI d'édition avec bouton "Sauvegarder" qui appelle cet endpoint | Point d'appel naturel de `/api/admin/reload-prompts`. |
| 3 | Auth réelle + permissions | Remplacera le check localhost-only. |

## Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Reload échoue silencieusement sans remonter l'erreur | Faible | Élevé (illusion de fonctionnement) | L'endpoint retourne explicitement 400 avec le message de `PromptConfigError`. |
| État partiellement mis à jour (dict à moitié clearé) si une exception survient pendant `.update()` | Très faible | Critique | Toute erreur de validation est capturée **avant** le `.clear()` (appel à `_load_all()` qui lève). Le seul scénario restant est une erreur système (MemoryError) pendant `.update()` — négligeable en pratique. |
| Endpoint accessible depuis Internet si déployé derrière un proxy qui masque l'IP source | Moyenne (en cas de déploiement) | Critique | Documenter dans le README que l'application ne doit pas être exposée publiquement tant que chantier 3 n'a pas livré. Le check localhost reste une ceinture de sécurité, pas une solution finale. |
| Plusieurs workers uvicorn : un reload sur un worker ne propage pas aux autres | Moyenne (en prod multi-worker) | Moyen | Hors scope 1.3. À résoudre si/quand le déploiement passe en multi-worker (Redis pub/sub ou équivalent). |

## Plan de bascule

1. Ajouter `reload()` à `core/prompts.py`.
2. Modifier `core/extraction.py` pour accéder à `PROMPT_TEXTE` via `_prompts.PROMPT_TEXTE`.
3. Ajouter dans `api/routes.py` : la dépendance `_require_localhost` et l'endpoint `POST /api/admin/reload-prompts`.
4. Smoke tests manuels :
   a. Appeler l'endpoint → 200, vérifier le payload.
   b. Éditer `a2m.yaml` (ajout d'un mot-clé), rappeler l'endpoint, vérifier que `/api/fournisseurs` reflète l'état attendu.
   c. Casser un YAML, rappeler l'endpoint → 400 avec le nom du fichier.
   d. Simuler une requête non-localhost → 403.
5. Commit unique : `feat(prompts): hot-reload endpoint POST /api/admin/reload-prompts`.
