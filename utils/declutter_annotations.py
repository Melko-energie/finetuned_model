import json
import os
from pathlib import Path


INPUT_DIR = Path("data/annotations_cleaned")
OUTPUT_DIR = Path("data/simple_annotations")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def simplify_annotation_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pdf_filename = data.get("data", {}).get("pdf_filename", "")
    simplified = {
        "pdf_filename": pdf_filename,
        "annotations": []
    }

    # The labels live under data["annotations"][0]["result"]
    ann_blocks = data.get("annotations", [])
    if not ann_blocks:
        return simplified

    results = ann_blocks[0].get("result", [])

    for r in results:
        value = r.get("value", {})
        raw_labels = value.get("labels", [])

        if not raw_labels:
            continue

        # Remove B- prefix to keep clean label
        clean_label = raw_labels[0].replace("B-", "").replace("I-", "")

        entry = {
            "label": clean_label,
            "page": r.get("page", 0),
            "word_indices": []
        }

        # Preserve EXACT word indices — these are your pointers
        for w in r.get("words", []):
            idx = w.get("word_idx")
            if isinstance(idx, int):
                entry["word_indices"].append(idx)

        # Ignore corrupted / empty annotations
        if entry["word_indices"]:
            simplified["annotations"].append(entry)

    return simplified


def process_all():
    files = list(INPUT_DIR.glob("*.json"))

    if not files:
        print("No cleaned annotations found.")
        return

    for f in files:
        simplified = simplify_annotation_file(f)
        out_path = OUTPUT_DIR / f.name

        with open(out_path, "w", encoding="utf-8") as out:
            json.dump(simplified, out, indent=2, ensure_ascii=False)

        print(f"✓ Simplified {f.name} → {out_path.name}")


if __name__ == "__main__":
    process_all()
    print("\nDone. Your annotations are now pointer-clean and dataset-safe.")
