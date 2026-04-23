"""CLI: run the smart extraction pipeline on a few sample PDFs and dump
the per-supplier results to data/test_gemma2_smart_results.json.

Replaces the old `scripts/12_gemma2_smart.py` __main__ block.
"""

import os
import json

from core.config import PDF_DIR, DATA_DIR
from core.detection import detect_installateur, detect_avoir
from core.ocr import get_ocr_text
from core.extraction import extraire_champs
from core.postprocess import inverser_montants_avoir


SAMPLE_PDFS = [
    PDF_DIR / "a2m" / "S1120630_MICROLAD-22AAC00000.PDF",
    PDF_DIR / "esteve" / "S1120318_MICROLAD-22A4924000.PDF",
    PDF_DIR / "ternel" / "S1120317_MICROLAD-22A4925000.PDF",
]


def pipeline(pdf_path):
    print(f"\n{'='*60}\nFacture : {pdf_path.name}")

    texte = get_ocr_text(str(pdf_path))
    if texte is None:
        print("  ERREUR: OCR introuvable")
        return None, "ERREUR", False

    installateur = detect_installateur(texte)
    is_avoir = detect_avoir(texte)
    print(f"  Fournisseur : {installateur}{' (AVOIR)' if is_avoir else ''}")

    result = extraire_champs(texte, installateur)
    if is_avoir and result:
        result = inverser_montants_avoir(result)
    return result, installateur, is_avoir


def main():
    print("=== GEMMA2:9b SMART — extraction CLI ===")

    results = []
    success = 0

    for pdf_path in SAMPLE_PDFS:
        if not pdf_path.exists():
            print(f"\n  SKIP: {pdf_path} introuvable")
            continue

        result, installateur, is_avoir = pipeline(pdf_path)
        if result:
            success += 1
            for k, v in result.items():
                status = "ok" if v and str(v).lower() != "null" else "--"
                print(f"     [{status}] {k}: {v}")
            results.append({
                "facture": pdf_path.name,
                "installateur_detecte": installateur,
                "extraction": result,
            })

    print(f"\n{'='*60}\nRésumé : {success}/{len(SAMPLE_PDFS)} factures extraites")

    total = sum(len(r["extraction"]) for r in results)
    found = sum(1 for r in results for v in r["extraction"].values()
                if v and str(v).lower() != "null")
    if total:
        print(f"Champs non-null : {found}/{total} ({round(found / total * 100)}%)")

    output_path = DATA_DIR / "test_gemma2_smart_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Résultats sauvegardés : {output_path}")


if __name__ == "__main__":
    main()
