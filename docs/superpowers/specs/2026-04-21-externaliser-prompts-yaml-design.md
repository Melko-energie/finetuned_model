# Externaliser les prompts vers YAML — Design

**Date** : 2026-04-21
**Chantier** : 1.1 (premier sous-chantier de l'externalisation des prompts)
**Statut** : design validé, en attente de plan d'implémentation

---

## Contexte

Aujourd'hui, les 30 prompts d'extraction par fournisseur vivent en dur dans `core/prompts.py`, sous forme d'un grand dict Python `PROMPTS_INSTALLATEURS` (~700 lignes). Toute évolution d'un prompt — ajout d'un fournisseur, correction d'une particularité, ajustement d'une règle — exige :

1. d'éditer du code Python,
2. de redéployer l'application.

Cette dépendance au cycle développeur est incompatible avec la mise en production : le métier doit pouvoir intervenir lui-même, à terme via une UI dédiée.

Ce chantier (1.1) est la **première marche** vers cet objectif : sortir les prompts du code et les placer dans des fichiers de configuration éditables. Sans encore d'UI, sans rechargement à chaud, sans validation stricte. Juste le déplacement.

## Objectif

Déplacer le contenu de `PROMPTS_INSTALLATEURS` et `PROMPT_TEXTE` depuis `core/prompts.py` vers des fichiers YAML sous `config/prompts/`, sans changement de comportement observable.

**Critère de réussite ultime** : un développeur peut éditer le prompt d'un fournisseur en modifiant un fichier YAML (sans toucher au code Python), et l'application chargera la nouvelle version au prochain démarrage.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Format | YAML | Bloc texte propre (`prompt: \|`) pour les longs prompts multi-lignes. Surcoût `PyYAML` négligeable. |
| Emplacement | `config/prompts/` | Sémantique claire : configuration runtime éditable, distincte de `core/` (code) et `data/` (données métier brutes). Ouvre la voie à d'autres configs futures. |
| Granularité | 1 fichier par fournisseur | Diff PR lisible, ajout/suppression triviale, futur éditeur UI peut éditer un fichier à la fois. |
| Compatibilité API | Aucun changement | `core/detection.py`, `core/extraction.py`, `api/routes.py` ne sont pas touchés. |

## Conception

### Structure de fichiers

```
config/
└── prompts/
    ├── texte.yaml         # PROMPT_TEXTE (générique, page /texte)
    ├── default.yaml       # Fallback DEFAULT
    ├── a2m.yaml
    ├── arcana.yaml
    ├── ...
    └── total_energies.yaml
```

Le **stem du fichier** (nom sans extension) **est** la clé utilisée dans `PROMPTS_INSTALLATEURS`. Convention :

- `default.yaml` → clé `DEFAULT` (cas spécial, conservation de l'API existante)
- `texte.yaml` → exporté via `PROMPT_TEXTE` séparément (pas dans le dict)
- Tous les autres : `<stem>.yaml` → clé `<stem>` (lowercase, comme actuellement)

### Schéma d'un fichier fournisseur

```yaml
detecter:
  - "a2m elec"
  - "a2melec"
  - "a2melecmahdi@sfr.fr"

prompt: |
  Tu es un extracteur de données de factures BTP.
  ...
```

Schéma minimal :

- `detecter` : liste de chaînes (mots-clés OCR pour `detect_installateur`). Vide pour `default.yaml`.
- `prompt` : chaîne de caractères. Texte multi-lignes via `|` (block scalar).

Pour `texte.yaml` : seule la clé `prompt` est requise. Pas de `detecter`.

### Loader

`core/prompts.py` est réécrit comme un loader de ~30 lignes. Il expose la même API publique qu'aujourd'hui :

```python
import yaml
from pathlib import Path

_DIR = Path(__file__).resolve().parent.parent / "config" / "prompts"

def _load():
    prompts, generic = {}, ""
    for f in sorted(_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        key = f.stem
        if key == "texte":
            generic = data["prompt"]
            continue
        if key == "default":
            key = "DEFAULT"
        prompts[key] = {
            "detecter": data.get("detecter", []),
            "prompt": data["prompt"],
        }
    return prompts, generic

PROMPTS_INSTALLATEURS, PROMPT_TEXTE = _load()
```

Chargement **au moment de l'import** du module (comportement identique à l'actuel). Le rechargement à chaud arrivera en chantier 1.3.

### Migration (one-shot)

Un script `scripts/migrate_prompts.py` qui :

1. Importe l'ancien `PROMPTS_INSTALLATEURS` et `PROMPT_TEXTE` (depuis une copie figée de l'ancien `core/prompts.py`, sauvegardée temporairement en `core/prompts_legacy.py`).
2. Génère un fichier YAML par entrée dans `config/prompts/`.
3. Affiche un récap (`30 fichiers générés` + listing).

