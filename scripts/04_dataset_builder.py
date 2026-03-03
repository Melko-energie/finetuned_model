#!/usr/bin/env python3
"""
Convert annotations to HuggingFace dataset format for LayoutLMv3
"""

import os
import json
import torch
from datasets import Dataset, DatasetDict
from transformers import LayoutLMv3Processor
from PIL import Image
import logging
from tqdm import tqdm
from typing import Dict, List, Any, Optional, Tuple  # Add to imports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatasetBuilder:
    def __init__(self, label_schema_path: str, model_name: str = "microsoft/layoutlmv3-base"):
        with open(label_schema_path, 'r') as f:
            self.label_schema = json.load(f)
        
        self.label2id = self.label_schema["label2id"]
        self.id2label = self.label_schema["id2label"]
        
        # Initialize processor
        self.processor = LayoutLMv3Processor.from_pretrained(
            model_name, 
            apply_ocr=False
        )
    
    def load_annotations(self, annotation_dir: str, ocr_dir: str):
        """Load and pair annotations with OCR data"""
        samples = []
        
        annotation_files = [f for f in os.listdir(annotation_dir) if f.endswith('.json')]
        
        for ann_file in tqdm(annotation_files, desc="Loading annotations"):
            # Load annotation
            ann_path = os.path.join(annotation_dir, ann_file)
            with open(ann_path, 'r') as f:
                annotation_data = json.load(f)
            
            # Get corresponding OCR data
            ocr_filename = annotation_data["data"]["pdf_filename"]
            ocr_file = os.path.splitext(ocr_filename)[0] + ".json"
            ocr_path = os.path.join(ocr_dir, ocr_file)
            
            if not os.path.exists(ocr_path):
                logger.warning(f"OCR data not found for {ocr_filename}")
                continue
            
            with open(ocr_path, 'r') as f:
                ocr_data = json.load(f)
            
            # Create sample for each page
            for page_num, page_words in enumerate(ocr_data["pages"]):
                sample = self.create_sample(
                    ocr_data, 
                    annotation_data, 
                    page_num
                )
                if sample:
                    samples.append(sample)
        
        return samples
    
    def create_sample(self, ocr_data: Dict, annotation_data: Dict, page_num: int) -> Dict:
        """Create a single training sample from OCR and annotations"""
        page_words = ocr_data["pages"][page_num]
        
        if not page_words:
            return None
        
        # Extract words and boxes
        words = [word["text"] for word in page_words]
        boxes = [word["bbox"] for word in page_words]
        
        # Initialize all labels as "O"
        labels = ["O"] * len(words)
        
        # Get annotations for this page
        for ann_set in annotation_data.get("annotations", []):
            for ann in ann_set.get("result", []):
                if ann.get("page", 0) != page_num:
                    continue
                
                # Get label
                label = ann["value"]["labels"][0]
                
                # Find which words are in this annotation
                for word_info in ann.get("words", []):
                    word_idx = word_info.get("word_idx")
                    if word_idx is not None and word_idx < len(words):
                        # Check if word matches
                        if words[word_idx] == word_info["word"]:
                            labels[word_idx] = label
        
        # Convert labels to IDs
        label_ids = [self.label2id.get(label, 0) for label in labels]
        
        return {
            "id": f"{ocr_data['filename']}_page{page_num}",
            "words": words,
            "bboxes": boxes,
            "labels": label_ids,
            "page_number": page_num,
            "image_path": self.get_image_path(ocr_data["filename"], page_num)
        }
    
    def get_image_path(self, pdf_filename: str, page_num: int) -> str:
        """Get path to rendered PDF page image"""
        # This assumes you have pre-rendered PDF pages as images
        base_name = os.path.splitext(pdf_filename)[0]
        return f"../data/page_images/{base_name}_page{page_num}.png"
    
    def prepare_for_training(self, samples: List[Dict], split_ratio: float = 0.8):
        """Prepare dataset for training"""
        # Encode samples using LayoutLMv3 processor
        encoded_samples = []
        
        for sample in tqdm(samples, desc="Encoding samples"):
            try:
                # Load image
                image = Image.open(sample["image_path"]).convert("RGB")
                
                # Encode
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
                
                # Convert to dict
                encoded_sample = {
                    "input_ids": encoding["input_ids"].squeeze(),
                    "attention_mask": encoding["attention_mask"].squeeze(),
                    "bbox": encoding["bbox"].squeeze(),
                    "labels": encoding["labels"].squeeze(),
                    "pixel_values": encoding["pixel_values"].squeeze()
                }
                
                encoded_samples.append(encoded_sample)
                
            except Exception as e:
                logger.warning(f"Error encoding sample {sample['id']}: {str(e)}")
                continue
        
        # Create HuggingFace dataset
        dataset = Dataset.from_list(encoded_samples)
        
        # Split
        split_idx = int(len(dataset) * split_ratio)
        train_dataset = dataset.select(range(split_idx))
        eval_dataset = dataset.select(range(split_idx, len(dataset)))
        
        dataset_dict = DatasetDict({
            "train": train_dataset,
            "validation": eval_dataset
        })
        
        return dataset_dict
    
    def save_dataset(self, dataset_dict: DatasetDict, output_dir: str):
        """Save dataset to disk"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save dataset
        dataset_dict.save_to_disk(output_dir)
        
        # Save dataset info
        info = {
            "num_train": len(dataset_dict["train"]),
            "num_validation": len(dataset_dict["validation"]),
            "label2id": self.label2id,
            "id2label": self.id2label
        }
        
        with open(os.path.join(output_dir, "dataset_info.json"), 'w') as f:
            json.dump(info, f, indent=2)
        
        logger.info(f"Dataset saved to {output_dir}")
        logger.info(f"Train samples: {info['num_train']}")
        logger.info(f"Validation samples: {info['num_validation']}")

if __name__ == "__main__":
    # Configuration
    ANNOTATION_DIR = "../data/annotations_cleaned"
    OCR_DIR = "../data/ocr_texts"
    OUTPUT_DIR = "../data/formatted_dataset"
    LABEL_SCHEMA = "../data/label_schema.json"
    
    builder = DatasetBuilder(LABEL_SCHEMA)
    
    # Load and prepare data
    samples = builder.load_annotations(ANNOTATION_DIR, OCR_DIR)
    logger.info(f"Loaded {len(samples)} samples")
    
    # Create dataset
    dataset_dict = builder.prepare_for_training(samples)
    
    # Save dataset
    builder.save_dataset(dataset_dict, OUTPUT_DIR)