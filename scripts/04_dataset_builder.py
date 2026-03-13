#!/usr/bin/env python3
"""
Script 04 — Dataset Builder (v2)
Lit les annotations au format LabelStudio (script 07) ET au format regex (script 03).
Construit le dataset HuggingFace pour LayoutLMv3.

Formats supportés :
  Format LabelStudio (script 07) :
    { "image_name": "...", "tokens": [{"text","bbox","label"}], "source": "labelstudio_manual" }

  Format regex (script 03) :
    { "data": {"pdf_filename": "..."}, "annotations": [...] }
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from datasets import Dataset, DatasetDict
from transformers import LayoutLMv3Processor
from PIL import Image
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Chemins ────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent.parent
ANNOTATION_DIR = BASE_DIR / "data" / "annotations_cleaned"
OCR_DIR        = BASE_DIR / "data" / "ocr_texts"
IMAGE_DIR      = BASE_DIR / "data" / "page_images"
OUTPUT_DIR     = BASE_DIR / "data" / "formatted_dataset"
LABEL_SCHEMA   = BASE_DIR / "data" / "label_schema.json"


class DatasetBuilder:

    def __init__(self, label_schema_path: str, model_name: str = "microsoft/layoutlmv3-base"):
        with open(label_schema_path, "r") as f:
            self.label_schema = json.load(f)

        self.label2id = self.label_schema["label2id"]
        self.id2label = self.label_schema["id2label"]

        self.processor = LayoutLMv3Processor.from_pretrained(
            model_name,
            apply_ocr=False
        )

    # ── Détection du format ────────────────────────────────────────

    def detect_format(self, annotation_data: dict) -> str:
        if "tokens" in annotation_data and "image_name" in annotation_data:
            return "labelstudio"
        if "data" in annotation_data:
            return "regex"
        return "unknown"

    # ── Helpers communs ────────────────────────────────────────────

    def find_image(self, image_name: str) -> Optional[Path]:
        import re
        # Cherche exactement
        name = Path(image_name).name
        for img_file in IMAGE_DIR.rglob("*.png"):
           if img_file.name.lower() == name.lower():
               return img_file
        # Normalise _page_001 → _page0, _page_002 → _page1
        stem  = Path(image_name).stem
        match = re.search(r'_page[_]?(\d+)$', stem, re.IGNORECASE)
        if match:
            num       = int(match.group(1))
            page_idx  = max(0, num - 1) if num >= 1 else 0
            stem_norm = re.sub(r'_page[_]?\d+$', f'_page{page_idx}', stem, flags=re.IGNORECASE)
            name_norm = stem_norm + ".png"
            for img_file in IMAGE_DIR.rglob("*.png"):
                if img_file.name.lower() == name_norm.lower():
                    return img_file
        return None

    def find_ocr_file(self, pdf_filename: str) -> Optional[Path]:
        stem     = Path(pdf_filename).stem
        ocr_name = (stem + ".json").lower()
        for json_file in OCR_DIR.rglob("*.json"):
            if json_file.name.lower() == ocr_name:
                return json_file
        return None

    def normalize_bbox(self, bbox, page_width, page_height):
        x0, y0, x1, y1 = bbox
        x0 = min(int(x0 / page_width  * 1000), 1000)
        y0 = min(int(y0 / page_height * 1000), 1000)
        x1 = min(int(x1 / page_width  * 1000), 1000)
        y1 = min(int(y1 / page_height * 1000), 1000)
        return [x0, y0, x1, y1]

    # ── Format LabelStudio ─────────────────────────────────────────

    def load_labelstudio_sample(self, annotation_data: dict) -> Optional[dict]:
        image_name = annotation_data.get("image_name", "")
        tokens     = annotation_data.get("tokens", [])

        if not tokens:
            return None

        words     = [t["text"]  for t in tokens]
        bboxes    = [t["bbox"]  for t in tokens]
        labels    = [t["label"] for t in tokens]
        label_ids = [self.label2id.get(l, self.label2id.get("O", 0)) for l in labels]

        image_path = self.find_image(image_name)

        return {
            "id"        : Path(image_name).stem,
            "words"     : words,
            "bboxes"    : bboxes,
            "labels"    : label_ids,
            "image_path": str(image_path) if image_path else None,
            "source"    : "labelstudio_manual",
        }

    # ── Format Regex ───────────────────────────────────────────────

    def load_regex_samples(self, annotation_data: dict, ocr_data: dict) -> List[dict]:
        samples = []
        for page_num, page_words in enumerate(ocr_data.get("pages", [])):
            if not page_words:
                continue

            words      = [w["text"] for w in page_words]
            image_name = f"{Path(ocr_data['filename']).stem}_page{page_num}.png"
            image_path = self.find_image(image_name)

            try:
                with Image.open(image_path) as img:
                    pw, ph = img.size
            except Exception:
                pw, ph = 2480, 3508

            bboxes = [self.normalize_bbox(w["bbox"], pw, ph) for w in page_words]
            labels = ["O"] * len(words)

            for ann_set in annotation_data.get("annotations", []):
                for ann in ann_set.get("result", []):
                    if ann.get("page", 0) != page_num:
                        continue
                    label = ann["value"]["labels"][0]
                    for word_info in ann.get("words", []):
                        idx = word_info.get("word_idx")
                        if idx is not None and idx < len(words):
                            labels[idx] = label

            label_ids = [self.label2id.get(l, 0) for l in labels]

            samples.append({
                "id"        : f"{ocr_data['filename']}_page{page_num}",
                "words"     : words,
                "bboxes"    : bboxes,
                "labels"    : label_ids,
                "image_path": str(image_path) if image_path else None,
                "source"    : "regex_auto",
            })

        return samples

    # ── Chargement principal ───────────────────────────────────────

    def load_annotations(self) -> List[dict]:
        samples   = []
        ann_files = list(ANNOTATION_DIR.glob("*.json"))
        logger.info(f"Fichiers annotations : {len(ann_files)}")
        stats = {"labelstudio": 0, "regex": 0, "skipped": 0}

        for ann_path in tqdm(ann_files, desc="Loading annotations"):
            with open(ann_path, "r", encoding="utf-8") as f:
                annotation_data = json.load(f)

            fmt = self.detect_format(annotation_data)

            if fmt == "labelstudio":
                sample = self.load_labelstudio_sample(annotation_data)
                if sample:
                    samples.append(sample)
                    stats["labelstudio"] += 1
                else:
                    stats["skipped"] += 1

            elif fmt == "regex":
                # DÉSACTIVÉ TEMPORAIREMENT — option 1 test
                stats["skipped"] += 1
                continue
                try:
                    pdf_filename = annotation_data["data"]["pdf_filename"]
                    ocr_path     = self.find_ocr_file(pdf_filename)
                    if not ocr_path:
                        stats["skipped"] += 1
                        continue
                    with open(ocr_path, "r", encoding="utf-8") as f:
                        ocr_data = json.load(f)
                    regex_samples = self.load_regex_samples(annotation_data, ocr_data)
                    samples.extend(regex_samples)
                    stats["regex"] += len(regex_samples)
                except Exception as e:
                    logger.warning(f"Erreur regex {ann_path.name} : {e}")
                    stats["skipped"] += 1
            else:
                stats["skipped"] += 1

        logger.info(f"LabelStudio : {stats['labelstudio']} | Regex : {stats['regex']} | Ignorés : {stats['skipped']}")
        return samples

    # ── Encodage ──────────────────────────────────────────────────

    def prepare_for_training(self, samples: List[dict], split_ratio: float = 0.85):
        encoded = []

        for sample in tqdm(samples, desc="Encoding samples"):
            image_path = sample.get("image_path")
            if not image_path or not Path(image_path).exists():
                logger.warning(f"Image introuvable : {image_path}")
                continue
            try:
                image    = Image.open(image_path).convert("RGB")
                encoding = self.processor(
                    image,
                    sample["words"],
                    boxes=sample["bboxes"],
                    word_labels=sample["labels"],
                    return_tensors="pt",
                    truncation=True,
                    padding="max_length",
                    max_length=512
                )
                encoded.append({
                    "input_ids"     : encoding["input_ids"].squeeze(),
                    "attention_mask": encoding["attention_mask"].squeeze(),
                    "bbox"          : encoding["bbox"].squeeze(),
                    "labels"        : encoding["labels"].squeeze(),
                    "pixel_values"  : encoding["pixel_values"].squeeze(),
                })
            except Exception as e:
                logger.warning(f"Erreur encodage {sample['id']} : {e}")

        if not encoded:
            raise ValueError("Aucun sample encodé.")

        dataset   = Dataset.from_list(encoded)
        split_idx = int(len(dataset) * split_ratio)

        return DatasetDict({
            "train"     : dataset.select(range(split_idx)),
            "validation": dataset.select(range(split_idx, len(dataset))),
        })

    def save_dataset(self, dataset_dict: DatasetDict, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        dataset_dict.save_to_disk(output_dir)

        info = {
            "num_train"     : len(dataset_dict["train"]),
            "num_validation": len(dataset_dict["validation"]),
            "label2id"      : self.label2id,
            "id2label"      : self.id2label,
        }
        with open(os.path.join(output_dir, "dataset_info.json"), "w") as f:
            json.dump(info, f, indent=2)

        logger.info(f"Dataset sauvegardé : {output_dir}")
        logger.info(f"Train      : {info['num_train']}")
        logger.info(f"Validation : {info['num_validation']}")


# ── Main ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    builder      = DatasetBuilder(str(LABEL_SCHEMA))
    samples      = builder.load_annotations()
    logger.info(f"Total samples : {len(samples)}")
    dataset_dict = builder.prepare_for_training(samples)
    builder.save_dataset(dataset_dict, str(OUTPUT_DIR))