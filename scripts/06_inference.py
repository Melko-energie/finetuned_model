#!/usr/bin/env python3
"""
Inference script for extracting information from new PDFs
"""

import os
import json
import torch
from transformers import (
    LayoutLMv3Processor,
    LayoutLMv3ForTokenClassification
)
from PIL import Image
import fitz
import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFExtractor:
    def __init__(self, model_path: str):
        # Load model and processor
        self.model = LayoutLMv3ForTokenClassification.from_pretrained(model_path)
        self.processor = LayoutLMv3Processor.from_pretrained(model_path)
        
        # Load label mappings
        config_path = os.path.join(model_path, "training_config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
            self.id2label = config["id2label"]
            self.label2id = config["label2id"]
        
        # Move model to device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        
        logger.info(f"Model loaded on {self.device}")
    
    def extract_text_and_boxes(self, pdf_path: str) -> List[Dict]:
        """Extract text and bounding boxes from PDF"""
        doc = fitz.open(pdf_path)
        pages_data = []
        
        for page_num, page in enumerate(doc):
            # Get page image
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            img_data = pix.tobytes("png")
            
            # Extract text blocks
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
            
            pages_data.append({
                "words": page_words,
                "image_data": img_data,
                "page_num": page_num,
                "width": pix.width,
                "height": pix.height
            })
        
        return pages_data
    
    def preprocess_page(self, page_data: Dict) -> Dict:
        """Preprocess page data for model"""
        words = [w["text"] for w in page_data["words"]]
        boxes = [w["bbox"] for w in page_data["words"]]
        
        # Load image
        image = Image.open(io.BytesIO(page_data["image_data"])).convert("RGB")
        
        # Encode
        encoding = self.processor(
            image,
            words,
            boxes=boxes,
            truncation=True,
            padding="max_length",
            max_length=512,
            return_tensors="pt"
        )
        
        return {
            "encoding": encoding,
            "words": words,
            "boxes": boxes,
            "image": image
        }
    
    def predict(self, preprocessed_data: Dict) -> List[Dict]:
        """Run model prediction"""
        encoding = preprocessed_data["encoding"]
        
        # Move to device
        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)
        bbox = encoding["bbox"].to(self.device)
        pixel_values = encoding["pixel_values"].to(self.device)
        
        # Predict
        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                bbox=bbox,
                pixel_values=pixel_values
            )
        
        # Get predictions
        predictions = outputs.logits.argmax(-1).squeeze().tolist()
        
        # Map to labels
        labels = [self.id2label[str(p)] for p in predictions]
        
        # Filter out special tokens and padding
        results = []
        for idx, (word, box, label) in enumerate(zip(
            preprocessed_data["words"],
            preprocessed_data["boxes"],
            labels
        )):
            if label != "O" and idx < len(preprocessed_data["words"]):
                results.append({
                    "word": word,
                    "label": label,
                    "bbox": box,
                    "position": idx
                })
        
        return results
    
    def group_predictions(self, predictions: List[Dict]) -> Dict[str, List]:
        """Group predictions by label type"""
        grouped = {}
        
        current_entity = None
        current_words = []
        current_label = None
        
        for pred in sorted(predictions, key=lambda x: x["position"]):
            label = pred["label"]
            word = pred["word"]
            
            if label.startswith("B-"):
                # Save previous entity if exists
                if current_entity and current_words:
                    entity_type = current_label[2:] if current_label else "UNKNOWN"
                    if entity_type not in grouped:
                        grouped[entity_type] = []
                    grouped[entity_type].append(" ".join(current_words))
                
                # Start new entity
                current_label = label
                current_words = [word]
                current_entity = label[2:]
            
            elif label.startswith("I-") and current_label:
                # Continue current entity
                if label[2:] == current_label[2:]:
                    current_words.append(word)
                else:
                    # Mismatch, treat as new entity
                    if current_words:
                        entity_type = current_label[2:] if current_label else "UNKNOWN"
                        if entity_type not in grouped:
                            grouped[entity_type] = []
                        grouped[entity_type].append(" ".join(current_words))
                    
                    current_label = label
                    current_words = [word]
                    current_entity = label[2:]
            
            else:
                # Save previous entity
                if current_words:
                    entity_type = current_label[2:] if current_label else "UNKNOWN"
                    if entity_type not in grouped:
                        grouped[entity_type] = []
                    grouped[entity_type].append(" ".join(current_words))
                
                current_label = None
                current_words = []
                current_entity = None
        
        # Save last entity
        if current_words:
            entity_type = current_label[2:] if current_label else "UNKNOWN"
            if entity_type not in grouped:
                grouped[entity_type] = []
            grouped[entity_type].append(" ".join(current_words))
        
        return grouped
    
    def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Main extraction pipeline"""
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Extract text and boxes
        pages_data = self.extract_text_and_boxes(pdf_path)
        
        all_predictions = []
        extracted_data = {}
        
        for page_data in pages_data:
            # Preprocess
            preprocessed = self.preprocess_page(page_data)
            
            # Predict
            predictions = self.predict(preprocessed)
            
            # Group predictions
            grouped = self.group_predictions(predictions)
            
            # Merge with existing data
            for entity_type, values in grouped.items():
                if entity_type not in extracted_data:
                    extracted_data[entity_type] = []
                extracted_data[entity_type].extend(values)
            
            all_predictions.extend(predictions)
        
        # Create final structured output
        result = {
            "filename": os.path.basename(pdf_path),
            "total_pages": len(pages_data),
            "extracted_fields": {},
            "raw_predictions": all_predictions,
            "confidence_scores": self.calculate_confidence(all_predictions)
        }
        
        # Take first value for each field (or handle multiple values)
        for field, values in extracted_data.items():
            if values:
                result["extracted_fields"][field] = values[0] if len(values) == 1 else values
        
        return result
    
    def calculate_confidence(self, predictions: List[Dict]) -> Dict:
        """Calculate confidence scores for predictions"""
        if not predictions:
            return {"overall": 0.0}
        
        # Simple confidence based on label type
        label_counts = {}
        for pred in predictions:
            label = pred["label"]
            if label not in label_counts:
                label_counts[label] = 0
            label_counts[label] += 1
        
        return {
            "total_predictions": len(predictions),
            "unique_labels": len(label_counts),
            "label_distribution": label_counts
        }
    
    def save_results(self, results: Dict[str, Any], output_dir: str):
        """Save extraction results"""
        os.makedirs(output_dir, exist_ok=True)
        
        filename = results["filename"]
        output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_extracted.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Results saved to {output_path}")
        return output_path

if __name__ == "__main__":
    import io
    import sys
    
    # Configuration
    MODEL_PATH = "../models/finetuned_lora"
    PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else "../data/raw_pdfs/sample.pdf"
    OUTPUT_DIR = "../outputs/predictions"
    
    # Initialize extractor
    extractor = PDFExtractor(MODEL_PATH)
    
    # Extract from PDF
    results = extractor.extract_from_pdf(PDF_PATH)
    
    # Save results
    extractor.save_results(results, OUTPUT_DIR)
    
    # Print summary
    print("\n" + "="*50)
    print("EXTRACTION RESULTS")
    print("="*50)
    for field, value in results["extracted_fields"].items():
        print(f"{field}: {value}")
    print("="*50)#!/usr/bin/env python3
"""
Inference script for extracting information from new PDFs
"""

import os
import json
import torch
from transformers import (
    LayoutLMv3Processor,
    LayoutLMv3ForTokenClassification
)
from PIL import Image
import fitz
import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFExtractor:
    def __init__(self, model_path: str):
        # Load model and processor
        self.model = LayoutLMv3ForTokenClassification.from_pretrained(model_path)
        self.processor = LayoutLMv3Processor.from_pretrained(model_path)
        
        # Load label mappings
        config_path = os.path.join(model_path, "training_config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
            self.id2label = config["id2label"]
            self.label2id = config["label2id"]
        
        # Move model to device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        
        logger.info(f"Model loaded on {self.device}")
    
    def extract_text_and_boxes(self, pdf_path: str) -> List[Dict]:
        """Extract text and bounding boxes from PDF"""
        doc = fitz.open(pdf_path)
        pages_data = []
        
        for page_num, page in enumerate(doc):
            # Get page image
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            img_data = pix.tobytes("png")
            
            # Extract text blocks
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
            
            pages_data.append({
                "words": page_words,
                "image_data": img_data,
                "page_num": page_num,
                "width": pix.width,
                "height": pix.height
            })
        
        return pages_data
    
    def preprocess_page(self, page_data: Dict) -> Dict:
        """Preprocess page data for model"""
        words = [w["text"] for w in page_data["words"]]
        boxes = [w["bbox"] for w in page_data["words"]]
        
        # Load image
        image = Image.open(io.BytesIO(page_data["image_data"])).convert("RGB")
        
        # Encode
        encoding = self.processor(
            image,
            words,
            boxes=boxes,
            truncation=True,
            padding="max_length",
            max_length=512,
            return_tensors="pt"
        )
        
        return {
            "encoding": encoding,
            "words": words,
            "boxes": boxes,
            "image": image
        }
    
    def predict(self, preprocessed_data: Dict) -> List[Dict]:
        """Run model prediction"""
        encoding = preprocessed_data["encoding"]
        
        # Move to device
        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)
        bbox = encoding["bbox"].to(self.device)
        pixel_values = encoding["pixel_values"].to(self.device)
        
        # Predict
        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                bbox=bbox,
                pixel_values=pixel_values
            )
        
        # Get predictions
        predictions = outputs.logits.argmax(-1).squeeze().tolist()
        
        # Map to labels
        labels = [self.id2label[str(p)] for p in predictions]
        
        # Filter out special tokens and padding
        results = []
        for idx, (word, box, label) in enumerate(zip(
            preprocessed_data["words"],
            preprocessed_data["boxes"],
            labels
        )):
            if label != "O" and idx < len(preprocessed_data["words"]):
                results.append({
                    "word": word,
                    "label": label,
                    "bbox": box,
                    "position": idx
                })
        
        return results
    
    def group_predictions(self, predictions: List[Dict]) -> Dict[str, List]:
        """Group predictions by label type"""
        grouped = {}
        
        current_entity = None
        current_words = []
        current_label = None
        
        for pred in sorted(predictions, key=lambda x: x["position"]):
            label = pred["label"]
            word = pred["word"]
            
            if label.startswith("B-"):
                # Save previous entity if exists
                if current_entity and current_words:
                    entity_type = current_label[2:] if current_label else "UNKNOWN"
                    if entity_type not in grouped:
                        grouped[entity_type] = []
                    grouped[entity_type].append(" ".join(current_words))
                
                # Start new entity
                current_label = label
                current_words = [word]
                current_entity = label[2:]
            
            elif label.startswith("I-") and current_label:
                # Continue current entity
                if label[2:] == current_label[2:]:
                    current_words.append(word)
                else:
                    # Mismatch, treat as new entity
                    if current_words:
                        entity_type = current_label[2:] if current_label else "UNKNOWN"
                        if entity_type not in grouped:
                            grouped[entity_type] = []
                        grouped[entity_type].append(" ".join(current_words))
                    
                    current_label = label
                    current_words = [word]
                    current_entity = label[2:]
            
            else:
                # Save previous entity
                if current_words:
                    entity_type = current_label[2:] if current_label else "UNKNOWN"
                    if entity_type not in grouped:
                        grouped[entity_type] = []
                    grouped[entity_type].append(" ".join(current_words))
                
                current_label = None
                current_words = []
                current_entity = None
        
        # Save last entity
        if current_words:
            entity_type = current_label[2:] if current_label else "UNKNOWN"
            if entity_type not in grouped:
                grouped[entity_type] = []
            grouped[entity_type].append(" ".join(current_words))
        
        return grouped
    
    def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Main extraction pipeline"""
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Extract text and boxes
        pages_data = self.extract_text_and_boxes(pdf_path)
        
        all_predictions = []
        extracted_data = {}
        
        for page_data in pages_data:
            # Preprocess
            preprocessed = self.preprocess_page(page_data)
            
            # Predict
            predictions = self.predict(preprocessed)
            
            # Group predictions
            grouped = self.group_predictions(predictions)
            
            # Merge with existing data
            for entity_type, values in grouped.items():
                if entity_type not in extracted_data:
                    extracted_data[entity_type] = []
                extracted_data[entity_type].extend(values)
            
            all_predictions.extend(predictions)
        
        # Create final structured output
        result = {
            "filename": os.path.basename(pdf_path),
            "total_pages": len(pages_data),
            "extracted_fields": {},
            "raw_predictions": all_predictions,
            "confidence_scores": self.calculate_confidence(all_predictions)
        }
        
        # Take first value for each field (or handle multiple values)
        for field, values in extracted_data.items():
            if values:
                result["extracted_fields"][field] = values[0] if len(values) == 1 else values
        
        return result
    
    def calculate_confidence(self, predictions: List[Dict]) -> Dict:
        """Calculate confidence scores for predictions"""
        if not predictions:
            return {"overall": 0.0}
        
        # Simple confidence based on label type
        label_counts = {}
        for pred in predictions:
            label = pred["label"]
            if label not in label_counts:
                label_counts[label] = 0
            label_counts[label] += 1
        
        return {
            "total_predictions": len(predictions),
            "unique_labels": len(label_counts),
            "label_distribution": label_counts
        }
    
    def save_results(self, results: Dict[str, Any], output_dir: str):
        """Save extraction results"""
        os.makedirs(output_dir, exist_ok=True)
        
        filename = results["filename"]
        output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_extracted.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Results saved to {output_path}")
        return output_path

if __name__ == "__main__":
    import io
    import sys
    
    # Configuration
    MODEL_PATH = "../models/finetuned_lora"
    PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else "../data/raw_pdfs/sample.pdf"
    OUTPUT_DIR = "../outputs/predictions"
    
    # Initialize extractor
    extractor = PDFExtractor(MODEL_PATH)
    
    # Extract from PDF
    results = extractor.extract_from_pdf(PDF_PATH)
    
    # Save results
    extractor.save_results(results, OUTPUT_DIR)
    
    # Print summary
    print("\n" + "="*50)
    print("EXTRACTION RESULTS")
    print("="*50)
    for field, value in results["extracted_fields"].items():
        print(f"{field}: {value}")
    print("="*50)