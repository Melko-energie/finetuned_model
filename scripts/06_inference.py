#!/usr/bin/env python3
"""
Inference script using LayoutLMv3 + LoRA with DocTR for OCR.
Supports PNG images and PDF files as input.
"""

import os
import io
import sys
import json
import torch
import numpy as np
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from peft import PeftModel
from PIL import Image
import fitz
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFExtractor:
    def __init__(self, model_path: str):
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(model_path)),
            "data", "label_schema.json"
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        self.id2label = schema["id2label"]
        self.label2id = schema["label2id"]

        base_model = LayoutLMv3ForTokenClassification.from_pretrained(
            "microsoft/layoutlmv3-base",
            num_labels=len(self.id2label),
            id2label=self.id2label,
            label2id=self.label2id
        )

        self.model = PeftModel.from_pretrained(base_model, model_path)
        self.model.eval()

        self.processor = LayoutLMv3Processor.from_pretrained(
            "microsoft/layoutlmv3-base",
            apply_ocr=False
        )

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        logger.info(f"Model loaded on {self.device}")

        # Initialize DocTR
        from doctr.models import ocr_predictor
        self.ocr = ocr_predictor(
            det_arch='db_resnet50',
            reco_arch='crnn_vgg16_bn',
            pretrained=True
        )
        logger.info("DocTR initialized")

    def normalize_bbox(self, bbox, width, height):
        x0, y0, x1, y1 = bbox
        x0 = min(int(x0 / width * 1000), 1000)
        y0 = min(int(y0 / height * 1000), 1000)
        x1 = min(int(x1 / width * 1000), 1000)
        y1 = min(int(y1 / height * 1000), 1000)
        return [x0, y0, x1, y1]

    def ocr_with_doctr(self, image: Image.Image) -> List[Dict]:
        """Extract words and bboxes from an image using DocTR."""
        img_array = np.array(image)
        result = self.ocr([img_array])

        words = []
        page = result.pages[0]
        h, w = page.dimensions

        for block in page.blocks:
            for line in block.lines:
                for word in line.words:
                    text = word.value.strip()
                    confidence = float(word.confidence)
                    if text and confidence > 0.4:
                        (x0_rel, y0_rel), (x1_rel, y1_rel) = word.geometry
                        words.append({
                            "text": text,
                            "bbox": [x0_rel * w, y0_rel * h, x1_rel * w, y1_rel * h],
                            "confidence": confidence
                        })

        return words

    def load_input(self, input_path: str) -> List[Dict]:
        """Load a PNG image or PDF and extract tokens with DocTR."""
        ext = os.path.splitext(input_path)[1].lower()

        if ext in ('.png', '.jpg', '.jpeg', '.tiff', '.bmp'):
            return self._load_image(input_path)
        elif ext == '.pdf':
            return self._load_pdf(input_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _load_image(self, image_path: str) -> List[Dict]:
        """Load a single image and run OCR."""
        image = Image.open(image_path).convert("RGB")
        width, height = image.size

        ocr_words = self.ocr_with_doctr(image)
        logger.info(f"Image: {len(ocr_words)} words extracted (DocTR)")

        page_words = []
        for w in ocr_words:
            page_words.append({
                "text": w["text"],
                "bbox": self.normalize_bbox(w["bbox"], width, height)
            })

        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")

        return [{
            "words": page_words,
            "image_data": img_bytes.getvalue(),
            "page_num": 0,
            "width": width,
            "height": height
        }]

    def _load_pdf(self, pdf_path: str) -> List[Dict]:
        """Load a PDF: use PyMuPDF for digital PDFs, DocTR for scanned ones."""
        doc = fitz.open(pdf_path)
        pages_data = []
        zoom = 200 / 72

        for page_num, page in enumerate(doc):
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            width, height = pix.width, pix.height

            words_raw = page.get_text("words")

            if len(words_raw) > 10:
                # Digital PDF
                page_words = []
                for w in words_raw:
                    x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
                    text = text.strip()
                    if text:
                        page_words.append({
                            "text": text,
                            "bbox": self.normalize_bbox(
                                [x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom],
                                width, height
                            )
                        })
            else:
                # Scanned PDF -> DocTR
                logger.info(f"Page {page_num}: scanned PDF, using DocTR")
                image = Image.open(io.BytesIO(img_data)).convert("RGB")
                ocr_words = self.ocr_with_doctr(image)
                page_words = []
                for w in ocr_words:
                    page_words.append({
                        "text": w["text"],
                        "bbox": self.normalize_bbox(w["bbox"], width, height)
                    })

            logger.info(f"Page {page_num}: {len(page_words)} words extracted")
            pages_data.append({
                "words": page_words,
                "image_data": img_data,
                "page_num": page_num,
                "width": width,
                "height": height
            })

        doc.close()
        return pages_data

    def predict_page(self, page_data: Dict) -> List[Dict]:
        words = [w["text"] for w in page_data["words"]]
        boxes = [w["bbox"] for w in page_data["words"]]

        if not words:
            return []

        image = Image.open(io.BytesIO(page_data["image_data"])).convert("RGB")

        encoding = self.processor(
            image,
            words,
            boxes=boxes,
            truncation=True,
            padding="max_length",
            max_length=512,
            return_tensors="pt"
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)
        bbox = encoding["bbox"].to(self.device)
        pixel_values = encoding["pixel_values"].to(self.device)

        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                bbox=bbox,
                pixel_values=pixel_values
            )

        predictions = outputs.logits.argmax(-1).squeeze().tolist()
        labels = [self.id2label[str(p)] for p in predictions]

        results = []
        for idx, (word, box, label) in enumerate(zip(words, boxes, labels)):
            if label != "O":
                results.append({
                    "word": word,
                    "label": label,
                    "bbox": box,
                    "position": idx
                })

        return results

    def group_predictions(self, predictions: List[Dict]) -> Dict[str, List]:
        grouped = {}
        current_label = None
        current_words = []

        for pred in sorted(predictions, key=lambda x: x["position"]):
            label = pred["label"]
            word = pred["word"]

            if label.startswith("B-"):
                if current_words and current_label:
                    entity_type = current_label[2:]
                    grouped.setdefault(entity_type, []).append(" ".join(current_words))
                current_label = label
                current_words = [word]

            elif label.startswith("I-") and current_label and label[2:] == current_label[2:]:
                current_words.append(word)

            else:
                if current_words and current_label:
                    entity_type = current_label[2:]
                    grouped.setdefault(entity_type, []).append(" ".join(current_words))
                current_label = None
                current_words = []

        if current_words and current_label:
            entity_type = current_label[2:]
            grouped.setdefault(entity_type, []).append(" ".join(current_words))

        return grouped

    def extract(self, input_path: str) -> Dict[str, Any]:
        """Run full extraction pipeline on a PNG or PDF."""
        logger.info(f"Processing: {input_path}")

        pages_data = self.load_input(input_path)
        all_predictions = []
        extracted_data = {}

        for page_data in pages_data:
            predictions = self.predict_page(page_data)
            grouped = self.group_predictions(predictions)

            for entity_type, values in grouped.items():
                extracted_data.setdefault(entity_type, []).extend(values)

            all_predictions.extend(predictions)

        extracted_fields = {}
        for field, values in extracted_data.items():
            extracted_fields[field] = values[0] if len(values) == 1 else values

        return {
            "filename": os.path.basename(input_path),
            "total_pages": len(pages_data),
            "extracted_fields": extracted_fields,
            "total_predictions": len(all_predictions)
        }

    def save_results(self, results: Dict, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        filename = results["filename"]
        output_path = os.path.join(
            output_dir,
            f"{os.path.splitext(filename)[0]}_extracted.json"
        )
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Results saved to {output_path}")
        return output_path


if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

    MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "finetuned_lora")
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "predictions")

    if len(sys.argv) < 2:
        print("Usage: python 06_inference.py <image.png|document.pdf>")
        sys.exit(1)

    INPUT_PATH = sys.argv[1]

    extractor = PDFExtractor(MODEL_PATH)
    results = extractor.extract(INPUT_PATH)
    output_path = extractor.save_results(results, OUTPUT_DIR)

    print("\n" + "=" * 50)
    print("EXTRACTION RESULTS")
    print("=" * 50)
    print(f"File: {results['filename']}")
    print(f"Pages: {results['total_pages']}")
    print("-" * 50)
    for field, value in results["extracted_fields"].items():
        print(f"  {field}: {value}")
    print(f"\nTotal predictions: {results['total_predictions']}")
    print(f"JSON saved: {output_path}")
    print("=" * 50)
