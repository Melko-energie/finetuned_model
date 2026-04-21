"""OCR access: DocTR model singleton, pre-computed JSON loader, and live
DocTR pipeline (PDF/image bytes -> reconstructed text)."""

import io
import os
import glob
import json

import numpy as np
from PIL import Image
import fitz

from core.config import OCR_DIR

_MONTANT_KEYWORDS = ["ht", "tva", "ttc", "total", "net", "payer", "montant"]

_ocr_model = None


def get_ocr_model():
    """Return a singleton DocTR predictor (lazy import — DocTR pulls torch)."""
    global _ocr_model
    if _ocr_model is None:
        from doctr.models import ocr_predictor
        _ocr_model = ocr_predictor(
            det_arch="db_resnet50", reco_arch="crnn_vgg16_bn", pretrained=True
        )
    return _ocr_model


def _prefuse_numeric_neighbors(tokens):
    """Fuse adjacent numeric tokens (Δy<3, Δx<12) before line grouping.

    Motivation: OCR may split "1 856.00" into "1" and "856.00" sitting on
    nearly-identical Y. Without pre-fusion, the "1" token gets attached to a
    paragraph above and the amount line is split.
    """
    tokens = sorted(tokens, key=lambda t: (t["page"], t["y"], t["x"]))
    used = [False] * len(tokens)
    out = []
    for i, t in enumerate(tokens):
        if used[i]:
            continue
        cur = dict(t)
        used[i] = True
        j = i + 1
        while j < len(tokens):
            if used[j]:
                j += 1
                continue
            u = tokens[j]
            if u["page"] != cur["page"]:
                break
            if u["y"] - cur["y"] > 10:
                break
            dy = abs(u["y"] - cur["y"])
            dx = u["x"] - cur["x2"]
            prev_ends_digit = cur["text"] and cur["text"][-1].isdigit()
            cur_starts_num = u["text"] and (u["text"][0].isdigit() or u["text"][0] in ",.")
            if prev_ends_digit and cur_starts_num and dy < 3 and -2 < dx < 12:
                cur["text"] = cur["text"] + u["text"]
                cur["x2"] = u["x2"]
                cur["y"] = max(cur["y"], u["y"])
                used[j] = True
            j += 1
        out.append(cur)
    return out


def _group_tokens_to_text(all_tokens) -> str:
    """Group spatially-close tokens into lines, fuse intra-line numeric
    neighbors, return a multi-line string."""
    all_tokens = _prefuse_numeric_neighbors(all_tokens)
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
            if not token["text"]:
                continue
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
    return "\n".join(lines)


def get_ocr_text(pdf_path: str):
    """Locate the pre-computed DocTR JSON for a PDF and rebuild its text.

    Looks under data/ocr_texts/<supplier>/ for a JSON whose base name matches
    `pdf_path` (case-insensitive substring). Returns None if not found.
    Selects page 0 plus, for multi-page docs, the page with the most
    montant-related keywords.
    """
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    ocr_dir_str = str(OCR_DIR)

    json_path = None
    if os.path.isdir(ocr_dir_str):
        for supplier_dir in os.listdir(ocr_dir_str):
            supplier_path = os.path.join(ocr_dir_str, supplier_dir)
            if not os.path.isdir(supplier_path):
                continue
            for f in os.listdir(supplier_path):
                if f.endswith(".json"):
                    f_base = os.path.splitext(f)[0]
                    if pdf_name.upper() in f_base.upper() or f_base.upper() in pdf_name.upper():
                        json_path = os.path.join(supplier_path, f)
                        break
                if json_path:
                    break
            if json_path:
                break

    if not json_path:
        pattern = os.path.join(ocr_dir_str, "**", f"*{pdf_name}*")
        json_matches = [m for m in glob.glob(pattern, recursive=True) if m.endswith(".json")]
        if json_matches:
            json_path = json_matches[0]

    if not json_path:
        return None

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pages = data["pages"]
    nb = len(pages)

    if nb == 1:
        pages_to_read = [(0, pages[0])]
    else:
        best_page = nb - 1
        best_score = 0
        for pi in range(1, nb):
            words = [t.get("text", "").lower() for t in pages[pi]]
            score = sum(1 for w in words for kw in _MONTANT_KEYWORDS if kw in w)
            if score > best_score or (score == best_score and pi > best_page):
                best_score = score
                best_page = pi
        pages_to_read = [(0, pages[0])] if best_page == 0 else [(0, pages[0]), (best_page, pages[best_page])]

    all_tokens = []
    for page_idx, page_tokens in pages_to_read:
        for token in page_tokens:
            bbox = token.get("bbox", [0, 0, 0, 0])
            all_tokens.append({
                "text": token["text"],
                "y": bbox[1],
                "x": bbox[0],
                "x2": bbox[2],
                "page": page_idx,
            })

    return _group_tokens_to_text(all_tokens)


def run_doctr_ocr(file_bytes: bytes, suffix: str) -> str:
    """Live OCR pipeline: PDF/image bytes -> reconstructed text via DocTR.

    Selects page 0 plus the page with the most montant-related keywords
    (same heuristic as get_ocr_text). Returns "" if no text was extracted.
    """
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
    model = get_ocr_model()
    np_images = [np.array(img) for img in pil_images]
    result_ocr = model(np_images)

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
            score = sum(1 for w in words for kw in _MONTANT_KEYWORDS if kw in w)
            if score > best_score or (score == best_score and pi > best_page):
                best_score = score
                best_page = pi
        pages_indices = [0] if best_page == 0 else [0, best_page]

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
                        "text": word.value,
                        "y": y0 * h,
                        "x": x0 * w,
                        "x2": x1 * w,
                        "page": pi,
                    })

    return _group_tokens_to_text(all_tokens)
