"""Render evaluation results to terminal and optionally dump JSON."""

import json
from pathlib import Path

from core.config import ALL_FIELD_KEYS


def render_terminal(result: dict) -> None:
    """Print a human-readable evaluation report."""
    meta = result["meta"]
    metrics = result["metrics"]
    per_field = metrics["per_field"]
    g = metrics["global"]

    print()
    print("=" * 62)
    print(f"  Evaluation Report")
    print("=" * 62)
    print(f"  Dataset     : {meta['pdfs_dir']}")
    print(f"  Ground truth: {meta['truth_file']}")
    print(f"  Matched     : {meta['matched']} PDFs")
    print(f"  Missing     : {meta['missing_on_disk']} (in truth, absent on disk)")
    print(f"  Skipped     : {meta['skipped_no_truth']} (on disk, absent in truth)")
    print(f"  Model       : {meta['model']}")
    print(f"  Duration    : {meta['duration_seconds']:.1f}s")
    print()
    print("  Per-field accuracy:")
    print()
    max_field_len = max(len(k) for k in ALL_FIELD_KEYS)
    for field in ALL_FIELD_KEYS:
        c = per_field[field]
        acc = c["accuracy"]
        bar = _bar(acc, width=10)
        print(f"    {field:<{max_field_len}}  {bar}  {acc*100:5.1f}%   "
              f"({c['match']} ok  / {c['mismatch']} mis / {c['missing']} miss / {c['unexpected']} unex)")
    print()
    print(f"  Global micro accuracy: {g['accuracy']*100:5.1f}%   ({g['match']} / {g['total']} cells)")
    print(f"  Global macro accuracy: {g['accuracy_macro']*100:5.1f}%   (mean of per-field)")
    print("=" * 62)


def _bar(ratio: float, width: int = 10) -> str:
    filled = int(round(ratio * width))
    return "█" * filled + "░" * (width - filled)


def dump_json(result: dict, output_path: Path) -> None:
    """Write full results to JSON (machine-readable, for later diff in 2.5)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
