#!/usr/bin/env python3
import os
import argparse
from pdf2image import convert_from_path
from tqdm import tqdm  # Note: tqdm is imported but not used in current implementation

def shred_pdf(input_path, output_dir, dpi=200):
    """Convert a single PDF into page images inside output_dir"""
    os.makedirs(output_dir, exist_ok=True)
    try:
        # Consider adding PDF validation here
        pages = convert_from_path(input_path, dpi=dpi)
        
        # 🚨 tqdm could be used here for visual progress on large PDFs
        for i, page in enumerate(pages, start=1):
            image_name = f"page_{i:03d}.png"
            image_path = os.path.join(output_dir, image_name)
            page.save(image_path, "PNG")
            
    except Exception as e:
        # 🚨 Consider more specific exception handling
        print(f"[ERROR] Failed to process {input_path}: {e}")

def shred_folder(input_folder, output_folder, dpi=200):
    """Recursively find and convert all PDFs"""
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                # Mirror folder structure under output_folder
                rel_path = os.path.relpath(root, input_folder)
                dest_dir = os.path.join(output_folder, rel_path, os.path.splitext(file)[0])
                print(f"🧩 Shredding: {pdf_path}")
                shred_pdf(pdf_path, dest_dir, dpi)
                # 🚨 Consider adding a success/failure counter

def main():
    parser = argparse.ArgumentParser(
        description="Recursively shred PDFs into per-page PNG images."
    )
    parser.add_argument("input", help="Input folder containing PDFs")
    parser.add_argument("output", help="Output folder for images")
    parser.add_argument("--dpi", type=int, default=200, help="Image DPI (default: 200)")
    
    # 🚨 Consider adding more options:
    # parser.add_argument("--format", choices=["png", "jpg"], default="png")
    # parser.add_argument("--threads", type=int, help="Parallel processing")
    
    args = parser.parse_args()

    # 🚨 Add input validation
    if not os.path.exists(args.input):
        print(f"❌ Input path does not exist: {args.input}")
        return

    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)

    print(f"🚀 Starting PDF shredding...\nInput: {input_path}\nOutput: {output_path}\n")
    shred_folder(input_path, output_path, dpi=args.dpi)
    print("\n✅ Done shredding all PDFs!")

if __name__ == "__main__":
    main()