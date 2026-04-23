"""Project-wide configuration: paths, model, fields, JSON template.

Paths assume the new server/ui split:
  <repo>/
  ├── server/
  │   ├── core/config.py   ← this file
  │   ├── config/prompts/  ← YAML prompts
  │   └── data/            ← runtime data (gitignored)
  └── ui/
      ├── templates/       ← Jinja2
      └── static/          ← JS, CSS

PROJECT_ROOT keeps its historical name but now points to the repo root
(<root>), not the Python package root. SERVER_ROOT is the new alias for
'<root>/server', where Python code, config and data live.
"""

from pathlib import Path

# This file is at <root>/server/core/config.py
# parent.parent       → <root>/server
# parent.parent.parent → <root>
SERVER_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SERVER_ROOT.parent
DATA_DIR = SERVER_ROOT / "data"
OCR_DIR = DATA_DIR / "ocr_texts"
PDF_DIR = DATA_DIR / "raw_pdfs"

MODEL_NAME = "gemma2:9b"
OLLAMA_OPTIONS = {"temperature": 0, "seed": 42}

FIELDS_LEFT = [
    ("NUMERO_FACTURE", "Numero Facture"),
    ("DATE_FACTURE", "Date Facture"),
    ("MONTANT_HT", "Montant HT"),
    ("TAUX_TVA", "Taux TVA"),
    ("MONTANT_TTC", "Montant TTC"),
]
FIELDS_RIGHT = [
    ("NOM_INSTALLATEUR", "Installateur"),
    ("COMMUNE_TRAVAUX", "Commune"),
    ("CODE_POSTAL", "Code Postal"),
    ("ADRESSE_TRAVAUX", "Adresse Travaux"),
]
ALL_FIELD_KEYS = [k for k, _ in FIELDS_LEFT + FIELDS_RIGHT]

JSON_TEMPLATE = """{
  "NUMERO_FACTURE": "...",
  "DATE_FACTURE": "...",
  "MONTANT_HT": "...",
  "TAUX_TVA": "...",
  "MONTANT_TTC": "...",
  "NOM_INSTALLATEUR": "...",
  "COMMUNE_TRAVAUX": "...",
  "CODE_POSTAL": "...",
  "ADRESSE_TRAVAUX": "..."
}"""
