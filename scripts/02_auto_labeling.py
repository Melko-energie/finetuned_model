# #!/usr/bin/env python3
# """
# Auto-labeling script using regex patterns to create initial annotations
# """

# import os
# import json
# import re
# from typing import List, Dict, Any
# import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# class AutoLabeler:
#     def __init__(self, label_schema_path: str):
#         with open(label_schema_path, 'r', encoding='utf-8') as f:  # FIXED: added encoding
#             self.label_schema = json.load(f)
        
#         # Define regex patterns for YOUR field types (customize these)
#         self.patterns = {
#             "DATE_FACTURE": [
#                 r'\b\d{2}/\d{2}/\d{4}\b',  # 31/08/2022
#                 r'\b\d{2}-\d{2}-\d{4}\b',
#                 r'\bDATE\s*:?\s*\d{2}/\d{2}/\d{4}\b',
#             ],
#             "MONTANT_HT": [
#                 r'\b\d+[,.]\d{2}\s*€\b',  # 167,00 €
#                 r'\b\d+[,.]\d{2}\s*EUR\b',
#                 r'\b(?:montant|total|HT)\s*:?\s*\d+[,.]\d{2}\b',
#             ],
#             "TAUX_TVA": [
#                 r'\bTVA\s*:?\s*\d+[,.]?\d*%\b',  # TVA 5,50%
#                 r'\b\d+[,.]?\d*%\s*(?:TVA|T\.V\.A\.)\b',
#             ],
#             "CODE_POSTAL": [
#                 r'\b\d{5}\b',  # 80000, 80290
#                 r'\b-\d{5}\b',
#             ],
#             "NUMERO_FACTURE": [
#                 r'\bFACTURE\s*[N°]?\s*[A-Z0-9\-/]+\b',
#                 r'\b(?:N°|num\.?|ref\.?)\s*[A-Z0-9\-/]+\b',
#             ]
#         }
        
#         # Compile all patterns
#         self.compiled_patterns = {}
#         for label, pattern_list in self.patterns.items():
#             self.compiled_patterns[label] = [re.compile(p, re.IGNORECASE) for p in pattern_list]
    
#     def find_matches(self, text: str) -> List[Dict[str, Any]]:
#         """Find all regex matches in text"""
#         matches = []
        
#         for label, patterns in self.compiled_patterns.items():
#             for pattern in patterns:
#                 for match in pattern.finditer(text):
#                     matches.append({
#                         "label": f"B-{label}",  # ADD B- prefix!
#                         "text": match.group(),
#                         "start": match.start(),
#                         "end": match.end(),
#                         "confidence": 0.9  # High confidence for regex matches
#                     })
        
#         return matches
    
#     def label_ocr_data(self, ocr_data: Dict) -> List[Dict]:
#         """Label OCR data using regex patterns"""
#         annotations = []
        
#         for page_num, page_words in enumerate(ocr_data.get("pages", [])):
#             # Combine words into full page text for regex matching
#             page_text = " ".join([word["text"] for word in page_words])
            
#             # Find matches in page text
#             matches = self.find_matches(page_text)
            
#             # Create annotation objects
#             for match in matches:
#                 # Find which word(s) contain this match
#                 matched_words = []
#                 current_pos = 0
                
#                 for word_idx, word in enumerate(page_words):
#                     word_start = page_text.find(word["text"], current_pos)
#                     if word_start == -1:
#                         continue
                    
#                     word_end = word_start + len(word["text"])
                    
#                     # Check if word overlaps with match
#                     if not (word_end <= match["start"] or word_start >= match["end"]):
#                         matched_words.append({
#                             "word_idx": word_idx,
#                             "word": word["text"],
#                             "bbox": word["bbox"]
#                         })
                    
#                     current_pos = word_end
                
#                 if matched_words:
#                     annotation = {
#                         "id": f"auto_{page_num}_{len(annotations)}",
#                         "type": "labels",
#                         "value": {
#                             "start": match["start"],
#                             "end": match["end"],
#                             "text": match["text"],
#                             "labels": [match["label"]]
#                         },
#                         "origin": "auto",
#                         "to_name": "text",
#                         "from_name": "label",
#                         "page": page_num,
#                         "words": matched_words,
#                         "confidence": match["confidence"]
#                     }
#                     annotations.append(annotation)
        
#         return annotations
    
#     def process_file(self, ocr_file_path: str, output_dir: str):
#         """Process a single OCR file"""
#         with open(ocr_file_path, 'r', encoding='utf-8') as f:  # FIXED: added encoding
#             ocr_data = json.load(f)
        
#         # Generate auto annotations
#         annotations = self.label_ocr_data(ocr_data)
        
#         # Create Label Studio format
#         ls_annotation = {
#             "data": {
#                 "text": " ".join([word["text"] for page in ocr_data["pages"] for word in page]),
#                 "pdf_filename": ocr_data["filename"]
#             },
#             "annotations": [{
#                 "result": annotations,
#                 "was_cancelled": False,
#                 "ground_truth": False,
#                 "created_at": "auto_generated",
#                 "updated_at": "auto_generated",
#                 "lead_time": 0
#             }],
#             "predictions": []
#         }
        
#         # Save to output directory
#         base_name = os.path.splitext(os.path.basename(ocr_file_path))[0]
#         output_path = os.path.join(output_dir, f"{base_name}.json")
        
#         with open(output_path, 'w', encoding='utf-8') as f:  # FIXED: added encoding
#             json.dump(ls_annotation, f, ensure_ascii=False, indent=2)  # FIXED: added ensure_ascii=False
        
#         logger.info(f"Auto-labeled {ocr_file_path}: {len(annotations)} annotations")
#         return len(annotations)
    
#     def process_all(self, ocr_dir: str, output_dir: str):
#         """Process all OCR files in directory"""
#         os.makedirs(output_dir, exist_ok=True)
        
#         ocr_files = []
#         for root, dirs, files in os.walk(ocr_dir):
#             for file in files:
#                 if file.endswith('.json'):
#                     rel_path = os.path.relpath(os.path.join(root, file), ocr_dir)
#                     ocr_files.append(rel_path)
        
#         total_annotations = 0
#         for ocr_file in ocr_files:
#             ocr_path = os.path.join(ocr_dir, ocr_file)
#             annotations_count = self.process_file(ocr_path, output_dir)
#             total_annotations += annotations_count
        
#         logger.info(f"Total auto-generated annotations: {total_annotations}")

# if __name__ == "__main__":
#     import os
#     # Get the directory where this script is located
#     SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
#     PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    
#     # Configuration - Use absolute paths
#     OCR_DIR = os.path.join(PROJECT_ROOT, "data", "ocr_texts")
#     ANNOTATIONS_DIR = os.path.join(PROJECT_ROOT, "data", "annotations")
#     LABEL_SCHEMA = os.path.join(PROJECT_ROOT, "data", "label_schema.json")
    
#     print(f"Looking for OCR files in: {OCR_DIR}")
#     print(f"Output will go to: {ANNOTATIONS_DIR}")
#     print(f"Label schema: {LABEL_SCHEMA}")
    
#     # Check if directories exist
#     if not os.path.exists(OCR_DIR):
#         print(f"ERROR: OCR directory not found: {OCR_DIR}")
#         print("Did you run 01_ocr_extraction.py first?")
#         exit(1)
    
#     if not os.path.exists(LABEL_SCHEMA):
#         print(f"ERROR: Label schema not found: {LABEL_SCHEMA}")
#         print("Create data/label_schema.json first")
#         exit(1)
    
#     labeler = AutoLabeler(LABEL_SCHEMA)
#     labeler.process_all(OCR_DIR, ANNOTATIONS_DIR)


# # #!/usr/bin/env python3
# # """
# # Auto-labeling v3: token-based, anchor-based, layout-aware

# # - Works directly on OCR tokens (no flatten-then-regex hack)
# # - Uses simple heuristics and anchors tuned for French invoices
# # - Produces Label Studio-style JSON with word_idx + bbox per entity
# # """

# # import os
# # import json
# # import re
# # from typing import List, Dict, Any, Tuple
# # from pathlib import Path
# # import logging

# # logging.basicConfig(level=logging.INFO)
# # logger = logging.getLogger(__name__)


# # # ----------------------------
# # # Helpers
# # # ----------------------------

# # def is_number_token(text: str) -> bool:
# #     return bool(re.fullmatch(r"\d+[.,]\d{2}", text))


# # def is_percent_token(text: str) -> bool:
# #     return bool(re.fullmatch(r"\d+[.,]?\d*%", text))


# # def looks_like_date(text: str) -> bool:
# #     return bool(re.fullmatch(r"\d{2}[\/\-.]\d{2}[\/\-.]\d{4}", text))


# # def is_postal_code(text: str) -> bool:
# #     return bool(re.fullmatch(r"\d{5}", text))


# # def normalize_str(s: str) -> str:
# #     return s.lower().strip()


# # def group_lines_by_y(tokens: List[Dict[str, Any]], y_threshold: int = 10) -> Dict[int, List[int]]:
# #     """
# #     Group tokens into lines using bbox top y-coordinate.

# #     Returns: dict line_id -> list of token indices (in tokens list)
# #     """
# #     # tokens already in reading order (ocr output order)
# #     if not tokens:
# #         return {}

# #     # attach original index
# #     enriched = [
# #         (i, t, t.get("bbox", [0, 0, 0, 0])[1])  # (idx, token, y_top)
# #         for i, t in enumerate(tokens)
# #     ]
# #     # sort by y, then x-ish (bbox[0])
# #     enriched.sort(key=lambda x: (x[2], x[1].get("bbox", [0, 0, 0, 0])[0]))

