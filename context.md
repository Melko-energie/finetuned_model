# CONTEXT.md — Projet LayoutLMv3 BTP Invoice NER
# À lire en PREMIER avant toute modification

---

## 🎯 Objectif du projet

Extraction automatique de champs depuis des factures BTP françaises (16 fournisseurs, 119 PDFs).
Pipeline complet : OCR → Annotation → Fine-tuning LayoutLMv3 + LoRA → Inférence.

**Champs extraits :** NUMERO_FACTURE, DATE_FACTURE, MONTANT_HT, TAUX_TVA, MONTANT_TTC,
NOM_INSTALLATEUR, COMMUNE_TRAVAUX, CODE_POSTAL, ADRESSE_TRAVAUX, DETAIL_TRAVAUX

---

## 📁 Architecture du projet

```
finetuned_model/
├── run.py                          ← Router CLI
├── app.py                          ← Interface Streamlit (3 onglets)
├── assets/logo.png
├── configs/
│   ├── training_args.json          ← Config training (source de vérité)
│   └── best_config.json            ← Meilleure config trouvée
├── data/
│   ├── raw_pdfs/                   ← PDFs source par fournisseur
│   │   ├── rcpi/, gazette/, nvins/, ...
│   ├── page_images/                ← PNG générés par script 00
│   │   └── convention : _page0, _page1 (commence à 0)
│   ├── images_flat/                ← PNG aplatis pour LabelStudio
│   │   └── convention : _page0, _page1 (MÊME que page_images)
│   ├── ocr_texts/                  ← JSON DocTR par fournisseur
│   │   └── structure : {filename, pages: [[{text, bbox, page, confidence}]]}
│   ├── annotations_labelstudio.json ← Export LabelStudio (131 tâches)
│   ├── annotations_cleaned/        ← Output script 07 (format pipeline)
│   │   └── UNIQUEMENT format LabelStudio — PAS de fichiers Regex
│   │   └── structure : {image_name, tokens:[{text,bbox,label}], source}
│   ├── formatted_dataset/          ← Dataset HuggingFace final
│   │   ├── train/ (59 samples)
│   │   └── validation/ (11 samples)
│   └── label_schema.json
├── models/finetuned_lora/          ← Modèle sauvegardé
└── scripts/
    ├── 00_pdf_to_images.py         ← PDF → PNG (convention _page0)
    ├── 01_ocr_extraction.py        ← DocTR OCR → JSON
    ├── 02_auto_labeling.py         ← Regex (DÉSACTIVÉ)
    ├── 03_label_cleaner.py         ← Nettoyage (DÉSACTIVÉ)
    ├── 04_dataset_builder.py       ← Annotations → Dataset HuggingFace
    ├── 05_train_model.py           ← Fine-tuning LayoutLMv3 + LoRA
    ├── 06_inference.py             ← Inférence DocTR + LayoutLMv3
    ├── 07_convert_labelstudio.py   ← Export LS → annotations_cleaned
    ├── flatten_images.py           ← page_images → images_flat
    ├── diagnostic_dataset.py       ← Diagnostic dataset
    ├── debug_overlap.py            ← Debug overlap bbox
    └── test_gemma3.py              ← Test Gemma3:12b vision
```

---

## ⚙️ Configuration optimale (NE PAS MODIFIER sans raison)

### configs/training_args.json
```json
{
    "num_train_epochs": 100,
    "per_device_train_batch_size": 16,
    "per_device_eval_batch_size": 16,
    "gradient_accumulation_steps": 1,
    "learning_rate": 5e-5,
    "weight_decay": 0.0,
    "warmup_ratio": 0.0,
    "eval_steps": 999999,
    "save_steps": 999999,
    "load_best_model_at_end": false,
    "dataloader_num_workers": 0
}
```

### scripts/05_train_model.py — Class weights
```python
# MEILLEURE CONFIG TROUVÉE — NE PAS CHANGER
if label_str == "O":
    weights[int(label_id)] = 0.15      # ← 0.15 optimal
else:
    weights[int(label_id)] = 3.0       # ← 3.0 optimal
```

### LoRA config
```python
# NE PAS MODIFIER
lora_r     = 16    # testé 32 → moins bon
lora_alpha = 32    # testé 64 → moins bon
```

---

## 📊 Meilleurs résultats obtenus

