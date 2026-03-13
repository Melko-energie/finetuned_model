#!/usr/bin/env python3
import os
import fitz
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PDF_DIR = "../data/raw_pdfs"
OUTPUT_DIR = "../data/page_images"
DPI = 200

def convert_all_pdfs(pdf_dir, output_dir, dpi=200):

    pdf_files = []
    for root, dirs, files in os.walk(pdf_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    logger.info(f"Trouvé {len(pdf_files)} PDFs à convertir")

    converted = 0
    errors = 0
    skipped = 0
    zoom = dpi / 72

    for pdf_path in tqdm(pdf_files, desc="Conversion PDFs"):

        subfolder = os.path.basename(os.path.dirname(pdf_path))
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

        out_subfolder = os.path.join(output_dir, subfolder)
        os.makedirs(out_subfolder, exist_ok=True)

        first_page_path = os.path.join(out_subfolder, f"{pdf_name}_page0.png")
        if os.path.exists(first_page_path):
            skipped += 1
            continue

        try:
            doc = fitz.open(pdf_path)
            mat = fitz.Matrix(zoom, zoom)
            nb_pages = len(doc)

            for page_num in range(nb_pages):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=mat)
                out_path = os.path.join(out_subfolder, f"{pdf_name}_page{page_num}.png")
                pix.save(out_path)

            doc.close()
            converted += 1
            logger.info(f"✅ {subfolder}/{pdf_name} → {nb_pages} page(s)")

        except Exception as e:
            errors += 1
            logger.error(f"❌ Erreur sur {pdf_path}: {str(e)}")
            continue

    logger.info("=" * 50)
    logger.info(f"Convertis  : {converted}")
    logger.info(f"Ignorés    : {skipped} (déjà existants)")
    logger.info(f"Erreurs    : {errors}")
    logger.info(f"Images dans: {output_dir}")

if __name__ == "__main__":
    convert_all_pdfs(PDF_DIR, OUTPUT_DIR, DPI)