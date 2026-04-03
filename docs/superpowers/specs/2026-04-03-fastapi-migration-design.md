# Migration Streamlit vers FastAPI + HTML Tailwind

## Contexte

L'application actuelle utilise Streamlit (`app.py`) pour servir une interface d'extraction de factures BTP. Le design system "Architectural Ledger" a été concu dans `stitch/` sous forme de 4 pages HTML/Tailwind statiques. L'objectif est de remplacer Streamlit par FastAPI servant ces pages HTML, connectees au backend Python existant via des endpoints REST.

## Architecture

```
finetuned_model/
├── main.py                  — app FastAPI, montage routes + static
├── api/
│   └── routes.py            — endpoints REST (upload, extract, batch, export)
├── core/
│   └── extraction.py        — logique metier (adapte depuis app.py + 12_gemma2_smart.py)
├── templates/
│   ├── base.html            — layout commun (header, sidebar, scripts)
│   ├── texte.html           — Gemma2:9b Texte
│   ├── smart.html           — Gemma2 Smart
│   ├── nouvelle.html        — Nouvelle Facture (OCR live)
│   └── batch.html           — Traitement par lot
└── static/
    └── js/
        └── app.js           — JS vanilla pour appels API + DOM
```

## Routes pages (GET)

| URL | Page | Description |
|-----|------|-------------|
| `/` | Redirect | Redirige vers `/texte` |
| `/texte` | texte.html | Extraction textuelle Gemma2:9b avec OCR pre-calcule |
| `/smart` | smart.html | Extraction Smart avec detection fournisseur |
| `/nouvelle` | nouvelle.html | Pipeline complet OCR DocTR live + extraction |
| `/batch` | batch.html | Traitement par lot ZIP, export Excel multi-feuilles |

Navigation multi-pages : chaque lien de la sidebar charge une nouvelle URL.

## Endpoints API (POST)

| Endpoint | Input | Output |
|----------|-------|--------|
| `POST /api/extract-texte` | PDF/image (multipart) | JSON: champs extraits, is_avoir |
| `POST /api/extract-smart` | PDF/image (multipart) + fournisseur (form field, optionnel) | JSON: champs, installateur detecte, is_avoir |
| `POST /api/extract-ocr` | PDF/image (multipart) + fournisseur (form field, optionnel) | JSON: champs extraits via OCR live DocTR, installateur, is_avoir |
| `POST /api/batch` | ZIP (multipart) | JSON: liste de resultats [{filename, fields, installateur, is_avoir}] |
| `POST /api/export-excel` | JSON body: liste de resultats | Fichier .xlsx (application/octet-stream) |
| `POST /api/export-excel-multi` | JSON body: liste de resultats | Fichier .xlsx multi-feuilles |
| `GET /api/fournisseurs` | - | JSON: liste des fournisseurs disponibles |

## Frontend

### Layout (base.html)
- Header fixe gradient `from-[#003d9b] to-[#0052cc]` avec titre "Extraction de Factures BTP"
- Sidebar fixe `bg-[#eceef0]` avec nav items, item actif surligne avec `bg-white border-r-4 border-[#003d9b]`
- Contenu principal `ml-72 pt-24`
- Tailwind CDN + Manrope/Inter Google Fonts + Material Symbols Outlined
- La page active est determinee par l'URL courante

### Pages (heritent de base.html)
Chaque page reprend le contenu exact du fichier stitch correspondant (zone upload, cards, grilles bento, JSON expander, etc.) avec les `id` necessaires pour le JS.

### JavaScript (app.js)
- Upload via `FormData` + `fetch()` vers les endpoints API
- Pendant le traitement : bouton disabled, spinner visible
- Reponse JSON parsee et injectee dans les cards de donnees extraites
- Gestion des etats : loading, succes (vert), erreur (rouge), warning/incoherence (orange), avoir (ambre `tertiary-fixed`)
- Export Excel : `fetch` blob + `URL.createObjectURL` pour telecharger
- Dropdown fournisseurs : charge depuis `GET /api/fournisseurs` au chargement

### Gestion des avoirs dans le frontend
- Badge "AVOIR" avec style `bg-tertiary-fixed text-on-tertiary-fixed-variant` 
- Ligne avoir dans le tableau batch : `bg-tertiary-fixed/30 border-l-4 border-tertiary`
- Montants negatifs affiches en `text-error`

## Backend (core/extraction.py)

### Fonctions reutilisees depuis le code existant
- `smart_detect_installateur(texte)` — detection fournisseur
- `smart_detect_avoir(texte)` — detection avoir
- `smart_extraire_champs(texte, installateur)` — extraction Gemma2
- `smart_inverser_montants_avoir(result)` — inversion montants
- `verifier_coherence_montants(result, is_avoir)` — verification HT/TTC
- `smart_get_ocr_text(filename)` — lecture OCR pre-calcule
- Pipeline OCR DocTR live (adapte de `process_single_file` sans dependances Streamlit)
- `export_excel_batch(results_list)` — export Excel simple
- `export_excel_multi_sheets(results_list)` — export Excel multi-feuilles

### OCR DocTR
- Modele charge une seule fois au demarrage de FastAPI (equivalent `@st.cache_resource`)
- Stocke en variable globale du module

### Adaptation
- Supprimer toutes les dependances Streamlit (`st.*`)
- Les fonctions retournent des dicts/bytes au lieu d'ecrire dans le DOM Streamlit
- `process_single_file` adapte pour accepter des bytes et retourner `(fields, error, installateur, is_avoir)`

## Mode d'interaction
- Bloquant : le frontend attend la reponse de chaque requete
- Bouton loading + spinner pendant le traitement
- Pas de WebSocket ni polling

## Deploiement
- Local uniquement pour l'instant
- `uvicorn main:app --reload --port 8000`

## Dependances ajoutees
- `fastapi`
- `uvicorn`
- `python-multipart` (pour les uploads)
- `jinja2` (pour le templating base.html)
