# Extraction de Factures BTP

> Extraction automatisée des champs de factures BTP francaises via OCR DocTR + LLM Gemma2:9b servi par Ollama.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688)
![Ollama](https://img.shields.io/badge/LLM-gemma2%3A9b-orange)
![OCR](https://img.shields.io/badge/OCR-DocTR-7B61FF)

## Description

Application web qui extrait automatiquement 9 champs (numero, date, HT, TVA, TTC, installateur, commune, code postal, adresse) depuis des PDF de factures BTP, sans appel a un service externe : tout tourne en local (OCR via DocTR, LLM via Ollama).

Concue pour Melko Energie (gestion administrative de chantiers de renovation energetique), elle gere **30 profils de fournisseurs** avec des prompts specialises par emetteur — incluant les auto-facturations SIP AMIENS (sous-traitants NVINS) — pour maximiser la qualite d'extraction sur des mises en page tres heterogenes.

Public cible : equipes administratives qui manipulent des lots de factures BTP en francais.

## Aperçu

L'interface FastAPI expose 4 pages :

| Page       | Usage                                                                  |
| ---------- | ---------------------------------------------------------------------- |
| `/texte`   | Prompt generique sur le texte OCR pre-calcule                          |
| `/smart`   | Detection automatique du fournisseur + prompt specialise               |
| `/nouvelle`| Upload d'une nouvelle facture (OCR live via DocTR)                     |
| `/batch`   | Extraction par lot d'un ZIP avec progression en SSE et export Excel    |

## Champs extraits

| Champ              | Description                          |
| ------------------ | ------------------------------------ |
| `NUMERO_FACTURE`   | Numero complet de la facture         |
| `DATE_FACTURE`     | Date d'emission (JJ/MM/AAAA)         |
| `MONTANT_HT`       | Montant hors taxes                   |
| `TAUX_TVA`         | Taux TVA (5.5 %, 10 %, 20 %)         |
| `MONTANT_TTC`      | Montant TTC / Net a payer            |
| `NOM_INSTALLATEUR` | Entreprise emettrice                 |
| `COMMUNE_TRAVAUX`  | Ville du chantier                    |
| `CODE_POSTAL`      | Code postal du chantier              |
| `ADRESSE_TRAVAUX`  | Adresse complete du chantier         |

## Prerequisites

- **Python 3.11+**
- **Ollama** installe et lance ([https://ollama.com](https://ollama.com))
- **GPU recommande** : NVIDIA avec >= 12 GB VRAM (testé sur RTX 5080 Laptop, 15.9 GB)
- **OS** : Windows 11 (developpe et teste). Les commandes shell ci-dessous fonctionnent sous Git Bash, WSL, macOS et Linux.

## Installation

```bash
# 1. Cloner le repo
git clone https://github.com/Melko-energie/finetuned_model.git
cd finetuned_model

# 2. Creer un environnement virtuel
python -m venv venv
# Windows (Git Bash) :
source venv/Scripts/activate
# macOS / Linux :
# source venv/bin/activate

# 3. Installer les dependances Python
pip install -r requirements.txt

# 4. Telecharger le modele Gemma2 dans Ollama
ollama pull gemma2:9b
```

Raccourci avec le `Makefile` (cf. section [Make](#make)) :

```bash
make install
```

## Configuration

Aucune variable d'environnement requise. Tous les parametres techniques sont centralises dans **`core/config.py`** :

| Constante         | Valeur par defaut          | Role                                         |
| ----------------- | -------------------------- | -------------------------------------------- |
| `MODEL_NAME`      | `"gemma2:9b"`              | Modele Ollama utilise pour l'extraction      |
| `OLLAMA_OPTIONS`  | `{temperature: 0, seed: 42}` | Determinisme : indispensable a chaque appel  |
| `OCR_DIR`         | `data/ocr_texts/`          | JSON DocTR pre-calcules                      |
| `PDF_DIR`         | `data/raw_pdfs/`           | PDF source organises par fournisseur         |
| `ALL_FIELD_KEYS`  | 9 cles                     | Champs a extraire                            |

Pour changer de modele LLM (par ex. `qwen2.5:14b`) ou ajuster les paths, editer `core/config.py` — un seul endroit a modifier.

## Usage

### Interface web

```bash
uvicorn main:app --reload
```

Ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000). Si le port est bloque (Windows reserve parfois 8000) :

```bash
uvicorn main:app --reload --port 8001
```

### Pipeline OCR pour de nouvelles factures

```bash
# Deposer les PDF dans data/raw_pdfs/<fournisseur>/
python scripts/pdf_to_images.py   # PDF -> PNG (convention _page0, _page1...)
python scripts/run_ocr.py         # PNG -> JSON DocTR dans data/ocr_texts/
```

### Extraction CLI (sanity check sur 3 PDF echantillons)

```bash
python scripts/extract_cli.py
```

Resultats serialises dans `data/test_gemma2_smart_results.json`.

### Appels API directs

```bash
# Lister les fournisseurs supportes
curl http://127.0.0.1:8001/api/fournisseurs

# Extraction live d'un fichier
curl -F "file=@facture.pdf" -F "fournisseur=Auto-detect" \
     http://127.0.0.1:8001/api/extract-ocr

# Extraction d'un lot ZIP avec progression SSE
curl -F "file=@lot.zip" http://127.0.0.1:8001/api/batch
```

## Tests

Pas encore de suite de tests automatises. La verification de regression se fait via `scripts/extract_cli.py` qui rejoue 3 factures de reference (A2M, ESTEVE, TERNEL) et affiche les champs extraits.

A faire : `pytest` avec un dossier `tests/fixtures/` contenant 5–10 PDFs de reference + JSON attendu, pour eviter qu'un tweak de prompt casse silencieusement un fournisseur.

## Structure du projet

```
finetuned_model/
├── main.py                     # Entree FastAPI (routes /texte /smart /nouvelle /batch)
├── api/
│   └── routes.py               # Endpoints /api/* (upload, batch SSE, exports Excel)
├── core/                       # Logique metier pure (sans dependance web ni CLI)
│   ├── config.py               # Paths, MODEL_NAME, OLLAMA_OPTIONS, FIELDS, JSON_TEMPLATE
│   ├── prompts.py              # PROMPTS_INSTALLATEURS (30 profils) + PROMPT_TEXTE
│   ├── detection.py            # detect_installateur, detect_avoir
│   ├── ocr.py                  # DocTR singleton, lecture JSON, OCR live
│   ├── postprocess.py          # clean_json, coherence montants, blacklist SIP HQ
│   ├── extraction.py           # 3 entry points : texte, smart, live
│   ├── batch.py                # iter_batch_zip + process_batch_zip
│   └── excel.py                # Exports Excel (single + multi-sheets)
├── templates/                  # Jinja2 (base, texte, smart, nouvelle, batch)
├── static/js/                  # JS front (upload, rendu batch)
├── scripts/                    # CLIs one-shot
│   ├── pdf_to_images.py        # PDF -> PNG (convention _page0)
│   ├── run_ocr.py              # PNG -> JSON DocTR
│   └── extract_cli.py          # Smoke test sur 3 PDF echantillons
├── assets/logo.png
├── data/                       # gitignore (PDF, images, OCR)
│   ├── raw_pdfs/<fournisseur>/
│   ├── page_images/
│   └── ocr_texts/
├── Makefile
├── requirements.txt
└── README.md
```

Regle d'architecture : **`api/` et `scripts/` consomment `core/`**. L'inverse est interdit. `core/` n'a aucune dependance a FastAPI.

## Fournisseurs supportes (30 profils)

### Fournisseurs principaux (16)

| Fournisseur     | TVA           | Particularite                                    |
| --------------- | ------------- | ------------------------------------------------ |
| A2M             | 5.5 %         | Electricien RGE, renovation energetique          |
| ARCANA          | 20 %          | Architecture, note d'honoraires                  |
| CAILLOCE        | 20 %          | Avocat, facturation horaire                      |
| CLOROFIL        | 20 %          | Bureau d'etudes / paysage                        |
| DILA            | 20 %          | Titre de perception (gouvernement)               |
| ECO2E           | 20 %          | Bureau d'etudes fluides                          |
| ESTEVE          | 20 %          | Electricite                                      |
| EXIM            | 20 %          | Diagnostics amiante (ATHOS)                      |
| GAZ DE BORDEAUX | 20 %          | Energie                                          |
| GAZETTE         | 20 %          | Annonces legales                                 |
| GIGABAT         | 20 %          | Coordination SPS                                 |
| HESTIA          | 10 %          | Bureau d'etudes habitat                          |
| JLA             | 20 %          | Etudes / maitrise d'oeuvre                       |
| KELVIN          | 20 %          | Etudes thermiques                                |
| LOGISTA         | 20 %          | Logistique / fournitures                         |
| OREA            | 20 %          | Maitrise d'oeuvre                                |
| OTIS            | 20 %          | Ascenseurs / maintenance                         |
| POULAIN         | 20 %          | Bureau d'etudes thermiques                       |
| RCPI            | 20 %          | Maitrise d'oeuvre batiment                       |
| SOCOTEC         | 20 %          | Controle technique                               |
| TERNEL          | 20 % + 5.5 %  | Couverture / charpente, TVA mixte                |
| TOTAL ENERGIES  | 20 %          | Energie                                          |

### Sous-installateurs NVINS (auto-facturations SIP AMIENS)

| Installateur          | Prefixe | Metier                                |
| --------------------- | ------- | ------------------------------------- |
| KLISZ                 | 8DE-    | Peinture / finitions                  |
| PROXISERVE            | 8PR-    | Plomberie / chauffage (TVA 5.5 %)     |
| LOGISTA               | 8LO-    | Plomberie / chauffage                 |
| L'UNION DES PEINTRES  | 8UN-    | Peinture (SCOP)                       |
| SAS APPLI             | 8AP-    | Peinture                              |
| TECHSOL               | 8TH-    | Revetements de sols                   |
| NUMERISS              | 8NU-    | Electricite                           |
| SIP AMIENS            | —       | Fallback generique                    |

Plus un prompt `DEFAULT` declenche pour tout fournisseur non reconnu.

## Make

Cibles disponibles (necessite [`make`](https://www.gnu.org/software/make/) installe — natif sur macOS, Linux et WSL ; `choco install make` ou `scoop install make` sous Windows) :

```bash
make install   # Cree le venv et installe les dependances Python
make run       # Lance l'application FastAPI sur le port 8001
make ocr       # Pipeline complet : pdf_to_images puis run_ocr
make cli       # Smoke test extract_cli sur 3 PDF echantillons
make clean     # Supprime les caches __pycache__
make help      # Affiche les cibles disponibles
```

## Contraintes techniques

A respecter pour ne rien casser :

- `options={"temperature": 0, "seed": 42}` sur **chaque** appel Ollama (deja centralise dans `core/config.OLLAMA_OPTIONS`).
- OCR DocTR : `data["pages"][idx]` est une liste de tokens — **jamais** acceder via `blocks/lines/words` (ancien format).
- Convention nommage images : `_page0`, `_page1` (commence a 0, jamais `_page_001`).
- Reponse Gemma2 nettoyee via `core.postprocess.clean_json` pour retirer les balises markdown.

## Contributing

Les contributions sont les bienvenues :

1. Fork du depot
2. Creer une branche feature : `git checkout -b feature/ma-feature`
3. Commit : `git commit -m "feat: ma feature"`
4. Push : `git push origin feature/ma-feature`
5. Ouvrir une Pull Request

## License

Projet de stage — propriete intellectuelle Melko Energie. Aucune licence open source actuellement attachee.

---

Stage 2026 — MADANI Yassine | Melko Energie