```
Config optimale : O=0.15 / entities=3.0 / epochs=100 / GPU RTX 5080
Dataset         : 59 train / 11 valid (LS pur, filtré, propre)
Résultats       :
  F1        = 0.2599  ← RECORD ABSOLU
  Precision = 16.4%
  Recall    = 62.2%
  train_loss = 1.22
  eval_loss  = 0.76
```

### Historique complet des runs
```
O=0.05 r=16 lr=5e-5   epochs=100  →  F1 0.1435
O=0.10 r=16 lr=5e-5   epochs=100  →  F1 0.1956
O=0.15 r=16 lr=5e-5   epochs=100  →  F1 0.2599  ← MEILLEUR
O=0.15 r=32 lr=5e-5   epochs=100  →  F1 0.1893  (r=32 moins bon)
O=0.10 r=16 lr=3e-5   cosine      →  F1 0.1283  (cosine moins bon)
O=0.10 r=16 lr=5e-5   epochs=100  →  F1 0.2094  (dataset propre)
```

---

## 🔑 Règles critiques — TOUJOURS respecter

### Convention nommage images
```
Script 00 génère    : _page0, _page1, _page2...  (commence à 0)
LabelStudio importe : _page0, _page1, _page2...  (MÊME convention)
JAMAIS utiliser     : _page_001, _page_002 (ancienne convention)
```

### Format OCR (data/ocr_texts/)
```python
# Structure correcte
data = json.load(f)
pages = data["pages"]           # liste de pages
page_tokens = pages[0]          # liste de tokens de la page 0
token = page_tokens[0]          # {"text": "...", "bbox": [...], "page": 0}

# JAMAIS accéder via blocks/lines/words (ancien format)
```

### Format annotations_cleaned/
```python
# Structure correcte
{
    "image_name": "FOURNISSEUR_XXX_page0.png",
    "image_width": 1645,
    "image_height": 2339,
    "page_index": 0,
    "tokens": [
        {"text": "RCPI", "bbox": [111, 37, 210, 66], "label": "B-INSTALLATEUR"},
        {"text": "42",   "bbox": [379, 260, 396, 269], "label": "O"},
        ...
    ],
    "source": "labelstudio_manual"
}

# JAMAIS format Regex dans ce dossier
# JAMAIS {"data": {"pdf_filename": ...}}
```

### Filtres obligatoires dans script 04
```python
# Ces deux filtres DOIVENT rester actifs
# 1. Filtre samples sans image
# 2. Filtre samples sans entité (0 tokens non-O)
```

---

## ⚠️ Bugs connus et corrections appliquées

### Bug 1 — Noms doublés LabelStudio (CORRIGÉ)
```
Symptôme : S1120317_MICROLAD_S1120317_MICROLAD_page0.png
Cause    : LabelStudio duplique le nom
Fix      : fonction deduplicate_stem() dans 07 et 04
```

### Bug 2 — Convention nommage _page_001 vs _page0 (CORRIGÉ)
```
Symptôme : images introuvables
Fix      : 3 variantes testées dans find_image() de script 04
```

### Bug 3 — Format JSON DocTR (CORRIGÉ)
```
Symptôme : 0 tokens extraits
Cause    : accès via blocks/lines/words (mauvais)
Fix      : accès direct pages[idx] = liste de tokens
```

### Bug 4 — Fichiers _-_Copie (CONNU, NON BLOQUANT)
```
3 fichiers avec "_-_Copie" dans le nom
→ les originaux existent déjà
→ 3 samples perdus, pas grave
```

### Bug 5 — Annotations 250+ entités (CORRIGÉ)
```
Symptôme : KLISZ page1 avait 272 entités (tout le tableau annoté)
Fix      : annotations supprimées dans LabelStudio
Règle    : NE JAMAIS annoter les tableaux de détails de travaux
```

### Bug 6 — Windows NamedTemporaryFile (CORRIGÉ dans app.py)
```
Fix : tempfile.mkdtemp() + shutil.rmtree()
```

---

## 🔄 Pipeline complet — Ordre d'exécution

```bash
# 1. Nouveaux PDFs → images
python scripts/00_pdf_to_images.py

# 2. Images → OCR
python scripts/01_ocr_extraction.py

# 3. Aplatir pour LabelStudio
python scripts/flatten_images.py

# [ANNOTER DANS LABELSTUDIO]
# Exporter → JSON → remplacer data/annotations_labelstudio.json

# 4. Convertir annotations LabelStudio
python scripts/07_convert_labelstudio.py

# 5. Construire dataset
python scripts/04_dataset_builder.py

# 6. Vérifier dataset AVANT training
python scripts/diagnostic_dataset.py
# Vérifier : 0 samples avec 250+ entités
#            0 samples sans image
#            validation >= 10 samples

# 7. Entraîner
python scripts/05_train_model.py

# 8. Interface
streamlit run app.py
```