# #     lines: Dict[int, List[int]] = {}
# #     current_line_id = 0
# #     last_y = enriched[0][2]
# #     lines[current_line_id] = []

# #     for idx, tok, y in enriched:
# #         if abs(y - last_y) > y_threshold:
# #             current_line_id += 1
# #             lines[current_line_id] = []
# #         lines[current_line_id].append(idx)
# #         last_y = y

# #     return lines


# # # ----------------------------
# # # Detector functions
# # # ----------------------------

# # def detect_code_postal_and_commune(
# #     tokens: List[Dict[str, Any]],
# #     lines: Dict[int, List[int]],
# # ) -> List[Dict[str, Any]]:
# #     """
# #     Detect CODE_POSTAL and COMMUNE based on pattern: 5-digit code followed by city token on same line.
# #     """
# #     instances: List[Dict[str, Any]] = []

# #     for line_id, token_indices in lines.items():
# #         for pos, ti in enumerate(token_indices):
# #             tok = tokens[ti]
# #             text = tok["text"]

# #             if is_postal_code(text):
# #                 # CODE_POSTAL
# #                 instances.append({
# #                     "label": "CODE_POSTAL",
# #                     "word_indices": [ti]
# #                 })

# #                 # Try COMMUNE = next token on same line if alphabetic
# #                 if pos + 1 < len(token_indices):
# #                     next_tok = tokens[token_indices[pos + 1]]
# #                     if re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ\-]+", next_tok["text"]):
# #                         instances.append({
# #                             "label": "COMMUNE",
# #                             "word_indices": [token_indices[pos + 1]]
# #                         })

# #     return instances


# # def detect_date_facture(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
# #     """
# #     Pick the most plausible DATE_FACTURE:
# #     - Prefer dates near 'date', 'facture', 'facturation'
# #     - Fallback to first date in document
# #     """
# #     instances: List[Dict[str, Any]] = []

# #     # collect all date candidates
# #     date_candidates: List[Tuple[int, str]] = []
# #     for i, tok in enumerate(tokens):
# #         if looks_like_date(tok["text"]):
# #             date_candidates.append((i, tok["text"]))

# #     if not date_candidates:
# #         return instances

# #     # anchor words
# #     anchor_indices = []
# #     for i, tok in enumerate(tokens):
# #         t = normalize_str(tok["text"])
# #         if t in {"date", "facture", "facturation", "émission", "emission"}:
# #             anchor_indices.append(i)

# #     # if anchors exist, pick date closest to any anchor
# #     if anchor_indices:
# #         best_pair = None
# #         best_dist = 9999
# #         for di, _ in date_candidates:
# #             for ai in anchor_indices:
# #                 d = abs(di - ai)
# #                 if d < best_dist:
# #                     best_dist = d
# #                     best_pair = di
# #         if best_pair is not None:
# #             instances.append({
# #                 "label": "DATE_FACTURE",
# #                 "word_indices": [best_pair]
# #             })
# #     else:
# #         # fallback: first date
# #         di, _ = date_candidates[0]
# #         instances.append({
# #             "label": "DATE_FACTURE",
# #             "word_indices": [di]
# #         })

# #     return instances


# # def detect_numero_facture(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
# #     """
# #     Detect NUMERO_FACTURE using anchor tokens like 'Facture', 'Avoir', 'N°'.

# #     Heuristic:
# #     - when seeing 'Facture' or 'Avoir' followed nearby by 'N°', grab the next numeric-like tokens
# #     - or when 'N°' + long digit/slash/hyphen token appears, assume invoice number
# #     """
# #     instances: List[Dict[str, Any]] = []

# #     n = len(tokens)
# #     used_indices = set()

# #     for i, tok in enumerate(tokens):
# #         t = normalize_str(tok["text"])

# #         # Pattern 1: 'Facture' ... 'N°' ... [invoice]
# #         if t.startswith("facture") or t.startswith("avoir"):
# #             # look ahead within small window
# #             for j in range(i + 1, min(i + 7, n)):
# #                 tj = normalize_str(tokens[j]["text"])
# #                 if tj in {"n°", "n", "nº", "no"}:
# #                     # candidate invoice tokens after j
# #                     k = j + 1
# #                     word_indices = []
# #                     while k < n:
# #                         tk = tokens[k]["text"]
# #                         if re.fullmatch(r"[A-Za-z0-9\-_/]+", tk) and len(tk) >= 4:
# #                             word_indices.append(k)
# #                             k += 1
# #                         else:
# #                             break
# #                     if word_indices:
# #                         # avoid duplicates
# #                         if not any(idx in used_indices for idx in word_indices):
# #                             instances.append({
# #                                 "label": "NUMERO_FACTURE",
# #                                 "word_indices": word_indices
# #                             })
# #                             used_indices.update(word_indices)
# #                     break  # stop scanning j for this i

# #         # Pattern 2: isolated 'N°' with strong ID after
# #         if t in {"n°", "n", "nº", "no"}:
# #             j = i + 1
# #             word_indices = []
# #             while j < n:
# #                 tj = tokens[j]["text"]
# #                 if re.fullmatch(r"[A-Za-z0-9\-_/]+", tj) and len(tj) >= 6:
# #                     word_indices.append(j)
# #                     j += 1
# #                 else:
# #                     break
# #             if word_indices and not any(idx in used_indices for idx in word_indices):
# #                 instances.append({
# #                     "label": "NUMERO_FACTURE",
# #                     "word_indices": word_indices
# #                 })
# #                 used_indices.update(word_indices)

# #     return instances


# # def detect_montant_ht(tokens: List[Dict[str, Any]], lines: Dict[int, List[int]]) -> List[Dict[str, Any]]:
# #     """
# #     Detect MONTANT_HT with anchor tokens like 'Montant', 'Total', 'HT'.
# #     Prefers amounts on same line as 'Montant HT' or 'Total HT'.
# #     """
# #     instances: List[Dict[str, Any]] = []

# #     # map token index -> line_id
# #     token_to_line = {}
# #     for line_id, idxs in lines.items():
# #         for ti in idxs:
# #             token_to_line[ti] = line_id

# #     for line_id, idxs in lines.items():
# #         # see if line looks like an HT summary line
# #         line_tokens = [normalize_str(tokens[i]["text"]) for i in idxs]
# #         line_str = " ".join(line_tokens)

# #         if any(key in line_str for key in ["montant ht", "total ht", "h.t", "ht :"]):
# #             # search for numeric tokens on this line
# #             word_indices = []
# #             for ti in idxs:
# #                 if is_number_token(tokens[ti]["text"]):
# #                     word_indices.append(ti)
# #             # attach currency if directly after
# #             if word_indices:
# #                 last_idx = word_indices[-1]
# #                 if last_idx + 1 < len(tokens):
# #                     next_text = normalize_str(tokens[last_idx + 1]["text"])
# #                     if next_text in {"€", "eur", "euros"}:
# #                         word_indices.append(last_idx + 1)

# #                 instances.append({
# #                     "label": "MONTANT_HT",
# #                     "word_indices": word_indices
# #                 })

# #     # fallback: pick last amount on page if nothing found
# #     if not instances:
# #         amount_indices = [i for i, tok in enumerate(tokens) if is_number_token(tok["text"])]
# #         if amount_indices:
# #             idx = amount_indices[-1]
# #             word_indices = [idx]
# #             if idx + 1 < len(tokens):
# #                 if normalize_str(tokens[idx + 1]["text"]) in {"€", "eur", "euros"}:
# #                     word_indices.append(idx + 1)
# #             instances.append({
# #                 "label": "MONTANT_HT",
# #                 "word_indices": word_indices
# #             })

# #     return instances


# # def detect_taux_tva(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
# #     """
# #     Detect TAUX_TVA using percent tokens near 'TVA'.
# #     """
# #     instances: List[Dict[str, Any]] = []
# #     n = len(tokens)

# #     for i, tok in enumerate(tokens):
# #         if "tva" in normalize_str(tok["text"]):
# #             # look around for percentage tokens
# #             for j in range(max(0, i - 5), min(n, i + 6)):
# #                 if is_percent_token(tokens[j]["text"]):
# #                     instances.append({
# #                         "label": "TAUX_TVA",
# #                         "word_indices": [j]
# #                     })
# #     return instances


# # def detect_taux_retenue_and_rg(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
# #     """
# #     Detect TAUX_RETENUE and RETENUE_GARANTIE using anchors like 'retenue', 'garantie', 'RG'.
# #     """
# #     instances: List[Dict[str, Any]] = []
# #     n = len(tokens)

# #     # TAUX_RETENUE via percent near 'retenue' or 'RG'
# #     for i, tok in enumerate(tokens):
# #         t = normalize_str(tok["text"])
# #         if "retenue" in t or t == "rg":
# #             for j in range(i, min(i + 7, n)):
# #                 if is_percent_token(tokens[j]["text"]):
# #                     instances.append({
# #                         "label": "TAUX_RETENUE",
# #                         "word_indices": [j]
# #                     })
# #                     break

# #     # RETENUE_GARANTIE via amount near 'retenue', 'garantie', 'rg'
# #     for i, tok in enumerate(tokens):
# #         t = normalize_str(tok["text"])
# #         if "retenue" in t or "garantie" in t or t == "rg":
# #             for j in range(i, min(i + 10, n)):
# #                 if is_number_token(tokens[j]["text"]):
# #                     widxs = [j]
# #                     if j + 1 < n and normalize_str(tokens[j + 1]["text"]) in {"€", "eur", "euros"}:
# #                         widxs.append(j + 1)
# #                     instances.append({
# #                         "label": "RETENUE_GARANTIE",
# #                         "word_indices": widxs
# #                     })
# #                     break

