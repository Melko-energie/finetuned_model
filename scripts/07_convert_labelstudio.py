"""
Script 07 — Conversion annotations LabelStudio → format pipeline
Input  : data/annotations_labelstudio.json
Output : data/annotations_cleaned/

Format OCR DocTR réel :
{
  "filename": "...",
  "pages": [
    [  <- liste de tokens par page
      {"text": "...", "bbox": [x1, y1, x2, y2], "page": 0, "confidence": 0.99},
      ...
    ],
    [ ... ]  <- page 1
  ]
}
"""

import json
import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

# ── Chemins ────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
INPUT_JSON = BASE_DIR / "data" / "annotations_labelstudio.json"
OCR_DIR    = BASE_DIR / "data" / "ocr_texts"
OUTPUT_DIR = BASE_DIR / "data" / "annotations_cleaned"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Mapping noms LabelStudio → noms internes pipeline ─────────────
LABEL_MAP = {
    "Numéro de facture"         : "NUMERO_FACTURE",
    "Date de facture"           : "DATE_FACTURE",
    "Montant HT facture"        : "MONTANT_HT",
    "Taux de TVA facture"       : "TAUX_TVA",
    "Retenue de garantie"       : "RETENUE_GARANTIE",
    "Taux de retenue"           : "TAUX_RETENUE",
    "Code Postal"               : "CODE_POSTAL",
    "Commune"                   : "COMMUNE",
    "Adresse des travaux"       : "ADRESSE_TRAVAUX",
    "Installateur"              : "INSTALLATEUR",
    "Détail des travaux retenus": "DETAIL_TRAVAUX",
}

# ── Index OCR ─────────────────────────────────────────────────────
def build_ocr_index(ocr_dir: Path) -> dict:
    index = {}
    for json_file in ocr_dir.rglob("*.json"):
        index[json_file.name.lower()] = json_file
    logger.info(f"Index OCR : {len(index)} fichiers dans {ocr_dir}")
    return index


def find_ocr_file(image_name: str, ocr_index: dict):
    stem       = Path(image_name).stem
    stem_clean = re.sub(r'[_\s]page[_\s]?\d+$', '', stem, flags=re.IGNORECASE)
    ocr_name   = (stem_clean + ".json").lower()

    if ocr_name in ocr_index:
        return ocr_index[ocr_name]

    # Fallback recherche partielle
    for key, path in ocr_index.items():
        if stem_clean.lower() in key:
            return path

    return None


# ── Helpers ────────────────────────────────────────────────────────
def extract_image_name(file_upload: str) -> str:
    name  = Path(file_upload).name
    parts = name.split("-", 1)
    if len(parts) == 2 and len(parts[0]) == 8:
        return parts[1]
    return name


