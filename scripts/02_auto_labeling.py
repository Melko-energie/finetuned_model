#!/usr/bin/env python3
"""
Auto-labeling script using regex patterns to create initial annotations
"""

import os
import json
import re
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoLabeler:
    def __init__(self, label_schema_path: str):
        with open(label_schema_path, 'r', encoding='utf-8') as f:
            self.label_schema = json.load(f)

        self.patterns = {
            
            "NUMERO_FACTURE": [
                r'\b(?:n[°º]\s*facture|facture\s*n[°º])\s*:?\s*([A-Z]{1,4}\d{2}[-/]\d{2,})\b',
                r'\b(?:n[°º]\s*arcana|arcana\s*n[°º])\s*:?\s*(\d{5,})\b',
                r'\bfacture\s+n[°º°]?\s*:?\s*(\d{3,6})\b',
                r'\bnote\s+d.honoraires\s+n[°º]\s*(\d{2,})\b',
                r'\bfacture\s+n[°º]\s*(\d{4,})\b',
            ],

            "DATE_FACTURE": [
                r'\b\d{2}/\d{2}/\d{4}\b',
                r'\b\d{2}\.\d{2}\.\d{4}\b',
                r'\b\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}\b',
                r'(?:le\s+|date\s*:?\s*)\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}\b',
            ],

            "MONTANT_HT": [
                r'(?:total\s+h\.?t\.?|montant\s+h\.?t\.?|total\s+€\s*h\.?t\.?)\s*[:\|]?\s*([\d\s]+[,.]\d{2})\s*€?',
                r'(?:acompte\s+demandé?\s+h\.?t\.?)\s*[:\|]?\s*([\d\s]+[,.]\d{2})\s*€?',
                r'(?:montant\s+h\.t\s+de\s+la\s+note)\s*[:\|]?\s*([\d\s]+[,.]\d{2})\s*€?',
            ],

            "TAUX_TVA": [
                r'\bT\.?V\.?A\.?\s+(\d{1,2}[,.]\d{0,2}\s*%)',
                r'\bT\.V\.A\.\s*(\d{1,2}[,.]?\d{0,2}\s*%)',
            ],

            "RETENUE_GARANTIE": [
                r'retenue\s+de\s+garantie\s*:?\s*([\d\s]+[,.]\d{2})\s*€?',
                r'\bR\.?G\.?\s*:?\s*([\d\s]+[,.]\d{2})\s*€?',
                r'([\d\s]+[,.]\d{2})\s*€?\s*(?:retenue\s+de\s+garantie|R\.G\.)',
            ],

            "TAUX_RETENUE": [
                r'retenue\s+de\s+garantie\s*:?\s*(\d{1,2}[,.]\d{0,2}\s*%)',
                r'\b(\d{1,2}[,.]\d{0,2}\s*%)\s*(?:retenue|R\.G\.)',
            ],

            "CODE_POSTAL": [
                r'\b((?:0[1-9]|[1-8]\d|9[0-5])\d{3})\s+([A-ZÀÂÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\s\-]{2,}?)(?:\s|$)',
            ],

            "COMMUNE": [
                r'(?:0[1-9]|[1-8]\d|9[0-5])\d{3}\s+([A-ZÀÂÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\s\-]{2,20}?)(?:\s+CEDEX|\s*$|\s*\n)',
            ],

            "ADRESSE_TRAVAUX": [
                r'\b\d{1,4}\s+(?:rue|avenue|boulevard|allée|impasse|place|chemin)\s+[A-Za-zÀ-ÿ\s\-]{3,40}',
                r'[A-Z]{3,}\s*[-]\s*\d{1,4}\s+(?:rue|avenue|boulevard|allée|impasse|place)\s+[A-Za-zÀ-ÿ\s\-]{3,40}',
            ],

            "INSTALLATEUR": [
                r'\b([A-Z][A-Za-zÀ-ÿ\s]{2,30})\s*,?\s*(?:EURL|SARL|SAS|SA|SASU|EARL)\b',
                r"(?:bureau\s+d['\s]études?\s+)([A-Za-zÀ-ÿ\s\-]{3,30})",
            ],

            "DETAIL_TRAVAUX": [
                r'(?:objet\s*:?\s*|désignation\s*:?\s*)([A-Za-zÀ-ÿ\s,\-]{10,100})',
                r'(?:fourniture\s+et\s+pose|installation|remplacement|transformation)\s+[A-Za-zÀ-ÿ\s,\-]{5,80}',
            ],
        }

        # Compiler tous les patterns
        self.compiled_patterns = {}
        for label, pattern_list in self.patterns.items():
            self.compiled_patterns[label] = [
                re.compile(p, re.IGNORECASE | re.UNICODE) for p in pattern_list
            ]

    def find_matches(self, text: str) -> List[Dict[str, Any]]:
        matches = []
        for label, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    matches.append({
                        "label": label,
                        "text": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.9
                    })
        return matches

    def create_bio_labels(self, matched_words: List[Dict], label: str) -> List[str]:
        if len(matched_words) == 1:
            return [f"B-{label}"]
        else:
            return [f"B-{label}"] + [f"I-{label}"] * (len(matched_words) - 1)

    def label_ocr_data(self, ocr_data: Dict) -> List[Dict]:
        annotations = []

        for page_num, page_words in enumerate(ocr_data.get("pages", [])):
            if not page_words:
                continue

            page_text = " ".join([word["text"] for word in page_words])
            matches = self.find_matches(page_text)

            for match in matches:
                matched_words = []
                current_pos = 0

                for word_idx, word in enumerate(page_words):
                    word_start = page_text.find(word["text"], current_pos)
                    if word_start == -1:
                        continue
                    word_end = word_start + len(word["text"])
                    if not (word_end <= match["start"] or word_start >= match["end"]):
                        matched_words.append({
                            "word_idx": word_idx,
                            "word": word["text"],
                            "bbox": word["bbox"]
                        })
                    current_pos = word_end

                if matched_words:
                    bio_labels = self.create_bio_labels(matched_words, match["label"])
                    labels_to_assign = bio_labels if len(matched_words) > 1 else [bio_labels[0]]

                    annotation = {
                        "id": f"auto_{page_num}_{len(annotations)}",
                        "type": "labels",
                        "value": {
                            "start": match["start"],
                            "end": match["end"],
                            "text": match["text"],
                            "labels": labels_to_assign
                        },
                        "origin": "auto",
                        "to_name": "text",
                        "from_name": "label",
                        "page": page_num,
                        "words": matched_words,
                        "confidence": match["confidence"]
                    }
                    annotations.append(annotation)

        return annotations

    def process_file(self, ocr_file_path: str, output_dir: str):
        with open(ocr_file_path, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)

        annotations = self.label_ocr_data(ocr_data)

        ls_annotation = {
            "data": {
                "text": " ".join([word["text"] for page in ocr_data["pages"] for word in page]),
                "pdf_filename": ocr_data["filename"]
            },
            "annotations": [{
                "result": annotations,
                "was_cancelled": False,
                "ground_truth": False,
                "created_at": "auto_generated",
                "updated_at": "auto_generated",
                "lead_time": 0
            }],
            "predictions": []
        }

        base_name = os.path.splitext(os.path.basename(ocr_file_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.json")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ls_annotation, f, ensure_ascii=False, indent=2)

        label_counts = {}
        for ann in annotations:
            for label in ann["value"]["labels"]:
                base_label = label.replace("B-", "").replace("I-", "")
                label_counts[base_label] = label_counts.get(base_label, 0) + 1

        logger.info(f"Auto-labeled {ocr_file_path}: {len(annotations)} annotations")
        for label, count in label_counts.items():
            logger.info(f"  - {label}: {count}")

        return len(annotations)

    def process_all(self, ocr_dir: str, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)

        ocr_files = []
        for root, dirs, files in os.walk(ocr_dir):
            for file in files:
                if file.endswith('.json'):
                    rel_path = os.path.relpath(os.path.join(root, file), ocr_dir)
                    ocr_files.append(rel_path)

        total_annotations = 0

        for ocr_file in ocr_files:
            ocr_path = os.path.join(ocr_dir, ocr_file)
            annotations_count = self.process_file(ocr_path, output_dir)
            total_annotations += annotations_count

        logger.info(f"Total auto-generated annotations: {total_annotations}")

        summary_path = os.path.join(output_dir, "auto_labeling_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                "total_files": len(ocr_files),
                "total_annotations": total_annotations,
                "processed_files": ocr_files
            }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys

    LABEL_SCHEMA_PATH = "../data/label_schema.json"
    OCR_DIR = "../data/ocr_texts"
    OUTPUT_DIR = "../data/annotations"

    labeler = AutoLabeler(LABEL_SCHEMA_PATH)
    labeler.process_all(OCR_DIR, OUTPUT_DIR)