# #     return instances


# # def detect_adresse_travaux(tokens: List[Dict[str, Any]], lines: Dict[int, List[int]]) -> List[Dict[str, Any]]:
# #     """
# #     Rough heuristic:
# #     - find line with 'adresse', 'chantier', or 'expédition'
# #     - take that line + possibly next line as ADRESSE_TRAVAUX
# #     """
# #     instances: List[Dict[str, Any]] = []

# #     for line_id, idxs in lines.items():
# #         line_text = " ".join(normalize_str(tokens[i]["text"]) for i in idxs)
# #         if any(key in line_text for key in ["adresse", "chantier", "expédition", "expedition", "travaux"]):
# #             # build address from this line and maybe next line
# #             word_indices = list(idxs)

# #             next_line_id = line_id + 1
# #             if next_line_id in lines:
# #                 # extend with next line if it looks like address (contains digits + letters)
# #                 next_line_tokens = [tokens[i]["text"] for i in lines[next_line_id]]
# #                 next_line_str = " ".join(next_line_tokens)
# #                 if re.search(r"\d", next_line_str) and re.search(r"[A-Za-z]", next_line_str):
# #                     word_indices.extend(lines[next_line_id])

# #             # sort & dedupe
# #             word_indices = sorted(set(word_indices))
# #             instances.append({
# #                 "label": "ADRESSE_TRAVAUX",
# #                 "word_indices": word_indices
# #             })
# #             break  # assume one adresse_travaux per page

# #     return instances


# # def detect_installateur(tokens: List[Dict[str, Any]], lines: Dict[int, List[int]]) -> List[Dict[str, Any]]:
# #     """
# #     Heuristic:
# #     - supplier name is usually near top (first few lines)
# #     - pick the line that contains 'société', 'societe', 'sas', 'sarl', or all-uppercase company name
# #     """
# #     instances: List[Dict[str, Any]] = []

# #     # consider first N lines only (header zone)
# #     header_line_ids = sorted(lines.keys())[:5]

# #     for line_id in header_line_ids:
# #         idxs = lines[line_id]
# #         line_tokens = [tokens[i]["text"] for i in idxs]
# #         line_text_norm = " ".join(normalize_str(t) for t in line_tokens)

# #         if any(key in line_text_norm for key in ["société", "societe", "sas", "sarl", "eurl", "construction"]):
# #             instances.append({
# #                 "label": "INSTALLATEUR",
# #                 "word_indices": idxs
# #             })
# #             break

# #         # fallback: all-caps line
# #         if all(t.isupper() or not re.search(r"[A-Za-z]", t) for t in line_tokens) and len(" ".join(line_tokens)) > 5:
# #             instances.append({
# #                 "label": "INSTALLATEUR",
# #                 "word_indices": idxs
# #             })
# #             break

# #     return instances


# # def detect_detail_travaux(tokens: List[Dict[str, Any]], lines: Dict[int, List[int]]) -> List[Dict[str, Any]]:
# #     """
# #     Very rough:
# #     - find line with 'travaux', 'prestation', 'objet'
# #     - capture that line and maybe next 1–2 lines until amounts section
# #     """
# #     instances: List[Dict[str, Any]] = []

# #     line_ids_sorted = sorted(lines.keys())
# #     n_lines = len(line_ids_sorted)

# #     for idx_l, line_id in enumerate(line_ids_sorted):
# #         idxs = lines[line_id]
# #         line_text_norm = " ".join(normalize_str(tokens[i]["text"]) for i in idxs)
# #         if any(key in line_text_norm for key in ["travaux", "prestation", "objet", "nature des travaux"]):
# #             word_indices = list(idxs)

# #             # optionally extend 1–2 following lines unless they look numeric-heavy (amount tables)
# #             for k in range(1, 3):
# #                 if idx_l + k >= n_lines:
# #                     break
# #                 next_line_id = line_ids_sorted[idx_l + k]
# #                 next_idxs = lines[next_line_id]
# #                 next_line_text = " ".join(tokens[i]["text"] for i in next_idxs)
# #                 # if line has mostly numbers and currency, stop
# #                 if len(re.findall(r"\d", next_line_text)) > len(next_line_text) * 0.4:
# #                     break
# #                 word_indices.extend(next_idxs)

# #             word_indices = sorted(set(word_indices))
# #             instances.append({
# #                 "label": "DETAIL_TRAVAUX",
# #                 "word_indices": word_indices
# #             })
# #             break

# #     return instances


# # # ----------------------------
# # # Main auto-labeler class
# # # ----------------------------

# # class EnhancedAutoLabeler:
# #     def __init__(self, label_schema_path: str):
# #         with open(label_schema_path, "r", encoding="utf-8") as f:
# #             self.label_schema = json.load(f)

# #         # compute allowed base labels (without B-/I-)
# #         self.base_labels = {
# #             lab.split("-", 1)[-1]
# #             for lab in self.label_schema.get("labels", [])
# #             if lab != "O"
# #         }

# #     def label_page(self, page_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
# #         """
# #         Build annotation objects for a single page's tokens.
# #         """
# #         tokens = [{"text": w["text"], "bbox": w.get("bbox", [0, 0, 0, 0])} for w in page_words]
# #         lines = group_lines_by_y(tokens)

# #         # collect field instances from detectors
# #         instances: List[Dict[str, Any]] = []

# #         instances += detect_code_postal_and_commune(tokens, lines)
# #         instances += detect_date_facture(tokens)
# #         instances += detect_numero_facture(tokens)
# #         instances += detect_montant_ht(tokens, lines)
# #         instances += detect_taux_tva(tokens)
# #         instances += detect_taux_retenue_and_rg(tokens)
# #         instances += detect_adresse_travaux(tokens, lines)
# #         instances += detect_installateur(tokens, lines)
# #         instances += detect_detail_travaux(tokens, lines)

# #         # filter invalid labels / empty
# #         cleaned_instances: List[Dict[str, Any]] = []
# #         seen = set()

# #         for inst in instances:
# #             label = inst["label"]
# #             if label not in self.base_labels:
# #                 continue
# #             widxs = sorted(set(inst["word_indices"]))
# #             if not widxs:
# #                 continue
# #             key = (label, tuple(widxs))
# #             if key in seen:
# #                 continue
# #             seen.add(key)
# #             cleaned_instances.append({"label": label, "word_indices": widxs})

# #         # build Label Studio-style annotations
# #         annotations: List[Dict[str, Any]] = []
# #         for i, inst in enumerate(cleaned_instances):
# #             label = inst["label"]
# #             widxs = inst["word_indices"]

# #             words = [
# #                 {
# #                     "word_idx": wi,
# #                     "word": page_words[wi]["text"],
# #                     "bbox": page_words[wi].get("bbox", [0, 0, 0, 0]),
# #                 }
# #                 for wi in widxs
# #             ]
# #             text = " ".join(w["word"] for w in words)

# #             annotation = {
# #                 "id": f"auto_0_{i}",
# #                 "type": "labels",
# #                 "value": {
# #                     "start": 0,
# #                     "end": 0,
# #                     "text": text,
# #                     "labels": [f"B-{label}"],
# #                 },
# #                 "origin": "auto",
# #                 "to_name": "text",
# #                 "from_name": "label",
# #                 "page": 0,  # adjusted by caller
# #                 "words": words,
# #                 "confidence": 0.8,
# #             }
# #             annotations.append(annotation)

# #         return annotations

# #     def label_ocr_data(self, ocr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
# #         """
# #         Process full OCR JSON with multiple pages.
# #         """
# #         all_annotations: List[Dict[str, Any]] = []

# #         for page_num, page_words in enumerate(ocr_data.get("pages", [])):
# #             page_annotations = self.label_page(page_words)
# #             # fix page number in each annotation
# #             for ann in page_annotations:
# #                 ann["page"] = page_num
# #                 ann["id"] = f"auto_{page_num}_{len(all_annotations)}"
# #                 all_annotations.append(ann)

# #         return all_annotations

# #     def process_file(self, ocr_file_path: str, output_dir: str) -> Tuple[int, Dict[str, Any]]:
# #         """
# #         Process a single OCR file and save Label Studio-style annotations.
# #         """
# #         with open(ocr_file_path, "r", encoding="utf-8") as f:
# #             ocr_data = json.load(f)

# #         annotations = self.label_ocr_data(ocr_data)

# #         # label counts for debug
# #         label_counts: Dict[str, int] = {}
# #         for ann in annotations:
# #             base = ann["value"]["labels"][0].replace("B-", "").replace("I-", "")
# #             label_counts[base] = label_counts.get(base, 0) + 1

# #         # build Label Studio doc
# #         ls_annotation = {
# #             "data": {
# #                 "text": " ".join(
# #                     word.get("text", "")
# #                     for page in ocr_data.get("pages", [])
# #                     for word in page
# #                 ),
# #                 "pdf_filename": ocr_data.get("filename", ""),
# #             },
# #             "annotations": [
# #                 {
# #                     "result": annotations,
# #                     "was_cancelled": False,
# #                     "ground_truth": False,
# #                     "created_at": "auto_generated",
# #                     "updated_at": "auto_generated",
# #                     "lead_time": 0,
# #                 }
# #             ],
# #             "predictions": [],
# #         }

