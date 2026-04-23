# Extraction de Factures BTP

> Extraction automatisée des champs de factures BTP francaises via OCR DocTR + LLM Gemma2:9b servi par Ollama, avec interface d'administration des prompts et banc d'évaluation intégré.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688)
![Ollama](https://img.shields.io/badge/LLM-gemma2%3A9b-orange)
![OCR](https://img.shields.io/badge/OCR-DocTR-7B61FF)

## Description

Application web qui extrait automatiquement 9 champs (numéro, date, HT, TVA, TTC, installateur, commune, code postal, adresse) depuis des PDF de factures BTP, sans appel à un service externe : tout tourne en local (OCR via DocTR, LLM via Ollama).

Conçue pour Melko Energie (gestion administrative de chantiers de rénovation énergétique), elle gère **30 profils de fournisseurs** avec des prompts spécialisés par émetteur — incluant les auto-facturations SIP AMIENS (sous-traitants NVINS).

**Ce que le projet apporte de spécifique** :

- **Les prompts vivent en dehors du code** dans `server/config/prompts/*.yaml` : ils sont éditables par le métier via une interface web `/admin` sans redéploiement.
- **Un banc d'évaluation intégré** (CLI + API HTTP + UI `/eval-lab`) mesure objectivement la qualité d'extraction par champ et par fournisseur, compare deux runs pour détecter régressions et améliorations.
- **Une UI expérimentale `/admin-lab`** permet de générer un nouveau prompt automatiquement à partir de 2-5 factures échantillons + un Excel de valeurs attendues (Gemma2 produit un brouillon, le métier relit et sauvegarde).

Public cible : équipes administratives qui manipulent des lots de factures BTP en français, et leurs référents techniques.

## Aperçu

L'interface FastAPI expose 7 pages :

| Page         | Usage                                                                    |
| ------------ | ------------------------------------------------------------------------ |
| `/texte`     | Prompt générique sur le texte OCR pré-calculé                            |
| `/smart`     | Détection automatique du fournisseur + prompt spécialisé                 |
| `/nouvelle`  | Upload d'une nouvelle facture (OCR live via DocTR)                       |
| `/batch`     | Extraction par lot d'un ZIP avec progression SSE et export Excel         |
| `/admin`     | Édition des prompts, version **stable** (CRUD + hot-reload)              |
| `/admin-lab` | Version **expérimentale** : `/admin` + génération assistée par LLM       |
| `/eval-lab`  | Banc d'évaluation web : upload → metrics en live → historique → diff A/B |

## Champs extraits

| Champ              | Description                          |
| ------------------ | ------------------------------------ |
| `NUMERO_FACTURE`   | Numéro complet de la facture         |
| `DATE_FACTURE`     | Date d'émission (JJ/MM/AAAA)         |
| `MONTANT_HT`       | Montant hors taxes                   |
| `TAUX_TVA`         | Taux TVA (5.5 %, 10 %, 20 %)         |
| `MONTANT_TTC`      | Montant TTC / Net à payer            |
| `NOM_INSTALLATEUR` | Entreprise émettrice                 |
| `COMMUNE_TRAVAUX`  | Ville du chantier                    |
| `CODE_POSTAL`      | Code postal du chantier              |
| `ADRESSE_TRAVAUX`  | Adresse complète du chantier         |

## Prerequisites

- **Python 3.11+**
- **Ollama** installé et lancé ([https://ollama.com](https://ollama.com))
- **GPU recommandé** : NVIDIA avec >= 12 GB VRAM (testé sur RTX 5080 Laptop, 15.9 GB)
- **OS** : Windows 11 (développé et testé). Les commandes shell ci-dessous fonctionnent sous Git Bash, WSL, macOS et Linux.

## Installation et lancement

### En une seule commande (recommandé)

```bash
git clone https://github.com/Melko-energie/finetuned_model.git
cd finetuned_model

# ↓ Tout-en-un : crée le venv, installe les dépendances, vérifie Ollama,
#   télécharge le modèle si absent, lance le serveur sur le port 8001.
python start.py
```

Premier lancement : 3 à 5 minutes (téléchargement du modèle `gemma2:9b` si absent).
Lancements suivants : ~5 secondes.

Quand le serveur est lancé, ouvrir [http://127.0.0.1:8001](http://127.0.0.1:8001).

`start.py` est un script Python pur, **cross-platform** (Windows / macOS / Linux), qui ne dépend que de Python lui-même — pas besoin de `make` ni d'autres outils externes.

### Sous-commandes disponibles

```bash
python start.py --help            # liste toutes les commandes
python start.py                   # ⭐ équivaut à 'go' : tout-en-un
python start.py go                # idem, explicite
python start.py install           # juste venv + dépendances Python
python start.py check             # diagnostique Ollama + modèle dispo
python start.py run               # lance uvicorn (suppose tout installé)
python start.py ocr               # pipeline OCR : PDFs → PNG → JSON
python start.py cli               # smoke test sur 3 factures de référence
python start.py eval --pdfs <dir> --truth <truth.xlsx>   # banc d'éval CLI
python start.py clean             # nettoie les caches __pycache__
```

Options globales : `--port 8002` pour changer le port d'écoute, `--model gemma3:latest` pour un autre modèle Ollama.

### Via Docker (pour tests en équipe)

Si tu veux faire essayer l'app à un collègue dev sans qu'il ait à toucher au venv Python, l'app est conteneurisée. Il aura besoin de :

1. **Docker Desktop** (Windows/Mac) ou `docker` + `docker compose` (Linux)
2. **Ollama Desktop** installé et lancé sur sa machine, avec le modèle pulled :
   ```bash
   ollama pull gemma2:9b
   ```

Puis :

```bash
git clone https://github.com/Melko-energie/finetuned_model.git
cd finetuned_model
docker compose up
```

Premier `up` : ~6 min (build de l'image, ~9 GB avec torch + cuda toolchain).
Ensuite : ~10 secondes au démarrage.

Ouvrir [http://localhost:8001](http://localhost:8001).

**Comment ça marche** : le container fait tourner FastAPI en isolé, mais se connecte à l'Ollama qui tourne sur la machine hôte (via `http://host.docker.internal:11434`). Avantages : pas besoin de GPU passthrough, le testeur garde son GPU local pour Ollama, et chacun peut tester sans interférer avec les autres.

Les volumes montés (`server/data/`, `server/config/prompts/`) font que les runs d'éval, les prompts édités via `/admin`, etc. **persistent entre les redémarrages** et restent éditables depuis l'hôte avec un éditeur normal (VS Code, etc.) hors du container.

```bash
docker compose up                # démarre
docker compose up --build        # rebuild après modif du code
docker compose down              # arrête + supprime le container
docker compose logs -f           # suit les logs
```

### Étape par étape (équivalent manuel)

Si tu veux comprendre / contrôler chaque étape sans passer par `start.py` :

```bash
# 1. venv
python -m venv venv
source venv/Scripts/activate    # Windows Git Bash
# source venv/bin/activate       # macOS / Linux

# 2. dépendances Python
pip install -r requirements.txt

# 3. Modèle Ollama (à faire une seule fois)
ollama pull gemma2:9b

# 4. Lancer le serveur
uvicorn main:app --reload --port 8001 --app-dir server
```

## Configuration

Aucune variable d'environnement requise. Tous les paramètres techniques sont centralisés dans **`server/core/config.py`** :

| Constante         | Valeur par défaut             | Rôle                                         |
| ----------------- | ----------------------------- | -------------------------------------------- |
| `MODEL_NAME`      | `"gemma2:9b"`                 | Modèle Ollama utilisé pour l'extraction      |
| `OLLAMA_OPTIONS`  | `{temperature: 0, seed: 42}`  | Déterminisme : indispensable à chaque appel  |
| `SERVER_ROOT`     | `<repo>/server/`              | Racine du code Python                        |
| `OCR_DIR`         | `server/data/ocr_texts/`      | JSON DocTR pré-calculés                      |
| `PDF_DIR`         | `server/data/raw_pdfs/`       | PDF source organisés par fournisseur         |
| `ALL_FIELD_KEYS`  | 9 clés                        | Champs à extraire                            |

**Les prompts d'extraction** sont dans `server/config/prompts/*.yaml` (un fichier par fournisseur). Ils sont éditables :

- Manuellement à la main, puis rechargés via `POST /api/admin/reload-prompts`.
- Via l'interface web `/admin` qui fait l'édition + le reload automatiquement.

## Usage

### Interface web

```bash
uvicorn main:app --reload --app-dir server
```

Ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000). Si le port est bloqué (Windows réserve parfois 8000) :

```bash
uvicorn main:app --reload --app-dir server --port 8001
```

Le `--app-dir server` indique à uvicorn d'aller chercher `main:app` dans le dossier `server/` (cf. [structure du projet](#structure-du-projet)).

### Édition des prompts par le métier

Ouvrir [/admin](http://127.0.0.1:8001/admin) (version stable) :

- Liste des 32 prompts à gauche (30 fournisseurs + `texte` + `default`), barre de recherche, groupes `Fournisseurs` / `Système`.
- Éditeur à droite : clé, mots-clés de détection, prompt multi-lignes.
- `+ Nouveau` pour créer un fournisseur.
- `Sauvegarder` recharge automatiquement l'application, la prochaine extraction utilise la nouvelle version.

### Génération assistée d'un nouveau prompt

Ouvrir [/admin-lab](http://127.0.0.1:8001/admin-lab) (version expérimentale) :

- Bouton `Générer depuis des factures`.
- Modal : saisir la clé du fournisseur + déposer 2 à 5 PDFs échantillons + un Excel ground truth (valeurs attendues).
- Le serveur lance l'OCR live sur chaque PDF puis demande à Gemma2 de produire un brouillon de prompt + une liste de mots-clés de détection, d'après les échantillons et les valeurs attendues.
- Le brouillon pré-remplit l'éditeur en mode `brouillon`, accompagné d'un panneau **Auto-test** qui extrait les mêmes samples avec le nouveau prompt et affiche l'accuracy par champ. L'utilisateur relit, corrige les champs problématiques, puis `Sauvegarder`.

### Évaluation sur un lot annoté (UI)

Ouvrir [/eval-lab](http://127.0.0.1:8001/eval-lab) :

- Upload d'un ZIP de PDFs + d'un Excel de vérité terrain (même format que l'export `/batch`).
- Barre de progression live via SSE (chantier 5.4) : `N/total PDFs traités`, % et nom du dernier PDF.
- Résultats : tuiles micro/macro, tableau par champ, liste par fournisseur (pires en premier), bouton de téléchargement du rapport XLSX coloré.
- Section **Historique** : liste des runs passés, clic `Voir` recharge sans réexécuter.
- Sélectionner 2 runs + `Comparer` → section diff : deltas global / par champ / par fournisseur + listes de régressions et améliorations par-PDF.

⚠️ `/admin`, `/admin-lab` et `/eval-lab` sont **protégés par une restriction localhost-only** tant que le chantier d'authentification n'est pas livré. **Ne pas exposer sur le réseau** (cette protection n'est PAS suffisante pour la production).

### Pipeline OCR pour de nouvelles factures

```bash
# Déposer les PDF dans server/data/raw_pdfs/<fournisseur>/
python server/scripts/pdf_to_images.py   # PDF -> PNG (convention _page0, _page1…)
python server/scripts/run_ocr.py         # PNG -> JSON DocTR dans server/data/ocr_texts/
```

### Banc d'évaluation

Mesure objective de la qualité d'extraction sur un lot de factures, à partir d'un Excel de vérité terrain (ground truth).

**Format du ground truth** : même structure que l'export de `/batch` (feuille `Extractions` ou `TOUTES_FACTURES`). Flux pratique :

1. Lancer `/batch` sur un lot de factures connues → exporter en Excel.
2. Ouvrir l'Excel et corriger manuellement les cellules où l'extraction s'est trompée.
3. Sauver sous `ground_truth.xlsx`.

```bash
# Lancer une évaluation (sauvegardée automatiquement dans server/data/eval_runs/<timestamp>/)
python server/scripts/run_eval.py run --pdfs server/data/echantillon --truth ground_truth.xlsx --excel rapport.xlsx

# Lister les runs passés
python server/scripts/run_eval.py list

# Comparer deux runs (typiquement avant/après édition d'un prompt)
python server/scripts/run_eval.py diff previous latest
```

Sortie terminal : accuracy par champ + globale, breakdown par fournisseur (pires en premier), barres ASCII. L'export Excel colore les cellules par verdict (match / mismatch / missing / unexpected).

### API REST

```bash
# Endpoints publics
curl http://127.0.0.1:8001/api/fournisseurs
curl -F "file=@facture.pdf" http://127.0.0.1:8001/api/extract-smart
curl -F "file=@lot.zip" http://127.0.0.1:8001/api/batch

# Endpoints admin (localhost-only)
curl http://127.0.0.1:8001/api/admin/prompts
curl -X POST http://127.0.0.1:8001/api/admin/reload-prompts

# Génération assistée d'un nouveau prompt
curl -F "key=acme_sarl" \
     -F "pdfs=@sample_a.pdf" -F "pdfs=@sample_b.pdf" \
     -F "truth_xlsx=@truth.xlsx" \
     http://127.0.0.1:8001/api/admin/prompts/generate

# Lancer un eval via HTTP (JSON sync)
curl -F "pdfs_zip=@lot.zip" -F "truth_xlsx=@truth.xlsx" \
     http://127.0.0.1:8001/api/admin/eval

# Lancer un eval en streaming SSE (recommandé pour les gros lots)
curl -N -F "pdfs_zip=@lot.zip" -F "truth_xlsx=@truth.xlsx" \
     http://127.0.0.1:8001/api/admin/eval/stream

# Historique + diff
curl http://127.0.0.1:8001/api/admin/eval/runs
curl http://127.0.0.1:8001/api/admin/eval/runs/<run_id>
curl http://127.0.0.1:8001/api/admin/eval/runs/<id_a>/diff/<id_b>
```

## Tests

Pas encore de suite de tests automatisés (chantier futur). La vérification de régression se fait via :

- `python server/scripts/extract_cli.py` qui rejoue 3 factures de référence.
- `python server/scripts/run_eval.py run --pdfs … --truth …` qui mesure la qualité sur un lot annoté + `diff previous latest` pour confirmer qu'un changement de prompt n'a pas régressé.

## Structure du projet

L'arborescence suit la convention **server / ui** utilisée sur tous les projets Melko : tout le Python vit dans `server/`, tout ce qui est rendu visuel vit dans `ui/`. Quelqu'un qui ouvre le repo sait immédiatement où chercher.

```
finetuned_model/
├── server/                            # Tout le Python (backend + données)
│   ├── main.py                        # Entrée FastAPI (routes des pages + montage des routers)
│   ├── api/
│   │   ├── routes.py                  # Endpoints publics /api/* (extraction, batch, exports)
│   │   ├── admin.py                   # Endpoints admin /api/admin/* (CRUD prompts, reload, generate)
│   │   └── admin_eval.py              # Endpoints admin /api/admin/eval/* (eval sync + SSE stream)
│   ├── core/                          # Logique métier pure (zéro dépendance web)
│   │   ├── config.py                  # SERVER_ROOT, paths, MODEL_NAME, OLLAMA_OPTIONS, FIELDS
│   │   ├── prompts.py                 # Loader YAML + reload() hot-swap
│   │   ├── detection.py               # detect_installateur, detect_avoir
│   │   ├── ocr.py                     # DocTR singleton + JSON loader + live pipeline
│   │   ├── postprocess.py             # clean_json, cohérence montants, blacklist SIP HQ
│   │   ├── extraction.py              # 3 entry points + extraire_champs_with_prompt (inline)
│   │   ├── batch.py                   # iter_batch_zip, process_batch_zip
│   │   ├── excel.py                   # Exports Excel (single + multi-sheets)
│   │   ├── prompt_gen.py              # Génération d'un brouillon de prompt via LLM (chantier 4)
│   │   └── eval/                      # Banc d'évaluation
│   │       ├── normalize.py           # Normalisation par champ (dates, nombres, accents)
│   │       ├── dataset.py             # Load ground truth Excel + index PDFs
│   │       ├── compare.py             # Verdicts match / mismatch / missing / unexpected
│   │       ├── metrics.py             # Agrégation globale + par fournisseur
│   │       ├── report.py              # Rendu terminal + dump JSON
│   │       ├── excel_report.py        # Rapport XLSX coloré (Summary / Details / Per-Supplier)
│   │       ├── history.py             # Sauvegarde et chargement des runs passés
│   │       ├── diff.py                # Diff structuré entre deux runs
│   │       └── runner.py              # iter_run_eval (SSE) + run_eval (wrapper sync)
│   ├── scripts/                       # CLIs one-shot
│   │   ├── pdf_to_images.py           # PDF -> PNG
│   │   ├── run_ocr.py                 # PNG -> JSON DocTR
│   │   ├── extract_cli.py             # Smoke test sur 3 PDFs
│   │   └── run_eval.py                # CLI eval (run / list / diff)
│   ├── config/
│   │   └── prompts/*.yaml             # 30 fournisseurs + texte.yaml + default.yaml
│   └── data/                          # gitignored (PDF, images, OCR, eval runs, listes)
│       ├── raw_pdfs/<fournisseur>/
│       ├── page_images/
│       ├── ocr_texts/
│       └── eval_runs/<id>/result.json (+ report.xlsx)
├── ui/                                # Tout ce qui est rendu visuel
│   ├── templates/                     # Jinja2 (base, texte, smart, nouvelle, batch,
│   │                                  #         admin, admin_lab, eval_lab)
│   └── static/js/                     # JS client (app.js, admin.js, admin_lab.js, eval_lab.js)
├── assets/logo.png                    # Branding projet
├── docs/superpowers/specs/            # Specs de design par chantier
├── start.py                           # Lanceur cross-platform pour dev local
├── Dockerfile                         # Image runtime (Python + deps + code)
├── docker-compose.yml                 # Stack de test pour l'équipe
├── .dockerignore                      # Exclut venv, data, docs des layers
├── requirements.txt
└── README.md
```

**Règles d'architecture** :

- `server/api/` et `server/scripts/` consomment `server/core/`. `server/core/` n'a aucune dépendance à FastAPI ni à l'écosystème web — testable en pur Python.
- `ui/templates/` est rendu **côté serveur** par FastAPI (Jinja2). Les fichiers HTML ne sont pas des SPAs autonomes ; ils ont besoin du serveur pour être affichés.
- `ui/static/js/` est le seul code qui s'exécute **réellement dans le navigateur** : appels REST vers `/api/*`, manipulation DOM, gestion d'état local.
- Les endpoints admin (CRUD prompts + éval) sont isolés dans leurs propres fichiers pour garder `routes.py` focalisé sur l'extraction publique.
- Pour démarrer le serveur : `uvicorn main:app --app-dir server` (le flag `--app-dir` indique à uvicorn d'aller chercher `main:app` dans le sous-dossier `server/`).

## Fournisseurs supportés (30 profils)

### Fournisseurs principaux (22)

A2M, ARCANA, CAILLOCE, CLOROFIL, DILA, ECO2E, ESTEVE, EXIM, GAZ DE BORDEAUX, GAZETTE, GIGABAT, HESTIA, JLA, KELVIN, LOGISTA, OREA, OTIS, POULAIN, RCPI, SOCOTEC, TERNEL, TOTAL ENERGIES.

### Sous-installateurs NVINS (8 auto-facturations SIP AMIENS)

KLISZ, PROXISERVE, LOGISTA, L'UNION DES PEINTRES, SAS APPLI, TECHSOL, NUMERISS, SIP AMIENS (fallback).

Plus un prompt `DEFAULT` déclenché pour tout fournisseur non reconnu.

## Contraintes techniques

À respecter pour ne rien casser :

- `options={"temperature": 0, "seed": 42}` sur **chaque** appel Ollama (déjà centralisé dans `core.config.OLLAMA_OPTIONS`, fichier `server/core/config.py`).
- OCR DocTR : `data["pages"][idx]` est une liste de tokens — **jamais** accéder via `blocks/lines/words` (ancien format).
- Convention nommage images : `_page0`, `_page1` (commence à 0, jamais `_page_001`).
- Réponse Gemma2 nettoyée via `core.postprocess.clean_json` pour retirer les balises markdown.
- Les prompts sont YAML, validés par Pydantic au chargement (champ `prompt` obligatoire et non vide, `detecter` liste de strings).

## État d'avancement

Projet de stage Melko Energie, livré par paliers :

| Chantier | Status | Valeur livrée |
|---|---|---|
| Refactor propre + split `server/ui/` | ✅ | Séparation `server/core` / `server/api` / `server/scripts` + `ui/templates` + `ui/static`, suppression du legacy Streamlit |
| 1 — Externaliser les prompts | ✅ | Fichiers YAML, UI `/admin`, hot-reload, API CRUD |
| 2 — Banc d'évaluation | ✅ | CLI + API, historique, diff A/B, normalisation dates/nombres |
| 3 — Authentification | ⏳ | **Requis avant mise en production réseau** |
| 4 — UI génération assistée | ✅ | `/admin-lab` + génération via Gemma2 + auto-test sur échantillons |
| 5 — UI test d'un fournisseur | ✅ | `/eval-lab` avec historique, diff A/B, progression SSE |
| 6 — Dashboard / rapports | ⏳ | Post-usage réel, quand données d'usage accumulées |

## Limites connues (à retenir avant déploiement)

- **Aucune authentification** : les pages `/admin`, `/admin-lab`, `/eval-lab` et tous les endpoints `/api/admin/*` ne sont protégés que par un check "localhost-only" côté serveur. Ce n'est **pas** de la sécurité — tout processus co-hébergé (container, second utilisateur) peut y accéder. À remplacer par une vraie authentification (chantier 3) avant toute exposition réseau.
- **Aucune suite de tests automatisés** dans le repo : la vérification se fait manuellement via `server/scripts/extract_cli.py` et via le banc d'évaluation. Une suite pytest est à prévoir.
- **Appels Ollama séquentiels** dans les batch et les évaluations : un lot de 100 PDFs prend ~15-20 min alors que Gemma2 sur RTX 5080 supporte 2-3 requêtes concurrentes. Optimisation via `ThreadPoolExecutor` possible pour diviser le temps par 3.
- **L'auto-test du chantier 4.4** évalue le prompt généré sur **les mêmes échantillons qui ont servi à le produire** : l'accuracy affichée est un indicateur de cohérence, pas une vraie mesure de généralisation. Toujours vérifier ensuite sur des factures nouvelles via `/eval-lab`.
- **Duplication `/admin` / `/admin-lab`** : les deux pages partagent le même backend mais ont chacune leur template et leur JS. À fusionner une fois les features lab stabilisées.
- **Pas de versioning des prompts** côté UI : l'historique n'est accessible que via `git log`. Si un utilisateur casse un prompt, la récupération demande un développeur.
- **Pas de rate limiting** sur les endpoints : protection à ajouter avant toute exposition.

## Contributing

1. Fork du dépôt
2. Créer une branche feature : `git checkout -b feature/ma-feature`
3. Commit : `git commit -m "feat: ma feature"`
4. Push : `git push origin feature/ma-feature`
5. Ouvrir une Pull Request

## License

Projet de stage — propriété intellectuelle Melko Energie. Aucune licence open source actuellement attachée.

---

Stage 2026 — MADANI Yassine | Melko Energie
