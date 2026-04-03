# FastAPI Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Streamlit frontend with FastAPI serving the stitch HTML/Tailwind pages, connected to the existing Python extraction backend via REST endpoints.

**Architecture:** FastAPI serves Jinja2 templates (adapted from stitch/ HTML) for 4 pages via GET routes, plus REST API endpoints (POST) for extraction/export. A shared `base.html` template provides the common layout (header, sidebar). Vanilla JS (`app.js`) handles uploads via `fetch()` and injects results into the DOM.

**Tech Stack:** FastAPI, Jinja2, uvicorn, python-multipart, Tailwind CSS (CDN), vanilla JavaScript, existing Python backend (Gemma2, DocTR, openpyxl).

---

## File Structure

```
finetuned_model/
├── main.py                          — FastAPI app, mount static/templates, include router
├── api/
│   ├── __init__.py
│   └── routes.py                    — all API endpoints (extract, batch, export, fournisseurs)
├── core/
│   ├── __init__.py
│   └── extraction.py                — extraction logic extracted from app.py (no Streamlit deps)
├── templates/
│   ├── base.html                    — shared layout (header + sidebar + block content)
│   ├── texte.html                   — page 1: Gemma2:9b Texte
│   ├── smart.html                   — page 2: Gemma2 Smart
│   ├── nouvelle.html                — page 3: Nouvelle Facture (OCR live)
│   └── batch.html                   — page 4: Traitement par lot
├── static/
│   └── js/
│       └── app.js                   — vanilla JS: uploads, API calls, DOM updates
└── requirements.txt                 — updated with fastapi, uvicorn, python-multipart, jinja2
```

---

### Task 1: Project scaffolding and dependencies

**Files:**
- Create: `main.py`
- Create: `api/__init__.py`
- Create: `api/routes.py`
- Create: `core/__init__.py`
- Create: `core/extraction.py`
- Create: `static/js/app.js`
- Create: `templates/base.html`
- Modify: `requirements.txt`

- [ ] **Step 1: Update requirements.txt**

Add FastAPI dependencies to `requirements.txt`:

```
streamlit>=1.30.0
pymupdf>=1.23.0
pillow>=10.0.0
ollama>=0.4.0
python-doctr[torch]>=0.9.0
fastapi>=0.115.0
uvicorn>=0.34.0
python-multipart>=0.0.20
jinja2>=3.1.0
```

- [ ] **Step 2: Install new dependencies**

Run: `pip install fastapi uvicorn python-multipart jinja2`

- [ ] **Step 3: Create directory structure**

Run:
```bash
mkdir -p api core templates static/js
touch api/__init__.py core/__init__.py
```

- [ ] **Step 4: Create minimal main.py**

```python
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pathlib import Path

app = FastAPI(title="Extraction de Factures BTP")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/")
async def root():
    return RedirectResponse(url="/texte")


@app.get("/texte")
async def page_texte(request: Request):
    return templates.TemplateResponse("texte.html", {"request": request, "active": "texte"})


@app.get("/smart")
async def page_smart(request: Request):
    return templates.TemplateResponse("smart.html", {"request": request, "active": "smart"})


@app.get("/nouvelle")
async def page_nouvelle(request: Request):
    return templates.TemplateResponse("nouvelle.html", {"request": request, "active": "nouvelle"})


@app.get("/batch")
async def page_batch(request: Request):
    return templates.TemplateResponse("batch.html", {"request": request, "active": "batch"})
```

- [ ] **Step 5: Create placeholder templates**

Create `templates/base.html`:
```html
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Extraction de Factures BTP</title>
</head>
<body>
<h1>Placeholder</h1>
{% block content %}{% endblock %}
</body>
</html>
```

Create `templates/texte.html`:
```html
{% extends "base.html" %}
{% block content %}<p>Texte page</p>{% endblock %}
```

Create `templates/smart.html`:
```html
{% extends "base.html" %}
{% block content %}<p>Smart page</p>{% endblock %}
```

Create `templates/nouvelle.html`:
```html
{% extends "base.html" %}
{% block content %}<p>Nouvelle page</p>{% endblock %}
```

Create `templates/batch.html`:
```html
{% extends "base.html" %}
{% block content %}<p>Batch page</p>{% endblock %}
```

- [ ] **Step 6: Create empty app.js**

Create `static/js/app.js`:
```javascript
// Extraction de Factures BTP — Frontend JS
console.log('app.js loaded');
```

- [ ] **Step 7: Create empty route and extraction files**

Create `api/routes.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api")
```

Create `core/extraction.py`:
```python
"""Extraction logic — adapted from app.py and scripts/12_gemma2_smart.py"""
```

- [ ] **Step 8: Wire router into main.py**

Add to `main.py` after the app definition:
```python
from api.routes import router as api_router
app.include_router(api_router)
```

- [ ] **Step 9: Test the server starts**

Run: `cd C:/Users/melko/Developer/finetuned_model && python -c "from main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 10: Commit**

```bash
git add main.py api/ core/ templates/ static/ requirements.txt
git commit -m "feat: scaffold FastAPI project structure"
```

---

### Task 2: Extract backend logic into core/extraction.py

**Files:**
- Create: `core/extraction.py` (full content)
- Read: `app.py` (lines 25-28, 265-377, 390-512, 538-587, 1037-1203)
- Read: `scripts/12_gemma2_smart.py` (lines 554-614, 745-873)

This task extracts all extraction and export logic from `app.py` into `core/extraction.py`, removing all Streamlit dependencies.

- [ ] **Step 1: Write core/extraction.py with OCR model loading**

```python
"""Extraction logic — no Streamlit dependencies."""

import io
import os
import json
import importlib.util
from pathlib import Path

import numpy as np
from PIL import Image
import fitz
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Import from scripts/12_gemma2_smart.py
_spec_smart = importlib.util.spec_from_file_location(
    "gemma2_smart", str(PROJECT_ROOT / "scripts" / "12_gemma2_smart.py")
)
_mod_smart = importlib.util.module_from_spec(_spec_smart)
_spec_smart.loader.exec_module(_mod_smart)

detect_installateur = _mod_smart.detect_installateur
detect_avoir = _mod_smart.detect_avoir
extraire_champs = _mod_smart.extraire_champs
inverser_montants_avoir = _mod_smart.inverser_montants_avoir
get_ocr_text = _mod_smart.get_ocr_text
PROMPTS_INSTALLATEURS = _mod_smart.PROMPTS_INSTALLATEURS

# OCR model singleton
_ocr_model = None


def get_ocr_model():
    global _ocr_model
    if _ocr_model is None:
        from doctr.models import ocr_predictor
        _ocr_model = ocr_predictor(
            det_arch="db_resnet50", reco_arch="crnn_vgg16_bn", pretrained=True
        )
    return _ocr_model
```

- [ ] **Step 2: Add FIELDS constants and clean_json**

Append to `core/extraction.py`:

```python
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