# #         out_dir = Path(output_dir)
# #         out_dir.mkdir(parents=True, exist_ok=True)
# #         base_name = Path(ocr_file_path).stem
# #         out_path = out_dir / f"{base_name}.json"

# #         with open(out_path, "w", encoding="utf-8") as f:
# #             json.dump(ls_annotation, f, ensure_ascii=False, indent=2)

# #         stats = {
# #             "file": base_name,
# #             "total_annotations": len(annotations),
# #             "label_counts": label_counts,
# #             "output_path": str(out_path),
# #         }

# #         return len(annotations), stats

# #     def process_all(self, ocr_dir: str, output_dir: str):
# #         """
# #         Process all OCR JSON files recursively under ocr_dir.
# #         """
# #         ocr_dir_path = Path(ocr_dir)
# #         if not ocr_dir_path.exists():
# #             logger.error(f"OCR directory not found: {ocr_dir_path}")
# #             return

# #         ocr_files = list(ocr_dir_path.rglob("*.json"))
# #         if not ocr_files:
# #             logger.error(f"No JSON files found in {ocr_dir_path}")
# #             return

# #         total_annotations = 0
# #         all_stats: List[Dict[str, Any]] = []

# #         for ocr_path in ocr_files:
# #             try:
# #                 count, stats = self.process_file(str(ocr_path), output_dir)
# #                 total_annotations += count
# #                 all_stats.append(stats)
# #                 logger.info(f"Auto-labeled {ocr_path.name}: {count} annotations")
# #                 for label, c in stats["label_counts"].items():
# #                     logger.info(f"  - {label}: {c}")
# #             except Exception as e:
# #                 logger.error(f"Error processing {ocr_path}: {e}")

# #         # summary
# #         logger.info("\n" + "=" * 50)
# #         logger.info("PROCESSING SUMMARY")
# #         logger.info("=" * 50)
# #         logger.info(f"Total files processed: {len(all_stats)}")
# #         logger.info(f"Total annotations generated: {total_annotations}")

# #         total_label_counts: Dict[str, int] = {}
# #         for st in all_stats:
# #             for label, c in st["label_counts"].items():
# #                 total_label_counts[label] = total_label_counts.get(label, 0) + c

# #         logger.info("\nLabel distribution:")
# #         for label, c in sorted(total_label_counts.items()):
# #             logger.info(f"  {label}: {c}")

# #         summary_path = Path(output_dir) / "auto_labeling_summary.json"
# #         summary = {
# #             "total_files": len(all_stats),
# #             "total_annotations": total_annotations,
# #             "label_distribution": total_label_counts,
# #             "file_stats": all_stats,
# #         }

# #         with open(summary_path, "w", encoding="utf-8") as f:
# #             json.dump(summary, f, ensure_ascii=False, indent=2)

# #         logger.info(f"\nSummary saved to: {summary_path}")


# # # ----------------------------
# # # Main entry point
# # # ----------------------------

# # def main():
# #     SCRIPT_DIR = Path(__file__).parent
# #     PROJECT_ROOT = SCRIPT_DIR.parent

# #     OCR_DIR = PROJECT_ROOT / "data" / "ocr_texts"
# #     ANNOTATIONS_DIR = PROJECT_ROOT / "data" / "annotations"
# #     LABEL_SCHEMA = PROJECT_ROOT / "data" / "label_schema.json"

# #     print("Enhanced Auto-Labeler v3 (token + layout aware)")
# #     print("=" * 60)
# #     print(f"Looking for OCR files in: {OCR_DIR}")
# #     print(f"Output will go to:       {ANNOTATIONS_DIR}")
# #     print(f"Label schema:            {LABEL_SCHEMA}")

# #     if not OCR_DIR.exists():
# #         print(f"ERROR: OCR directory not found: {OCR_DIR}")
# #         print("Did you run 01_ocr_extraction.py first?")
# #         raise SystemExit(1)

# #     if not LABEL_SCHEMA.exists():
# #         print(f"ERROR: Label schema not found: {LABEL_SCHEMA}")
# #         print("Create data/label_schema.json first")
# #         raise SystemExit(1)

# #     with open(LABEL_SCHEMA, "r", encoding="utf-8") as f:
# #         schema = json.load(f)

# #     labels = [l for l in schema.get("labels", []) if l != "O"]
# #     print(f"\nWill try to extract {len(labels)} entity tags (BIO total):")
# #     # print base labels only
# #     base_labels = sorted({l.split("-", 1)[-1] for l in labels})
# #     for b in base_labels:
# #         print(f"  - {b}")

# #     labeler = EnhancedAutoLabeler(str(LABEL_SCHEMA))
# #     labeler.process_all(str(OCR_DIR), str(ANNOTATIONS_DIR))


# # if __name__ == "__main__":
# #     main()
# # #!/usr/bin/env python3
# # """
# # Auto-labeling v4: Enhanced token-based, layout-aware with all entity types
# # Combines the best of both versions with improved French invoice detection
# # """

# # import json
# # import re
# # from typing import List, Dict, Any, Tuple, Set
# # from pathlib import Path
# # import logging
# # from collections import defaultdict
# # import sys

# # logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
# # logger = logging.getLogger(__name__)

# # # ----------------------------
# # # Enhanced Helpers
# # # ----------------------------

# # def normalize_french_text(text: str) -> str:
# #     """Normalize French text with common OCR errors"""
# #     text = text.lower().strip()
# #     # Replace French accents and common OCR errors
# #     replacements = {
# #         'à': 'a', 'â': 'a', 'ä': 'a',
# #         'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
# #         'î': 'i', 'ï': 'i',
# #         'ô': 'o', 'ö': 'o',
# #         'ù': 'u', 'û': 'u', 'ü': 'u',
# #         'ç': 'c',
# #         "'": ' ',
# #         '’': ' ',
# #         '°': ' ',
# #     }
# #     for old, new in replacements.items():
# #         text = text.replace(old, new)
# #     return text

# # def is_french_amount(text: str) -> bool:
# #     """Check if text looks like a French monetary amount"""
# #     # Remove spaces and check patterns
# #     cleaned = text.replace(' ', '')
# #     patterns = [
# #         r'^\d{1,3}(?:\d{3})*[.,]\d{2}$',          # 1234,56 or 1.234,56
# #         r'^\d+[.,]\d{2}\s*(?:€|EUR|EUROS)?$',     # 123,45 €
# #         r'^\d+[.,]\d{3}$',                        # Sometimes 3 decimals
# #     ]
# #     return any(re.match(p, cleaned) for p in patterns)

# # def is_percent_token(text: str) -> bool:
# #     """Check if text is a percentage"""
# #     return bool(re.fullmatch(r'\d+[.,]?\d*%', text))

# # def looks_like_date(text: str) -> bool:
# #     """Check if text looks like a date"""
# #     patterns = [
# #         r'^\d{2}[\/\-.]\d{2}[\/\-.]\d{4}$',       # DD/MM/YYYY
# #         r'^\d{2}[\/\-.]\d{2}[\/\-.]\d{2}$',       # DD/MM/YY
# #         r'^\d{1,2}\s+(?:janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc)\w*\s+\d{4}$',  # French month
# #     ]
# #     return any(re.match(p, text, re.IGNORECASE) for p in patterns)

# # def is_french_postal_code(text: str) -> bool:
# #     """Check if text is a valid French postal code"""
# #     if not re.fullmatch(r'\d{5}', text):
# #         return False
# #     # French postal codes start with specific digits
# #     first_two = text[:2]
# #     # Mainland France (01-95 except 20 for Corsica), Overseas (97-98)
# #     return (1 <= int(first_two) <= 95 and first_two != '20') or first_two in ['97', '98']

# # def group_lines_by_y(tokens: List[Dict[str, Any]], y_threshold: int = 10) -> Dict[int, List[int]]:
# #     """Group tokens into lines based on y-coordinate"""
# #     if not tokens:
# #         return {}

# #     # Enrich tokens with index and y position
# #     enriched = [(i, t, t.get("bbox", [0, 0, 0, 0])[1]) for i, t in enumerate(tokens)]
    
# #     # Sort by y, then x
# #     enriched.sort(key=lambda x: (x[2], x[1].get("bbox", [0, 0, 0, 0])[0]))

# #     lines: Dict[int, List[int]] = {}
# #     current_line_id = 0
# #     last_y = enriched[0][2]
# #     lines[current_line_id] = []

# #     for idx, tok, y in enriched:
# #         if abs(y - last_y) > y_threshold:
# #             current_line_id += 1
# #             lines[current_line_id] = []
# #         lines[current_line_id].append(idx)
# #         last_y = y

# #     return lines

# # # ----------------------------
# # # Enhanced Detector Functions
# # # ----------------------------

# # def detect_code_postal_and_commune(
# #     tokens: List[Dict[str, Any]],
# #     lines: Dict[int, List[int]]
# # ) -> List[Dict[str, Any]]:
# #     """Detect French postal codes and communes"""
# #     instances: List[Dict[str, Any]] = []

# #     for line_id, token_indices in lines.items():
# #         for pos, ti in enumerate(token_indices):
# #             tok = tokens[ti]
            
# #             if is_french_postal_code(tok["text"]):
# #                 # CODE_POSTAL
# #                 instances.append({
# #                     "label": "CODE_POSTAL",
# #                     "word_indices": [ti],
# #                     "confidence": 0.95
# #                 })

