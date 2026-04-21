"""Project-wide configuration: paths, model, fields, JSON template."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
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
