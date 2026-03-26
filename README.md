# Extraction de Factures BTP — Gemma2:9b + OCR DocTR

Extraction automatique de champs depuis des factures BTP francaises via **Gemma2:9b** (Ollama) et **OCR DocTR**.

Interface Streamlit avec 2 modes :
- **Gemma2 Texte** : prompt generique sur le texte OCR
- **Gemma2 Smart** : detection automatique du fournisseur + prompt specialise

---

## Champs extraits

| Champ | Description |
|---|---|
| NUMERO_FACTURE | Numero complet de la facture |
| DATE_FACTURE | Date d'emission (JJ/MM/AAAA) |
| MONTANT_HT | Montant hors taxes |
| TAUX_TVA | Taux de TVA (5.5%, 10%, 20%) |
| MONTANT_TTC | Montant TTC / Net a payer |
| NOM_INSTALLATEUR | Entreprise emettrice |
| COMMUNE_TRAVAUX | Ville du chantier |
| CODE_POSTAL | Code postal du chantier |
| ADRESSE_TRAVAUX | Adresse complete du chantier |

---

## Structure du projet

```
finetuned_model/
├── app.py                      # Interface Streamlit (2 onglets)
├── context.md                  # Documentation projet
├── requirements.txt
├── assets/logo.png
├── scripts/
│   ├── 00_pdf_to_images.py     # PDF → PNG (convention _page0)
│   ├── 01_ocr_extraction.py    # DocTR OCR → JSON
│   └── 12_gemma2_smart.py      # Extraction smart par fournisseur
└── data/
    ├── raw_pdfs/               # PDFs source (17 fournisseurs)
    ├── page_images/            # PNG generes par script 00
    └── ocr_texts/              # JSON OCR DocTR par fournisseur
```

---

## Demarrage rapide

### 1. Installation

```bash
git clone https://github.com/Melko-energie/finetuned_model.git
cd finetuned_model
pip install -r requirements.txt
```

Prerequis : **Ollama** avec le modele `gemma2:9b` :
```bash
ollama pull gemma2:9b
```

### 2. Pipeline OCR (pour nouvelles factures)

```bash
# Mettre les PDFs dans data/raw_pdfs/{fournisseur}/

# 1. PDF → Images PNG
python scripts/00_pdf_to_images.py

# 2. Images → OCR JSON
python scripts/01_ocr_extraction.py
```

### 3. Interface Streamlit

```bash
streamlit run app.py
```

### 4. Extraction en ligne de commande

```bash
python scripts/12_gemma2_smart.py
```

---

## Fournisseurs supportes (25 profils)

### Fournisseurs principaux (17)

| Fournisseur | TVA | Particularite |
|---|---|---|
| A2M | 5.5% | Electricien RGE, renovation energetique |
| ARCANA | 20% | Architecture, note d'honoraires |
| CAILLOCE | 20% | Avocat, facturation horaire |
| DILA | 20% | Titre de perception (gouvernement) |
| ECO2E | 20% | Bureau d'etudes fluides |
| ESTEVE | 20% | Electricite |
| EXIM | 20% | Diagnostics amiante (ATHOS) |
| GAZETTE | 20% | Annonces legales |
| GIGABAT | 20% | Coordination SPS |
| HESTIA | 10% | Bureau d'etudes habitat |
| KELVIN | 20% | Etudes thermiques |
| OREA | 20% | Maitrise d'oeuvre |
| POULAIN | 20% | Bureau d'etudes thermiques |
| RCPI | 20% | Maitrise d'oeuvre batiment |
| SOCOTEC | 20% | Controle technique |
| TERNEL | 20% + 5.5% | Couverture/charpente, TVA mixte |

### Sous-installateurs NVINS (8 auto-facturations SIP)

| Installateur | Prefixe | Metier |
|---|---|---|
| KLISZ | 8DE- | Peinture/finitions |
| PROXISERVE | 8PR- | Plomberie/chauffage (TVA 5.5%) |
| LOGISTA | 8LO- | Plomberie/chauffage |
| L'UNION DES PEINTRES | 8UN- | Peinture (SCOP) |
| SAS APPLI | 8AP- | Peinture |
| TECHSOL | 8TH- | Revetements de sols |
| NUMERISS | 8NU- | Electricite |
| SIP AMIENS | — | Fallback generique |

---

## Environnement technique

- **OS** : Windows 11
- **Python** : 3.11+
- **OCR** : DocTR
- **LLM** : Gemma2:9b via Ollama
- **Interface** : Streamlit
- **GPU** : NVIDIA RTX 5080 Laptop (15.9 GB VRAM)

---

## Contraintes techniques

- `options={"temperature": 0, "seed": 42}` sur **chaque** appel Ollama
- Reponse JSON uniquement, nettoyage des balises markdown
- OCR DocTR : acces via `data["pages"][idx]` = liste de tokens (jamais blocks/lines/words)
- Convention nommage images : `_page0`, `_page1` (commence a 0)

---

Stage 2026 — MADANI Yassine | Melko Energie
