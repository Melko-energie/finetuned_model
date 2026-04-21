"""Top-level orchestration: load dataset, run extraction on each PDF,
compare against ground truth, aggregate metrics."""

import time
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

from core.config import MODEL_NAME
from core.eval.compare import compare_fields
from core.eval.dataset import index_pdfs, load_ground_truth, match_pdf
from core.eval.metrics import aggregate
from core.extraction import extract_smart, process_file_live


def run_eval(pdfs_dir: Path, truth_file: Path) -> dict:
    """Run the full evaluation pipeline and return a result dict.

    Result shape:
      {
        "meta": {pdfs_dir, truth_file, matched, missing_on_disk,
                 skipped_no_truth, model, started_at, duration_seconds},
        "per_pdf": [{"filename", "pdf_path", "installateur",
                     "verdicts", "extracted", "expected"}, ...],
        "metrics": aggregate(...),
      }
    """
    started = time.perf_counter()
    started_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    truth_rows = load_ground_truth(truth_file)
    pdf_index = index_pdfs(pdfs_dir)

    truth_stems = {Path(r["filename"]).stem.lower() for r in truth_rows}
    disk_stems = set(pdf_index.keys())
    skipped_no_truth = sorted(disk_stems - truth_stems)
    for stem in skipped_no_truth:
        tqdm.write(f"  [skip] {pdf_index[stem].name} not in ground truth")

    per_pdf = []
    missing_on_disk = 0
    matched = 0

    for row in tqdm(truth_rows, desc="Evaluating", unit="pdf"):
        pdf_path = match_pdf(row["filename"], pdf_index)
        if pdf_path is None:
            tqdm.write(f"  [missing] {row['filename']} not found on disk")
            missing_on_disk += 1
            per_pdf.append({
                "filename": row["filename"],
                "pdf_path": None,
                "installateur": None,
                "verdicts": {k: "missing" if row["fields"].get(k) else "match" for k in row["fields"]},
                "extracted": None,
                "expected": row["fields"],
                "error": "not_on_disk",
            })
            continue

        matched += 1
        extracted, installateur, err = _extract_one(pdf_path)
        verdicts = compare_fields(extracted, row["fields"])
        per_pdf.append({
            "filename": pdf_path.name,
            "pdf_path": str(pdf_path),
            "installateur": installateur,
            "verdicts": verdicts,
            "extracted": extracted,
            "expected": row["fields"],
            "error": err,
        })

    duration = time.perf_counter() - started
    result = {
        "meta": {
            "pdfs_dir": str(pdfs_dir),
            "truth_file": str(truth_file),
            "matched": matched,
            "missing_on_disk": missing_on_disk,
            "skipped_no_truth": len(skipped_no_truth),
            "model": MODEL_NAME,
            "started_at": started_iso,
            "duration_seconds": duration,
        },
        "per_pdf": per_pdf,
        "metrics": aggregate(per_pdf),
    }
    return result


def _extract_one(pdf_path: Path) -> tuple[dict | None, str | None, str | None]:
    """Extract a single PDF. Try pre-computed OCR first, fallback to live DocTR.
    Returns (fields, installateur, error_msg)."""
    try:
        res = extract_smart(pdf_path.name, "Auto-detect")
        if res.get("fields"):
            return res["fields"], res.get("installateur"), None
    except Exception as e:
        # Continue to live fallback
        tqdm.write(f"  [warn] pre-computed OCR failed for {pdf_path.name}: {e}")

    try:
        file_bytes = pdf_path.read_bytes()
        suffix = pdf_path.suffix.lower()
        res = process_file_live(file_bytes, suffix, "Auto-detect")
        if res.get("fields"):
            return res["fields"], res.get("installateur"), None
        return None, res.get("installateur"), res.get("error") or "empty extraction"
    except Exception as e:
        return None, None, str(e)
