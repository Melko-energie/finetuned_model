"""CLI: evaluate extraction quality on a dataset vs a ground-truth Excel.

Example:
    python scripts/run_eval.py --pdfs data/echantillon --truth data/ground_truth.xlsx
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.eval.report import dump_json, render_terminal
from core.eval.runner import run_eval


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate extraction quality against a ground-truth Excel."
    )
    parser.add_argument("--pdfs", type=Path, required=True,
                        help="Directory containing PDFs (scanned recursively).")
    parser.add_argument("--truth", type=Path, required=True,
                        help="Ground-truth Excel (sheet 'Extractions' or 'TOUTES_FACTURES').")
    parser.add_argument("--output", type=Path, default=None,
                        help="Optional: dump full JSON results to this path.")
    args = parser.parse_args()

    if not args.pdfs.is_dir():
        print(f"error: --pdfs is not a directory: {args.pdfs}", file=sys.stderr)
        sys.exit(1)
    if not args.truth.is_file():
        print(f"error: --truth file not found: {args.truth}", file=sys.stderr)
        sys.exit(1)

    result = run_eval(args.pdfs, args.truth)
    render_terminal(result)

    if args.output:
        dump_json(result, args.output)
        print(f"  JSON dump  : {args.output}")


if __name__ == "__main__":
    main()