PROMPT_TEXTE = """Tu es un expert comptable specialise dans les factures BTP francaises.

REGLES :
- NUMERO_FACTURE : numero COMPLET apres "N", "Facture N", "Ref". Garde tous les caracteres.
- DATE_FACTURE : format JJ/MM/AAAA.
- MONTANT_HT : montant AVANT TVA. Format "358.83". Cherche "Total HT", "Net HT".
- TAUX_TVA : uniquement le pourcentage. Exemple "20%".
- MONTANT_TTC : montant FINAL avec TVA. Cherche "Total TTC", "Net a payer".
- NOM_INSTALLATEUR : nom COMPLET de l'entreprise emettrice (pas le client).
- COMMUNE_TRAVAUX : ville du chantier.
- CODE_POSTAL : code postal a 5 chiffres.
- ADRESSE_TRAVAUX : adresse complete du chantier.

TEXTE DE LA FACTURE :
{texte}

Reponds UNIQUEMENT en JSON valide. Aucun texte avant ou apres.
{{"NUMERO_FACTURE":null,"DATE_FACTURE":null,"MONTANT_HT":null,"TAUX_TVA":null,"MONTANT_TTC":null,"NOM_INSTALLATEUR":null,"COMMUNE_TRAVAUX":null,"CODE_POSTAL":null,"ADRESSE_TRAVAUX":null}}"""


def clean_json(raw):
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return raw
```

- [ ] **Step 3: Add extract_from_precomputed_ocr (for /texte page)**

Append to `core/extraction.py`:

```python
import ollama


