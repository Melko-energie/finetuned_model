# UI d'édition des prompts — Design

**Date** : 2026-04-21
**Chantier** : 1.5 (interface web d'édition, premier livrable utilisateur final du chantier 1)
**Prérequis** : 1.1 (YAML) + 1.2 (validation) + 1.3 (hot-reload) + 1.4 (API CRUD)
**Statut** : design validé, en attente d'implémentation

---

## Contexte

Après 1.1-1.4, un développeur peut éditer un prompt via appel REST ou directement sur le fichier YAML. Le métier, lui, n'a toujours aucun moyen d'intervenir sans passer par l'IT.

1.5 livre la **première interface métier** : une page web qui liste, affiche, édite, crée et supprime les prompts en consommant l'API REST 1.4.

C'est le **pallier de valeur** qui justifie tout le chantier 1 : à partir d'ici, l'utilisateur métier peut modifier un prompt existant sans développeur (objectif "stop après 1.5" qu'on avait discuté dans le pitch).

## Objectif

Exposer à l'adresse `/admin` une page single-page-app (vanilla JS + Jinja2 template + Tailwind) qui couvre les opérations CRUD sur les prompts, dans un layout master-detail qui reste utilisable avec 30+ fournisseurs.

**Critère de réussite ultime** : un utilisateur métier ouvre `/admin`, clique sur `a2m`, modifie le prompt, sauvegarde, et la prochaine extraction A2M utilise la nouvelle version — sans aucune action côté IT.

## Décisions clés

| Décision | Choix | Justification |
|---|---|---|
| Layout | Master-detail (liste gauche, éditeur droite) | 32 entrées + gros blocs de texte → besoin de voir les deux en même temps. VS Code-like. |
| Rendu | Vanilla JS + fetch, pas de framework | Cohérent avec `/batch` qui fait déjà ça. Zéro nouvelle dépendance front. |
| Access | Lien "Admin" dans la sidebar, visible par tous | Pas d'auth (chantier 3). Mention visible "localhost seulement" dans l'UI. |
| Widget `detecter` | Textarea multi-ligne (1 mot-clé par ligne) | Simple, zéro lib. Les chips/tags = sur-ingénierie. |
| Widget `prompt` | Textarea grande taille, monospace | YAGNI : pas de syntax highlighting. Le JSON template reste lisible. |
| Confirmation suppression | Modale custom (pas `confirm()`) | Cohérence avec le design system. |
| Dirty tracking | Flag JS local + `confirm()` avant de quitter | Simple. |

## Conception

### Emplacement dans la navigation

Ajout d'un 5e lien dans la sidebar `templates/base.html`, après `/batch` :

```html
<a href="/admin" ... >
  <span class="material-symbols-outlined">settings</span>
  <span>Admin</span>
</a>
```

Icône : `settings` (Material Symbols). Actif si `active == "admin"` (passé en contexte).

### Route Python

Dans `main.py` :

```python
@app.get("/admin")
async def page_admin(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html", context={"active": "admin"})
```

Aucune logique serveur : le template est statique, les données viennent de l'API CRUD 1.4.

### Layout HTML (master-detail)

