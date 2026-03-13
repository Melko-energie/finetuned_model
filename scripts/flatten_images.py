#!/usr/bin/env python3
import os
import shutil

INPUT_DIR  = r"C:\Users\melko\Developer\finetuned_model\data\page_images"
OUTPUT_DIR = r"C:\Users\melko\Developer\finetuned_model\data\images_flat"

os.makedirs(OUTPUT_DIR, exist_ok=True)

copied = 0
for root, dirs, files in os.walk(INPUT_DIR):
    for file in files:
        if file.lower().endswith('.png'):
            src = os.path.join(root, file)
            dst = os.path.join(OUTPUT_DIR, file)
            shutil.copy2(src, dst)
            copied += 1
            print(f"✅ {file}")

print(f"\nTotal copié : {copied} images dans {OUTPUT_DIR}")