import os
import json
import tempfile
import importlib.util
from pathlib import Path
import streamlit as st
from PIL import Image
import fitz
import ollama

PROJECT_ROOT = Path(__file__).resolve().parent
LOGO_PATH = PROJECT_ROOT / "assets" / "logo.png"

# Import pipeline from scripts/12_gemma2_smart.py
_spec_smart = importlib.util.spec_from_file_location(
    "gemma2_smart", str(PROJECT_ROOT / "scripts" / "12_gemma2_smart.py")
)
_mod_smart = importlib.util.module_from_spec(_spec_smart)
_spec_smart.loader.exec_module(_mod_smart)
smart_get_ocr_text = _mod_smart.get_ocr_text
smart_detect_installateur = _mod_smart.detect_installateur
smart_extraire_champs = _mod_smart.extraire_champs
SMART_INSTALLATEURS = _mod_smart.PROMPTS_INSTALLATEURS

FIELDS_LEFT = [
    ("NUMERO_FACTURE",  "Numéro de facture"),
    ("DATE_FACTURE",    "Date de facture"),
    ("MONTANT_HT",      "Montant HT"),
    ("TAUX_TVA",        "Taux de TVA"),
    ("MONTANT_TTC",     "Montant TTC"),
]
FIELDS_RIGHT = [
    ("NOM_INSTALLATEUR", "Installateur"),
    ("COMMUNE_TRAVAUX",  "Commune"),
    ("CODE_POSTAL",      "Code Postal"),
    ("ADRESSE_TRAVAUX",  "Adresse des travaux"),
]

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG & CSS
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Extraction Factures BTP",
    page_icon="🏗️",
    layout="wide",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@700;800&display=swap');

  :root {
    --btp-blue:       #1E3A5F;
    --btp-blue-light: #2C5282;
    --bg-light:       #F7F8FA;
    --border:         #D1D5DB;
    --green-bg:       #E6F4EA;
    --green-border:   #34A853;
    --red-bg:         #FDE8E8;
    --red-border:     #C53030;
  }

  /* ── header ── */
  .main-header {
    background: linear-gradient(135deg, var(--btp-blue) 0%, var(--btp-blue-light) 100%);
    padding: 1.2rem 2rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    color: white;
  }
  .main-header h1 { margin:0; font-size:1.8rem; font-weight:700; color:white; font-family:'Syne',sans-serif; }
  .main-header p  { margin:.25rem 0 0; font-size:.95rem; opacity:.85; color:#CBD5E0; }

  /* ── tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 2px solid var(--border);
    margin-bottom: 1.5rem;
  }
  .stTabs [data-baseweb="tab"] {
    background: var(--bg-light);
    border-radius: 8px 8px 0 0;
    padding: 8px 20px;
    font-weight: 600;
    font-size: .9rem;
    border: 1px solid var(--border);
    border-bottom: none;
    color: #6B7280;
  }
  .stTabs [aria-selected="true"] {
    background: white !important;
    color: var(--btp-blue) !important;
    border-color: var(--btp-blue) !important;
  }

  /* ── upload zone ── */
  .upload-zone {
    border: 2px dashed var(--border);
    border-radius: 10px;
    padding: 1.5rem;
    text-align: center;
    background: var(--bg-light);
    margin-bottom: 1.5rem;
  }
  .upload-zone p { color:#6B7280; margin:.5rem 0 0; font-size:.9rem; }

  /* ── field cards ── */
  .field-card {
    border-radius: 8px;
    padding: .85rem 1rem;
    margin-bottom: .6rem;
    border-left: 4px solid;
  }
  .field-card.detected { background:var(--green-bg); border-left-color:var(--green-border); }
  .field-card.missing  { background:var(--red-bg);   border-left-color:var(--red-border);   }
  .field-label {
    font-size:.78rem; text-transform:uppercase;
    letter-spacing:.04em; color:#6B7280; margin-bottom:.15rem;
  }
  .field-value         { font-size:1rem; font-weight:600; color:#111827; word-break:break-word; }
  .field-value.missing { color:var(--red-border); font-weight:500; }

  /* ── section title ── */
  .section-title {
    font-size:1.05rem; font-weight:600; color:var(--btp-blue);
    margin-bottom:.75rem; padding-bottom:.4rem;
    border-bottom:2px solid var(--btp-blue); display:inline-block;
  }

  /* ── model badge ── */
  .model-badge {
    display:inline-flex; align-items:center; gap:6px;
    padding:4px 12px; border-radius:20px;
    font-size:.8rem; font-weight:600;
    margin-bottom:1rem;
  }
  .badge-gemma2   { background:rgba(124,58,237,.1);color:#7c3aed;           border:1px solid #7c3aed;           }
  .badge-smart    { background:rgba(234,88,12,.1); color:#ea580c;           border:1px solid #ea580c;           }

  /* ── stats row ── */
  .stats-row { display:flex; gap:1rem; margin-top:1rem; }
  .stat-box  {
    flex:1; background:var(--bg-light); border:1px solid var(--border);
    border-radius:8px; padding:.75rem 1rem; text-align:center;
  }
  .stat-box .num { font-size:1.4rem; font-weight:700; color:var(--btp-blue); }
  .stat-box .lbl { font-size:.78rem; color:#6B7280; }

  /* ── info box ── */
  .info-box {
    background: #EFF6FF; border:1px solid #BFDBFE;
    border-left:4px solid #3B82F6;
    border-radius:8px; padding:.85rem 1rem; margin-bottom:1rem;
    font-size:.88rem; color:#1E40AF; line-height:1.6;
  }
  .warn-box {
    background:#FFFBEB; border:1px solid #FDE68A;
    border-left:4px solid #F59E0B;
    border-radius:8px; padding:.85rem 1rem; margin-bottom:1rem;
    font-size:.88rem; color:#92400E; line-height:1.6;
  }

  /* ── footer ── */
  .app-footer {
    text-align:center; padding:1.5rem 0 .5rem;
    color:#9CA3AF; font-size:.82rem;
    border-top:1px solid var(--border); margin-top:2rem;
  }

  /* ── sidebar ── */
  section[data-testid="stSidebar"] { background:var(--bg-light); }
  .sidebar-section {
    background:white; border:1px solid var(--border);
    border-radius:8px; padding:.85rem 1rem; margin-bottom:.75rem;
  }
  .sidebar-section h4 { margin:0 0 .5rem; font-size:.9rem; color:var(--btp-blue); }
  .sidebar-row {
    display:flex; justify-content:space-between;
    font-size:.82rem; padding:.2rem 0; color:#374151;
  }
  .sidebar-row span:last-child { font-weight:600; }

  #MainMenu, footer, header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HELPERS COMMUNS
# ─────────────────────────────────────────────────────────────
def render_field_card(label: str, value):
    if value is None or value == "null":
        return (
            '<div class="field-card missing">'
            f'<div class="field-label">{label}</div>'
            '<div class="field-value missing">Non détecté</div>'
            '</div>'
        )
    if isinstance(value, list):
        value = " | ".join(str(v) for v in value)
    return (
        '<div class="field-card detected">'
        f'<div class="field-label">{label}</div>'
        f'<div class="field-value">{value}</div>'
        '</div>'
    )


def show_stats(fields, extra_stats=None):
    detected = sum(1 for k, _ in FIELDS_LEFT + FIELDS_RIGHT
                   if fields.get(k) and fields.get(k) != "null")
    total = len(FIELDS_LEFT) + len(FIELDS_RIGHT)
    html = (
        '<div class="stats-row">'
        f'<div class="stat-box"><div class="num">{detected}/{total}</div>'
        '<div class="lbl">Champs détectés</div></div>'
    )
    if extra_stats:
        for val, lbl in extra_stats:
            html += (
                f'<div class="stat-box"><div class="num">{val}</div>'
                f'<div class="lbl">{lbl}</div></div>'
            )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def show_results(fields):
    c_left, c_right = st.columns(2)
    with c_left:
        for key, label in FIELDS_LEFT:
            st.markdown(render_field_card(label, fields.get(key)), unsafe_allow_html=True)
    with c_right:
        for key, label in FIELDS_RIGHT:
            st.markdown(render_field_card(label, fields.get(key)), unsafe_allow_html=True)


def show_preview(uploaded):
    suffix = os.path.splitext(uploaded.name)[1].lower()
    st.markdown('<div class="section-title">Aperçu du document</div>', unsafe_allow_html=True)
    if suffix == ".pdf":
        pdf_bytes = uploaded.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        preview = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        st.image(preview, use_container_width=True)
        doc.close()
        uploaded.seek(0)
    else:
        st.image(uploaded, use_container_width=True)
        uploaded.seek(0)


def clean_json(raw):
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return raw


# ─────────────────────────────────────────────────────────────
# HELPERS GEMMA2 TEXTE
# ─────────────────────────────────────────────────────────────
PROMPT_TEXTE = """Tu es un expert comptable spécialisé dans les factures BTP françaises.

RÈGLES :
- NUMERO_FACTURE : numéro COMPLET après "N°", "Facture N°", "Réf". Garde tous les caractères.
- DATE_FACTURE : format JJ/MM/AAAA.
- MONTANT_HT : montant AVANT TVA. Format "358.83". Cherche "Total HT", "Net HT".
- TAUX_TVA : uniquement le pourcentage. Exemple "20%".
- MONTANT_TTC : montant FINAL avec TVA. Cherche "Total TTC", "Net à payer".
- NOM_INSTALLATEUR : nom COMPLET de l'entreprise émettrice (pas le client).
- COMMUNE_TRAVAUX : ville du chantier.
- CODE_POSTAL : code postal à 5 chiffres.
- ADRESSE_TRAVAUX : adresse complète du chantier.

TEXTE DE LA FACTURE :
{texte}

Réponds UNIQUEMENT en JSON valide. Aucun texte avant ou après.
{{"NUMERO_FACTURE":null,"DATE_FACTURE":null,"MONTANT_HT":null,"TAUX_TVA":null,"MONTANT_TTC":null,"NOM_INSTALLATEUR":null,"COMMUNE_TRAVAUX":null,"CODE_POSTAL":null,"ADRESSE_TRAVAUX":null}}"""


def extract_gemma2(original_filename):
    """Extraction texte avec gemma2:9b — utilise l'OCR DocTR existant"""
    ocr_dir = PROJECT_ROOT / "data" / "ocr_texts"
    base_name = os.path.splitext(original_filename)[0]
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
                                        bbox = token.get("bbox", [0,0,0,0])
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
        return None, "OCR introuvable pour cette facture"

    prompt = PROMPT_TEXTE.format(texte=texte[:3000])
    response = ollama.chat(
        model="gemma2:9b",
        options={"temperature": 0, "seed": 42},
        messages=[{"role":"user","content":prompt}]
    )

    try:
        result = json.loads(clean_json(response["message"]["content"]))
        return result, None
    except json.JSONDecodeError:
        return None, "Réponse JSON invalide"


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=150)
    st.markdown("")

    st.markdown(
        '<div class="sidebar-section">'
        "<h4>📋 Projet</h4>"
        '<div class="sidebar-row"><span>OCR</span><span>DocTR</span></div>'
        '<div class="sidebar-row"><span>Modèle</span><span>Gemma2:9b</span></div>'
        '<div class="sidebar-row"><span>Version</span><span>3.0.0</span></div>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-section">'
        "<h4>🤖 Modèles disponibles</h4>"
        '<div class="sidebar-row"><span>Gemma2:9b</span><span style="color:#7c3aed">Texte</span></div>'
        '<div class="sidebar-row"><span>Gemma2 Smart</span><span style="color:#ea580c">Par fournisseur</span></div>'
        "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
if LOGO_PATH.exists():
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image(str(LOGO_PATH), width=120)
    with col_title:
        st.markdown(
            '<div class="main-header">'
            '<h1>🏗️ Extraction de Factures BTP</h1>'
            '<p>Gemma2:9b Texte · Gemma2 Smart par fournisseur</p>'
            '</div>',
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        '<div class="main-header">'
        '<h1>🏗️ Extraction de Factures BTP</h1>'
        '<p>Gemma2:9b Texte · Gemma2 Smart par fournisseur</p>'
        '</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# ONGLETS
# ─────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs([
    "📝 Gemma2:9b — Texte",
    "🎯 Gemma2 Smart — Par fournisseur",
])


# ═══════════════════════════════════════════════════
# ONGLET 1 — GEMMA2:9b TEXTE
# ═══════════════════════════════════════════════════
with tab1:
    st.markdown(
        '<span class="model-badge badge-gemma2">📝 Gemma2:9b — Extraction textuelle</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="warn-box"><strong>Gemma2:9b</strong> utilise le texte OCR extrait par DocTR '
        '(script 01). Il ne voit pas l\'image directement. Reconstruction des lignes par '
        'position Y pour préserver la structure des tableaux. '
        '<strong>Attention</strong> : nécessite que l\'OCR ait déjà été extrait via script 01.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="upload-zone">'
        '<p><strong>Déposez votre facture ici</strong></p>'
        '<p>Formats acceptés : PNG, JPG, PDF — OCR DocTR requis</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    uploaded1 = st.file_uploader(
        "Importer (Gemma2)",
        type=["png","jpg","jpeg","pdf"],
        label_visibility="collapsed",
        key="upload_gemma2",
    )

    if uploaded1:
        col_prev1, col_res1 = st.columns([1,1], gap="large")

        with col_prev1:
            show_preview(uploaded1)

        with st.spinner("Gemma2:9b analyse le texte OCR..."):
            fields1, error1 = extract_gemma2(original_filename=uploaded1.name)

        with col_res1:
            st.markdown('<div class="section-title">Champs extraits</div>', unsafe_allow_html=True)

            if error1:
                st.error(f"  {error1}")
                st.info(
                    "Vérifiez que l'OCR a bien été extrait via `python scripts/01_ocr_extraction.py` "
                    "et que le PDF source est dans `data/raw_pdfs/`"
                )
            elif fields1:
                show_results(fields1)
                show_stats(fields1)

        if fields1 and not error1:
            with st.expander("JSON brut"):
                st.json(fields1)


# ═══════════════════════════════════════════════════
# ONGLET 2 — GEMMA2 SMART (prompts par fournisseur)
# ═══════════════════════════════════════════════════
with tab2:
    st.markdown(
        '<span class="model-badge badge-smart">🎯 Gemma2:9b — Prompts spécialisés par fournisseur</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="info-box"><strong>Gemma2 Smart</strong> détecte automatiquement le fournisseur '
        'à partir du texte OCR et utilise un <strong>prompt spécialisé</strong> adapté à ses factures '
        '(format n° facture, taux TVA habituel, emplacement des montants). '
        '17 fournisseurs connus + prompt générique pour les inconnus. '
        '<strong>Nécessite</strong> que l\'OCR ait été extrait via script 01.</div>',
        unsafe_allow_html=True,
    )

    # Liste déroulante des fournisseurs
    noms_installateurs = [k for k in SMART_INSTALLATEURS.keys() if k != "DEFAULT"]
    noms_installateurs.sort()
    options_dropdown = ["Auto-detect"] + [n.upper() for n in noms_installateurs] + ["DEFAULT (generique)"]

    choix_installateur = st.selectbox(
        "Choisir le fournisseur",
        options_dropdown,
        index=0,
        help="Selectionnez le fournisseur manuellement si la facture contient plusieurs noms d'installateurs",
        key="select_installateur_smart",
    )

    st.markdown(
        '<div class="upload-zone">'
        '<p><strong>Deposez votre facture ici</strong></p>'
        '<p>Formats acceptes : PNG, JPG, PDF — OCR DocTR requis</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    uploaded2 = st.file_uploader(
        "Importer (Gemma2 Smart)",
        type=["png","jpg","jpeg","pdf"],
        label_visibility="collapsed",
        key="upload_gemma2_smart",
    )

    if uploaded2:
        col_prev2, col_res2 = st.columns([1,1], gap="large")

        with col_prev2:
            show_preview(uploaded2)

        with st.spinner("Gemma2 Smart — detection fournisseur et extraction..."):
            texte_ocr = smart_get_ocr_text(uploaded2.name)

            if texte_ocr is None:
                installateur_detecte = None
                fields2 = None
                error2 = "OCR introuvable pour cette facture"
            else:
                # Choix manuel ou auto-detect
                if choix_installateur == "Auto-detect":
                    installateur_detecte = smart_detect_installateur(texte_ocr)
                    mode_detection = "auto"
                elif choix_installateur == "DEFAULT (generique)":
                    installateur_detecte = "DEFAULT"
                    mode_detection = "manuel"
                else:
                    installateur_detecte = choix_installateur.lower()
                    mode_detection = "manuel"

                fields2 = smart_extraire_champs(texte_ocr, installateur_detecte)
                error2 = None

        with col_res2:
            st.markdown('<div class="section-title">Champs extraits</div>', unsafe_allow_html=True)

            if error2:
                st.error(f"  {error2}")
                st.info(
                    "Verifiez que l'OCR a bien ete extrait via `python scripts/01_ocr_extraction.py` "
                    "et que le PDF source est dans `data/raw_pdfs/`"
                )
            elif fields2:
                # Afficher le fournisseur detecte/choisi
                if installateur_detecte and installateur_detecte != "DEFAULT":
                    label_mode = "detecte automatiquement" if mode_detection == "auto" else "choisi manuellement"
                    st.markdown(
                        f'<div style="background:#FFF7ED;border:1px solid #FDBA74;border-left:4px solid #ea580c;'
                        f'border-radius:8px;padding:.75rem 1rem;margin-bottom:1rem;font-size:.88rem;color:#9A3412;">'
                        f'🎯 Fournisseur {label_mode} : <strong>{installateur_detecte.upper()}</strong> '
                        f'— prompt specialise utilise</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div style="background:#F3F4F6;border:1px solid #D1D5DB;border-left:4px solid #6B7280;'
                        'border-radius:8px;padding:.75rem 1rem;margin-bottom:1rem;font-size:.88rem;color:#374151;">'
                        'Fournisseur non reconnu — prompt generique utilise</div>',
                        unsafe_allow_html=True,
                    )

                show_results(fields2)
                show_stats(fields2, [
                    (installateur_detecte.upper() if installateur_detecte else "?", "Fournisseur"),
                ])

        if fields2 and not error2:
            with st.expander("JSON brut"):
                st.json(fields2)


# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-footer">Stage 2026 — MADANI Yassine · Gemma2:9b</div>',
    unsafe_allow_html=True,
)
