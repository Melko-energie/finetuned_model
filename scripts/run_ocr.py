#!/usr/bin/env python3
"""
OCR extraction script using DocTR (remplacement de Tesseract)
Spécialisé documents/factures, compatible Python 3.14
"""

import os
import json
import fitz
import numpy as np
from PIL import Image
from tqdm import tqdm
import logging
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCRProcessor:
    def __init__(self, pdf_dir: str, output_dir: str):
        self.pdf_dir = pdf_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Initialiser DocTR une seule fois
        from doctr.models import ocr_predictor
        self.ocr = ocr_predictor(
            det_arch='db_resnet50',
            reco_arch='crnn_vgg16_bn',
            pretrained=True
        )
        logger.info("DocTR initialisé ✅")

    def extract_with_pymupdf(self, pdf_path: str):
        """Extraction directe pour PDFs numériques (texte sélectionnable)"""
        doc = fitz.open(pdf_path)
        pages_data = []

        for page_num, page in enumerate(doc):
            words_raw = page.get_text("words")
            page_words = []

            for w in words_raw:
                x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
                text = text.strip()
                if text:
                    page_words.append({
                        "text": text,
                        "bbox": [x0, y0, x1, y1],
                        "page": page_num,
                        "confidence": 1.0
                    })

            logger.info(f"  Page {page_num} : {len(page_words)} mots (PyMuPDF)")
            pages_data.append(page_words)

        doc.close()
        return pages_data

    def extract_with_doctr(self, pdf_path: str):
        """Extraction OCR pour PDFs scannés via DocTR"""
        from doctr.io import DocumentFile

        # Charger le PDF
        doc_pages = DocumentFile.from_pdf(pdf_path)

        # Lancer OCR
        result = self.ocr(doc_pages)

        pages_data = []

        for page_num, page in enumerate(result.pages):
            page_words = []
            h, w = page.dimensions

            for block in page.blocks:
                for line in block.lines:
                    for word in line.words:
                        text = word.value.strip()
                        confidence = float(word.confidence)

                        if text and confidence > 0.4:
                            # Convertir coordonnées relatives → absolues
                            (x0_rel, y0_rel), (x1_rel, y1_rel) = word.geometry
                            x0 = x0_rel * w
                            y0 = y0_rel * h
                            x1 = x1_rel * w
                            y1 = y1_rel * h

                            page_words.append({
                                "text": text,
                                "bbox": [x0, y0, x1, y1],
                                "page": page_num,
                                "confidence": confidence
                            })

            logger.info(f"  Page {page_num} : {len(page_words)} mots (DocTR)")
            pages_data.append(page_words)

        return pages_data

    def process_pdf(self, pdf_filename: str) -> bool:
        """Traiter un seul PDF"""
        pdf_path = os.path.join(self.pdf_dir, pdf_filename)

        output_subdir = os.path.join(
            self.output_dir,
            os.path.dirname(pdf_filename)
        )
        os.makedirs(output_subdir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(pdf_filename))[0]
        output_path = os.path.join(output_subdir, f"{base_name}.json")

        try:
            # Essayer PyMuPDF d'abord
            pages_data = self.extract_with_pymupdf(pdf_path)
            total_words = sum(len(p) for p in pages_data)

            if total_words < 20:
                # PDF scanné → DocTR
                logger.info(f"PDF scanné détecté : {pdf_filename} → DocTR")
                pages_data = self.extract_with_doctr(pdf_path)
                total_words = sum(len(p) for p in pages_data)

            result = {
                "filename": pdf_filename,
                "pages": pages_data,
                "total_pages": len(pages_data),
                "total_words": total_words
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ {pdf_filename} : {total_words} mots")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur {pdf_filename} : {str(e)}")
            return False

    def process_all(self):
        """Traiter tous les PDFs du dossier"""
        pdf_files = []
        for root, dirs, files in os.walk(self.pdf_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    rel_path = os.path.relpath(
                        os.path.join(root, file), self.pdf_dir
                    )
                    pdf_files.append(rel_path)

        logger.info(f"PDFs trouvés : {len(pdf_files)}")

        success = 0
        for pdf_file in tqdm(pdf_files, desc="Extraction OCR"):
            if self.process_pdf(pdf_file):
                success += 1

        logger.info(f"✅ Traités avec succès : {success}/{len(pdf_files)}")


if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

    PDF_DIR = os.path.join(PROJECT_ROOT, "data", "raw_pdfs")
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "ocr_texts")

    print(f"PDFs source : {PDF_DIR}")
    print(f"Sortie OCR  : {OUTPUT_DIR}")

    processor = OCRProcessor(PDF_DIR, OUTPUT_DIR)
    processor.process_all()