Workflow d'exécution :

```bash
python scripts/migrate_prompts.py    # une seule fois
# vérifier les fichiers générés
# puis remplacer core/prompts.py par le loader
# puis supprimer scripts/migrate_prompts.py et core/prompts_legacy.py
```

### Dépendance

Ajout de `pyyaml>=6.0` dans `requirements.txt`.

## Critères d'acceptation

Le refactor est validé si **toutes** ces conditions sont vérifiées :

1. **Parité de contenu** : pour chaque clé du `PROMPTS_INSTALLATEURS` original, la version chargée depuis YAML doit avoir : la même liste `detecter` (même ordre, mêmes chaînes) et le même `prompt` (chaîne identique caractère pour caractère). Idem pour `PROMPT_TEXTE`. L'ordre d'itération du dict global peut différer (alphabétique strict après refactor) — sans impact sur `detect_installateur` car les mots-clés sont disjoints entre fournisseurs (à vérifier au passage).
2. **Sanity test CLI** : `python scripts/extract_cli.py` produit la même sortie sur les 3 PDFs de référence (A2M, ESTEVE, TERNEL) qu'avant le refactor.
3. **Sanity test API** :
   - `GET /api/fournisseurs` retourne 30 entrées (idem qu'avant).
   - `GET /texte`, `GET /smart`, `GET /nouvelle`, `GET /batch` retournent 200.
4. **Robustesse loader** : trois cas d'erreur produisent une exception explicite (pas un crash silencieux ni un comportement inattendu) :
   - Fichier YAML mal formé.
   - Clé `prompt` absente d'un fichier fournisseur.
   - Dossier `config/prompts/` vide ou inexistant.
5. **Aucune régression** : `core/detection.py`, `core/extraction.py`, `api/routes.py`, les templates, et le JS frontend ne sont pas modifiés.

## Hors scope (chantiers ultérieurs)

Décisions explicitement repoussées :

| Chantier | Apport | Repoussé pourquoi |
|---|---|---|
| 1.2 | Validation stricte du schéma (Pydantic ou JSON Schema) | Le loader actuel suffit pour un format stable géré par développeurs. La validation devient critique quand des non-techs éditent (1.5). |
| 1.3 | Rechargement à chaud (file watcher ou endpoint reload) | Indépendant et plus complexe (gestion des locks, des erreurs de reload). |
| 1.4 | API CRUD REST sur les prompts | Inutile sans UI ni hot-reload. |
| 1.5 | UI d'édition des prompts | Premier livrable utilisateur final, mérite un design propre dédié. |

## Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| YAML mal échappé fait diverger un prompt par rapport à l'original (caractères spéciaux, retours à la ligne) | Moyenne | Élevé (régression silencieuse sur l'extraction) | Critère d'acceptation #1 (parité bit-à-bit du contenu sérialisé). Si écart, corriger le script de migration et recommencer. |
| `PyYAML` ajoute une dépendance native problématique sur Windows | Très faible | Faible | `PyYAML` est pure-Python en fallback, pas de compilation requise. |
| Quelqu'un édite un YAML, casse le format, et l'application refuse de démarrer | Faible (devs uniquement à ce stade) | Moyen | Loader lève une exception explicite mentionnant le fichier fautif. Validation stricte arrivera en 1.2. |
| Le dossier `config/prompts/` n'est pas embarqué dans le déploiement | Moyenne | Critique | Documenter dans le README. Vérifier en CI/au démarrage que le dossier contient au moins `texte.yaml` et `default.yaml`. |

## Plan de bascule

1. Créer le dossier `config/prompts/` (vide).
2. Sauvegarder `core/prompts.py` actuel en `core/prompts_legacy.py` (temporaire).
3. Écrire `scripts/migrate_prompts.py`.
4. Lancer la migration : 30 fichiers YAML générés sous `config/prompts/`.
5. Vérifier la parité (critère #1).
6. Réécrire `core/prompts.py` en loader.
7. Supprimer `scripts/migrate_prompts.py` et `core/prompts_legacy.py`.
8. Ajouter `pyyaml>=6.0` à `requirements.txt`.
9. Lancer les sanity tests CLI + API (critères #2 et #3).
10. Commit unique : `refactor(prompts): externalize PROMPTS_INSTALLATEURS to config/prompts/*.yaml`.
