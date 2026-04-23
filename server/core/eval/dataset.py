"""Dataset loading: ground truth Excel parsing + PDF path resolution."""

from pathlib import Path

import pandas as pd

# Excel column label → internal field key (matches ALL_FIELD_KEYS in core.config)
_COLUMN_TO_FIELD = {
    "Numero Facture": "NUMERO_FACTURE",
    "Date Facture": "DATE_FACTURE",
    "Montant HT": "MONTANT_HT",
    "Taux TVA": "TAUX_TVA",
    "Montant TTC": "MONTANT_TTC",
    "Installateur": "NOM_INSTALLATEUR",
    "Commune": "COMMUNE_TRAVAUX",
    "Code Postal": "CODE_POSTAL",
    "Adresse Travaux": "ADRESSE_TRAVAUX",
    # Also accept the multi-sheet export header names
    "NUMERO_FACTURE": "NUMERO_FACTURE",
    "DATE_FACTURE": "DATE_FACTURE",
    "MONTANT_HT": "MONTANT_HT",
    "TAUX_TVA": "TAUX_TVA",
    "MONTANT_TTC": "MONTANT_TTC",
    "NOM_INSTALLATEUR": "NOM_INSTALLATEUR",
    "COMMUNE_TRAVAUX": "COMMUNE_TRAVAUX",
    "CODE_POSTAL": "CODE_POSTAL",
    "ADRESSE_TRAVAUX": "ADRESSE_TRAVAUX",
}

_SHEET_CANDIDATES = ("Extractions", "TOUTES_FACTURES")


def load_ground_truth(xlsx_path: Path) -> list[dict]:
    """Read the ground-truth Excel and return a list of rows.

    Each row: {"filename": str, "type": "FACTURE" | "AVOIR" | "", "fields": dict}
    where `fields` maps each FIELD_KEY (NUMERO_FACTURE, ...) to the expected value
    (string, or None if missing from the sheet).

    The expected sheet is "Extractions" (batch single-sheet export) or
    "TOUTES_FACTURES" (batch multi-sheet export). Either works — the first
    that exists is used.

    Raises FileNotFoundError or ValueError on bad input.
    """
    if not xlsx_path.is_file():
        raise FileNotFoundError(f"Ground truth file not found: {xlsx_path}")

    with pd.ExcelFile(xlsx_path) as xl:
        sheet = next((s for s in _SHEET_CANDIDATES if s in xl.sheet_names), None)
        sheet_names = list(xl.sheet_names)
    if sheet is None:
        raise ValueError(
            f"No expected sheet found in {xlsx_path.name}. "
            f"Looked for: {_SHEET_CANDIDATES}. Got: {sheet_names}"
        )

    # The batch export uses startrow=2, so the real header is on Excel row 3
    # (0-indexed row 2). Pandas: header=2 when reading directly.
    df = pd.read_excel(xlsx_path, sheet_name=sheet, header=2, dtype=object)

    # Find the filename column (either "Nom du PDF" or "NOM_FICHIER")
    filename_col = None
    for candidate in ("Nom du PDF", "NOM_FICHIER"):
        if candidate in df.columns:
            filename_col = candidate
            break
    if filename_col is None:
        raise ValueError(
            f"No filename column in sheet '{sheet}'. "
            f"Looked for 'Nom du PDF' or 'NOM_FICHIER'. Got: {list(df.columns)}"
        )

    type_col = "Type" if "Type" in df.columns else ("TYPE" if "TYPE" in df.columns else None)

    rows = []
    for _, row in df.iterrows():
        filename = row[filename_col]
        if pd.isna(filename) or not str(filename).strip():
            continue  # blank rows
        fields = {}
        for col, field_key in _COLUMN_TO_FIELD.items():
            if col in df.columns:
                val = row[col]
                fields[field_key] = None if pd.isna(val) else str(val)
        rows.append({
            "filename": str(filename).strip(),
            "type": str(row[type_col]).strip().upper() if type_col and not pd.isna(row[type_col]) else "",
            "fields": fields,
        })
    return rows


def index_pdfs(pdfs_dir: Path) -> dict[str, Path]:
    """Index all .pdf / .PDF files under pdfs_dir (recursive) by their
    stem (lowercase, no extension). Later used to look up a ground-truth
    row's `filename` and resolve it to an actual path on disk.
    """
    if not pdfs_dir.is_dir():
        raise FileNotFoundError(f"PDFs directory not found: {pdfs_dir}")
    index = {}
    for path in pdfs_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() == ".pdf":
            index[path.stem.lower()] = path
    return index


def match_pdf(filename: str, pdf_index: dict[str, Path]) -> Path | None:
    """Look up a PDF by the filename recorded in the ground truth."""
    stem = Path(filename).stem.lower()
    return pdf_index.get(stem)
