"""CLI for the evaluation pipeline.

Subcommands:
  run   — execute an eval and save the result under data/eval_runs/
  list  — list all saved runs
  diff  — compare two saved runs (IDs, or aliases 'latest' / 'previous')

Examples:
  python scripts/run_eval.py run --pdfs data/echantillon --truth truth.xlsx
  python scripts/run_eval.py run --pdfs X --truth Y --excel report.xlsx --no-save
  python scripts/run_eval.py list
  python scripts/run_eval.py diff previous latest
  python scripts/run_eval.py diff 2026-04-21_170245 latest --limit 30
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.eval.diff import diff_results, render_diff_terminal
from core.eval.excel_report import dump_excel
from core.eval.history import list_runs, load_run, save_run
from core.eval.report import dump_json, render_terminal
from core.eval.runner import run_eval


def cmd_run(args) -> int:
    if not args.pdfs.is_dir():
        print(f"error: --pdfs is not a directory: {args.pdfs}", file=sys.stderr)
        return 1
    if not args.truth.is_file():
        print(f"error: --truth file not found: {args.truth}", file=sys.stderr)
        return 1

    result = run_eval(args.pdfs, args.truth)
    render_terminal(result)

    if args.output:
        dump_json(result, args.output)
        print(f"  JSON dump  : {args.output}")
    if args.excel:
        dump_excel(result, args.excel)
        print(f"  Excel      : {args.excel}")

    if not args.no_save:
        run_dir = save_run(result, run_name=args.run_name)
        print(f"  Saved run  : {run_dir.name}  (at {run_dir})")

    return 0


def cmd_list(args) -> int:
    runs = list_runs()
    if not runs:
        print("No saved runs yet.")
        return 0

    print()
    print("=" * 90)
    print(f"  {'ID':<22}  {'Started (UTC)':<19}  {'Dataset':<30}  {'Micro':>6}  {'Dur.':>5}")
    print("=" * 90)
    for r in runs:
        started = r["started_at"][:19].replace("T", " ") if r["started_at"] else "?"
        acc = f"{r['accuracy_micro']*100:.1f}%"
        dur = f"{r['duration_seconds']:.0f}s"
        pdfs = r["pdfs_dir"]
        if len(pdfs) > 30:
            pdfs = "…" + pdfs[-29:]
        print(f"  {r['id']:<22}  {started:<19}  {pdfs:<30}  {acc:>6}  {dur:>5}")
    print("=" * 90)
    return 0


def cmd_diff(args) -> int:
    try:
        a = load_run(args.run_a)
        b = load_run(args.run_b)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    # Resolve aliases to real IDs for nice display
    a_id = args.run_a
    b_id = args.run_b
    if a_id in ("latest", "previous"):
        runs = list_runs()
        a_id = runs[0]["id"] if a_id == "latest" else runs[1]["id"]
    if b_id in ("latest", "previous"):
        runs = list_runs()
        b_id = runs[0]["id"] if b_id == "latest" else runs[1]["id"]

    diff = diff_results(a, b)
    render_diff_terminal(diff, a_id, b_id, limit=args.limit)
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Evaluate extraction quality against ground truth + manage run history.",
    )
    subs = parser.add_subparsers(dest="cmd", required=True)

    p_run = subs.add_parser("run", help="run a new evaluation")
    p_run.add_argument("--pdfs", type=Path, required=True,
                       help="Directory containing PDFs (scanned recursively).")
    p_run.add_argument("--truth", type=Path, required=True,
                       help="Ground-truth Excel.")
    p_run.add_argument("--output", type=Path, default=None,
                       help="Optional: dump full JSON to this path.")
    p_run.add_argument("--excel", type=Path, default=None,
                       help="Optional: dump colored XLSX report.")
    p_run.add_argument("--no-save", action="store_true",
                       help="Skip saving the run under data/eval_runs/.")
    p_run.add_argument("--run-name", default=None,
                       help="Override the auto timestamp as run ID.")

    subs.add_parser("list", help="list saved runs")

    p_diff = subs.add_parser("diff", help="diff two saved runs")
    p_diff.add_argument("run_a", help="Run ID or 'latest' / 'previous'.")
    p_diff.add_argument("run_b", help="Run ID or 'latest' / 'previous'.")
    p_diff.add_argument("--limit", type=int, default=20,
                        help="Max per-PDF regressions/improvements to display.")

    args = parser.parse_args()

    if args.cmd == "run":
        return cmd_run(args)
    if args.cmd == "list":
        return cmd_list(args)
    if args.cmd == "diff":
        return cmd_diff(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