# #                 # Try COMMUNE after postal code (French format: 75000 PARIS)
# #                 if pos + 1 < len(token_indices):
# #                     next_idx = token_indices[pos + 1]
# #                     next_tok = tokens[next_idx]
# #                     # Check if it looks like a city name
# #                     if (re.match(r'^[A-Z][a-zÀ-ÖØ-öø-ÿ\-\s]+$', next_tok["text"]) and
# #                         len(next_tok["text"]) > 1 and
# #                         not is_french_amount(next_tok["text"])):
# #                         instances.append({
# #                             "label": "COMMUNE",
# #                             "word_indices": [next_idx],
# #                             "confidence": 0.85
# #                         })

# #     return instances

# # def detect_date_facture(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
# #     """Detect invoice date with context awareness"""
# #     instances: List[Dict[str, Any]] = []

# #     # Collect all date candidates
# #     date_candidates: List[Tuple[int, str]] = []
# #     for i, tok in enumerate(tokens):
# #         if looks_like_date(tok["text"]):
# #             date_candidates.append((i, tok["text"]))

# #     if not date_candidates:
# #         return instances

# #     # Find anchor words for date context
# #     anchor_indices = []
# #     date_keywords = {'date', 'facture', 'facturation', 'émission', 'emission', 'du', 'le'}
    
# #     for i, tok in enumerate(tokens):
# #         norm_text = normalize_french_text(tok["text"])
# #         if norm_text in date_keywords:
# #             anchor_indices.append(i)

# #     # If anchors exist, find closest date to any anchor
# #     if anchor_indices:
# #         best_idx = None
# #         best_dist = float('inf')
        
# #         for date_idx, _ in date_candidates:
# #             for anchor_idx in anchor_indices:
# #                 dist = abs(date_idx - anchor_idx)
# #                 if dist < best_dist and dist <= 10:  # Limit search radius
# #                     best_dist = dist
# #                     best_idx = date_idx
        
# #         if best_idx is not None:
# #             instances.append({
# #                 "label": "DATE_FACTURE",
# #                 "word_indices": [best_idx],
# #                 "confidence": 0.9
# #             })
# #     else:
# #         # Fallback: use the first date found
# #         date_idx, _ = date_candidates[0]
# #         instances.append({
# #             "label": "DATE_FACTURE",
# #             "word_indices": [date_idx],
# #             "confidence": 0.7
# #         })

# #     return instances

# # def detect_numero_facture(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
# #     """Detect invoice number with French patterns"""
# #     instances: List[Dict[str, Any]] = []
# #     n = len(tokens)
# #     used_indices: Set[int] = set()

# #     invoice_keywords = {'facture', 'avoir', 'note', 'devis', 'commande'}
# #     number_keywords = {'n°', 'n', 'nº', 'no', 'numéro', 'num', 'réf', 'ref'}

# #     for i, tok in enumerate(tokens):
# #         t = normalize_french_text(tok["text"])

# #         # Pattern 1: Invoice keyword followed by number keyword
# #         if t in invoice_keywords:
# #             for j in range(i + 1, min(i + 8, n)):
# #                 tj = normalize_french_text(tokens[j]["text"])
# #                 if tj in number_keywords:
# #                     # Collect invoice number tokens after number keyword
# #                     k = j + 1
# #                     word_indices = []
# #                     while k < n and len(word_indices) < 3:  # Limit to 3 tokens
# #                         tk_text = tokens[k]["text"]
# #                         # Invoice number patterns: alphanumeric with common separators
# #                         if re.match(r'^[A-Za-z0-9\-_/]+$', tk_text) and len(tk_text) >= 3:
# #                             word_indices.append(k)
# #                             k += 1
# #                         else:
# #                             break
                    
# #                     if word_indices and not any(idx in used_indices for idx in word_indices):
# #                         instances.append({
# #                             "label": "NUMERO_FACTURE",
# #                             "word_indices": word_indices,
# #                             "confidence": 0.9
# #                         })
# #                         used_indices.update(word_indices)
# #                     break

# #         # Pattern 2: Direct number keyword with invoice-like token
# #         if t in number_keywords and i + 1 < n:
# #             next_text = tokens[i + 1]["text"]
# #             if re.match(r'^[A-Za-z0-9\-_/]+$', next_text) and len(next_text) >= 6:
# #                 if i + 1 not in used_indices:
# #                     instances.append({
# #                         "label": "NUMERO_FACTURE",
# #                         "word_indices": [i + 1],
# #                         "confidence": 0.85
# #                     })
# #                     used_indices.add(i + 1)

# #     return instances

# # def detect_montant_ht(tokens: List[Dict[str, Any]], lines: Dict[int, List[int]]) -> List[Dict[str, Any]]:
# #     """Detect HT amounts with French formatting"""
# #     instances: List[Dict[str, Any]] = []

# #     # Map token index to line ID
# #     token_to_line = {}
# #     for line_id, idxs in lines.items():
# #         for ti in idxs:
# #             token_to_line[ti] = line_id

# #     ht_keywords = {'montant', 'total', 'ht', 'h.t', 'net', 'à payer'}
# #     currency_symbols = {'€', 'EUR', 'EUROS'}

# #     for line_id, idxs in lines.items():
# #         line_tokens = [normalize_french_text(tokens[i]["text"]) for i in idxs]
# #         line_str = " ".join(line_tokens)

# #         # Check if line contains HT keywords
# #         if any(keyword in line_str for keyword in ht_keywords):
# #             # Find amounts in this line
# #             amount_indices = []
# #             for ti in idxs:
# #                 if is_french_amount(tokens[ti]["text"]):
# #                     amount_indices.append(ti)
# #                     # Include currency symbol if present
# #                     if ti + 1 in idxs:
# #                         next_text = normalize_french_text(tokens[ti + 1]["text"])
# #                         if next_text in currency_symbols:
# #                             amount_indices.append(ti + 1)

# #             if amount_indices:
# #                 instances.append({
# #                     "label": "MONTANT_HT",
# #                     "word_indices": amount_indices,
# #                     "confidence": 0.95
# #                 })

# #     # Fallback: find the last amount in the document
# #     if not instances:
# #         for i in range(len(tokens) - 1, -1, -1):
# #             if is_french_amount(tokens[i]["text"]):
# #                 amount_indices = [i]
# #                 # Include currency if present
# #                 if i + 1 < len(tokens):
# #                     next_text = normalize_french_text(tokens[i + 1]["text"])
# #                     if next_text in currency_symbols:
# #                         amount_indices.append(i + 1)
                
# #                 instances.append({
# #                     "label": "MONTANT_HT",
# #                     "word_indices": amount_indices,
# #                     "confidence": 0.7
# #                 })
# #                 break

# #     return instances

# # def detect_taux_tva(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
# #     """Detect TVA rate"""
# #     instances: List[Dict[str, Any]] = []
# #     n = len(tokens)
# #     tva_keywords = {'tva', 't.v.a', 'taxe', 'valeur', 'ajoutée'}

# #     for i, tok in enumerate(tokens):
# #         if any(keyword in normalize_french_text(tok["text"]) for keyword in tva_keywords):
# #             # Look for percentage nearby (before or after)
# #             search_start = max(0, i - 3)
# #             search_end = min(n, i + 4)
            
# #             for j in range(search_start, search_end):
# #                 if is_percent_token(tokens[j]["text"]):
# #                     instances.append({
# #                         "label": "TAUX_TVA",
# #                         "word_indices": [j],
# #                         "confidence": 0.9
# #                     })
# #                     break

# #     return instances

# # def detect_taux_retenue(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
# #     """Detect retention rate"""
# #     instances: List[Dict[str, Any]] = []
# #     n = len(tokens)
# #     taux_keywords = {'taux', 'retenue', 'garantie', 'rg'}

# #     for i, tok in enumerate(tokens):
# #         t = normalize_french_text(tok["text"])
# #         if any(keyword in t for keyword in taux_keywords):
# #             # Look for percentage nearby
# #             for j in range(max(0, i - 3), min(n, i + 4)):
# #                 if is_percent_token(tokens[j]["text"]):
# #                     instances.append({
# #                         "label": "TAUX_RETENUE",
# #                         "word_indices": [j],
# #                         "confidence": 0.85
# #                     })
# #                     break

# #     return instances

# # def detect_retenue_garantie(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
# #     """Detect retention guarantee amount"""
# #     instances: List[Dict[str, Any]] = []
# #     n = len(tokens)
# #     rg_keywords = {'retenue', 'garantie', 'rg'}
# #     currency_symbols = {'€', 'EUR', 'EUROS'}

# #     for i, tok in enumerate(tokens):
# #         t = normalize_french_text(tok["text"])
# #         if any(keyword in t for keyword in rg_keywords):
# #             # Look for amount nearby
# #             for j in range(max(0, i - 5), min(n, i + 6)):
# #                 if is_french_amount(tokens[j]["text"]):
# #                     amount_indices = [j]
# #                     # Include currency if present
# #                     if j + 1 < n:
# #                         next_text = normalize_french_text(tokens[j + 1]["text"])
# #                         if next_text in currency_symbols:
# #                             amount_indices.append(j + 1)
                    
# #                     instances.append({
# #                         "label": "RETENUE_GARANTIE",
# #                         "word_indices": amount_indices,
# #                         "confidence": 0.8
# #                     })
# #                     break

# #     return instances

# # def detect_adresse_travaux(tokens: List[Dict[str, Any]], lines: Dict[int, List[int]]) -> List[Dict[str, Any]]:
# #     """Detect work address"""
# #     instances: List[Dict[str, Any]] = []
# #     address_keywords = {'adresse', 'chantier', 'lieu', 'travaux', 'expédition', 'expedition', 'livraison'}