```
┌──────────────────────────────────────────────────────────────────┐
│  [sidebar]    Prompts (32)                     [+ Nouveau]       │
│              ─────────────────────────────────────────────────   │
│              ┌───────────────┬─────────────────────────────────┐ │
│              │ [🔍 search]   │  ← empty-state par défaut       │ │
│              │ ───────────── │                                 │ │
│              │ ▸ a2m         │  Clé : a2m  (type: supplier)    │ │
│              │   arcana      │  Mots-clés (un par ligne) :     │ │
│              │   ...         │  [textarea 4 rows]              │ │
│              │ ─── System    │  Prompt :                       │ │
│              │   default     │  [textarea 30 rows, monospace]  │ │
│              │   texte       │  [Save] [Delete (si supplier)]  │ │
│              └───────────────┴─────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Structure JS (`static/js/admin.js`)

État local :

```js
const state = {
  items: [],          // liste renvoyée par GET /api/admin/prompts
  currentKey: null,   // clé du prompt en cours d'édition (null = rien sélectionné)
  currentData: null,  // {detecter, prompt} chargés depuis le serveur (référence)
  isDirty: false,     // true si l'utilisateur a édité depuis le dernier load/save
  isNew: false,       // true si on crée un nouveau prompt
};
```

Fonctions principales :

- `loadList()` → `GET /api/admin/prompts`, peuple la colonne gauche, trie supplier/system.
- `loadDetail(key)` → `GET /api/admin/prompts/{key}`, peuple le formulaire de droite.
- `save()` → `POST` ou `PUT` selon `isNew`. Sur succès : refresh liste + toast.
- `remove()` → modale confirm → `DELETE`. Sur succès : reset form + refresh liste + toast.
- `startNew()` → vide le form, met `isNew=true`, focus sur le champ `key`.
- `filter(q)` → filtre la liste gauche par substring.

### Filtrage du champ `detecter` (un par ligne)

À l'écriture : on split sur `\n`, on trim, on ignore les lignes vides.
À la lecture : on join avec `\n`.

Côté serveur, l'API 1.4 reçoit une `list[str]` — le JS fait la conversion.

### Gestion des clés réservées (`texte`, `default`)

- Affichées dans un groupe "System" distinct dans la liste.
- Bouton Delete caché / désactivé pour ces clés.
- Pour `texte`, le champ `detecter` est masqué (non pertinent).
- Création (bouton "+ Nouveau") refuse ces clés côté UI (validation JS supplémentaire, en plus du 400 serveur).

### Feedback visuel

- **Toast succès** : petit bandeau vert en bas à droite, 3 sec.
- **Toast erreur** : idem mais rouge, texte = détail renvoyé par l'API.
- **Dirty indicator** : puce orange à côté de la clé courante, pastille "●" dans le titre.
- **État de chargement** : spinner pendant fetch (simple CSS).

## Critères d'acceptation

| # | Test | Résultat attendu |
|---|---|---|
| 1 | `GET /admin` | 200, page servie, sidebar avec lien Admin actif |
| 2 | Au chargement, la liste gauche se peuple | 32 entrées via `GET /api/admin/prompts` |
| 3 | Clic sur `a2m` | Le formulaire se remplit (key, detecter 4 lignes, prompt) |
| 4 | Clic sur `texte` | Le champ `detecter` est absent / caché |
| 5 | Edit + Save sur `a2m` | Toast succès, modification visible dans `GET /api/fournisseurs` via le reload auto de 1.4 |
| 6 | Bouton "+ Nouveau", saisir `ui_test_xyz` + prompt + save | Apparaît dans la liste sans refresh |
| 7 | Delete `ui_test_xyz` via modale | Disparaît de la liste |
| 8 | Tentative delete sur `default` | Bouton désactivé / absent |
| 9 | Saisir clé invalide `Bad-Key` au create | Erreur 422 du serveur affichée en toast |
| 10 | Create avec clé existante `a2m` | Erreur 409 du serveur affichée en toast |
| 11 | Edit sans save, cliquer un autre prompt | Confirmation "Modifications non sauvegardées ?" |
| 12 | Recherche "nvins" dans la barre | Liste filtrée aux 8 NVINS uniquement |
| 13 | Aucune régression sur `/texte`, `/smart`, `/nouvelle`, `/batch` | Tous 200, aucun changement visuel |

## Hors scope

| Chantier | Apport | Repoussé pourquoi |
|---|---|---|
| 3 (big plan) | Auth + permissions | Chantier dédié. |
| 2 (big plan) | Tester un prompt avec métriques | Banc d'évaluation, chantier dédié. |
| 4 (big plan) | Génération de prompt assistée par LLM | Cœur du pitch, chantier dédié. |
| 6 (big plan) | Dashboard / rapports | Trop tôt sans données d'usage. |
| — | Syntax highlighting / autocomplete | YAGNI. |
| — | Undo/redo, historique d'édition | Pas avant le versioning (hors scope 1.4 aussi). |
| — | Import/export bulk YAML | YAGNI tant qu'on ajoute un fournisseur à la fois. |

## Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Perte de modif en cas de navigation accidentelle | Moyenne | Moyen | `confirm()` sur unsaved changes + indicator dirty. |
| Utilisateur non-admin tombe sur `/admin` en prod | Moyenne | Critique | Bannière "localhost seulement, à protéger avant prod". Chantier 3 résout définitivement. |
| Textarea `prompt` mal adaptée à des prompts longs (>2000 chars) | Moyenne | Faible | Hauteur 30 rows + scroll vertical natif. `monospace` pour lisibilité. |
| Délai de reload après save fait croire à un bug | Faible | Faible | Toast "Sauvegardé" n'apparaît qu'après réponse OK, qui inclut le reload côté serveur. |

## Plan de bascule

1. Ajouter la route `GET /admin` dans `main.py`.
2. Ajouter le lien "Admin" dans `templates/base.html` (sidebar).
3. Créer `templates/admin.html` (extend `base.html`, master-detail layout).
4. Créer `static/js/admin.js` (fetch + DOM + state).
5. Smoke tests manuels (critères 1-13).
6. Commit unique : `feat(admin): prompts editor UI at /admin`.
