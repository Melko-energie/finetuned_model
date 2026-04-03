# CONTEXT.md — Projet Extraction Factures BTP
# A lire en PREMIER avant toute modification

---

## Objectif du projet

Extraction automatique de champs depuis des factures BTP francaises (17 fournisseurs + 8 sous-installateurs nvins).
Pipeline : OCR DocTR → Detection fournisseur → Extraction Gemma2:9b avec prompts specialises.

**Champs extraits :** NUMERO_FACTURE, DATE_FACTURE, MONTANT_HT, TAUX_TVA, MONTANT_TTC,
NOM_INSTALLATEUR, COMMUNE_TRAVAUX, CODE_POSTAL, ADRESSE_TRAVAUX

---

## Architecture du projet

```
finetuned_model/
├── app.py                          ← Interface Streamlit (2 onglets)
├── context.md                      ← Ce fichier
├── requirements.txt
├── assets/logo.png
├── scripts/
│   ├── 00_pdf_to_images.py         ← PDF → PNG (convention _page0)
│   ├── 01_ocr_extraction.py        ← DocTR OCR → JSON
│   └── 12_gemma2_smart.py          ← Extraction smart par fournisseur
└── data/
    ├── raw_pdfs/                   ← PDFs source par fournisseur
    │   ├── a2m/, arcana/, ..., ternel/  (17 dossiers)
    ├── page_images/                ← PNG generes par script 00
    │   └── convention : _page0, _page1 (commence a 0)
    └── ocr_texts/                  ← JSON DocTR par fournisseur
        └── structure : {filename, pages: [[{text, bbox, page, confidence}]]}
```

---

## Pipeline complet

```bash
# 1. Nouveaux PDFs → images
python scripts/00_pdf_to_images.py

# 2. Images → OCR
python scripts/01_ocr_extraction.py

# 3. Interface
streamlit run app.py

# 4. Test en ligne de commande
python scripts/12_gemma2_smart.py
```

---

## Modele : Gemma2:9b (Ollama)

```
Usage    : texte OCR DocTR existant
Mode 1   : prompt generique (onglet Gemma2 Texte)
Mode 2   : prompt specialise par fournisseur (onglet Gemma2 Smart)
Fix      : options={"temperature": 0, "seed": 42} sur CHAQUE appel
```

### Gemma2 Smart — 25 profils fournisseurs

17 fournisseurs principaux :
a2m, arcana, cailloce, dila, eco2e, esteve, exim, gazette,
gigabat, hestia, kelvin, orea, poulain, rcpi, socotec, ternel

8 sous-installateurs nvins (auto-facturations SIP AMIENS) :
nvins_klisz, nvins_proxiserve, nvins_logista, nvins_lunion,
nvins_sas_appli, nvins_techsol, nvins_numeriss, nvins_sip_amiens

+ DEFAULT (prompt generique pour fournisseurs inconnus)

### Detection en 2 etapes pour nvins

1. Detecter "auto-facturation" dans le texte → mode nvins
2. Identifier le vrai installateur (KLISZ, PROXISERVE, etc.)
3. Appliquer le prompt specialise correspondant

---

## Regles critiques — TOUJOURS respecter

### Convention nommage images
```
Script 00 genere    : _page0, _page1, _page2...  (commence a 0)
JAMAIS utiliser     : _page_001, _page_002 (ancienne convention)
```

### Format OCR (data/ocr_texts/)
```python
# Structure correcte
data = json.load(f)
pages = data["pages"]           # liste de pages
page_tokens = pages[0]          # liste de tokens de la page 0
token = page_tokens[0]          # {"text": "...", "bbox": [...], "page": 0}

# JAMAIS acceder via blocks/lines/words (ancien format)
```

### Appels Ollama
```python
# OBLIGATOIRE sur chaque appel
options={"temperature": 0, "seed": 42}
```

---

## Ce qu'il NE FAUT PAS faire

```
- Acceder a l'OCR via blocks/lines/words (ancien format)
- Creer des images _page_001 (utiliser _page0)
- Oublier temperature=0 et seed=42 sur les appels Ollama
- Mettre dataloader_num_workers > 0 sur Windows (bugs)
- Utiliser NamedTemporaryFile sans delete=False sur Windows
```

---

## Environnement technique

```
OS       : Windows 11
Python   : 3.11+
GPU      : NVIDIA RTX 5080 Laptop (15.9 GB VRAM)
OCR      : DocTR
LLM      : Gemma2:9b via Ollama
Interface: Streamlit
```

---