# #     for line_id, idxs in lines.items():
# #         line_text = " ".join(normalize_french_text(tokens[i]["text"]) for i in idxs)
        
# #         if any(keyword in line_text for keyword in address_keywords):
# #             # Collect address lines
# #             address_indices = list(idxs)
            
# #             # Add next line if it looks like address continuation
# #             next_line_id = line_id + 1
# #             if next_line_id in lines:
# #                 next_idxs = lines[next_line_id]
# #                 next_line_tokens = [tokens[i]["text"] for i in next_idxs]
# #                 next_line_str = " ".join(next_line_tokens)
                
# #                 # Check if next line contains address elements
# #                 has_street_number = any(re.match(r'^\d+[A-Za-z]?$', t) for t in next_line_tokens)
# #                 has_postal_code = any(is_french_postal_code(t) for t in next_line_tokens)
# #                 has_street_name = any(re.match(r'^(rue|avenue|boulevard|place|allée|impasse|chemin)', t, re.I) for t in next_line_tokens)
                
# #                 if has_street_number or has_postal_code or has_street_name:
# #                     address_indices.extend(next_idxs)
            
# #             if len(address_indices) >= 2:
# #                 instances.append({
# #                     "label": "ADRESSE_TRAVAUX",
# #                     "word_indices": sorted(set(address_indices)),
# #                     "confidence": 0.75
# #                 })
# #                 break  # Usually only one work address

# #     return instances

# # def detect_installateur(tokens: List[Dict[str, Any]], lines: Dict[int, List[int]]) -> List[Dict[str, Any]]:
# #     """Detect installer/company name"""
# #     instances: List[Dict[str, Any]] = []
    
# #     # Look in first 5 lines (header area)
# #     header_line_ids = sorted(lines.keys())[:5]
# #     company_keywords = {'société', 'sas', 'sarl', 'eurl', 'entreprise', 'societe', 'construction', 'installation'}

# #     for line_id in header_line_ids:
# #         idxs = lines[line_id]
# #         line_tokens = [normalize_french_text(tokens[i]["text"]) for i in idxs]
# #         line_text_norm = " ".join(line_tokens)

# #         # Check for company indicators
# #         has_company_keyword = any(keyword in line_text_norm for keyword in company_keywords)
# #         has_all_caps = all(tokens[i].get("text", "").isupper() for i in idxs if tokens[i].get("text", "").isalpha())
        
# #         if has_company_keyword or (has_all_caps and len(idxs) > 1):
# #             instances.append({
# #                 "label": "INSTALLATEUR",
# #                 "word_indices": idxs,
# #                 "confidence": 0.8 if has_company_keyword else 0.6
# #             })
# #             break

# #     return instances

# # def detect_detail_travaux(tokens: List[Dict[str, Any]], lines: Dict[int, List[int]]) -> List[Dict[str, Any]]:
# #     """Detect work details/description"""
# #     instances: List[Dict[str, Any]] = []
# #     work_keywords = {'travaux', 'prestation', 'service', 'réalisation', 'mission', 'objet', 'description', 'nature'}

# #     line_ids_sorted = sorted(lines.keys())
    
# #     for idx_l, line_id in enumerate(line_ids_sorted):
# #         idxs = lines[line_id]
# #         line_text_norm = " ".join(normalize_french_text(tokens[i]["text"]) for i in idxs)
        
# #         if any(keyword in line_text_norm for keyword in work_keywords):
# #             # Collect description lines
# #             description_indices = list(idxs)
            
# #             # Add following lines until we hit amounts or section break
# #             for k in range(1, 4):  # Look at next 3 lines max
# #                 next_line_idx = idx_l + k
# #                 if next_line_idx >= len(line_ids_sorted):
# #                     break
                    
# #                 next_idxs = lines[line_ids_sorted[next_line_idx]]
# #                 next_line_tokens = [tokens[i]["text"] for i in next_idxs]
# #                 next_line_str = " ".join(next_line_tokens)
                
# #                 # Stop if line contains amounts or section headers
# #                 if (any(is_french_amount(t) for t in next_line_tokens) or
# #                     any(keyword in normalize_french_text(next_line_str) 
# #                         for keyword in ['montant', 'total', 'prix', '€', 'ht', 'tva'])):
# #                     break
                
# #                 description_indices.extend(next_idxs)
            
# #             if len(description_indices) >= 3:  # At least 3 tokens for meaningful description
# #                 instances.append({
# #                     "label": "DETAIL_TRAVAUX",
# #                     "word_indices": sorted(set(description_indices)),
# #                     "confidence": 0.7
# #                 })
# #                 break

# #     return instances

# # # ----------------------------
# # # Main AutoLabeler Class
# # # ----------------------------

# # class EnhancedAutoLabeler:
# #     def __init__(self, label_schema_path: str):
# #         with open(label_schema_path, "r", encoding="utf-8") as f:
# #             self.label_schema = json.load(f)

# #         # Compute allowed base labels (without B-/I-)
# #         self.base_labels = {
# #             lab.split("-", 1)[-1]
# #             for lab in self.label_schema.get("labels", [])
# #             if lab != "O"
# #         }
        
# #         logger.info(f"Loaded {len(self.base_labels)} entity types from schema")

# #     def label_page(self, page_words: List[Dict[str, Any]], page_num: int = 0) -> List[Dict[str, Any]]:
# #         """Build annotation objects for a single page's tokens"""
# #         tokens = [{"text": w["text"], "bbox": w.get("bbox", [0, 0, 0, 0])} for w in page_words]
# #         lines = group_lines_by_y(tokens)

# #         # Collect field instances from detectors
# #         instances: List[Dict[str, Any]] = []

# #         # Run detectors based on available labels
# #         if "CODE_POSTAL" in self.base_labels or "COMMUNE" in self.base_labels:
# #             instances.extend(detect_code_postal_and_commune(tokens, lines))
        
# #         if "DATE_FACTURE" in self.base_labels:
# #             instances.extend(detect_date_facture(tokens))
        
# #         if "NUMERO_FACTURE" in self.base_labels:
# #             instances.extend(detect_numero_facture(tokens))
        
# #         if "MONTANT_HT" in self.base_labels:
# #             instances.extend(detect_montant_ht(tokens, lines))
        
# #         if "TAUX_TVA" in self.base_labels:
# #             instances.extend(detect_taux_tva(tokens))
        
# #         if "TAUX_RETENUE" in self.base_labels:
# #             instances.extend(detect_taux_retenue(tokens))
        
# #         if "RETENUE_GARANTIE" in self.base_labels:
# #             instances.extend(detect_retenue_garantie(tokens))
        
# #         if "ADRESSE_TRAVAUX" in self.base_labels:
# #             instances.extend(detect_adresse_travaux(tokens, lines))
        
# #         if "INSTALLATEUR" in self.base_labels:
# #             instances.extend(detect_installateur(tokens, lines))
        
# #         if "DETAIL_TRAVAUX" in self.base_labels:
# #             instances.extend(detect_detail_travaux(tokens, lines))

# #         # Filter invalid labels and deduplicate
# #         cleaned_instances: List[Dict[str, Any]] = []
# #         seen_indices: Set[int] = set()
        
# #         for inst in instances:
# #             label = inst.get("label", "")
# #             if label not in self.base_labels:
# #                 continue
                
# #             widxs = sorted(set(inst.get("word_indices", [])))
# #             if not widxs:
# #                 continue
                
# #             # Skip if too many indices overlap with already used tokens
# #             overlap = seen_indices.intersection(widxs)
# #             if len(overlap) / len(widxs) > 0.5:  # More than 50% overlap
# #                 continue
                
# #             # Create key for deduplication
# #             key = (label, tuple(widxs))
# #             if key in [(ci["label"], tuple(ci["word_indices"])) for ci in cleaned_instances]:
# #                 continue
                
# #             cleaned_instances.append({
# #                 "label": label,
# #                 "word_indices": widxs,
# #                 "confidence": inst.get("confidence", 0.8)
# #             })
# #             seen_indices.update(widxs)

# #         # Build Label Studio-style annotations
# #         annotations: List[Dict[str, Any]] = []
# #         for i, inst in enumerate(cleaned_instances):
# #             label = inst["label"]
# #             widxs = inst["word_indices"]
# #             confidence = inst.get("confidence", 0.8)

# #             words = [
# #                 {
# #                     "word_idx": wi,
# #                     "word": page_words[wi]["text"],
# #                     "bbox": page_words[wi].get("bbox", [0, 0, 0, 0]),
# #                 }
# #                 for wi in widxs
# #             ]
# #             text = " ".join(w["word"] for w in words)

# #             # Create BIO labels for multi-word entities
# #             if len(widxs) > 1:
# #                 labels = [f"B-{label}"] + [f"I-{label}"] * (len(widxs) - 1)
# #             else:
# #                 labels = [f"B-{label}"]

# #             annotation = {
# #                 "id": f"auto_{page_num}_{i}",
# #                 "type": "labels",
# #                 "value": {
# #                     "start": 0,
# #                     "end": 0,
# #                     "text": text,
# #                     "labels": labels,
# #                 },
# #                 "origin": "auto",
# #                 "to_name": "text",
# #                 "from_name": "label",
# #                 "page": page_num,
# #                 "words": words,
# #                 "confidence": confidence,
# #             }
# #             annotations.append(annotation)

# #         return annotations

