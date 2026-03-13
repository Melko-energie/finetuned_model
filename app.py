import os
import sys
import json
import tempfile
import importlib.util
from pathlib import Path
import streamlit as st
from PIL import Image
import fitz

PROJECT_ROOT = Path(__file__).resolve().parent
LOGO_PATH = PROJECT_ROOT / "assets" / "logo.png"

# Import PDFExtractor from scripts/06_inference.py (name starts with digit)
_spec = importlib.util.spec_from_file_location(
    "inference", str(PROJECT_ROOT / "scripts" / "06_inference.py")
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
PDFExtractor = _mod.PDFExtractor

MODEL_PATH = str(PROJECT_ROOT / "models" / "finetuned_lora")
SCHEMA_PATH = PROJECT_ROOT / "data" / "label_schema.json"

# Two-column layout: left = financial, right = location/identity
FIELDS_LEFT = [
    ("NUMERO_FACTURE", "Numero de facture"),
    ("DATE_FACTURE", "Date de facture"),
    ("MONTANT_HT", "Montant HT"),
    ("TAUX_TVA", "Taux de TVA"),
]
FIELDS_RIGHT = [
    ("INSTALLATEUR", "Installateur"),
    ("COMMUNE", "Commune"),
    ("CODE_POSTAL", "Code Postal"),
    ("ADRESSE_TRAVAUX", "Adresse des travaux"),
]

# ---------------------------------------------------------------------------
# Page config & global CSS
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Extraction de Factures BTP",
    page_icon="\U0001F3D7\uFE0F",
    layout="wide",
)

