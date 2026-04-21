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

- **Les prompts vivent en dehors du code** dans `config/prompts/*.yaml` : ils sont éditables par le métier via une interface web `/admin` sans redéploiement.
- **Un banc d'évaluation intégré** (CLI + API HTTP) mesure objectivement la qualité d'extraction par champ et par fournisseur, compare deux runs pour détecter régressions et améliorations.

Public cible : équipes administratives qui manipulent des lots de factures BTP en français, et leurs référents techniques.

## Aperçu

L'interface FastAPI expose 5 pages :

| Page       | Usage                                                                  |
| ---------- | ---------------------------------------------------------------------- |
| `/texte`   | Prompt générique sur le texte OCR pré-calculé                          |
| `/smart`   | Détection automatique du fournisseur + prompt spécialisé               |
| `/nouvelle`| Upload d'une nouvelle facture (OCR live via DocTR)                     |
| `/batch`   | Extraction par lot d'un ZIP avec progression SSE et export Excel       |
| `/admin`   | **Interface d'édition des prompts** (CRUD + hot-reload)                |

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

## Installation

```bash
# 1. Cloner le repo
git clone https://github.com/Melko-energie/finetuned_model.git
cd finetuned_model

# 2. Créer un environnement virtuel
python -m venv venv
# Windows (Git Bash) :
source venv/Scripts/activate
# macOS / Linux :
# source venv/bin/activate

# 3. Installer les dépendances Python
pip install -r requirements.txt

# 4. Télécharger le modèle Gemma2 dans Ollama
ollama pull gemma2:9b
```

