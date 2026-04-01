# scripts/preprocess_image.py
"""
Prétraitement des images avant OCR pour améliorer la qualité
sur les PDFs scannés (contraste, binarisation, débruitage)
"""

import cv2
import numpy as np
from PIL import Image
import io


def preprocess_for_ocr(pil_image: Image.Image) -> Image.Image:
    """
    Améliore la qualité d'une image PIL avant OCR.
    Retourne une image PIL améliorée.
    """
    # PIL → numpy
    img = np.array(pil_image.convert("RGB"))

    # 1. Convertir en niveaux de gris
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # 2. Débruitage léger
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # 3. Augmenter le contraste (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(denoised)

    # 4. Binarisation adaptative (noir/blanc pur)
    binary = cv2.adaptiveThreshold(
        contrasted,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        21,   # taille bloc
        10    # constante soustraction
    )

    # 5. Légère dilation pour reconstituer les chiffres fragmentés
    kernel = np.ones((1, 2), np.uint8)
    dilated = cv2.dilate(binary, kernel, iterations=1)

    # numpy → PIL (mode RGB pour DocTR)
    result = Image.fromarray(dilated).convert("RGB")
    return result


def preprocess_pdf_page(pil_image: Image.Image, is_scanned: bool = True) -> Image.Image:
    """
    Wrapper intelligent :
    - PDF scanné  → applique le prétraitement complet
    - PDF natif   → retourne l'image telle quelle
    """
    if not is_scanned:
        return pil_image
    return preprocess_for_ocr(pil_image)


if __name__ == "__main__":
    """
    Test sur une facture RCPI scannée
    Compare OCR avant et après prétraitement
    """
    import json
    import sys
    import os
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, BASE_DIR)

    from doctr.models import ocr_predictor
    from doctr.io import DocumentFile
    import fitz

    PDF_TEST = os.path.join(BASE_DIR, "data", "raw_pdfs", "rcpi", "F2-S1113153_MICROLAD-2246848010.PDF")

    print("=== TEST PRÉTRAITEMENT IMAGE ===\n")

    # Charger le PDF
    doc = fitz.open(PDF_TEST)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 144 DPI
    img_original = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()

    print(f"Image originale : {img_original.size}")

    # Sauvegarder avant/après pour comparaison visuelle
    img_original.save(os.path.join(BASE_DIR, "data", "test_original.png"))
    img_preprocessed = preprocess_for_ocr(img_original)
    img_preprocessed.save(os.path.join(BASE_DIR, "data", "test_preprocessed.png"))
    print("Images sauvegardées : data/test_original.png / test_preprocessed.png")

    # OCR sur image originale
    model = ocr_predictor(pretrained=True)

    def ocr_image(pil_img):
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        buf.seek(0)
        doc = DocumentFile.from_images([buf.read()])
        result = model(doc)
        tokens = []
        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    for word in line.words:
                        (x0, y0), (x1, y1) = word.geometry
                        w, h = pil_img.size
                        tokens.append({
                            "text": word.value,
                            "x0": round(x0 * w),
                            "x1": round(x1 * w),
                            "conf": round(word.confidence, 3)
                        })
        return tokens

    print("\n--- OCR ORIGINAL ---")
    tokens_orig = ocr_image(img_original)
    # Chercher les tokens autour des montants
    for t in tokens_orig:
        if any(c.isdigit() for c in t["text"]) and len(t["text"]) <= 8:
            print(f"  '{t['text']}' x={t['x0']}-{t['x1']} conf={t['conf']}")

    print("\n--- OCR APRÈS PRÉTRAITEMENT ---")
    tokens_pre = ocr_image(img_preprocessed)
    for t in tokens_pre:
        if any(c.isdigit() for c in t["text"]) and len(t["text"]) <= 8:
            print(f"  '{t['text']}' x={t['x0']}-{t['x1']} conf={t['conf']}")

    # Comparer les montants trouvés
    print("\n--- COMPARAISON MONTANTS ---")
    montants_orig = [t["text"] for t in tokens_orig if "860" in t["text"] or "2860" in t["text"]]
    montants_pre  = [t["text"] for t in tokens_pre  if "860" in t["text"] or "2860" in t["text"]]
    print(f"Original    : {montants_orig}")
    print(f"Prétraité   : {montants_pre}")