st.markdown("""
<style>
    /* ---------- palette ---------- */
    :root {
        --btp-blue: #1E3A5F;
        --btp-blue-light: #2C5282;
        --bg-light: #F7F8FA;
        --border: #D1D5DB;
        --green-bg: #E6F4EA;
        --green-border: #34A853;
        --red-bg: #FDE8E8;
        --red-border: #C53030;
    }

    /* ---------- header ---------- */
    .main-header {
        background: linear-gradient(135deg, var(--btp-blue) 0%, var(--btp-blue-light) 100%);
        padding: 1.2rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        color: white;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }
    .main-header .header-logo img {
        max-height: 70px;
        border-radius: 6px;
    }
    .main-header .header-text h1 {
        margin: 0; font-size: 1.8rem; font-weight: 700; color: white;
    }
    .main-header .header-text p {
        margin: .25rem 0 0; font-size: .95rem; opacity: .85; color: #CBD5E0;
    }

    /* ---------- upload zone ---------- */
    .upload-zone {
        border: 2px dashed var(--border);
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background: var(--bg-light);
        margin-bottom: 1.5rem;
    }
    .upload-zone p {
        color: #6B7280; margin: .5rem 0 0; font-size: .9rem;
    }

    /* ---------- field cards ---------- */
    .field-card {
        border-radius: 8px;
        padding: .85rem 1rem;
        margin-bottom: .6rem;
        border-left: 4px solid;
    }
    .field-card.detected {
        background: var(--green-bg);
        border-left-color: var(--green-border);
    }
    .field-card.missing {
        background: var(--red-bg);
        border-left-color: var(--red-border);
    }
    .field-label {
        font-size: .78rem;
        text-transform: uppercase;
        letter-spacing: .04em;
        color: #6B7280;
        margin-bottom: .15rem;
    }
    .field-value {
        font-size: 1rem;
        font-weight: 600;
        color: #111827;
        word-break: break-word;
    }
    .field-value.missing {
        color: var(--red-border);
        font-weight: 500;
    }

    /* ---------- section title ---------- */
    .section-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: var(--btp-blue);
        margin-bottom: .75rem;
        padding-bottom: .4rem;
        border-bottom: 2px solid var(--btp-blue);
        display: inline-block;
    }

    /* ---------- stats row ---------- */
    .stats-row {
        display: flex; gap: 1rem; margin-top: 1rem;
    }
    .stat-box {
        flex: 1;
        background: var(--bg-light);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: .75rem 1rem;
        text-align: center;
    }
    .stat-box .num {
        font-size: 1.4rem; font-weight: 700; color: var(--btp-blue);
    }
    .stat-box .lbl {
        font-size: .78rem; color: #6B7280;
    }

    /* ---------- footer ---------- */
    .app-footer {
        text-align: center;
        padding: 1.5rem 0 .5rem;
        color: #9CA3AF;
        font-size: .82rem;
        border-top: 1px solid var(--border);
        margin-top: 2rem;
    }

    /* ---------- sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: var(--bg-light);
    }
    .sidebar-section {
        background: white;
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: .85rem 1rem;
        margin-bottom: .75rem;
    }
    .sidebar-section h4 {
        margin: 0 0 .5rem; font-size: .9rem; color: var(--btp-blue);
    }
    .sidebar-row {
        display: flex; justify-content: space-between;
        font-size: .82rem; padding: .2rem 0; color: #374151;
    }
    .sidebar-row span:last-child { font-weight: 600; }

    /* hide default streamlit branding */
    #MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def render_field_card(label: str, value):
    """Render a single field card (detected or missing)."""
    if value is None:
        return (
            '<div class="field-card missing">'
            f'  <div class="field-label">{label}</div>'
            '  <div class="field-value missing">Non detecte</div>'
            '</div>'
        )
    if isinstance(value, list):
        value = " | ".join(str(v) for v in value)
    return (
        '<div class="field-card detected">'
        f'  <div class="field-label">{label}</div>'
        f'  <div class="field-value">{value}</div>'
        '</div>'
    )


@st.cache_resource
def load_extractor():
    return PDFExtractor(MODEL_PATH)


def count_labels():
    """Read label schema to get label count for sidebar."""
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        return len(schema.get("labels", []))
    except Exception:
        return "?"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=150)
    st.markdown("")  # spacer

    st.markdown(
        '<div class="sidebar-section">'
        "<h4>\U0001F4CB Projet</h4>"
        '<div class="sidebar-row"><span>Modele</span><span>LayoutLMv3 + LoRA</span></div>'
        '<div class="sidebar-row"><span>OCR</span><span>DocTR</span></div>'
        f'<div class="sidebar-row"><span>Labels</span><span>{count_labels()}</span></div>'
        '<div class="sidebar-row"><span>Version</span><span>1.0.0</span></div>'
        "</div>",
        unsafe_allow_html=True,
    )

    # Model status — show loaded only after first extraction triggers caching
    model_loaded = "load_extractor" in st.session_state.get("_cache_resource", {}) \
        if hasattr(st.session_state, "get") else False
    # Simpler heuristic: check if we already ran an extraction this session
    if "results" in st.session_state:
        status_html = (
            '<div class="sidebar-section">'
            "<h4>\U0001F7E2 Statut du modele</h4>"
            '<div style="color:#34A853;font-weight:600;font-size:.9rem;">Charge</div>'
            "</div>"
        )
    else:
        status_html = (
            '<div class="sidebar-section">'
            "<h4>\u26AA Statut du modele</h4>"
            '<div style="color:#6B7280;font-size:.9rem;">Non charge — uploadez un document</div>'
            "</div>"
        )
    st.markdown(status_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
if LOGO_PATH.exists():
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image(str(LOGO_PATH), width=120)
    with col_title:
        st.markdown(
            '<div class="main-header">'
            '<div class="header-text">'
            "<h1>\U0001F3D7\uFE0F Extraction de Factures BTP</h1>"
            "<p>Powered by LayoutLMv3 + LoRA</p>"
            "</div></div>",
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        '<div class="main-header">'
        '<div class="header-text">'
        "<h1>\U0001F3D7\uFE0F Extraction de Factures BTP</h1>"
        "<p>Powered by LayoutLMv3 + LoRA</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Upload zone
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="upload-zone">'
    "<p><strong>Deposez votre facture ici</strong></p>"
    "<p>Formats acceptes : PNG, JPG, PDF</p>"
    "</div>",
    unsafe_allow_html=True,
)

uploaded = st.file_uploader(
    "Importer un document",
    type=["png", "jpg", "jpeg", "pdf"],
    label_visibility="collapsed",
)

# ---------------------------------------------------------------------------
# Main content (after upload)
# ---------------------------------------------------------------------------
if uploaded is not None:
    suffix = os.path.splitext(uploaded.name)[1]
    col_preview, col_results = st.columns([1, 1], gap="large")

    # -- Preview --
    with col_preview:
        st.markdown('<div class="section-title">Apercu du document</div>', unsafe_allow_html=True)
        if suffix.lower() == ".pdf":
            pdf_bytes = uploaded.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            preview = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            st.image(preview, use_container_width=True)
            doc.close()
            uploaded.seek(0)
        else:
            st.image(uploaded, use_container_width=True)

    # -- Inference --
    with st.spinner("Analyse en cours..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name
        try:
            extractor = load_extractor()
            results = extractor.extract(tmp_path)
        finally:
            os.unlink(tmp_path)

    st.session_state["results"] = results
    fields = results.get("extracted_fields", {})

    # -- Results --
    with col_results:
        st.markdown('<div class="section-title">Champs extraits</div>', unsafe_allow_html=True)

        c_left, c_right = st.columns(2)

        with c_left:
            for key, label in FIELDS_LEFT:
                st.markdown(render_field_card(label, fields.get(key)), unsafe_allow_html=True)

        with c_right:
            for key, label in FIELDS_RIGHT:
                st.markdown(render_field_card(label, fields.get(key)), unsafe_allow_html=True)

        # Stats
        total_pred = results.get("total_predictions", 0)
        total_pages = results.get("total_pages", 0)
        detected = sum(1 for k, _ in FIELDS_LEFT + FIELDS_RIGHT if fields.get(k) is not None)
        total_fields = len(FIELDS_LEFT) + len(FIELDS_RIGHT)

        st.markdown(
            '<div class="stats-row">'
            f'<div class="stat-box"><div class="num">{detected}/{total_fields}</div>'
            '<div class="lbl">Champs detectes</div></div>'
            f'<div class="stat-box"><div class="num">{total_pred}</div>'
            '<div class="lbl">Predictions</div></div>'
            f'<div class="stat-box"><div class="num">{total_pages}</div>'
            '<div class="lbl">Pages</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )

    # -- Raw JSON --
    with st.expander("JSON brut"):
        st.json(results)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="app-footer">Stage 2026 — MADANI Yassine</div>',
    unsafe_allow_html=True,
)