def extract_page_index(image_name: str) -> int:
    match = re.search(r'page[_\s]?(\d+)$', Path(image_name).stem, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        return max(0, num - 1) if num >= 1 else 0
    return 0


def bbox_ls_to_abs(x_pct, y_pct, w_pct, h_pct, img_w, img_h):
    x1 = (x_pct / 100) * img_w
    y1 = (y_pct / 100) * img_h
    x2 = x1 + (w_pct / 100) * img_w
    y2 = y1 + (h_pct / 100) * img_h
    return [int(x1), int(y1), int(x2), int(y2)]


def normalize_bbox(bbox, img_w, img_h):
    x1, y1, x2, y2 = bbox
    return [
        int(x1 / img_w * 1000),
        int(y1 / img_h * 1000),
        int(x2 / img_w * 1000),
        int(y2 / img_h * 1000),
    ]


def boxes_overlap(box_a, box_b, threshold=0.3):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return False
    inter  = (ix2 - ix1) * (iy2 - iy1)
    area_b = max((bx2 - bx1) * (by2 - by1), 1)
    return (inter / area_b) >= threshold


def assign_labels(ocr_tokens, annotations, img_w, img_h):
    anno_boxes = []
    for anno in annotations:
        val      = anno["value"]
        label_ls = val["rectanglelabels"][0]
        label    = LABEL_MAP.get(label_ls)
        if not label:
            logger.warning(f"Label inconnu : {label_ls}")
            continue
        anno_boxes.append({
            "label": label,
            "bbox" : bbox_ls_to_abs(val["x"], val["y"], val["width"], val["height"], img_w, img_h)
        })

    labeled = []
    prev    = None
    for token in ocr_tokens:
        tb    = token.get("bbox", [0, 0, 0, 0])
        label = "O"
        for ab in anno_boxes:
            if boxes_overlap(ab["bbox"], tb):
                entity = ab["label"]
                label  = f"I-{entity}" if prev == entity else f"B-{entity}"
                break
        prev = label.split("-")[-1] if label != "O" else None
        labeled.append({
            "text" : token.get("text", ""),
            "bbox" : normalize_bbox(tb, img_w, img_h),
            "label": label,
        })
    return labeled


def load_ocr_page(ocr_path: Path, page_index: int):
    """
    Charge les tokens d'une page depuis le JSON DocTR.
    Format : { "pages": [ [token, token, ...], [token, ...] ] }
    Chaque token : {"text": "...", "bbox": [x1,y1,x2,y2], "page": N}
    bbox est déjà en pixels absolus.
    """
    with open(ocr_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pages = data.get("pages", [])
    if not pages:
        return [], 1648, 2337

    # pages est une liste de listes de tokens
    idx        = min(page_index, len(pages) - 1)
    page_tokens = pages[idx]  # liste de tokens

    # Calcule les dimensions depuis les bbox
    img_w, img_h = 1648, 2337
    if page_tokens:
        max_x = max(t["bbox"][2] for t in page_tokens if "bbox" in t)
        max_y = max(t["bbox"][3] for t in page_tokens if "bbox" in t)
        img_w = max(max_x, 1)
        img_h = max(max_y, 1)

    tokens = []
    for t in page_tokens:
        tokens.append({
            "text": t.get("text", ""),
            "bbox": t.get("bbox", [0, 0, 0, 0]),
        })

    return tokens, img_w, img_h


# ── Main ───────────────────────────────────────────────────────────
def main():
    logger.info("=== Script 07 — Conversion LabelStudio → pipeline ===")

    if not INPUT_JSON.exists():
        logger.error(f"Fichier introuvable : {INPUT_JSON}")
        return

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    logger.info(f"Tâches chargées : {len(tasks)}")
    ocr_index = build_ocr_index(OCR_DIR)
    stats     = {"total": len(tasks), "converted": 0, "skipped": 0, "no_ocr": 0}

    for task in tasks:
        annotations = task.get("annotations", [])
        if not annotations or annotations[0].get("was_cancelled"):
            stats["skipped"] += 1
            continue

        result = annotations[0].get("result", [])
        if not result:
            stats["skipped"] += 1
            continue

        file_upload = task.get("file_upload", "")
        image_name  = extract_image_name(file_upload)
        page_index  = extract_page_index(image_name)

        ocr_path = find_ocr_file(image_name, ocr_index)
        if ocr_path is None:
            logger.warning(f"OCR introuvable : {image_name}")
            stats["no_ocr"] += 1
            continue

        img_w = result[0].get("original_width",  1648)
        img_h = result[0].get("original_height", 2337)

        try:
            ocr_tokens, _, _ = load_ocr_page(ocr_path, page_index)
        except Exception as e:
            logger.error(f"Erreur OCR {ocr_path.name} : {e}")
            stats["skipped"] += 1
            continue

        labeled = assign_labels(ocr_tokens, result, img_w, img_h)

        output_path = OUTPUT_DIR / (Path(image_name).stem + ".json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "image_name"  : image_name,
                "image_width" : img_w,
                "image_height": img_h,
                "page_index"  : page_index,
                "ocr_source"  : str(ocr_path),
                "tokens"      : labeled,
                "source"      : "labelstudio_manual",
            }, f, ensure_ascii=False, indent=2)

        nb_entities = sum(1 for t in labeled if t["label"] != "O")
        stats["converted"] += 1
        logger.info(f"✓ {image_name} | p{page_index} | {len(labeled)} tokens | {nb_entities} entités")

    logger.info("=" * 55)
    logger.info(f"Total      : {stats['total']}")
    logger.info(f"Converties : {stats['converted']}")
    logger.info(f"Sans OCR   : {stats['no_ocr']}")
    logger.info(f"Ignorées   : {stats['skipped']}")
    logger.info(f"Output     : {OUTPUT_DIR}")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()