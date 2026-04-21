"""Aggregate per-PDF verdicts into per-field and global accuracy metrics."""

from core.config import ALL_FIELD_KEYS


def aggregate(per_pdf: list[dict]) -> dict:
    """Compute per-field counts and global accuracy from a list of per-PDF
    verdict dicts.

    `per_pdf` is a list of `{"filename": str, "verdicts": {field: verdict}, ...}`
    entries — as produced by the runner.

    Returns:
      {
        "per_field": {field: {"match": N, "mismatch": N, "missing": N,
                              "unexpected": N, "total": N, "accuracy": float}},
        "global":    {"match": N, "total": N, "accuracy": float,
                      "accuracy_macro": float},
      }
    """
    per_field = {
        k: {"match": 0, "mismatch": 0, "missing": 0, "unexpected": 0}
        for k in ALL_FIELD_KEYS
    }
    for row in per_pdf:
        for field, verdict in row.get("verdicts", {}).items():
            if field in per_field:
                per_field[field][verdict] = per_field[field].get(verdict, 0) + 1

    # Per-field accuracy
    for field, counts in per_field.items():
        total = counts["match"] + counts["mismatch"] + counts["missing"] + counts["unexpected"]
        counts["total"] = total
        counts["accuracy"] = (counts["match"] / total) if total else 0.0

    # Global micro accuracy (each field-cell counts equally)
    total_cells = sum(c["total"] for c in per_field.values())
    total_match = sum(c["match"] for c in per_field.values())
    micro = (total_match / total_cells) if total_cells else 0.0

    # Global macro accuracy (average of per-field accuracies)
    macro = sum(c["accuracy"] for c in per_field.values()) / max(len(per_field), 1)

    return {
        "per_field": per_field,
        "global": {
            "match": total_match,
            "total": total_cells,
            "accuracy": micro,
            "accuracy_macro": macro,
        },
    }