---

## 🤖 Modèles disponibles

### LayoutLMv3 + LoRA
```
Modèle   : microsoft/layoutlmv3-base
LoRA     : r=16, alpha=32, dropout=0.1
Entrée   : image PNG + tokens OCR + bounding boxes
GPU      : RTX 5080 Laptop (15.9 GB VRAM)
Training : ~25-30 min pour 100 epochs sur 59 samples
```

### Gemma3:12b (Ollama)
```
Usage    : vision directe sur image PNG
Résultat : ~73% correct sans fine-tuning
Limites  : NOM_INSTALLATEUR tronqué, COMMUNE souvent null
Fix      : options={"temperature": 0, "seed": 42} sur chaque appel
```

### Gemma2:9b (Ollama)
```
Usage    : texte OCR DocTR existant
Résultat : ~20% correct (hallucine beaucoup)
Statut   : expérimental
```

---

## 📈 État actuel du dataset

```
131  images annotées dans LabelStudio
128  converties par script 07 (3 Copie perdues)
116  format LabelStudio dans annotations_cleaned/
 59  train samples filtrés et valides
 11  validation samples
```

### Samples perdus et pourquoi
```
-3   fichiers _Copie (non bloquant)
-16  images introuvables après fix noms doublés
-41  zéro entités après encodage
     dont : pages légitimes vides (détails travaux)
     dont : page0 non encore annotées (PROXISERVE, LOGISTA...)
```

### Prochaine action pour plus de données
```
Annoter dans LabelStudio :
→ PROXISERVE × 4 (page0 vides)
→ LOGISTA × 2
→ TECHSOL × 1
→ NUMERISS × 1
→ SIP_AMIENS_011 × 1
→ Nouvelles factures nvins/
Objectif : 90-100 train samples → F1 espéré 0.30-0.35
```

---

## 🚫 Ce qu'il NE FAUT PAS faire

```
❌ Réactiver les annotations Regex (format ancien)
❌ Mélanger Regex + LabelStudio dans le même dataset
❌ Annoter les tableaux de détails de travaux (DETAIL_TRAVAUX sur toute une page)
❌ Changer lora_r à 32 (testé, moins bon)
❌ Utiliser lr_scheduler cosine (testé, moins bon)
❌ Mettre load_best_model_at_end=true (coupe le training trop tôt)
❌ Mettre dataloader_num_workers > 0 sur Windows (bugs)
❌ Utiliser NamedTemporaryFile sans delete=False sur Windows
❌ Accéder à l'OCR via blocks/lines/words (ancien format)
❌ Créer des images _page_001 (utiliser _page0)
```

---

## ✅ Ce qui fonctionne bien

```
✅ GPU RTX 5080 avec PyTorch nightly cu128
✅ Dataset 100% LabelStudio pur (pas de mix Regex)
✅ Filtre samples vides actif dans script 04
✅ deduplicate_stem() dans scripts 07 et 04
✅ Interface Streamlit 3 onglets (LayoutLMv3 + Gemma3 + Gemma2)
✅ Gemma3:12b avec split haut/bas pour factures 1 page
✅ Gemma3:12b avec page0/dernière page pour multi-pages
✅ options temperature=0 seed=42 sur chaque appel Ollama
```

---

## 🛠️ Environnement technique

```
OS       : Windows 11, PowerShell
Python   : venv dans C:\Users\melko\Developer\finetuned_model\venv\
GPU      : NVIDIA RTX 5080 Laptop (15.9 GB VRAM)
CUDA     : 13.1
PyTorch  : 2.12.0.dev nightly cu128
Grep     : INDISPONIBLE → utiliser Select-String
Chemin   : JAMAIS préfixer par le dossier courant dans les commandes
```

---

## 📝 Comment utiliser ce fichier

Commence chaque prompt Claude Code par :

```
Lis d'abord CONTEXT.md à la racine du projet.
Ensuite : [ta demande ici]
Contraintes : ne modifie QUE ce qui est demandé,
ne refactorise pas, ne renomme pas les variables.
```