Raccourci avec le `Makefile` (cf. section [Make](#make)) :

```bash
make install
```

## Configuration

Aucune variable d'environnement requise. Tous les paramètres techniques sont centralisés dans **`core/config.py`** :

| Constante         | Valeur par défaut          | Rôle                                         |
| ----------------- | -------------------------- | -------------------------------------------- |
| `MODEL_NAME`      | `"gemma2:9b"`              | Modèle Ollama utilisé pour l'extraction      |
| `OLLAMA_OPTIONS`  | `{temperature: 0, seed: 42}` | Déterminisme : indispensable à chaque appel  |
| `OCR_DIR`         | `data/ocr_texts/`          | JSON DocTR pré-calculés                      |
| `PDF_DIR`         | `data/raw_pdfs/`           | PDF source organisés par fournisseur         |
| `ALL_FIELD_KEYS`  | 9 clés                     | Champs à extraire                            |

**Les prompts d'extraction** sont dans `config/prompts/*.yaml` (un fichier par fournisseur). Ils sont éditables :

- Manuellement à la main, puis rechargés via `POST /api/admin/reload-prompts`.
- Via l'interface web `/admin` qui fait l'édition + le reload automatiquement.

## Usage

### Interface web

```bash
uvicorn main:app --reload
```

Ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000). Si le port est bloqué (Windows réserve parfois 8000) :

```bash
uvicorn main:app --reload --port 8001
```

### Édition des prompts par le métier

Ouvrir [/admin](http://127.0.0.1:8001/admin) :

- Liste des 32 prompts à gauche (30 fournisseurs + `texte` + `default`), barre de recherche, groupes `Fournisseurs` / `Système`.
- Éditeur à droite : clé, mots-clés de détection, prompt multi-lignes.
- `+ Nouveau` pour créer un fournisseur.
- `Sauvegarder` recharge automatiquement l'application, la prochaine extraction utilise la nouvelle version.

⚠️ `/admin` est **protégé par une restriction localhost-only** tant que le chantier d'authentification n'est pas livré. **Ne pas exposer sur le réseau.**

### Pipeline OCR pour de nouvelles factures

```bash
# Déposer les PDF dans data/raw_pdfs/<fournisseur>/
python scripts/pdf_to_images.py   # PDF -> PNG (convention _page0, _page1…)
python scripts/run_ocr.py         # PNG -> JSON DocTR dans data/ocr_texts/
```

### Banc d'évaluation

Mesure objective de la qualité d'extraction sur un lot de factures, à partir d'un Excel de vérité terrain (ground truth).

**Format du ground truth** : même structure que l'export de `/batch` (feuille `Extractions` ou `TOUTES_FACTURES`). Flux pratique :

1. Lancer `/batch` sur un lot de factures connues → exporter en Excel.
2. Ouvrir l'Excel et corriger manuellement les cellules où l'extraction s'est trompée.
3. Sauver sous `ground_truth.xlsx`.

```bash
# Lancer une évaluation (sauvegardée automatiquement dans data/eval_runs/<timestamp>/)
python scripts/run_eval.py run --pdfs data/echantillon --truth ground_truth.xlsx --excel rapport.xlsx

# Lister les runs passés
python scripts/run_eval.py list

# Comparer deux runs (typiquement avant/après édition d'un prompt)
python scripts/run_eval.py diff previous latest
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

# Lancer un eval via HTTP
curl -F "pdfs_zip=@lot.zip" -F "truth_xlsx=@truth.xlsx" \
     http://127.0.0.1:8001/api/admin/eval
```

## Tests

Pas encore de suite de tests automatisés (chantier futur). La vérification de régression se fait via :

- `python scripts/extract_cli.py` qui rejoue 3 factures de référence.
- `python scripts/run_eval.py run --pdfs … --truth …` qui mesure la qualité sur un lot annoté + `diff previous latest` pour confirmer qu'un changement de prompt n'a pas régressé.

## Structure du projet

```
finetuned_model/
├── main.py                      # Entrée FastAPI (routes des pages + montage des routers)
├── api/
│   ├── routes.py                # Endpoints publics /api/* (extraction, batch, exports)
│   ├── admin.py                 # Endpoints admin /api/admin/* (CRUD prompts, reload)
│   └── admin_eval.py            # Endpoints admin /api/admin/eval/* (banc d'évaluation)
├── core/                        # Logique métier pure (zéro dépendance web)
│   ├── config.py                # Paths, MODEL_NAME, OLLAMA_OPTIONS, FIELDS
│   ├── prompts.py               # Loader YAML + reload() hot-swap
│   ├── detection.py             # detect_installateur, detect_avoir
│   ├── ocr.py                   # DocTR singleton + JSON loader + live pipeline
│   ├── postprocess.py           # clean_json, cohérence montants, blacklist SIP HQ
│   ├── extraction.py            # 3 entry points : texte, smart, live
│   ├── batch.py                 # iter_batch_zip, process_batch_zip
│   ├── excel.py                 # Exports Excel (single + multi-sheets)
│   └── eval/                    # Banc d'évaluation
│       ├── normalize.py         # Normalisation par champ (dates, nombres, accents)
│       ├── dataset.py           # Load ground truth Excel + index PDFs
│       ├── compare.py           # Verdicts match / mismatch / missing / unexpected
│       ├── metrics.py           # Agrégation globale + par fournisseur
│       ├── report.py            # Rendu terminal + dump JSON
│       ├── excel_report.py      # Rapport XLSX coloré (Summary / Details / Per-Supplier)
│       ├── history.py           # Sauvegarde et chargement des runs passés
│       ├── diff.py              # Diff structuré entre deux runs
│       └── runner.py            # Orchestration end-to-end
├── config/
│   └── prompts/*.yaml           # 30 fournisseurs + texte.yaml + default.yaml
├── templates/                   # Jinja2 (base, texte, smart, nouvelle, batch, admin)
├── static/js/                   # JS front (app.js, admin.js)
├── scripts/
│   ├── pdf_to_images.py         # PDF -> PNG
│   ├── run_ocr.py               # PNG -> JSON DocTR
│   ├── extract_cli.py           # Smoke test sur 3 PDFs
│   └── run_eval.py              # CLI eval (run / list / diff)
├── assets/logo.png
├── data/                        # gitignore (PDF, images, OCR, eval runs, listes installateurs)
│   ├── raw_pdfs/<fournisseur>/
│   ├── page_images/
│   ├── ocr_texts/
│   └── eval_runs/<id>/result.json (+ report.xlsx)
├── docs/superpowers/specs/      # Specs de design par chantier
├── Makefile
├── requirements.txt
└── README.md
```

**Règle d'architecture** : `api/` et `scripts/` consomment `core/`. `core/` n'a aucune dépendance à FastAPI ni à l'écosystème web. Les endpoints admin (CRUD prompts + eval) sont isolés dans leurs propres fichiers pour garder `routes.py` focalisé sur l'extraction publique.

## Fournisseurs supportés (30 profils)

### Fournisseurs principaux (22)

A2M, ARCANA, CAILLOCE, CLOROFIL, DILA, ECO2E, ESTEVE, EXIM, GAZ DE BORDEAUX, GAZETTE, GIGABAT, HESTIA, JLA, KELVIN, LOGISTA, OREA, OTIS, POULAIN, RCPI, SOCOTEC, TERNEL, TOTAL ENERGIES.

### Sous-installateurs NVINS (8 auto-facturations SIP AMIENS)

KLISZ, PROXISERVE, LOGISTA, L'UNION DES PEINTRES, SAS APPLI, TECHSOL, NUMERISS, SIP AMIENS (fallback).

Plus un prompt `DEFAULT` déclenché pour tout fournisseur non reconnu.

## Make

Cibles disponibles (nécessite [`make`](https://www.gnu.org/software/make/) installé) :

```bash
make install   # Crée le venv et installe les dépendances
make run       # Lance FastAPI sur le port 8001
make ocr       # Pipeline OCR complet : pdf_to_images puis run_ocr
make cli       # Smoke test extract_cli sur 3 PDFs
make clean     # Supprime les caches __pycache__
make help      # Liste les cibles
```

## Contraintes techniques

À respecter pour ne rien casser :

- `options={"temperature": 0, "seed": 42}` sur **chaque** appel Ollama (déjà centralisé dans `core/config.OLLAMA_OPTIONS`).
- OCR DocTR : `data["pages"][idx]` est une liste de tokens — **jamais** accéder via `blocks/lines/words` (ancien format).
- Convention nommage images : `_page0`, `_page1` (commence à 0, jamais `_page_001`).
- Réponse Gemma2 nettoyée via `core.postprocess.clean_json` pour retirer les balises markdown.
- Les prompts sont YAML, validés par Pydantic au chargement (champ `prompt` obligatoire et non vide, `detecter` liste de strings).

## État d'avancement

Projet de stage Melko Energie, livré par paliers :

| Chantier | Status | Valeur livrée |
|---|---|---|
| Refactor propre | ✅ | Séparation `core` / `api` / `scripts`, suppression du legacy Streamlit |
| 1 — Externaliser les prompts | ✅ | Fichiers YAML, UI `/admin`, hot-reload, API CRUD |
| 2 — Banc d'évaluation | ✅ | CLI + API, historique, diff A/B, normalisation dates/nombres |
| 3 — Authentification | ⏳ | Requis avant mise en production réseau |
| 4 — UI génération assistée | ⏳ | Cœur du pitch métier (input factures → prompt auto) |
| 5 — UI test d'un fournisseur | ⏳ | Consomme l'API d'évaluation déjà livrée |
| 6 — Dashboard / rapports | ⏳ | Post-usage réel |

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