# #     def label_ocr_data(self, ocr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
# #         """Process full OCR JSON with multiple pages"""
# #         all_annotations: List[Dict[str, Any]] = []

# #         for page_num, page_words in enumerate(ocr_data.get("pages", [])):
# #             if not page_words:
# #                 continue
                
# #             page_annotations = self.label_page(page_words, page_num)
# #             all_annotations.extend(page_annotations)

# #         return all_annotations

# #     def process_file(self, ocr_file_path: str, output_dir: str) -> Tuple[int, Dict[str, Any]]:
# #         """Process a single OCR file"""
# #         try:
# #             with open(ocr_file_path, "r", encoding="utf-8") as f:
# #                 ocr_data = json.load(f)
# #         except Exception as e:
# #             logger.error(f"Failed to read {ocr_file_path}: {e}")
# #             return 0, {}

# #         annotations = self.label_ocr_data(ocr_data)

# #         # Count annotations by label
# #         label_counts: Dict[str, int] = defaultdict(int)
# #         for ann in annotations:
# #             for label in ann["value"]["labels"]:
# #                 base = label.split("-", 1)[-1]
# #                 label_counts[base] += 1

# #         # Build Label Studio format
# #         ls_annotation = {
# #             "data": {
# #                 "text": " ".join(
# #                     word.get("text", "")
# #                     for page in ocr_data.get("pages", [])
# #                     for word in page
# #                 ),
# #                 "pdf_filename": ocr_data.get("filename", Path(ocr_file_path).name),
# #             },
# #             "annotations": [{
# #                 "result": annotations,
# #                 "was_cancelled": False,
# #                 "ground_truth": False,
# #                 "created_at": "auto_generated",
# #                 "updated_at": "auto_generated",
# #                 "lead_time": 0,
# #             }],
# #             "predictions": [],
# #         }

# #         # Save output
# #         out_dir = Path(output_dir)
# #         out_dir.mkdir(parents=True, exist_ok=True)
# #         base_name = Path(ocr_file_path).stem
# #         out_path = out_dir / f"{base_name}.json"

# #         try:
# #             with open(out_path, "w", encoding="utf-8") as f:
# #                 json.dump(ls_annotation, f, ensure_ascii=False, indent=2)
# #         except Exception as e:
# #             logger.error(f"Failed to write {out_path}: {e}")
# #             return 0, {}

# #         stats = {
# #             "file": base_name,
# #             "total_annotations": len(annotations),
# #             "label_counts": dict(label_counts),
# #             "output_path": str(out_path),
# #         }

# #         return len(annotations), stats

# #     def process_all(self, ocr_dir: str, output_dir: str):
# #         """Process all OCR JSON files"""
# #         ocr_dir_path = Path(ocr_dir)
# #         if not ocr_dir_path.exists():
# #             logger.error(f"OCR directory not found: {ocr_dir_path}")
# #             return

# #         ocr_files = list(ocr_dir_path.rglob("*.json"))
# #         if not ocr_files:
# #             logger.error(f"No JSON files found in {ocr_dir_path}")
# #             return

# #         total_annotations = 0
# #         all_stats: List[Dict[str, Any]] = []
# #         total_label_counts: Dict[str, int] = defaultdict(int)

# #         logger.info(f"Processing {len(ocr_files)} OCR files...")

# #         for ocr_path in ocr_files:
# #             try:
# #                 count, stats = self.process_file(str(ocr_path), output_dir)
# #                 total_annotations += count
# #                 all_stats.append(stats)
                
# #                 # Update total counts
# #                 for label, c in stats["label_counts"].items():
# #                     total_label_counts[label] += c
                
# #                 if count > 0:
# #                     logger.info(f"✓ {ocr_path.name}: {count} annotations")
# #                 else:
# #                     logger.warning(f"⚠ {ocr_path.name}: No annotations found")
                    
# #             except Exception as e:
# #                 logger.error(f"✗ Error processing {ocr_path}: {e}")

# #         # Print summary
# #         logger.info("\n" + "=" * 60)
# #         logger.info("PROCESSING SUMMARY")
# #         logger.info("=" * 60)
# #         logger.info(f"Total files processed: {len(all_stats)}")
# #         logger.info(f"Total annotations generated: {total_annotations}")
        
# #         if total_label_counts:
# #             logger.info("\nLabel distribution:")
# #             for label, count in sorted(total_label_counts.items()):
# #                 percentage = (count / total_annotations * 100) if total_annotations > 0 else 0
# #                 logger.info(f"  {label}: {count} ({percentage:.1f}%)")
# #         else:
# #             logger.info("No annotations generated")

# #         # Save detailed summary
# #         summary_path = Path(output_dir) / "auto_labeling_summary.json"
# #         summary = {
# #             "total_files": len(all_stats),
# #             "total_annotations": total_annotations,
# #             "label_distribution": dict(total_label_counts),
# #             "file_stats": all_stats,
# #         }

# #         try:
# #             with open(summary_path, "w", encoding="utf-8") as f:
# #                 json.dump(summary, f, ensure_ascii=False, indent=2)
# #             logger.info(f"\nSummary saved to: {summary_path}")
# #         except Exception as e:
# #             logger.error(f"Failed to save summary: {e}")

# # # ----------------------------
# # # Main Entry Point
# # # ----------------------------

# # def main():
# #     """Main function with configuration"""
# #     # Determine project structure
# #     SCRIPT_DIR = Path(__file__).parent
# #     PROJECT_ROOT = SCRIPT_DIR.parent
    
# #     # Configuration paths
# #     OCR_DIR = PROJECT_ROOT / "data" / "ocr_texts"
# #     ANNOTATIONS_DIR = PROJECT_ROOT / "data" / "annotations"
# #     LABEL_SCHEMA = PROJECT_ROOT / "data" / "label_schema.json"

# #     print("=" * 60)
# #     print("Enhanced Auto-Labeler v4")
# #     print("Token-based, layout-aware French invoice annotation")
# #     print("=" * 60)
# #     print(f"OCR directory:    {OCR_DIR}")
# #     print(f"Output directory: {ANNOTATIONS_DIR}")
# #     print(f"Label schema:     {LABEL_SCHEMA}")

# #     # Validate paths
# #     if not OCR_DIR.exists():
# #         print(f"\n❌ ERROR: OCR directory not found: {OCR_DIR}")
# #         print("   Did you run 01_ocr_extraction.py first?")
# #         sys.exit(1)

# #     if not LABEL_SCHEMA.exists():
# #         print(f"\n❌ ERROR: Label schema not found: {LABEL_SCHEMA}")
# #         print("   Create data/label_schema.json first")
# #         sys.exit(1)

# #     # Load and display label schema
# #     try:
# #         with open(LABEL_SCHEMA, 'r', encoding='utf-8') as f:
# #             schema = json.load(f)
        
# #         base_labels = sorted({lab.split('-', 1)[-1] for lab in schema.get('labels', []) if lab != 'O'})
# #         print(f"\n📋 Will extract {len(base_labels)} entity types:")
# #         for label in base_labels:
# #             print(f"   • {label}")
# #     except Exception as e:
# #         print(f"\n❌ ERROR: Failed to load label schema: {e}")
# #         sys.exit(1)

# #     # Create and run labeler
# #     print("\n🚀 Starting auto-labeling...")
# #     labeler = EnhancedAutoLabeler(str(LABEL_SCHEMA))
# #     labeler.process_all(str(OCR_DIR), str(ANNOTATIONS_DIR))
    
# #     print("\n✅ Auto-labeling completed!")

