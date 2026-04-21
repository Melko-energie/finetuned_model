"""Top-level orchestration: load dataset, run extraction on each PDF,
compare against ground truth, aggregate metrics.

Two entry points:
  - iter_run_eval(pdfs_dir, truth_file): generator yielding events
      {type: init | progress | done}. Used by the SSE endpoint (5.4).
  - run_eval(pdfs_dir, truth_file): drains the generator, returns the
      final result dict. Used by the CLI and the non-streaming
      /api/admin/eval endpoint.
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from tqdm import tqdm

from core.config import MODEL_NAME
from core.eval.compare import compare_fields
from core.eval.dataset import index_pdfs, load_ground_truth, match_pdf
from core.eval.metrics import aggregate, aggregate_by_supplier
from core.extraction import extract_smart, process_file_live


def iter_run_eval(pdfs_dir: Path, truth_file: Path) -> Iterator[dict]:
    """Generator version of the eval pipeline.

    Yields dict events:
      {"type": "init",     "total": N, "pdfs_dir": ..., "truth_file": ...}
      {"type": "progress", "index": k, "total": N,
                           "filename": str, "installateur": str|None,
                           "verdicts": dict, "error": str|None}
      {"type": "done",     "result": {meta, per_pdf, metrics, metrics_by_supplier}}

    The final 'done' event carries the same result dict that `run_eval`
    returned before the refactor — no shape change for existing consumers.
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

    total = len(truth_rows)
    yield {
        "type": "init",
        "total": total,
        "pdfs_dir": str(pdfs_dir),
        "truth_file": str(truth_file),
        "skipped_no_truth": len(skipped_no_truth),
    }

    per_pdf = []
    missing_on_disk = 0
    matched = 0

    for idx, row in enumerate(tqdm(truth_rows, desc="Evaluating", unit="pdf"), start=1):
        pdf_path = match_pdf(row["filename"], pdf_index)
        if pdf_path is None:
            tqdm.write(f"  [missing] {row['filename']} not found on disk")
            missing_on_disk += 1
            verdicts = {
                k: "missing" if row["fields"].get(k) else "match"
                for k in row["fields"]
            }
            entry = {
                "filename": row["filename"],
                "pdf_path": None,
                "installateur": None,
                "verdicts": verdicts,
                "extracted": None,
                "expected": row["fields"],
                "error": "not_on_disk",
            }
            per_pdf.append(entry)
            yield {
                "type": "progress",
                "index": idx,
                "total": total,
                "filename": row["filename"],
                "installateur": None,
                "verdicts": verdicts,
                "error": "not_on_disk",
            }
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
        yield {
            "type": "progress",
            "index": idx,
            "total": total,
            "filename": pdf_path.name,
            "installateur": installateur,
            "verdicts": verdicts,
            "error": err,
        }

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
        "metrics_by_supplier": aggregate_by_supplier(per_pdf),
    }
    yield {"type": "done", "result": result}


def run_eval(pdfs_dir: Path, truth_file: Path) -> dict:
    """Drain iter_run_eval and return the final result dict.

    Kept as the stable entry point for the CLI and the non-streaming
    /api/admin/eval endpoint. Shape is unchanged since chantier 2.1.
    """
    final = None
    for event in iter_run_eval(pdfs_dir, truth_file):
        if event["type"] == "done":
            final = event["result"]
    return final


def _extract_one(pdf_path: Path) -> tuple[dict | None, str | None, str | None]:
    """Extract a single PDF. Try pre-computed OCR first, fallback to live DocTR.
    Returns (fields, installateur, error_msg)."""
    try:
        res = extract_smart(pdf_path.name, "Auto-detect")
        if res.get("fields"):
            return res["fields"], res.get("installateur"), None
    except Exception as e:
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
