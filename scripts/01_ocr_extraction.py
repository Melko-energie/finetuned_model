#!/usr/bin/env python3
"""
OCR extraction script using PyMuPDF for PDF structure and Tesseract for OCR
"""

import os
import json
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import cv2
import numpy as np
from pdf2image import convert_from_path
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self, pdf_dir, output_dir):
        self.pdf_dir = pdf_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def extract_with_pymupdf(self, pdf_path):
        """Extract text and bounding boxes using PyMuPDF"""
        doc = fitz.open(pdf_path)
        pages_data = []
        
        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            page_words = []
            
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            bbox = span["bbox"]
                            word = {
                                "text": span["text"].strip(),
                                "bbox": [bbox[0], bbox[1], bbox[2], bbox[3]],
                                "page": page_num,
                                "block": block["number"]
                            }
                            if word["text"]:
                                page_words.append(word)
            
            pages_data.append(page_words)
        
        return pages_data
    
    def extract_with_tesseract(self, pdf_path):
        """Extract text using Tesseract OCR for scanned PDFs"""
        images = convert_from_path(pdf_path, dpi=300)
        pages_data = []
        
        for page_num, image in enumerate(images):
            # Convert to OpenCV format
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Get OCR data
            data = pytesseract.image_to_data(
                img_cv, 
                output_type=pytesseract.Output.DICT,
                config='--psm 6'
            )
            
            page_words = []
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                if int(data['conf'][i]) > 60 and data['text'][i].strip():
                    word = {
                        "text": data['text'][i].strip(),
                        "bbox": [
                            data['left'][i],
                            data['top'][i],
                            data['left'][i] + data['width'][i],
                            data['top'][i] + data['height'][i]
                        ],
                        "page": page_num,
                        "confidence": float(data['conf'][i])
                    }
                    page_words.append(word)
            
            pages_data.append(page_words)
        
        return pages_data
    
    def process_pdf(self, pdf_filename):
        """Process a single PDF file"""
        pdf_path = os.path.join(self.pdf_dir, pdf_filename)
        # Create output subdirectory structure if needed
        output_subdir = os.path.join(self.output_dir, os.path.dirname(pdf_filename))
        os.makedirs(output_subdir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(pdf_filename))[0]
        output_path = os.path.join(output_subdir, f"{base_name}.json")
        
        try:
            # Try PyMuPDF first (for digital PDFs)
            if pdf_path.lower().endswith('.pdf'):
                pages_data = self.extract_with_pymupdf(pdf_path)
                
                # If little text extracted, try Tesseract
                total_words = sum(len(page) for page in pages_data)
                if total_words < 20:
                    logger.info(f"Few words found with PyMuPDF, trying Tesseract for {pdf_filename}")
                    pages_data = self.extract_with_tesseract(pdf_path)
            else:
                return False
                
            # Save extracted data
            result = {
                "filename": pdf_filename,
                "pages": pages_data,
                "total_pages": len(pages_data),
                "total_words": sum(len(page) for page in pages_data)
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Processed {pdf_filename}: {result['total_words']} words")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {pdf_filename}: {str(e)}")
            return False
    
    def process_all(self):
        """Process all PDFs in the directory and subdirectories"""
        # Find all PDFs recursively
        pdf_files = []
        for root, dirs, files in os.walk(self.pdf_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    # Store relative path from pdf_dir
                    rel_path = os.path.relpath(os.path.join(root, file), self.pdf_dir)
                    pdf_files.append(rel_path)
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        success_count = 0
        for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
            if self.process_pdf(pdf_file):
                success_count += 1
        
        logger.info(f"Successfully processed {success_count}/{len(pdf_files)} files")
if __name__ == "__main__":
    # Configuration - Use relative to THIS script file
    import os
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    
    PDF_DIR = os.path.join(PROJECT_ROOT, "data", "raw_pdfs")
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "ocr_texts")
    
    print(f"Looking for PDFs in: {PDF_DIR}")
    print(f"Output will go to: {OUTPUT_DIR}")
    
    processor = OCRProcessor(PDF_DIR, OUTPUT_DIR)
    processor.process_all()