# # if __name__ == "__main__":
# #     main()


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
        
        # Define regex patterns for ALL field types in your schema
        self.patterns = {
            "DATE_FACTURE": [
                r'\b\d{2}/\d{2}/\d{4}\b',  # 31/08/2022
                r'\b\d{2}-\d{2}-\d{4}\b',  # 31-08-2022
                r'\b\d{1,2}\s+(?:janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc)\.?\s+\d{4}\b',  # French month names
                r'\b(?:date|le|du|facture)\s*[:.]?\s*\d{2}/\d{2}/\d{4}\b',  # Date with prefix
            ],
            "MONTANT_HT": [
                r'\b\d{1,3}(?:\s?\d{3})*[.,]\d{2}\s*€\b',  # 1 234,56 € or 1.234,56 €
                r'\b\d+[.,]\d{2}\s*EUR\b',  # 1234,56 EUR
                r'\b(?:montant|total|HT|h\.t\.?|net)\s*:?\s*\d{1,3}(?:\s?\d{3})*[.,]\d{2}\b',  # Montant HT: 1 234,56
                r'\b\d+[.,]\d{2}\s*(?:euros|euro|eur|€)\b',  # 123,45 euros
            ],
            "TAUX_TVA": [
                r'\bTVA\s*:?\s*\d+[.,]?\d*%\b',  # TVA: 5,50% or TVA 20%
                r'\b\d+[.,]?\d*%\s*(?:TVA|T\.V\.A\.)\b',  # 20% TVA
                r'\b(?:taux\s+)?TVA\s*:?\s*\d+[.,]?\d*\s*%\b',  # taux TVA: 20%
            ],
            "TAUX_RETENUE": [
                r'\b(?:taux\s+)?retenue\s*:?\s*\d+[.,]?\d*%\b',  # taux retenue: 5%
                r'\b(?:RG|retenue\s+garantie)\s*:?\s*\d+[.,]?\d*%\b',  # RG: 5%
                r'\b\d+[.,]?\d*%\s*(?:retenue|RG)\b',  # 5% retenue
            ],
            "RETENUE_GARANTIE": [
                r'\b(?:retenue|garantie|RG)\s*:?\s*\d{1,3}(?:\s?\d{3})*[.,]\d{2}\s*€\b',  # Retenue: 1 234,56 €
                r'\b\d{1,3}(?:\s?\d{3})*[.,]\d{2}\s*€\s*(?:retenue|garantie)\b',  # 1 234,56 € retenue
                r'\bRG\s*:?\s*\d+[.,]\d{2}\s*€\b',  # RG: 123,45 €
            ],
            "NUMERO_FACTURE": [
                r'\bFACTURE\s*(?:N[°º]?\s*)?[A-Z0-9\-_/]+\b',  # FACTURE N° INV-2023-001
                r'\b(?:Facture|Fact|F)\s*[N°º]?\s*[A-Z0-9\-_/]+\b',  # Facture N°12345
                r'\b(?:N[°º]|numéro|num|ref|réf)\s*:?\s*[A-Z0-9\-_/]+\b',  # N°: INV-2023-001
                r'\b[A-Z]{2,}\d{3,}[A-Z0-9\-_/]*\b',  # Patterns like INV2023001, DEVIS-2023-123
            ],
            "CODE_POSTAL": [
                r'\b\d{5}\b',  # 80000, 75001 (French postal codes)
                r'\b\d{5}\s+[A-ZÀ-ÿ][a-zÀ-ÿ\-]+\b',  # 75001 PARIS
                r'\bCP\s*:?\s*\d{5}\b',  # CP: 80000
            ],
            "COMMUNE": [
                r'(?<=\d{5}\s)[A-ZÀ-ÿ][a-zÀ-ÿ\-]+\b',  # City after postal code: 75001 Paris
                r'\b(?:ville|commune)\s*:?\s*[A-ZÀ-ÿ][a-zÀ-ÿ\-\s]+\b',  # Ville: Amiens
            ],
            "ADRESSE_TRAVAUX": [
                r'\b(?:adresse\s+chantier|chantier|lieu\s+travaux)\s*:?\s*[A-Za-z0-9À-ÿ\-\s,]+\b',  # Adresse chantier: 12 Rue...
                r'\b\d+\s+(?:rue|avenue|boulevard|place|allée|chemin|impasse)\s+[A-Za-zÀ-ÿ\-\s]+\b',  # 12 Rue de la Paix
                r'\b(?:expédition|livraison)\s*:?\s*[A-Za-z0-9À-ÿ\-\s,]+\b',  # Expédition: 12 Rue...
            ],
            "INSTALLATEUR": [
                r'\b(?:société|entreprise|installateur|prestataire)\s*:?\s*[A-Za-zÀ-ÿ\-\s&]+\b',  # Société: DUPONT SA
                r'\b(?:SARL|SAS|EURL|SA|SASU|EI|EIRL|SCI|SELARL|SNC)\s+[A-Za-zÀ-ÿ\-\s&]+\b',  # SARL DUPONT & FILS
                r'\b[A-Z][A-Za-zÀ-ÿ\-]+\s+(?:SARL|SAS|EURL|SA|SASU)\b',  # DUPONT SARL
                r'\b(?:Tél|Tel|Téléphone)\s*:.*\n.*[A-Z][A-Za-zÀ-ÿ\-\s&]+\b',  # Company name near phone number
            ],
            "DETAIL_TRAVAUX": [
                r'\b(?:détail|nature|description)\s+(?:des\s+)?travaux\s*:?\s*[A-Za-zÀ-ÿ0-9\-\s,.;]+\b',  # Détail travaux: Installation...
                r'\b(?:prestation|service|mission)\s*:?\s*[A-Za-zÀ-ÿ0-9\-\s,.;]+\b',  # Prestation: Installation...
                r'\b(?:objet|sujet)\s*:?\s*[A-Za-zÀ-ÿ0-9\-\s,.;]+\b',  # Objet: Installation...
                r'\btravaux\s+(?:de|d[^\s]+)\s+[A-Za-zÀ-ÿ0-9\-\s,.;]{10,}\b',  # Travaux de rénovation...
            ]
        }
        
        # Compile all patterns
        self.compiled_patterns = {}
        for label, pattern_list in self.patterns.items():
            self.compiled_patterns[label] = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in pattern_list]
    
    def find_matches(self, text: str) -> List[Dict[str, Any]]:
        """Find all regex matches in text"""
        matches = []
        
        for label, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    matches.append({
                        "label": label,  # Base label without B-/I- prefix
                        "text": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.9  # High confidence for regex matches
                    })
        
        return matches
    
    def create_bio_labels(self, matched_words: List[Dict], label: str) -> List[str]:
        """Create B-I-O labels for multi-word entities"""
        if len(matched_words) == 1:
            return [f"B-{label}"]
        else:
            return [f"B-{label}"] + [f"I-{label}"] * (len(matched_words) - 1)
    
    def label_ocr_data(self, ocr_data: Dict) -> List[Dict]:
        """Label OCR data using regex patterns"""
        annotations = []
        
        for page_num, page_words in enumerate(ocr_data.get("pages", [])):
            if not page_words:
                continue
                
            # Combine words into full page text for regex matching
            page_text = " ".join([word["text"] for word in page_words])
            
            # Find matches in page text
            matches = self.find_matches(page_text)
            
            # Create annotation objects
            for match in matches:
                # Find which word(s) contain this match
                matched_words = []
                current_pos = 0
                
                for word_idx, word in enumerate(page_words):
                    word_start = page_text.find(word["text"], current_pos)
                    if word_start == -1:
                        continue
                    
                    word_end = word_start + len(word["text"])
                    
                    # Check if word overlaps with match
                    if not (word_end <= match["start"] or word_start >= match["end"]):
                        matched_words.append({
                            "word_idx": word_idx,
                            "word": word["text"],
                            "bbox": word["bbox"]
                        })
                    
                    current_pos = word_end
                
                if matched_words:
                    # Create BIO labels
                    bio_labels = self.create_bio_labels(matched_words, match["label"])
                    
                    # For single-word entities, just use B- label
                    # For multi-word entities, use B- for first, I- for rest
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
        """Process a single OCR file"""
        with open(ocr_file_path, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)
        
        # Generate auto annotations
        annotations = self.label_ocr_data(ocr_data)
        
        # Create Label Studio format
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
        
        # Save to output directory
        base_name = os.path.splitext(os.path.basename(ocr_file_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ls_annotation, f, ensure_ascii=False, indent=2)
        
        # Log statistics
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
        """Process all OCR files in directory"""
        os.makedirs(output_dir, exist_ok=True)
        
        ocr_files = []
        for root, dirs, files in os.walk(ocr_dir):
            for file in files:
                if file.endswith('.json'):
                    rel_path = os.path.relpath(os.path.join(root, file), ocr_dir)
                    ocr_files.append(rel_path)
        
        total_annotations = 0
        label_summary = {}
        
        for ocr_file in ocr_files:
            ocr_path = os.path.join(ocr_dir, ocr_file)
            annotations_count = self.process_file(ocr_path, output_dir)
            total_annotations += annotations_count
        
        logger.info(f"Total auto-generated annotations: {total_annotations}")
        
        # Save summary
        summary_path = os.path.join(output_dir, "auto_labeling_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                "total_files": len(ocr_files),
                "total_annotations": total_annotations,
                "processed_files": ocr_files
            }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import os
    # Get the directory where this script is located
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    
    # Configuration - Use absolute paths
    OCR_DIR = os.path.join(PROJECT_ROOT, "data", "ocr_texts")
    ANNOTATIONS_DIR = os.path.join(PROJECT_ROOT, "data", "annotations")
    LABEL_SCHEMA = os.path.join(PROJECT_ROOT, "data", "label_schema.json")
    
    print(f"Looking for OCR files in: {OCR_DIR}")
    print(f"Output will go to: {ANNOTATIONS_DIR}")
    print(f"Label schema: {LABEL_SCHEMA}")
    
    # Check if directories exist
    if not os.path.exists(OCR_DIR):
        print(f"ERROR: OCR directory not found: {OCR_DIR}")
        print("Did you run 01_ocr_extraction.py first?")
        exit(1)
    
    if not os.path.exists(LABEL_SCHEMA):
        print(f"ERROR: Label schema not found: {LABEL_SCHEMA}")
        print("Create data/label_schema.json first")
        exit(1)
    
    # Verify label schema has all required fields
    with open(LABEL_SCHEMA, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    required_labels = [
        "DATE_FACTURE", "MONTANT_HT", "TAUX_TVA", "TAUX_RETENUE", 
        "RETENUE_GARANTIE", "NUMERO_FACTURE", "CODE_POSTAL", "COMMUNE",
        "ADRESSE_TRAVAUX", "INSTALLATEUR", "DETAIL_TRAVAUX"
    ]
    
    labels_in_schema = [label.replace("B-", "").replace("I-", "") for label in schema.get("labels", []) if label != "O"]
    unique_labels = set(labels_in_schema)
    
    print(f"\nLabels in schema: {sorted(unique_labels)}")
    print(f"Expected labels: {required_labels}")
    
    # Check for missing labels
    missing_labels = [label for label in required_labels if label not in unique_labels]
    if missing_labels:
        print(f"\nWARNING: Missing labels in schema: {missing_labels}")
        print("Some entities may not be labeled correctly.")
    
    labeler = AutoLabeler(LABEL_SCHEMA)
    labeler.process_all(OCR_DIR, ANNOTATIONS_DIR)