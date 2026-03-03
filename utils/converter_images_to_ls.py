import os
import json
from pathlib import Path

DATA_DIR = Path("data/images")
OUTPUT = "label_studio_import.json"

def collect_images():
    tasks = []
    
    # Walk through all folders recursively
    for png_path in DATA_DIR.rglob("*.png"):
        # Normalize the path for LS
        task = {
            "data": {
                "image": str(png_path.as_posix())
            },
            "meta": {
                "invoice_id": png_path.parent.name,
                "supplier": png_path.parent.parent.name,
                "page": png_path.stem
            }
        }
        tasks.append(task)

    return tasks


if __name__ == "__main__":
    tasks = collect_images()
    
    print(f"Found {len(tasks)} pages.")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)

    print(f"Label Studio import file generated: {OUTPUT}")
import os
import json
from pathlib import Path

DATA_DIR = Path("data/images")
OUTPUT = "label_studio_import.json"

def collect_images():
    tasks = []
    
    # Walk through all folders recursively
    for png_path in DATA_DIR.rglob("*.png"):
        # Normalize the path for LS
        task = {
            "data": {
                "image": str(png_path.as_posix())
            },
            "meta": {
                "invoice_id": png_path.parent.name,
                "supplier": png_path.parent.parent.name,
                "page": png_path.stem
            }
        }
        tasks.append(task)

    return tasks


if __name__ == "__main__":
    tasks = collect_images()
    
    print(f"Found {len(tasks)} pages.")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)

    print(f"Label Studio import file generated: {OUTPUT}")