def extract_from_precomputed_ocr(filename: str) -> dict:
    """Extract using pre-computed OCR text + generic Gemma2 prompt.
    Returns {"fields": dict, "error": str|None, "is_avoir": bool}
    """
    ocr_dir = PROJECT_ROOT / "data" / "ocr_texts"
    base_name = os.path.splitext(filename)[0]
    base_name = base_name.replace("_page0", "").replace("_page_001", "")

    texte = ""
    for root, dirs, files in os.walk(str(ocr_dir)):
        for f in files:
            if base_name.lower() in f.lower():
                try:
                    with open(os.path.join(root, f), "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        pages_ocr = data.get("pages", [])
                        for page in pages_ocr:
                            if isinstance(page, list):
                                lignes = {}
                                for token in page:
                                    if isinstance(token, dict):
                                        text = token.get("text", "").strip()
                                        if not text:
                                            continue
                                        bbox = token.get("bbox", [0, 0, 0, 0])
                                        y = round(bbox[1] / 10) * 10
                                        if y not in lignes:
                                            lignes[y] = []
                                        lignes[y].append((bbox[0], text))
                                for y in sorted(lignes.keys()):
                                    tokens_ligne = sorted(lignes[y], key=lambda t: t[0])
                                    texte += "  ".join(t[1] for t in tokens_ligne) + "\n"
                except Exception:
                    pass
                break

    if not texte:
        return {"fields": None, "error": "OCR introuvable pour cette facture", "is_avoir": False}

    is_avoir = detect_avoir(texte)

    prompt = PROMPT_TEXTE.format(texte=texte[:3000])
    response = ollama.chat(
        model="gemma2:9b",
        options={"temperature": 0, "seed": 42},
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        result = json.loads(clean_json(response["message"]["content"]))
        if is_avoir and result:
            result = inverser_montants_avoir(result)
        return {"fields": result, "error": None, "is_avoir": is_avoir}
    except json.JSONDecodeError:
        return {"fields": None, "error": "Reponse JSON invalide", "is_avoir": False}
```

- [ ] **Step 4: Add extract_smart (for /smart page)**

Append to `core/extraction.py`:

```python
def extract_smart(filename: str, fournisseur: str = "Auto-detect") -> dict:
    """Extract using pre-computed OCR + smart supplier-specific prompt.
    Returns {"fields": dict, "error": str|None, "installateur": str, "is_avoir": bool}
    """
    texte = get_ocr_text(filename)
    if texte is None:
        return {
            "fields": None,
            "error": "OCR introuvable pour cette facture",
            "installateur": None,
            "is_avoir": False,
        }

    if fournisseur == "Auto-detect":
        installateur = detect_installateur(texte)
    elif fournisseur == "DEFAULT":
        installateur = "DEFAULT"
    else:
        installateur = fournisseur.lower()

    is_avoir = detect_avoir(texte)
    fields = extraire_champs(texte, installateur)
    if is_avoir and fields:
        fields = inverser_montants_avoir(fields)

    return {
        "fields": fields,
        "error": None,
        "installateur": installateur,
        "is_avoir": is_avoir,
    }
```

- [ ] **Step 5: Add process_file_live (for /nouvelle page — OCR DocTR live)**

Append to `core/extraction.py`:

```python
def process_file_live(file_bytes: bytes, suffix: str, fournisseur: str = "Auto-detect") -> dict:
    """Full pipeline: DocTR OCR in memory + Gemma2 extraction.
    Returns {"fields": dict, "error": str|None, "installateur": str, "is_avoir": bool}
    """
    # Convert to PIL images
    pil_images = []
    if suffix == ".pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            pil_images.append(img)
        doc.close()
    else:
        pil_images.append(Image.open(io.BytesIO(file_bytes)).convert("RGB"))

    nb_pages = len(pil_images)

    # OCR DocTR
    model_ocr = get_ocr_model()
    np_images = [np.array(img) for img in pil_images]
    result_ocr = model_ocr(np_images)

    # Find the page with financial keywords
    MONTANT_KEYWORDS = ["ht", "tva", "ttc", "total", "net", "payer", "montant"]
    if nb_pages == 1:
        pages_indices = [0]
    else:
        best_page = nb_pages - 1
        best_score = 0
        for pi in range(1, nb_pages):
            words = [
                word.value.lower()
                for block in result_ocr.pages[pi].blocks
                for line in block.lines
                for word in line.words
            ]
            score = sum(1 for w in words for kw in MONTANT_KEYWORDS if kw in w)
            if score > best_score or (score == best_score and pi > best_page):
                best_score = score
                best_page = pi
        pages_indices = [0] if best_page == 0 else [0, best_page]

    # Reconstruct text
    all_tokens = []
    for pi in pages_indices:
        page = result_ocr.pages[pi]
        h, w = pil_images[pi].height, pil_images[pi].width
        for block in page.blocks:
            for line in block.lines:
                for word in line.words:
                    x0, y0 = word.geometry[0]
                    x1 = word.geometry[1][0]
                    all_tokens.append({
                        "text": word.value, "y": y0 * h, "x": x0 * w,
                        "x2": x1 * w, "page": pi,
                    })

    all_tokens.sort(key=lambda t: (t["page"], t["y"], t["x"]))

    grouped_lines = []
    current_line = []
    current_y = -999
    current_page = -1
    for token in all_tokens:
        if token["page"] != current_page or abs(token["y"] - current_y) > 5:
            if current_line:
                grouped_lines.append(current_line)
            current_line = [token]
            current_y = token["y"]
            current_page = token["page"]
        else:
            current_line.append(token)
    if current_line:
        grouped_lines.append(current_line)

    lines = []
    for line_tokens in grouped_lines:
        line_tokens.sort(key=lambda t: t["x"])
        fused = []
        for token in line_tokens:
            if fused:
                prev = fused[-1]
                prev_ends_digit = prev["text"][-1].isdigit()
                cur_starts_num = token["text"][0].isdigit() or token["text"][0] in ",."
                distance = token["x"] - prev["x2"]
                if prev_ends_digit and cur_starts_num and abs(distance) < 20:
                    prev["text"] = prev["text"] + token["text"]
                    prev["x2"] = token["x2"]
                    continue
            fused.append(dict(token))
        lines.append(" ".join(t["text"] for t in fused))

    texte = "\n".join(lines)
    if not texte.strip():
        return {"fields": None, "error": "Aucun texte OCR", "installateur": None, "is_avoir": False}

    # Detect supplier + avoir + extract
    if fournisseur == "Auto-detect":
        installateur = detect_installateur(texte)
    elif fournisseur == "DEFAULT":
        installateur = "DEFAULT"
    else:
        installateur = fournisseur.lower()

    is_avoir = detect_avoir(texte)
    fields = extraire_champs(texte, installateur)
    if is_avoir and fields:
        fields = inverser_montants_avoir(fields)

    return {
        "fields": fields,
        "error": None,
        "installateur": installateur,
        "is_avoir": is_avoir,
    }
```

- [ ] **Step 6: Add process_batch_zip (for /batch page)**

Append to `core/extraction.py`:

```python
import zipfile


def process_batch_zip(zip_bytes: bytes) -> list[dict]:
    """Process a ZIP of invoices. Returns list of result dicts."""
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    valid_ext = {".pdf", ".png", ".jpg", ".jpeg"}
    file_names = [
        n for n in zf.namelist()
        if not n.startswith("__") and not n.endswith("/")
        and os.path.splitext(n)[1].lower() in valid_ext
    ]
    file_names.sort()

    results = []
    for fname in file_names:
        short_name = os.path.basename(fname)

        # Try pre-computed OCR first
        texte = get_ocr_text(short_name)
        if texte:
            installateur = detect_installateur(texte)
            is_avoir = detect_avoir(texte)
            fields = extraire_champs(texte, installateur)
            if is_avoir and fields:
                fields = inverser_montants_avoir(fields)
            if fields:
                results.append({
                    "filename": short_name,
                    "fields": fields,
                    "installateur": installateur or "DEFAULT",
                    "is_avoir": is_avoir,
                    "source": "OCR pre-calcule",
                })
                continue

        # Fallback: DocTR live
        try:
            file_bytes = zf.read(fname)
            suffix = os.path.splitext(fname)[1].lower()
            res = process_file_live(file_bytes, suffix, "Auto-detect")
            if res["fields"] and not res["error"]:
                results.append({
                    "filename": short_name,
                    "fields": res["fields"],
                    "installateur": res["installateur"] or "DEFAULT",
                    "is_avoir": res["is_avoir"],
                    "source": "DocTR live",
                })
            else:
                results.append({
                    "filename": short_name,
                    "fields": {k: None for k in ALL_FIELD_KEYS},
                    "installateur": "ERREUR",
                    "is_avoir": False,
                    "source": res["error"] or "Echec extraction",
                })
        except Exception as e:
            results.append({
                "filename": short_name,
                "fields": {k: None for k in ALL_FIELD_KEYS},
                "installateur": "ERREUR",
                "is_avoir": False,
                "source": str(e),
            })

    return results
```

- [ ] **Step 7: Add Excel export functions**

Append to `core/extraction.py`:

```python
def export_excel_batch(results_list: list[dict]) -> bytes:
    """Generate styled Excel with one row per invoice. Returns bytes."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    all_labels = ["Nom du PDF", "Type"] + [lbl for _, lbl in FIELDS_LEFT + FIELDS_RIGHT] + ["Fournisseur"]
    rows = []
    for res in results_list:
        row = {"Nom du PDF": res["filename"]}
        row["Type"] = "AVOIR" if res.get("is_avoir") else "FACTURE"
        for key, label in FIELDS_LEFT + FIELDS_RIGHT:
            val = res["fields"].get(key)
            if val is None or val == "null":
                val = ""
            elif isinstance(val, list):
                val = " | ".join(str(v) for v in val)
            row[label] = str(val)
        row["Fournisseur"] = res.get("installateur", "").upper()
        rows.append(row)
    df = pd.DataFrame(rows, columns=all_labels)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Extractions", startrow=2)
        ws = writer.sheets["Extractions"]

        nb_cols = len(all_labels)
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=nb_cols)
        title_cell = ws.cell(row=1, column=1, value=f"Extraction batch - {len(results_list)} factures")
        title_cell.font = Font(name="Calibri", size=14, bold=True, color="1E3A5F")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 30

        header_fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        thin_border = Border(
            left=Side(style="thin", color="D1D5DB"),
            right=Side(style="thin", color="D1D5DB"),
            top=Side(style="thin", color="D1D5DB"),
            bottom=Side(style="thin", color="D1D5DB"),
        )

        for col_idx in range(1, nb_cols + 1):
            cell = ws.cell(row=3, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border
        ws.row_dimensions[3].height = 32

        val_font = Font(name="Calibri", size=11)
        val_fill_ok = PatternFill(start_color="E6F4EA", end_color="E6F4EA", fill_type="solid")
        val_fill_empty = PatternFill(start_color="FDE8E8", end_color="FDE8E8", fill_type="solid")
        val_fill_avoir = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
        val_fill_warn = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
        val_font_warn = Font(name="Calibri", size=11, italic=True, color="E65100")
        label_to_key = {lbl: key for key, lbl in FIELDS_LEFT + FIELDS_RIGHT}

        for row_idx in range(4, 4 + len(results_list)):
            res = results_list[row_idx - 4]
            fields = res.get("fields") or {}
            a_verifier = fields.get("_a_verifier", [])
            is_avoir = res.get("is_avoir", False)

            for col_idx in range(1, nb_cols + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font = val_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border
                col_label = all_labels[col_idx - 1]
                field_key = label_to_key.get(col_label, "")

                if is_avoir:
                    cell.fill = val_fill_avoir
                    if col_idx == 1:
                        cell.font = Font(name="Calibri", size=11, bold=True)
                    elif not cell.value:
                        cell.value = "Non detecte"
                        cell.font = Font(name="Calibri", size=11, italic=True, color="C53030")
                elif col_idx == 1:
                    cell.font = Font(name="Calibri", size=11, bold=True)
                elif field_key in a_verifier:
                    cell.fill = val_fill_warn
                    cell.font = val_font_warn
                    if cell.value:
                        cell.value = str(cell.value) + " (a verifier)"
                elif not cell.value:
                    cell.fill = val_fill_empty
                    cell.value = "Non detecte"
                    cell.font = Font(name="Calibri", size=11, italic=True, color="C53030")
                else:
                    cell.fill = val_fill_ok
            ws.row_dimensions[row_idx].height = 26

        for col_idx, label in enumerate(all_labels, 1):
            max_len = len(label)
            for row_idx in range(4, 4 + len(results_list)):
                val = str(ws.cell(row=row_idx, column=col_idx).value or "")
                max_len = max(max_len, len(val))
            ws.column_dimensions[ws.cell(row=3, column=col_idx).column_letter].width = max_len + 4

    return buf.getvalue()


def export_excel_multi_sheets(results_list: list[dict]) -> bytes:
    """Generate multi-sheet Excel (one per supplier + TOUTES_FACTURES). Returns bytes."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    columns = [
        "NOM_FICHIER", "TYPE", "NUMERO_FACTURE", "DATE_FACTURE",
        "MONTANT_HT", "TAUX_TVA", "MONTANT_TTC",
        "NOM_INSTALLATEUR", "COMMUNE_TRAVAUX", "CODE_POSTAL", "ADRESSE_TRAVAUX",
    ]
    field_keys = ALL_FIELD_KEYS

    def build_rows(items):
        rows = []
        for res in items:
            row = {"NOM_FICHIER": res["filename"]}
            row["TYPE"] = "AVOIR" if res.get("is_avoir") else "FACTURE"
            for col, key in zip(columns[2:], field_keys):
                val = res["fields"].get(key)
                if val is None or val == "null":
                    val = ""
                elif isinstance(val, list):
                    val = " | ".join(str(v) for v in val)
                row[col] = str(val)
            rows.append(row)
        return rows

    by_inst = {}
    for res in results_list:
        inst = res.get("installateur", "INCONNU").upper()
        by_inst.setdefault(inst, []).append(res)

    header_fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    val_font = Font(name="Calibri", size=11)
    err_font = Font(name="Calibri", size=11, italic=True, color="C53030")
    err_fill = PatternFill(start_color="FDE8E8", end_color="FDE8E8", fill_type="solid")
    ok_fill = PatternFill(start_color="E6F4EA", end_color="E6F4EA", fill_type="solid")
    warn_fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
    warn_font = Font(name="Calibri", size=11, italic=True, color="E65100")
    avoir_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB"),
    )
    col_to_key = dict(zip(columns[2:], field_keys))

    def style_sheet(ws, rows_data, items):
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))
        title_cell = ws.cell(row=1, column=1, value=ws.title)
        title_cell.font = Font(name="Calibri", size=14, bold=True, color="1E3A5F")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 30

        for col_idx, col_name in enumerate(columns, 1):
            cell = ws.cell(row=3, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border
        ws.row_dimensions[3].height = 32

        for row_idx in range(4, 4 + len(rows_data)):
            res = items[row_idx - 4]
            fields = res.get("fields") or {}
            a_verifier = fields.get("_a_verifier", [])
            is_avoir = res.get("is_avoir", False)

            for col_idx in range(1, len(columns) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border
                col_name = columns[col_idx - 1]
                field_key = col_to_key.get(col_name, "")

                if is_avoir:
                    cell.fill = avoir_fill
                    if col_idx == 1:
                        cell.font = Font(name="Calibri", size=11, bold=True)
                    elif not cell.value:
                        cell.value = "Non detecte"
                        cell.font = err_font
                    else:
                        cell.font = val_font
                elif col_idx == 1:
                    cell.font = Font(name="Calibri", size=11, bold=True)
                elif field_key in a_verifier:
                    cell.fill = warn_fill
                    cell.font = warn_font
                    if cell.value:
                        cell.value = str(cell.value) + " (a verifier)"
                elif not cell.value:
                    cell.value = "Non detecte"
                    cell.font = err_font
                    cell.fill = err_fill
                else:
                    cell.font = val_font
                    cell.fill = ok_fill
            ws.row_dimensions[row_idx].height = 26

        for col_idx, col_name in enumerate(columns, 1):
            max_len = len(col_name)
            for row_idx in range(4, 4 + len(rows_data)):
                val = str(ws.cell(row=row_idx, column=col_idx).value or "")
                max_len = max(max_len, len(val))
            ws.column_dimensions[ws.cell(row=3, column=col_idx).column_letter].width = max_len + 4

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        all_rows = build_rows(results_list)
        df_all = pd.DataFrame(all_rows, columns=columns)
        df_all.to_excel(writer, index=False, sheet_name="TOUTES_FACTURES", startrow=2)
        style_sheet(writer.sheets["TOUTES_FACTURES"], all_rows, results_list)

        for inst_name in sorted(by_inst.keys()):
            sheet_name = inst_name[:31]
            inst_items = by_inst[inst_name]
            inst_rows = build_rows(inst_items)
            df_inst = pd.DataFrame(inst_rows, columns=columns)
            df_inst.to_excel(writer, index=False, sheet_name=sheet_name, startrow=2)
            style_sheet(writer.sheets[sheet_name], inst_rows, inst_items)

    return buf.getvalue()


def get_fournisseurs_list() -> list[str]:
    """Return sorted list of known supplier names."""
    noms = [k for k in PROMPTS_INSTALLATEURS.keys() if k != "DEFAULT"]
    noms.sort()
    return noms
```

- [ ] **Step 8: Verify core/extraction.py imports cleanly**

Run: `cd C:/Users/melko/Developer/finetuned_model && python -c "from core.extraction import get_fournisseurs_list; print(get_fournisseurs_list()[:3])"`

Expected: A list of supplier names like `['a2m', 'arcana', 'cailloce']`

- [ ] **Step 9: Commit**

```bash
git add core/extraction.py
git commit -m "feat: extract backend logic into core/extraction.py"
```

---

### Task 3: Build API endpoints

**Files:**
- Modify: `api/routes.py` (replace placeholder)

- [ ] **Step 1: Write api/routes.py with all endpoints**

```python
from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
import os

from core.extraction import (
    extract_from_precomputed_ocr,
    extract_smart,
    process_file_live,
    process_batch_zip,
    export_excel_batch,
    export_excel_multi_sheets,
    get_fournisseurs_list,
)

router = APIRouter(prefix="/api")


@router.get("/fournisseurs")
async def list_fournisseurs():
    return {"fournisseurs": get_fournisseurs_list()}


@router.post("/extract-texte")
async def api_extract_texte(file: UploadFile = File(...)):
    result = extract_from_precomputed_ocr(file.filename)
    return result


@router.post("/extract-smart")
async def api_extract_smart(
    file: UploadFile = File(...),
    fournisseur: str = Form("Auto-detect"),
):
    result = extract_smart(file.filename, fournisseur)
    return result


@router.post("/extract-ocr")
async def api_extract_ocr(
    file: UploadFile = File(...),
    fournisseur: str = Form("Auto-detect"),
):
    file_bytes = await file.read()
    suffix = os.path.splitext(file.filename)[1].lower()
    result = process_file_live(file_bytes, suffix, fournisseur)
    return result


@router.post("/batch")
async def api_batch(file: UploadFile = File(...)):
    zip_bytes = await file.read()
    results = process_batch_zip(zip_bytes)
    return {"results": results, "total": len(results)}


class ExportRequest(BaseModel):
    results: list[dict]


@router.post("/export-excel")
async def api_export_excel(data: ExportRequest):
    xlsx_bytes = export_excel_batch(data.results)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=extraction.xlsx"},
    )


@router.post("/export-excel-multi")
async def api_export_excel_multi(data: ExportRequest):
    xlsx_bytes = export_excel_multi_sheets(data.results)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=extraction_multi.xlsx"},
    )
