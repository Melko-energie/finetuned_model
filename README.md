Voici un fichier README.md complet, en **français**, clair, structuré et prêt à l’emploi pour votre projet **d’extraction d’informations dans des documents avec LayoutLMv3 et LoRA**.

---

# 📄 Extraction d’informations dans des documents avec LayoutLMv3

Un modèle **LayoutLMv3** fine-tuné avec **LoRA** (Low-Rank Adaptation) pour l’extraction automatique et structurée d’informations dans des documents (PDF, images, etc.).

---

## 📁 Structure du projet

```
finetuned_model/
├── data/                        # Données brutes et annotées
├── scripts/                     # Scripts de traitement
├── models/                      # Modèles préentraînés et fine-tunés
├── outputs/                     # Résultats (logs, prédictions, exports)
├── notebooks/                   # Notebooks d’exploration
├── configs/                     # Fichiers de configuration
└── requirements.txt             # Dépendances Python
```

---

## 🚀 Démarrage rapide

### 1. Installation

```bash
# Cloner le dépôt
git clone <your-repo>
cd finetuned_model

# Installer les dépendances Python
pip install -r requirements.txt

# Installer Tesseract (OCR)
# Ubuntu/Debian :
sudo apt-get install tesseract-ocr

# macOS :
brew install tesseract
```

---

### 2. Préparation des données

Placez vos **PDFs** dans `data/raw_pdfs/`, puis exécutez la pipeline :

```bash
# 1. Extraction OCR
python scripts/01_ocr_extraction.py

# 2. Annotation automatique (regex)
python scripts/02_auto_labeling.py

# 3. Nettoyage des labels
python scripts/03_label_cleaner.py

# 4. Construction du dataset
python scripts/04_dataset_builder.py
```

---

### 3. Entraînement

```bash
# Lancer l’entraînement
python scripts/05_train_model.py

# (Optionnel) Activer Weights & Biases
wandb login
```

---

### 4. Inférence

```bash
# Extraire les informations d’un nouveau document
python scripts/06_inference.py chemin/vers/document.pdf
```

---

## ⚙️ Configuration

### Schéma des labels

Modifier `data/label_schema.json` pour définir vos propres entités :

- Ajouter/supprimer des champs
- Mettre à jour les expressions régulières dans `02_auto_labeling.py`

### Paramètres d’entraînement

Modifier `configs/training_args.json` :

- Taux d’apprentissage
- Taille des batchs
- Nombre d’époques
- Paramètres LoRA (rank, alpha, etc.)

---

## 🧠 Architecture

- **Modèle de base** : LayoutLMv3-base
- **Méthode de fine-tuning** : LoRA (PEFT)
- **Tâche** : Classification de tokens (NER)
- **Entrées** : Images de pages + texte + layout (bounding boxes)

---

## 🧾 Champs supportés (exemples)

| Champ        | Description                          |
|--------------|--------------------------------------|
| ACCISSE      | Numéros d’identification fiscale     |
| DATE         | Dates (formats variés)               |
| NOM          | Noms de famille                      |
| PRENOM       | Prénoms                              |
| ADRESSE      | Adresses postales                    |
| MONTANT      | Montants monétaires                  |
| DESIGNATION  | Libellés d’articles                  |
| REFERENCE    | Références de documents              |

---

## 📊 Performances (exemples)

| Métrique   | Plage typique |
|------------|---------------|
| F1-score   | 85 – 95 %     |
| Précision  | 82 – 93 %     |
| Rappel     | 84 – 94 %     |

> Les performances dépendent de la **qualité des données** et de la **cohérence des annotations**.

---

## 🛠️ Personnalisation

### Ajouter un nouveau champ

1. Ajouter le label dans `label_schema.json`
2. Ajouter une règle regex dans `02_auto_labeling.py`
3. Ajouter une règle de normalisation dans `03_label_cleaner.py`
4. Relancer l’entraînement

### Améliorer l’OCR

- Modifier la **résolution DPI** dans `01_ocr_extraction.py`
- Changer de moteur OCR (Tesseract, PyMuPDF, etc.)
- Prétraiter les images (débruitage, accentuation)

---

## 🔧 Résolution des problèmes courants

| Problème               | Solution rapide                                      |
|------------------------|------------------------------------------------------|
| OCR peu précis         | Augmenter la DPI, changer de moteur, prétraiter      |
| Modèle peu performant  | Ajouter des données, ajuster les poids de classe     |
| Problèmes de mémoire   | Réduire le batch size, activer fp16, gradient accumulation |

---

## 📄 Licence

MIT – voir le fichier `LICENSE`.

---

## 📣 Citation

Si vous utilisez ce projet dans vos travaux :

```bibtex
@software{layoutlmv3_finetuning,
  title  = {Extraction d'informations dans des documents avec LayoutLMv3 et LoRA},
  author = {Votre Nom},
  year   = {2024},
  url    = {https://github.com/yourusername/finetuned_model}
}
```

---

## ✅ Étapes suivantes

1. **Ajouter 5 à 10 PDFs d’exemple** dans `data/raw_pdfs/`
2. **Lancer la pipeline complète** :
   ```bash
   python scripts/01_ocr_extraction.py
   python scripts/02_auto_labeling.py
   python scripts/03_label_cleaner.py
   python scripts/04_dataset_builder.py
   ```
3. **Vérifier les annotations** dans `data/annotations_cleaned/` et corriger si besoin
4. **Entraîner le modèle** :
   ```bash
   python scripts/05_train_model.py
   ```
5. **Tester sur un nouveau document** :
   ```bash
   python scripts/06_inference.py data/raw_pdfs/test.pdf
   ```

---

## 🧩 Arborescence complète

```
finetuned_model/
├── data/
│   ├── raw_pdfs/                # PDFs originaux
│   ├── ocr_texts/               # Résultats OCR (texte + bbox)
│   ├── annotations/             # Annotations (format Label Studio)
│   ├── formatted_dataset/       # Dataset tokenisé prêt pour le training
│   └── label_schema.json        # Définition des champs
├── scripts/
│   ├── 01_ocr_extraction.py     # OCR avec Tesseract
│   ├── 02_auto_labeling.py      # Annotation automatique
│   ├── 03_label_cleaner.py      # Nettoyage des labels
│   ├── 04_dataset_builder.py    # Conversion vers HuggingFace dataset
│   ├── 05_train_model.py        # Entraînement avec LoRA
│   └── 06_inference.py          # Inférence sur nouveau document
├── models/
│   ├── layoutlmv3-base/         # Modèle préentraîné
│   └── finetuned_lora/          # Vos checkpoints
├── outputs/
│   ├── logs/                    # Logs et métriques
│   ├── predictions/             # Prédictions brutes
│   └── exported/                # JSON/Excel finaux
├── notebooks/
│   └── eda_dataset_explore.ipynb
├── configs/
│   └── training_args.json
├── requirements.txt
└── README.md
```

---

**Le projet est prêt à l’emploi.**  
Vous pouvez maintenant personnaliser le schéma de labels, ajouter vos propres PDFs, et entraîner votre modèle d’extraction intelligente !
