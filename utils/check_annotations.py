#!/usr/bin/env python3
"""
Check cleaned annotations against originals
"""

import os
import json
import sys

def compare_annotations(original_dir: str, cleaned_dir: str, filename: str):
    """Compare one file between original and cleaned"""
    
    original_path = os.path.join(original_dir, filename)
    cleaned_path = os.path.join(cleaned_dir, filename)
    
    if not os.path.exists(original_path):
        print(f"❌ Original not found: {original_path}")
        return
    
    if not os.path.exists(cleaned_path):
        print(f"❌ Cleaned not found: {cleaned_path}")
        return
    
    # Load both
    with open(original_path, 'r', encoding='utf-8') as f:
        original = json.load(f)
    
    with open(cleaned_path, 'r', encoding='utf-8') as f:
        cleaned = json.load(f)
    
    print(f"\n{'='*80}")
    print(f"COMPARING: {filename}")
    print('='*80)
    
    # Count annotations
    orig_anns = []
    clean_anns = []
    
    for ann_set in original.get("annotations", []):
        orig_anns.extend(ann_set.get("result", []))
    
    for ann_set in cleaned.get("annotations", []):
        clean_anns.extend(ann_set.get("result", []))
    
    print(f"Original: {len(orig_anns)} annotations")
    print(f"Cleaned:  {len(clean_anns)} annotations")
    print(f"Removed:  {len(orig_anns) - len(clean_anns)} annotations")
    
    # Show what was removed
    print(f"\n{'='*80}")
    print("ANNOTATIONS REMOVED BY CLEANER:")
    print('='*80)
    
    # Find annotations in original but not in cleaned
    orig_keys = set()
    for ann in orig_anns:
        value = ann.get("value", {})
        key = (
            value.get("start", 0),
            value.get("end", 0),
            tuple(value.get("labels", [])),
            ann.get("page", 0)
        )
        orig_keys.add(key)
    
    clean_keys = set()
    for ann in clean_anns:
        value = ann.get("value", {})
        key = (
            value.get("start", 0),
            value.get("end", 0),
            tuple(value.get("labels", [])),
            ann.get("page", 0)
        )
        clean_keys.add(key)
    
    removed_keys = orig_keys - clean_keys
    
    if removed_keys:
        print(f"Found {len(removed_keys)} removed annotations:")
        for i, key in enumerate(list(removed_keys)[:5]):  # Show first 5
            # Find the original annotation
            for ann in orig_anns:
                value = ann.get("value", {})
                ann_key = (
                    value.get("start", 0),
                    value.get("end", 0),
                    tuple(value.get("labels", [])),
                    ann.get("page", 0)
                )
                if ann_key == key:
                    text = value.get("text", "")
                    label = value.get("labels", [""])[0]
                    print(f"  {i+1}. '{text}' [{label}] - REMOVED")
                    break
        if len(removed_keys) > 5:
            print(f"  ... and {len(removed_keys) - 5} more")
    else:
        print("✅ No annotations removed (only normalization applied)")
    
    # Show normalized values
    print(f"\n{'='*80}")
    print("NORMALIZED VALUES:")
    print('='*80)
    
    norm_count = 0
    for ann in clean_anns:
        value = ann.get("value", {})
        if "normalized_text" in value:
            orig_text = value.get("text", "")
            norm_text = value.get("normalized_text", "")
            label = value.get("labels", [""])[0]
            if orig_text != norm_text:
                print(f"  '{orig_text}' → '{norm_text}' [{label}]")
                norm_count += 1
                if norm_count >= 10:  # Limit output
                    print(f"  ... and {len(clean_anns) - norm_count} more")
                    break
    
    if norm_count == 0:
        print("⚠️  No normalized values found (check if normalization rules match your labels)")
    
    # Show sample of kept annotations
    print(f"\n{'='*80}")
    print("SAMPLE OF CLEANED ANNOTATIONS (first 5):")
    print('='*80)
    
    for i, ann in enumerate(clean_anns[:5]):
        value = ann.get("value", {})
        text = value.get("text", "")
        norm_text = value.get("normalized_text", "N/A")
        label = value.get("labels", [""])[0]
        clean_label = value.get("clean_label", "N/A")
        print(f"  {i+1}. Text: '{text}'")
        print(f"     Label: {label} → Clean: {clean_label}")
        print(f"     Normalized: {norm_text}")
        print()

def main():
    """Main function"""
    
    # Get paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    original_dir = os.path.join(project_root, "data", "annotations")
    cleaned_dir = os.path.join(project_root, "data", "annotations_cleaned")
    
    # Check directories exist
    if not os.path.exists(original_dir):
        print(f"❌ Original directory not found: {original_dir}")
        sys.exit(1)
    
    if not os.path.exists(cleaned_dir):
        print(f"❌ Cleaned directory not found: {cleaned_dir}")
        print("Did you run 03_label_cleaner.py?")
        sys.exit(1)
    
    # Get all JSON files
    original_files = [f for f in os.listdir(original_dir) if f.endswith('.json')]
    cleaned_files = [f for f in os.listdir(cleaned_dir) if f.endswith('.json')]
    
    print(f"Original files: {len(original_files)}")
    print(f"Cleaned files:  {len(cleaned_files)}")
    
    if not original_files:
        print("❌ No original annotation files found")
        sys.exit(1)
    
    if not cleaned_files:
        print("❌ No cleaned annotation files found")
        sys.exit(1)
    
    # Check first 3 files
    files_to_check = original_files[:3]
    
    for filename in files_to_check:
        compare_annotations(original_dir, cleaned_dir, filename)
    
    print(f"\n{'='*80}")
    print("SUMMARY:")
    print('='*80)
    print("If the output shows:")
    print("  ✅ Normalization working (dates, amounts formatted)")
    print("  ✅ No valid annotations incorrectly removed")
    print("  ✅ Labels still correct")
    print("Then you can proceed to script 4.")
    print("\nIf you see:")
    print("  ❌ Many annotations removed")
    print("  ❌ Normalization not working")
    print("  ❌ Labels changed incorrectly")
    print("Then we need to fix the cleaner first.")

if __name__ == "__main__":
    main()