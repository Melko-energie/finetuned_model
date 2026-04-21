"""Persist and reload evaluation runs under data/eval_runs/<timestamp>/."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from core.config import DATA_DIR

RUNS_DIR = DATA_DIR / "eval_runs"

_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}$")


def _default_run_name() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")


def save_run(result: dict, run_name: str | None = None) -> Path:
    """Persist a run to data/eval_runs/<run_name>/result.json.

    Returns the run directory path. Caller gets the ID via run_dir.name.
    If run_name collides with an existing run, a numeric suffix is appended.
    """
    name = run_name or _default_run_name()
    target = RUNS_DIR / name
    suffix = 1
    while target.exists():
        suffix += 1
        target = RUNS_DIR / f"{name}-{suffix}"
    target.mkdir(parents=True, exist_ok=True)
    with (target / "result.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    return target


def list_runs() -> list[dict]:
    """Return a list of saved runs sorted newest first.

    Each entry: {"id", "path", "started_at", "pdfs_dir", "model",
                 "duration_seconds", "accuracy_micro", "accuracy_macro"}.
    """
    if not RUNS_DIR.is_dir():
        return []
    items = []
    for d in sorted(RUNS_DIR.iterdir(), reverse=True):
        result_file = d / "result.json"
        if not (d.is_dir() and result_file.exists()):
            continue
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        meta = data.get("meta", {})
        g = data.get("metrics", {}).get("global", {})
        items.append({
            "id": d.name,
            "path": d,
            "started_at": meta.get("started_at", ""),
            "pdfs_dir": meta.get("pdfs_dir", ""),
            "model": meta.get("model", ""),
            "duration_seconds": meta.get("duration_seconds", 0.0),
            "accuracy_micro": g.get("accuracy", 0.0),
            "accuracy_macro": g.get("accuracy_macro", 0.0),
        })
    return items


def load_run(run_id: str) -> dict:
    """Load a run by its ID (folder name) or the alias 'latest' / 'previous'."""
    runs = list_runs()
    if run_id == "latest":
        if not runs:
            raise FileNotFoundError("No saved runs.")
        run_id = runs[0]["id"]
    elif run_id == "previous":
        if len(runs) < 2:
            raise FileNotFoundError("Need at least 2 saved runs to use 'previous'.")
        run_id = runs[1]["id"]

    path = RUNS_DIR / run_id / "result.json"
    if not path.is_file():
        available = ", ".join(r["id"] for r in runs[:10]) or "none"
        raise FileNotFoundError(f"Run '{run_id}' not found. Available: {available}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
