"""Structured diff between two evaluation runs + terminal renderer."""

from core.config import ALL_FIELD_KEYS


def diff_results(a: dict, b: dict) -> dict:
    """Compute a structured diff between two eval results."""
    a_meta, b_meta = a.get("meta", {}), b.get("meta", {})
    a_global = a.get("metrics", {}).get("global", {})
    b_global = b.get("metrics", {}).get("global", {})
    a_per_field = a.get("metrics", {}).get("per_field", {})
    b_per_field = b.get("metrics", {}).get("per_field", {})
    a_by_sup = a.get("metrics_by_supplier", {}) or {}
    b_by_sup = b.get("metrics_by_supplier", {}) or {}

    # Per-field delta
    per_field = {}
    for field in ALL_FIELD_KEYS:
        a_acc = a_per_field.get(field, {}).get("accuracy", 0.0)
        b_acc = b_per_field.get(field, {}).get("accuracy", 0.0)
        per_field[field] = {"a": a_acc, "b": b_acc, "delta": b_acc - a_acc}

    # Per-supplier delta (intersection only — comparing suppliers that
    # aren't in both runs is misleading)
    shared = sorted(set(a_by_sup.keys()) & set(b_by_sup.keys()))
    per_supplier = {}
    for supplier in shared:
        a_acc = a_by_sup[supplier]["global"]["accuracy"]
        b_acc = b_by_sup[supplier]["global"]["accuracy"]
        per_supplier[supplier] = {
            "n_a": a_by_sup[supplier].get("n_pdfs", 0),
            "n_b": b_by_sup[supplier].get("n_pdfs", 0),
            "a": a_acc,
            "b": b_acc,
            "delta": b_acc - a_acc,
        }

    # Per-PDF verdict changes (only PDFs present in both)
    a_pdfs = {r["filename"]: r.get("verdicts", {}) for r in a.get("per_pdf", [])}
    b_pdfs = {r["filename"]: r.get("verdicts", {}) for r in b.get("per_pdf", [])}
    shared_pdfs = sorted(set(a_pdfs.keys()) & set(b_pdfs.keys()))

    regressions = []
    improvements = []
    for filename in shared_pdfs:
        a_v, b_v = a_pdfs[filename], b_pdfs[filename]
        for field in ALL_FIELD_KEYS:
            va, vb = a_v.get(field), b_v.get(field)
            if va == "match" and vb and vb != "match":
                regressions.append({"filename": filename, "field": field,
                                    "verdict_a": va, "verdict_b": vb})
            elif vb == "match" and va and va != "match":
                improvements.append({"filename": filename, "field": field,
                                     "verdict_a": va, "verdict_b": vb})

    return {
        "meta": {
            "a_started_at": a_meta.get("started_at", ""),
            "b_started_at": b_meta.get("started_at", ""),
            "a_model": a_meta.get("model", ""),
            "b_model": b_meta.get("model", ""),
            "a_dataset": a_meta.get("pdfs_dir", ""),
            "b_dataset": b_meta.get("pdfs_dir", ""),
        },
        "global": {
            "micro": {"a": a_global.get("accuracy", 0.0),
                      "b": b_global.get("accuracy", 0.0),
                      "delta": b_global.get("accuracy", 0.0) - a_global.get("accuracy", 0.0)},
            "macro": {"a": a_global.get("accuracy_macro", 0.0),
                      "b": b_global.get("accuracy_macro", 0.0),
                      "delta": b_global.get("accuracy_macro", 0.0) - a_global.get("accuracy_macro", 0.0)},
        },
        "per_field": per_field,
        "per_supplier": per_supplier,
        "regressions": regressions,
        "improvements": improvements,
    }


def _arrow(delta: float) -> str:
    if delta > 0.05:
        return "↑↑"
    if delta > 0.005:
        return "↑"
    if delta < -0.05:
        return "↓↓"
    if delta < -0.005:
        return "↓"
    return " "


def render_diff_terminal(diff: dict, a_id: str, b_id: str, limit: int = 20) -> None:
    meta = diff["meta"]
    g = diff["global"]

    print()
    print("=" * 66)
    print(f"  Diff: {a_id}  →  {b_id}")
    print("=" * 66)
    print(f"  Model   : {meta['a_model']} → {meta['b_model']}")
    print(f"  Dataset : {meta['a_dataset']}"
          + (" (same)" if meta["a_dataset"] == meta["b_dataset"] else f" → {meta['b_dataset']}"))
    print()
    print("  Global:")
    for kind in ("micro", "macro"):
        v = g[kind]
        print(f"    {kind}   {v['a']*100:5.1f}% → {v['b']*100:5.1f}%   "
              f"({v['delta']*100:+5.1f}pp)  {_arrow(v['delta'])}")

    print()
    print("  Per-field:")
    for field, v in diff["per_field"].items():
        print(f"    {field:<18}  {v['a']*100:5.1f}% → {v['b']*100:5.1f}%   "
              f"({v['delta']*100:+5.1f}pp)  {_arrow(v['delta'])}")

    if diff["per_supplier"]:
        print()
        print("  Per-supplier (shared only):")
        sorted_sup = sorted(diff["per_supplier"].items(), key=lambda kv: kv[1]["delta"])
        for supplier, v in sorted_sup:
            print(f"    {supplier:<20}  {v['a']*100:5.1f}% → {v['b']*100:5.1f}%   "
                  f"({v['delta']*100:+5.1f}pp)  {_arrow(v['delta'])}")

    regs = diff["regressions"]
    imps = diff["improvements"]
    print()
    print(f"  Regressions ({len(regs)} verdicts match → not-match):")
    for r in regs[:limit]:
        print(f"    {r['filename']:<42}  {r['field']:<18}  match → {r['verdict_b']}")
    if len(regs) > limit:
        print(f"    ... and {len(regs) - limit} more")

    print()
    print(f"  Improvements ({len(imps)} verdicts not-match → match):")
    for r in imps[:limit]:
        print(f"    {r['filename']:<42}  {r['field']:<18}  {r['verdict_a']} → match")
    if len(imps) > limit:
        print(f"    ... and {len(imps) - limit} more")

    print("=" * 66)