```

- [ ] **Step 2: Verify API routes load**

Run: `cd C:/Users/melko/Developer/finetuned_model && python -c "from api.routes import router; print(f'{len(router.routes)} routes loaded')"`

Expected: `7 routes loaded`

- [ ] **Step 3: Commit**

```bash
git add api/routes.py
git commit -m "feat: add FastAPI REST endpoints for extraction and export"
```

---

### Task 4: Build base.html template

**Files:**
- Modify: `templates/base.html` (replace placeholder)

The base template extracts the common header and sidebar from all 4 stitch HTML files. Content is injected via Jinja2 `{% block content %}`.

- [ ] **Step 1: Write templates/base.html**

```html
<!DOCTYPE html>
<html class="light" lang="fr">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Extraction de Factures BTP</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<script>
tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "tertiary-fixed-dim":"#ffb95f","secondary-fixed":"#d3e4fe",
        "on-secondary-fixed-variant":"#38485d","outline-variant":"#c3c6d6",
        "surface":"#f7f9fb","surface-variant":"#e0e3e5",
        "primary-fixed":"#dae2ff","on-primary-fixed":"#001848",
        "tertiary-fixed":"#ffddb8","on-error":"#ffffff",
        "secondary-container":"#d0e1fb","surface-container-low":"#f2f4f6",
        "primary-fixed-dim":"#b2c5ff","surface-container-lowest":"#ffffff",
        "inverse-primary":"#b2c5ff","on-secondary":"#ffffff",
        "on-background":"#191c1e","on-error-container":"#93000a",
        "tertiary-container":"#805000","outline":"#737685",
        "surface-container-high":"#e6e8ea","on-primary-container":"#c4d2ff",
        "surface-dim":"#d8dadc","error-container":"#ffdad6",
        "on-secondary-fixed":"#0b1c30","surface-container-highest":"#e0e3e5",
        "on-tertiary-fixed-variant":"#653e00","background":"#f7f9fb",
        "on-secondary-container":"#54647a","on-tertiary":"#ffffff",
        "on-primary-fixed-variant":"#0040a2","on-surface-variant":"#434654",
        "secondary-fixed-dim":"#b7c8e1","on-tertiary-fixed":"#2a1700",
        "on-primary":"#ffffff","primary":"#003d9b","secondary":"#505f76",
        "inverse-surface":"#2d3133","on-tertiary-container":"#ffc988",
        "surface-tint":"#0c56d0","surface-bright":"#f7f9fb",
        "inverse-on-surface":"#eff1f3","primary-container":"#0052cc",
        "on-surface":"#191c1e","tertiary":"#603b00",
        "surface-container":"#eceef0","error":"#ba1a1a"
      },
      borderRadius: {"DEFAULT":"0.125rem","lg":"0.25rem","xl":"0.5rem","full":"0.75rem"},
      fontFamily: {"headline":["Manrope"],"body":["Inter"],"label":["Inter"]}
    }
  }
}
</script>
<style>
body { font-family: 'Inter', sans-serif; background-color: #f7f9fb; min-height: 100dvh; }
.font-manrope { font-family: 'Manrope', sans-serif; }
.material-symbols-outlined { font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24; }
.tonal-shift-no-borders { border: none !important; }
.glass-preview { background: rgba(255,255,255,0.8); backdrop-filter: blur(16px); }
</style>
</head>
<body class="bg-surface font-body text-on-surface min-h-screen">

<!-- TopAppBar -->
<header class="fixed top-0 w-full z-50 flex items-center px-6 h-16 bg-gradient-to-r from-[#003d9b] to-[#0052cc] shadow-lg">
  <div class="flex items-center gap-3">
    <span class="material-symbols-outlined text-white" style="font-variation-settings: 'FILL' 1;">description</span>
    <h1 class="font-manrope font-bold text-2xl tracking-tight text-white">Extraction de Factures BTP</h1>
  </div>
  <div class="ml-auto flex items-center gap-6">
    <div class="text-white font-black tracking-widest uppercase text-sm">Melko</div>
  </div>
</header>

<!-- Sidebar -->
<aside class="h-screen w-72 fixed left-0 top-0 bg-[#eceef0] z-40 pt-16 tonal-shift-no-borders">
  <div class="flex flex-col h-full py-8 px-4">
    <div class="flex items-center gap-3 mb-10 px-2">
      <div class="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-white font-bold text-xl">M</div>
      <div>
        <h2 class="font-manrope font-extrabold text-blue-800 text-sm leading-tight">Extraction Suite</h2>
        <p class="text-xs text-slate-500">v3.0.0</p>
      </div>
    </div>
    <div class="px-4 mb-4">
      <p class="text-[10px] uppercase tracking-widest font-bold text-slate-400">Configuration</p>
      <div class="mt-2 p-3 bg-white/50 rounded-xl">
        <p class="text-xs font-medium text-slate-700">OCR: DocTR</p>
        <p class="text-xs font-medium text-slate-700">Model: Gemma2:9b</p>
      </div>
    </div>
    <nav class="space-y-1">
      <a href="/texte" class="flex items-center gap-3 px-4 py-3 {% if active == 'texte' %}bg-white text-[#003d9b] font-bold border-r-4 border-[#003d9b]{% else %}text-slate-600 hover:bg-slate-200/50 hover:translate-x-1 transition-transform duration-200{% endif %} text-sm font-medium tracking-normal">
        <span class="material-symbols-outlined text-xl" {% if active == 'texte' %}style="font-variation-settings: 'FILL' 1;"{% endif %}>article</span>
        <span>Gemma2:9b Texte</span>
      </a>
      <a href="/smart" class="flex items-center gap-3 px-4 py-3 {% if active == 'smart' %}bg-white text-[#003d9b] font-bold border-r-4 border-[#003d9b]{% else %}text-slate-600 hover:bg-slate-200/50 hover:translate-x-1 transition-transform duration-200{% endif %} text-sm font-medium tracking-normal">
        <span class="material-symbols-outlined text-xl" {% if active == 'smart' %}style="font-variation-settings: 'FILL' 1;"{% endif %}>psychology</span>
        <span>Gemma2 Smart</span>
      </a>
      <a href="/nouvelle" class="flex items-center gap-3 px-4 py-3 {% if active == 'nouvelle' %}bg-white text-[#003d9b] font-bold border-r-4 border-[#003d9b]{% else %}text-slate-600 hover:bg-slate-200/50 hover:translate-x-1 transition-transform duration-200{% endif %} text-sm font-medium tracking-normal">
        <span class="material-symbols-outlined text-xl" {% if active == 'nouvelle' %}style="font-variation-settings: 'FILL' 1;"{% endif %}>upload_file</span>
        <span>Nouvelle Facture</span>
      </a>
      <a href="/batch" class="flex items-center gap-3 px-4 py-3 {% if active == 'batch' %}bg-white text-[#003d9b] font-bold border-r-4 border-[#003d9b]{% else %}text-slate-600 hover:bg-slate-200/50 hover:translate-x-1 transition-transform duration-200{% endif %} text-sm font-medium tracking-normal">
        <span class="material-symbols-outlined text-xl" {% if active == 'batch' %}style="font-variation-settings: 'FILL' 1;"{% endif %}>layers</span>
        <span>Traitement par lot</span>
      </a>
    </nav>
    <div class="mt-auto px-4 pb-4">
      <span class="text-[10px] font-bold text-slate-400 tracking-widest">VERSION v3.0.0</span>
    </div>
  </div>
</aside>

<!-- Main Content -->
<main class="ml-72 pt-24 pb-12 px-8 min-h-screen bg-surface">
  <div class="max-w-6xl mx-auto space-y-8">
    {% block content %}{% endblock %}
  </div>
</main>

<script src="/static/js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify template renders**

Run: `cd C:/Users/melko/Developer/finetuned_model && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates')); t = env.get_template('base.html'); print('base.html OK')" `

Expected: `base.html OK`

- [ ] **Step 3: Commit**

```bash
git add templates/base.html
git commit -m "feat: add base.html template with shared layout"
```

---

### Task 5: Build page templates from stitch HTML

**Files:**
- Modify: `templates/texte.html` (replace placeholder)
- Modify: `templates/smart.html` (replace placeholder)
- Modify: `templates/nouvelle.html` (replace placeholder)
- Modify: `templates/batch.html` (replace placeholder)
- Source: `stitch/gemma2_9b_texte_extraction_g_n_rique/code.html`
- Source: `stitch/gemma2_smart_d_tection_fournisseur/code.html`
- Source: `stitch/nouvelle_facture_live_ocr_batch_processing/code.html`
- Source: `stitch/traitement_par_lot_multi_feuilles_excel_stats_batch/code.html`

Each template extends `base.html` and contains only the `<main>` content from the stitch HTML. Key elements get `id` attributes so `app.js` can manipulate them.

- [ ] **Step 1: Build templates/texte.html**

Extract the content inside `<main>` from `stitch/gemma2_9b_texte_extraction_g_n_rique/code.html` (lines 146-273). Wrap in `{% extends "base.html" %}{% block content %}...{% endblock %}`. Add `id` attributes to:
- Upload input: `id="upload-texte"`
- Upload zone: `id="upload-zone-texte"`
- Upload button: `id="btn-upload-texte"`
- Results container: `id="results-texte"` (initially `hidden`)
- Each data field card: `id="field-NUMERO_FACTURE"`, `id="field-DATE_FACTURE"`, etc.
- Export button: `id="btn-export-texte"`
- JSON expander pre: `id="json-raw-texte"`
- Loading spinner: add a `<div id="loading-texte" class="hidden">` with spinner

- [ ] **Step 2: Build templates/smart.html**

Same approach from `stitch/gemma2_smart_d_tection_fournisseur/code.html` (lines 152-328). Add `id` attributes:
- Upload input: `id="upload-smart"`
- Fournisseur select: `id="select-fournisseur-smart"`
- Detected fournisseur display: `id="detected-fournisseur"`
- Results container: `id="results-smart"` (initially `hidden`)
- Each data field: `id="smart-field-NUMERO_FACTURE"`, etc.
- Export button: `id="btn-export-smart"`
- JSON expander: `id="json-raw-smart"`
- Loading spinner: `id="loading-smart"`

Populate the fournisseur `<select>` dynamically via JS calling `GET /api/fournisseurs`.

- [ ] **Step 3: Build templates/nouvelle.html**

From `stitch/nouvelle_facture_live_ocr_batch_processing/code.html` (lines 141-336). Add `id` attributes:
- Mode radio buttons: `id="mode-unique"`, `id="mode-zip"`
- Upload inputs: `id="upload-nouvelle"`, `id="upload-zip-nouvelle"`
- Upload zones: `id="zone-unique"`, `id="zone-zip"` (toggle visibility with JS)
- Fournisseur select: `id="select-fournisseur-nouvelle"`
- Stats cards: `id="stat-extraites"`, `id="stat-erreurs"`, `id="stat-progress"`
- Results list container: `id="results-nouvelle"`
- Export button: `id="btn-export-nouvelle"`
- Loading: `id="loading-nouvelle"`

- [ ] **Step 4: Build templates/batch.html**

From `stitch/traitement_par_lot_multi_feuilles_excel_stats_batch/code.html` (lines 149-338). Add `id` attributes:
- Upload input: `id="upload-batch"`
- Progress bar: `id="progress-batch"`, `id="progress-text-batch"`
- Stats: `id="stat-traitees"`, `id="stat-ocr-precalc"`, `id="stat-doctr-live"`, `id="stat-installateurs"`, `id="stat-manquants"`, `id="stat-erreurs-batch"`
- Avoir detection card: keep as-is (informational)
- Results list: `id="results-batch"`
- Table preview: `id="table-preview-batch"`
- Export button: `id="btn-export-batch"`
- Loading: `id="loading-batch"`

- [ ] **Step 5: Verify all templates render**

Run:
```bash
cd C:/Users/melko/Developer/finetuned_model && python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('templates'))
for name in ['texte.html', 'smart.html', 'nouvelle.html', 'batch.html']:
    t = env.get_template(name)
    print(f'{name} OK')
"
```

Expected:
```
texte.html OK
smart.html OK
nouvelle.html OK
batch.html OK
```

- [ ] **Step 6: Commit**

```bash
git add templates/
git commit -m "feat: add 4 page templates from stitch HTML"
```

---

### Task 6: Build app.js — shared utilities

**Files:**
- Modify: `static/js/app.js` (replace placeholder)

- [ ] **Step 1: Write shared utility functions**

```javascript
// ── Extraction de Factures BTP — Frontend JS ──

/**
 * Show a loading spinner, disable a button.
 */
function showLoading(spinnerId, buttonId) {
  const spinner = document.getElementById(spinnerId);
  const btn = document.getElementById(buttonId);
  if (spinner) spinner.classList.remove('hidden');
  if (btn) { btn.disabled = true; btn.classList.add('opacity-50', 'cursor-not-allowed'); }
}

function hideLoading(spinnerId, buttonId) {
  const spinner = document.getElementById(spinnerId);
  const btn = document.getElementById(buttonId);
  if (spinner) spinner.classList.add('hidden');
  if (btn) { btn.disabled = false; btn.classList.remove('opacity-50', 'cursor-not-allowed'); }
}

/**
 * Upload a file to an API endpoint, return JSON.
 */
async function uploadFile(url, file, extraFields = {}) {
  const formData = new FormData();
  formData.append('file', file);
  for (const [key, val] of Object.entries(extraFields)) {
    formData.append(key, val);
  }
  const resp = await fetch(url, { method: 'POST', body: formData });
  if (!resp.ok) throw new Error(`Erreur serveur: ${resp.status}`);
  return resp.json();
}

/**
 * Download an Excel file from the export endpoint.
 */
async function downloadExcel(url, results, filename) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ results }),
  });
  if (!resp.ok) throw new Error(`Erreur export: ${resp.status}`);
  const blob = await resp.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

/**
 * Populate a field card with extracted value.
 * Handles: normal (green), missing (red), warning (orange), avoir (amber).
 */
function setFieldValue(elementId, value, status = 'ok') {
  const el = document.getElementById(elementId);
  if (!el) return;

  // Reset classes
  el.className = el.className.replace(/bg-\S+/g, '').replace(/text-\S+/g, '').trim();

  if (!value || value === 'null') {
    el.textContent = 'Donnee manquante';
    el.classList.add('bg-error-container', 'text-on-error-container', 'italic');
  } else if (status === 'warning') {
    el.textContent = value + ' (a verifier)';
    el.classList.add('bg-tertiary-fixed', 'text-on-tertiary-fixed-variant');
  } else if (status === 'avoir') {
    el.textContent = value;
    el.classList.add('bg-tertiary-fixed/30', 'text-on-tertiary-fixed-variant');
  } else {
    el.textContent = value;
    el.classList.add('bg-surface-container-low', 'text-on-surface');
  }
}

/**
 * Fill all 9 extraction fields from a result object.
 */
function fillFields(prefix, fields, isAvoir = false) {
  if (!fields) return;
  const aVerifier = fields._a_verifier || [];
  const allKeys = [
    'NUMERO_FACTURE', 'DATE_FACTURE', 'MONTANT_HT', 'TAUX_TVA', 'MONTANT_TTC',
    'NOM_INSTALLATEUR', 'COMMUNE_TRAVAUX', 'CODE_POSTAL', 'ADRESSE_TRAVAUX',
  ];
  for (const key of allKeys) {
    let status = 'ok';
    if (aVerifier.includes(key)) status = 'warning';
    else if (isAvoir) status = 'avoir';
    setFieldValue(`${prefix}-${key}`, fields[key], status);
  }
}

/**
 * Populate fournisseur dropdowns from API.
 */
async function loadFournisseurs(selectId) {
  const select = document.getElementById(selectId);
  if (!select) return;
  try {
    const resp = await fetch('/api/fournisseurs');
    const data = await resp.json();
    // Keep existing first option (Auto-detect)
    for (const name of data.fournisseurs) {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name.toUpperCase();
      select.appendChild(opt);
    }
    // Add DEFAULT at the end
    const defOpt = document.createElement('option');
    defOpt.value = 'DEFAULT';
    defOpt.textContent = 'DEFAULT (generique)';
    select.appendChild(defOpt);
  } catch (e) {
    console.error('Failed to load fournisseurs:', e);
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add static/js/app.js
git commit -m "feat: add app.js shared utilities (upload, fields, export)"
```

---

### Task 7: Build app.js — page-specific logic

**Files:**
- Modify: `static/js/app.js` (append)

- [ ] **Step 1: Add page-specific initialization at bottom of app.js**

Append to `static/js/app.js`:

```javascript
// ── PAGE-SPECIFIC LOGIC ──

document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;

  // ── PAGE: /texte ──
  if (path === '/texte') {
    const input = document.getElementById('upload-texte');
    const btnExport = document.getElementById('btn-export-texte');
    let lastResult = null;

    if (input) {
      input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        showLoading('loading-texte', 'btn-upload-texte');
        document.getElementById('results-texte')?.classList.add('hidden');
        try {
          const data = await uploadFile('/api/extract-texte', file);
          lastResult = data;
          if (data.error) {
            alert('Erreur: ' + data.error);
          } else {
            fillFields('field', data.fields, data.is_avoir);
            document.getElementById('json-raw-texte').textContent = JSON.stringify(data.fields, null, 2);
            document.getElementById('results-texte')?.classList.remove('hidden');
          }
        } catch (err) {
          alert('Erreur: ' + err.message);
        } finally {
          hideLoading('loading-texte', 'btn-upload-texte');
        }
      });
    }

    if (btnExport) {
      btnExport.addEventListener('click', () => {
        if (!lastResult?.fields) return;
        downloadExcel('/api/export-excel', [{
          filename: document.getElementById('upload-texte')?.files[0]?.name || 'facture',
          fields: lastResult.fields,
          installateur: 'gemma2-texte',
          is_avoir: lastResult.is_avoir,
        }], 'extraction.xlsx');
      });
    }
  }

  // ── PAGE: /smart ──
  if (path === '/smart') {
    loadFournisseurs('select-fournisseur-smart');
    const input = document.getElementById('upload-smart');
    const btnExport = document.getElementById('btn-export-smart');
    let lastResult = null;

    if (input) {
      input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const fournisseur = document.getElementById('select-fournisseur-smart')?.value || 'Auto-detect';
        showLoading('loading-smart', null);
        document.getElementById('results-smart')?.classList.add('hidden');
        try {
          const data = await uploadFile('/api/extract-smart', file, { fournisseur });
          lastResult = data;
          if (data.error) {
            alert('Erreur: ' + data.error);
          } else {
            // Show detected supplier
            const detEl = document.getElementById('detected-fournisseur');
            if (detEl) detEl.textContent = (data.installateur || '?').toUpperCase();

            fillFields('smart-field', data.fields, data.is_avoir);
            document.getElementById('json-raw-smart').textContent = JSON.stringify(data.fields, null, 2);
            document.getElementById('results-smart')?.classList.remove('hidden');
          }
        } catch (err) {
          alert('Erreur: ' + err.message);
        } finally {
          hideLoading('loading-smart', null);
        }
      });
    }

    if (btnExport) {
      btnExport.addEventListener('click', () => {
        if (!lastResult?.fields) return;
        downloadExcel('/api/export-excel', [{
          filename: document.getElementById('upload-smart')?.files[0]?.name || 'facture',
          fields: lastResult.fields,
          installateur: lastResult.installateur || '',
          is_avoir: lastResult.is_avoir,
        }], 'extraction_smart.xlsx');
      });
    }
  }

  // ── PAGE: /nouvelle ──
  if (path === '/nouvelle') {
    loadFournisseurs('select-fournisseur-nouvelle');
    const inputFile = document.getElementById('upload-nouvelle');
    const inputZip = document.getElementById('upload-zip-nouvelle');
    const btnExport = document.getElementById('btn-export-nouvelle');
    let batchResults = [];

    // Mode toggle
    const modeUnique = document.getElementById('mode-unique');
    const modeZip = document.getElementById('mode-zip');
    const zoneUnique = document.getElementById('zone-unique');
    const zoneZip = document.getElementById('zone-zip');

    if (modeUnique && modeZip) {
      modeUnique.addEventListener('change', () => {
        if (zoneUnique) zoneUnique.classList.remove('hidden');
        if (zoneZip) zoneZip.classList.add('hidden');
      });
      modeZip.addEventListener('change', () => {
        if (zoneUnique) zoneUnique.classList.add('hidden');
        if (zoneZip) zoneZip.classList.remove('hidden');
      });
    }

    // Single file upload
    if (inputFile) {
      inputFile.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const fournisseur = document.getElementById('select-fournisseur-nouvelle')?.value || 'Auto-detect';
        showLoading('loading-nouvelle', null);
        try {
          const data = await uploadFile('/api/extract-ocr', file, { fournisseur });
          batchResults = [{ filename: file.name, fields: data.fields, installateur: data.installateur || 'DEFAULT', is_avoir: data.is_avoir }];
          renderResultsList('results-nouvelle', batchResults);
          updateStats('nouvelle', batchResults);
        } catch (err) {
          alert('Erreur: ' + err.message);
        } finally {
          hideLoading('loading-nouvelle', null);
        }
      });
    }

    // ZIP upload
    if (inputZip) {
      inputZip.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        showLoading('loading-nouvelle', null);
        try {
          const data = await uploadFile('/api/batch', file);
          batchResults = data.results;
          renderResultsList('results-nouvelle', batchResults);
          updateStats('nouvelle', batchResults);
        } catch (err) {
          alert('Erreur: ' + err.message);
        } finally {
          hideLoading('loading-nouvelle', null);
        }
      });
    }

    if (btnExport) {
      btnExport.addEventListener('click', () => {
        if (!batchResults.length) return;
        downloadExcel('/api/export-excel', batchResults, 'extraction_nouvelle.xlsx');
      });
    }
  }

  // ── PAGE: /batch ──
  if (path === '/batch') {
    const input = document.getElementById('upload-batch');
    const btnExport = document.getElementById('btn-export-batch');
    let batchResults = [];

    if (input) {
      input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        showLoading('loading-batch', null);
        try {
          const data = await uploadFile('/api/batch', file);
          batchResults = data.results;
          renderResultsList('results-batch', batchResults);
          updateBatchStats(batchResults);
          renderBatchTable('table-preview-batch', batchResults);
        } catch (err) {
          alert('Erreur: ' + err.message);
        } finally {
          hideLoading('loading-batch', null);
        }
      });
    }

    if (btnExport) {
      btnExport.addEventListener('click', () => {
        if (!batchResults.length) return;
        downloadExcel('/api/export-excel-multi', batchResults, 'extraction_multi.xlsx');
      });
    }
  }
});
```

- [ ] **Step 2: Add helper functions for batch rendering**

Append to `static/js/app.js`:

```javascript
// ── BATCH RENDERING HELPERS ──

function renderResultsList(containerId, results) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';

  for (const res of results) {
    const isError = res.installateur === 'ERREUR';
    const isAvoir = res.is_avoir;

    const div = document.createElement('div');
    div.className = isAvoir
      ? 'bg-tertiary-fixed/30 rounded-xl overflow-hidden border-l-4 border-tertiary mb-2'
      : isError
        ? 'bg-surface-container-lowest rounded-xl overflow-hidden border-l-4 border-error mb-2'
        : 'bg-surface-container-lowest rounded-xl overflow-hidden mb-2';

    const icon = isError ? 'error' : 'check_circle';
    const iconColor = isError ? 'text-error' : 'text-green-600';
    const typeLabel = isAvoir ? 'AVOIR' : 'FACTURE';
    const typeBg = isAvoir ? 'bg-tertiary-fixed text-on-tertiary-fixed-variant' : 'bg-blue-50 text-blue-700';

    div.innerHTML = `
      <div class="p-4 flex items-center justify-between hover:bg-surface-container-low cursor-pointer transition-colors">
        <div class="flex items-center gap-4">
          <span class="material-symbols-outlined ${iconColor}" style="font-variation-settings: 'FILL' 1;">${icon}</span>
          <div>
            <div class="font-bold text-sm">${res.filename}</div>
            <div class="text-xs text-on-surface-variant">Fournisseur: <span class="font-semibold">${(res.installateur || '?').toUpperCase()}</span></div>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <span class="text-[10px] px-2 py-0.5 rounded ${typeBg} font-bold">${typeLabel}</span>
          ${res.fields?.MONTANT_TTC ? `<span class="font-headline font-bold text-sm ${isAvoir ? 'text-error' : ''}">${res.fields.MONTANT_TTC} &euro;</span>` : ''}
        </div>
      </div>
    `;
    container.appendChild(div);
  }
}

function updateStats(prefix, results) {
  const ok = results.filter(r => r.installateur !== 'ERREUR').length;
  const errors = results.length - ok;
  const el1 = document.getElementById(`stat-extraites`);
  const el2 = document.getElementById(`stat-erreurs`);
  if (el1) el1.textContent = `${ok}/${results.length}`;
  if (el2) el2.textContent = errors;
}

function updateBatchStats(results) {
  const ok = results.filter(r => r.installateur !== 'ERREUR').length;
  const errors = results.length - ok;
  const installateurs = new Set(results.filter(r => r.installateur !== 'ERREUR').map(r => r.installateur)).size;
  const preCalc = results.filter(r => r.source === 'OCR pre-calcule').length;
  const live = results.filter(r => r.source === 'DocTR live').length;

  const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  setText('stat-traitees', `${ok} / ${results.length}`);
  setText('stat-ocr-precalc', preCalc);
  setText('stat-doctr-live', live);
  setText('stat-installateurs', installateurs);
  setText('stat-erreurs-batch', errors);
}

function renderBatchTable(containerId, results) {
  const container = document.getElementById(containerId);
  if (!container) return;

  let html = `<table class="w-full text-left border-collapse">
    <thead><tr class="bg-surface-container-low">
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Fichier</th>
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Date</th>
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Fournisseur</th>
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Type</th>
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">HT</th>
      <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">TTC</th>
    </tr></thead><tbody class="divide-y divide-outline-variant/10">`;

  for (const res of results) {
    const isAvoir = res.is_avoir;
    const typeBg = isAvoir ? 'bg-tertiary-fixed text-on-tertiary-fixed-variant' : 'bg-blue-50 text-blue-700';
    const amountClass = isAvoir ? 'text-error' : '';
    html += `<tr class="hover:bg-surface-container-low/30">
      <td class="px-6 py-4 font-mono text-xs">${res.filename}</td>
      <td class="px-6 py-4 text-xs">${res.fields?.DATE_FACTURE || '-'}</td>
      <td class="px-6 py-4 text-xs font-semibold">${(res.installateur || '?').toUpperCase()}</td>
      <td class="px-6 py-4"><span class="text-[10px] px-2 py-0.5 rounded ${typeBg} font-bold">${isAvoir ? 'AVOIR' : 'FACTURE'}</span></td>
      <td class="px-6 py-4 font-headline text-xs font-bold ${amountClass}">${res.fields?.MONTANT_HT || '-'}</td>
      <td class="px-6 py-4 font-headline text-xs font-bold ${amountClass}">${res.fields?.MONTANT_TTC || '-'}</td>
    </tr>`;
  }
  html += '</tbody></table>';
  container.innerHTML = html;
}
```

- [ ] **Step 3: Commit**

```bash
git add static/js/app.js
git commit -m "feat: add page-specific JS logic and batch rendering"
```

---

### Task 8: Wire main.py and final integration

**Files:**
- Modify: `main.py` (finalize)

- [ ] **Step 1: Update main.py with router import**

The `main.py` from Task 1 already has the router import. Verify the full file looks like:

```python
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pathlib import Path

from api.routes import router as api_router

app = FastAPI(title="Extraction de Factures BTP")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(api_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/texte")


@app.get("/texte")
async def page_texte(request: Request):
    return templates.TemplateResponse("texte.html", {"request": request, "active": "texte"})


@app.get("/smart")
async def page_smart(request: Request):
    return templates.TemplateResponse("smart.html", {"request": request, "active": "smart"})


@app.get("/nouvelle")
async def page_nouvelle(request: Request):
    return templates.TemplateResponse("nouvelle.html", {"request": request, "active": "nouvelle"})


@app.get("/batch")
async def page_batch(request: Request):
    return templates.TemplateResponse("batch.html", {"request": request, "active": "batch"})
```

- [ ] **Step 2: Test the full server starts**

Run: `cd C:/Users/melko/Developer/finetuned_model && python -c "from main import app; print('App loaded with', len(app.routes), 'routes')"`

Expected: Something like `App loaded with 12 routes`

- [ ] **Step 3: Start the server manually to verify pages render**

Run: `cd C:/Users/melko/Developer/finetuned_model && timeout 5 uvicorn main:app --port 8000 2>&1 | head -5`

Then open `http://localhost:8000/texte` in browser to verify the page renders with sidebar, header, and content.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: finalize FastAPI app with all routes"
```

---

### Task 9: Final verification and cleanup

**Files:**
- No new files

- [ ] **Step 1: Verify all imports resolve**

Run:
```bash
cd C:/Users/melko/Developer/finetuned_model && python -c "
from main import app
from api.routes import router
from core.extraction import (
    extract_from_precomputed_ocr, extract_smart,
    process_file_live, process_batch_zip,
    export_excel_batch, export_excel_multi_sheets,
    get_fournisseurs_list
)
print('All imports OK')
print('Fournisseurs:', get_fournisseurs_list()[:3])
"
```

Expected:
```
All imports OK
Fournisseurs: ['a2m', 'arcana', 'cailloce']
```

- [ ] **Step 2: Verify API endpoint responds**

Start server in background, then test:
```bash
cd C:/Users/melko/Developer/finetuned_model && uvicorn main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/fournisseurs | python -m json.tool
kill %1
```

Expected: JSON with list of fournisseurs

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete FastAPI migration — 4 pages + REST API"
```
