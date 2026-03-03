#!/usr/bin/env python3
"""
Clean and normalize labels from annotations
"""

import os
import json
import re
import sys
from typing import Dict, List, Any, Optional
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LabelCleaner:
    def __init__(self, label_schema_path: str):
        if not os.path.exists(label_schema_path):
            logger.error(f"Label schema not found: {label_schema_path}")
            raise FileNotFoundError(f"Label schema not found: {label_schema_path}")
        
        with open(label_schema_path, 'r', encoding='utf-8') as f:
            self.label_schema = json.load(f)
        
        # Extract label mappings from schema
        self.label2id = self.label_schema["label2id"]
        self.id2label = self.label_schema["id2label"]
        
        # Extract base labels (without B-/I- prefix)
        self.base_labels = set()
        for label in self.label_schema["labels"]:
            if label != "O":
                if label.startswith(('B-', 'I-')):
                    self.base_labels.add(label[2:])
                else:
                    self.base_labels.add(label)
        
        logger.info(f"Loaded {len(self.label2id)} labels: {list(self.base_labels)}")
        
        # Normalization rules for YOUR specific labels
        self.normalization_rules = {
            "DATE_FACTURE": self.normalize_date,
            "MONTANT_HT": self.normalize_amount,
            "TAUX_TVA": self.normalize_percentage,
            "TAUX_RETENUE": self.normalize_percentage,
            "RETENUE_GARANTIE": self.normalize_amount,
            "NUMERO_FACTURE": self.normalize_reference,
            "CODE_POSTAL": self.normalize_postal_code,
            "COMMUNE": self.normalize_commune,
            "ADRESSE_TRAVAUX": self.normalize_address,
            "INSTALLATEUR": self.normalize_installer,
            "DETAIL_TRAVAUX": self.normalize_details,
        }
    
    def normalize_date(self, date_str: str) -> str:
        """Normalize date to YYYY-MM-DD format"""
        try:
            date_str = str(date_str).strip()
            
            # Remove common date prefixes
            date_str = re.sub(r'^(DATE|LE|DU|AU|FACTURE|ÉMISE)\s*[:.]?\s*', '', date_str, flags=re.IGNORECASE)
            
            # DD/MM/YYYY or DD-MM-YYYY (most common in French documents)
            date_match = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})', date_str)
            if date_match:
                day, month, year = date_match.groups()
                day = day.zfill(2)
                month = month.zfill(2)
                if len(year) == 2:
                    # Assume 21st century for years 00-50
                    year_int = int(year)
                    year = f"20{year}" if year_int < 50 else f"19{year}"
                return f"{year}-{month}-{day}"
            
            # Already YYYY-MM-DD
            if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                return date_str
            
            return date_str
        except Exception as e:
            logger.debug(f"Date normalization failed for '{date_str}': {e}")
            return date_str
    
    def normalize_amount(self, amount_str: str) -> str:
        """Normalize amount to decimal format (EUR)"""
        try:
            amount_str = str(amount_str).strip()
            
            # Extract numeric part (handle French formatting)
            match = re.search(r'([\d\s.,]+)', amount_str.replace('\xa0', ' '))  # Handle non-breaking spaces
            if not match:
                return amount_str
            
            numeric_part = match.group(1)
            
            # Remove spaces
            numeric_part = re.sub(r'\s', '', numeric_part)
            
            # Handle French number formatting (1 234,56 or 1.234,56)
            if ',' in numeric_part:
                # Remove thousand separators if present as dots
                if '.' in numeric_part:
                    # Format like 1.234,56 → remove dots, replace comma with dot
                    numeric_part = numeric_part.replace('.', '').replace(',', '.')
                else:
                    # Format like 1 234,56 or 1234,56
                    # Check if comma is decimal separator
                    parts = numeric_part.split(',')
                    if len(parts) == 2 and len(parts[1]) <= 2:
                        # Likely decimal separator: 1234,56 → 1234.56
                        numeric_part = numeric_part.replace(',', '.')
                    else:
                        # No decimal part or unusual format
                        numeric_part = numeric_part.replace(',', '.')
            
            # Clean up any remaining non-numeric characters except dot
            numeric_part = re.sub(r'[^\d.]', '', numeric_part)
            
            # Try to parse as float
            try:
                return str(float(numeric_part))
            except ValueError:
                return numeric_part
                
        except Exception as e:
            logger.debug(f"Amount normalization failed for '{amount_str}': {e}")
            return amount_str
    
    def normalize_percentage(self, percentage_str: str) -> str:
        """Normalize percentage values"""
        try:
            percentage_str = str(percentage_str).strip()
            
            # Extract percentage value
            match = re.search(r'(\d+[,.]?\d*)', percentage_str)
            if not match:
                return percentage_str
            
            value = match.group(1)
            
            # Replace comma with dot for decimal
            value = value.replace(',', '.')
            
            # Add % sign if not present
            if not value.endswith('%'):
                value = f"{value}%"
            
            return value
        except Exception as e:
            logger.debug(f"Percentage normalization failed: {e}")
            return percentage_str
    
    def normalize_reference(self, ref: str) -> str:
        """Normalize invoice/reference numbers"""
        try:
            ref = str(ref).strip().upper()
            
            # Remove common prefixes
            ref = re.sub(r'^(FACTURE|REF(?:ERENCE)?|NO?|NUM(?:ERO)?|ID)\s*[\.:]?\s*', '', ref, flags=re.IGNORECASE)
            
            # Remove trailing punctuation
            ref = re.sub(r'[.,;:\s]+$', '', ref)
            
            # Ensure it's clean
            ref = re.sub(r'\s+', ' ', ref).strip()
            
            return ref
        except Exception as e:
            logger.debug(f"Reference normalization failed: {e}")
            return ref
    
    def normalize_postal_code(self, code: str) -> str:
        """Normalize French postal codes"""
        try:
            code = str(code).strip()
            
            # Extract 5-digit code
            match = re.search(r'(\d{5})', code)
            if match:
                return match.group(1)
            
            return code
        except Exception as e:
            logger.debug(f"Postal code normalization failed: {e}")
            return code
    
    def normalize_commune(self, commune: str) -> str:
        """Normalize commune names"""
        try:
            commune = str(commune).strip()
            
            # Capitalize properly (French style)
            words = commune.split()
            capitalized_words = []
            for word in words:
                if word.lower() in ['de', 'la', 'le', 'les', 'du', 'des', 'à', 'aux', 'en']:
                    capitalized_words.append(word.lower())
                else:
                    capitalized_words.append(word.capitalize())
            
            return ' '.join(capitalized_words)
        except Exception as e:
            logger.debug(f"Commune normalization failed: {e}")
            return commune
    
    def normalize_address(self, address: str) -> str:
        """Normalize addresses"""
        try:
            address = str(address).strip()
            
            # Clean up extra spaces
            address = re.sub(r'\s+', ' ', address)
            
            # Standardize street types (French)
            replacements = {
                r'\bAV\b': 'AVENUE',
                r'\bBD\b': 'BOULEVARD',
                r'\bRUE\b': 'RUE',
                r'\bCHEMIN\b': 'CHEMIN',
                r'\bIMPASSE\b': 'IMPASSE',
                r'\bPLACE\b': 'PLACE',
                r'\bALLEE\b': 'ALLÉE',
                r'\bSQ\b': 'SQUARE',
                r'\bVILLA\b': 'VILLA',
            }
            
            for pattern, replacement in replacements.items():
                address = re.sub(pattern, replacement, address, flags=re.IGNORECASE)
            
            return address
        except Exception as e:
            logger.debug(f"Address normalization failed: {e}")
            return address
    
    def normalize_installer(self, installer: str) -> str:
        """Normalize installer names"""
        try:
            installer = str(installer).strip()
            
            # Clean up and capitalize properly
            installer = re.sub(r'\s+', ' ', installer)
            
            # For companies, ensure proper casing
            if 'SARL' in installer.upper() or 'SAS' in installer.upper() or 'EURL' in installer.upper():
                parts = installer.split()
                for i, part in enumerate(parts):
                    if part.upper() in ['SARL', 'SAS', 'EURL', 'SA', 'SC']:
                        parts[i] = part.upper()
                    elif len(part) > 2:
                        parts[i] = part.capitalize()
                installer = ' '.join(parts)
            
            return installer
        except Exception as e:
            logger.debug(f"Installer normalization failed: {e}")
            return installer
    
    def normalize_details(self, details: str) -> str:
        """Normalize work details"""
        try:
            details = str(details).strip()
            
            # Clean up extra whitespace
            details = re.sub(r'\s+', ' ', details)
            
            # Remove excessive punctuation
            details = re.sub(r'[.,;:]+$', '', details)
            
            return details
        except Exception as e:
            logger.debug(f"Details normalization failed: {e}")
            return details
    
    def clean_annotation(self, annotation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean a single annotation"""
        try:
            if "value" not in annotation:
                logger.debug("Annotation missing 'value' key")
                return None
            
            value = annotation["value"]
            
            if "labels" not in value:
                logger.debug("Annotation missing 'labels' key")
                return None
            
            labels = value["labels"]
            if not labels:
                logger.debug("Annotation has empty labels list")
                return None
            
            label = labels[0]
            text = value.get("text", "")
            
            # Extract base label (without B-/I- prefix)
            if label.startswith(('B-', 'I-')):
                base_label = label[2:]
            else:
                base_label = label
            
            # Apply normalization if rule exists for this base label
            if base_label in self.normalization_rules:
                normalized_text = self.normalization_rules[base_label](text)
                annotation["value"]["normalized_text"] = normalized_text
            
            # Add clean label (base label without prefix)
            annotation["value"]["clean_label"] = base_label
            
            return annotation
        except Exception as e:
            logger.error(f"Error cleaning annotation: {e}")
            return None
    
    def validate_annotation(self, annotation: Dict[str, Any]) -> bool:
        """Validate annotation quality"""
        try:
            if "value" not in annotation:
                return False
            
            value = annotation["value"]
            
            if "labels" not in value:
                return False
            
            labels = value.get("labels", [])
            if not labels:
                logger.debug("Empty labels in annotation")
                return False
            
            label = labels[0]
            
            # Check if label is in schema
            if label not in self.label2id:
                logger.debug(f"Label '{label}' not in schema. Has {self.label2id.get(label, 'NO')}")
                return False
            
            # Check text if present
            text = value.get("text", "")
            if len(str(text).strip()) == 0:
                logger.debug("Empty text in annotation")
                return False
            
            # Check for required fields
            if "start" not in value or "end" not in value:
                logger.debug("Annotation missing start/end positions")
                return False
            
            # Validate positions
            start = value.get("start", 0)
            end = value.get("end", 0)
            if end <= start:
                logger.debug(f"Invalid position range: {start}-{end}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
    
    def deduplicate_annotations(self, annotations: List[Dict]) -> List[Dict]:
        """Remove duplicate annotations based on position and label"""
        try:
            if not annotations:
                return []
            
            seen = set()
            unique_annotations = []
            
            for ann in annotations:
                if "value" not in ann:
                    continue
                    
                value = ann["value"]
                start = value.get("start", 0)
                end = value.get("end", 0)
                labels = tuple(value.get("labels", []))
                page = ann.get("page", 0)
                
                # Create unique key (position + label)
                key = (start, end, labels, page)
                
                if key not in seen:
                    seen.add(key)
                    unique_annotations.append(ann)
            
            logger.debug(f"Deduplicated: {len(annotations)} -> {len(unique_annotations)}")
            return unique_annotations
        except Exception as e:
            logger.error(f"Deduplication error: {e}")
            return annotations
    
    def process_file(self, annotation_file: str, output_dir: str) -> Dict:
        """Process a single annotation file"""
        stats = defaultdict(int)
        
        try:
            if not os.path.exists(annotation_file):
                logger.error(f"Annotation file not found: {annotation_file}")
                return stats
            
            logger.info(f"Processing: {annotation_file}")
            
            with open(annotation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "annotations" not in data:
                logger.warning(f"No 'annotations' key in {annotation_file}")
                return stats
            
            annotations_list = data.get("annotations", [])
            logger.debug(f"Found {len(annotations_list)} annotation sets")
            
            for annotation_set in annotations_list:
                if "result" not in annotation_set:
                    logger.debug("Annotation set missing 'result' key")
                    continue
                
                results = annotation_set.get("result", [])
                logger.debug(f"Processing {len(results)} annotations")
                
                cleaned_results = []
                for ann in results:
                    stats["total_before"] += 1
                    
                    # Validate
                    if not self.validate_annotation(ann):
                        stats["invalid"] += 1
                        continue
                    
                    # Clean
                    cleaned_ann = self.clean_annotation(ann)
                    if cleaned_ann is None:
                        stats["invalid"] += 1
                        continue
                    
                    cleaned_results.append(cleaned_ann)
                    stats["valid"] += 1
                
                # Deduplicate
                original_count = len(cleaned_results)
                cleaned_results = self.deduplicate_annotations(cleaned_results)
                stats["duplicates_removed"] = original_count - len(cleaned_results)
                stats["final_count"] = len(cleaned_results)
                
                # Update results
                annotation_set["result"] = cleaned_results
            
            # Save cleaned file
            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.basename(annotation_file)
            output_path = os.path.join(output_dir, base_name)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Cleaned {annotation_file}: {stats['valid']} valid, {stats['invalid']} invalid, removed {stats['duplicates_removed']} duplicates")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {annotation_file}: {e}")
        except Exception as e:
            logger.error(f"Error processing {annotation_file}: {e}")
            import traceback
            traceback.print_exc()
        
        return stats
    
    def process_all(self, input_dir: str, output_dir: str):
        """Process all annotation files"""
        if not os.path.exists(input_dir):
            logger.error(f"Input directory not found: {input_dir}")
            return
        
        annotation_files = []
        for root, dirs, files in os.walk(input_dir):
            for f in files:
                if f.endswith('.json'):
                    rel_path = os.path.relpath(os.path.join(root, f), input_dir)
                    annotation_files.append(rel_path)
        
        if not annotation_files:
            logger.warning(f"No JSON files found in {input_dir}")
            return
        
        logger.info(f"Found {len(annotation_files)} annotation files in {input_dir}")
        
        total_stats = defaultdict(int)
        for ann_file in annotation_files:
            ann_path = os.path.join(input_dir, ann_file)
            stats = self.process_file(ann_path, output_dir)
            
            for key, value in stats.items():
                total_stats[key] += value
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("CLEANING SUMMARY")
        logger.info("="*60)
        logger.info(f"Total files processed: {len(annotation_files)}")
        logger.info(f"Total annotations before: {total_stats.get('total_before', 0)}")
        logger.info(f"Valid annotations: {total_stats.get('valid', 0)}")
        logger.info(f"Invalid annotations: {total_stats.get('invalid', 0)}")
        logger.info(f"Duplicates removed: {total_stats.get('duplicates_removed', 0)}")
        logger.info(f"Final annotations: {total_stats.get('final_count', 0)}")
        
        if total_stats.get('total_before', 0) > 0:
            valid_percentage = (total_stats.get('valid', 0) / total_stats.get('total_before', 1)) * 100
            logger.info(f"Validation rate: {valid_percentage:.1f}%")
        
        logger.info("="*60)


if __name__ == "__main__":
    # Get script directory and project root
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    
    # Configuration
    INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "annotations")
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "annotations_cleaned")
    LABEL_SCHEMA = os.path.join(PROJECT_ROOT, "data", "label_schema.json")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Check if input exists
    if not os.path.exists(INPUT_DIR):
        logger.error(f"Input directory not found: {INPUT_DIR}")
        logger.info(f"Did you run 02_auto_labeling.py first?")
        logger.info(f"Expected path: {INPUT_DIR}")
        sys.exit(1)
    
    if not os.path.exists(LABEL_SCHEMA):
        logger.error(f"Label schema not found: {LABEL_SCHEMA}")
        logger.info("Create data/label_schema.json first with your label definitions")
        sys.exit(1)
    
    logger.info(f"Input directory: {INPUT_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Label schema: {LABEL_SCHEMA}")
    
    try:
        cleaner = LabelCleaner(LABEL_SCHEMA)
        cleaner.process_all(INPUT_DIR, OUTPUT_DIR)
        logger.info("✅ Label cleaning completed successfully!")
    except Exception as e:
        logger.error(f"❌ Label cleaning failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)