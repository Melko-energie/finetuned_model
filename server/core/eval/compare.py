"""Field-by-field comparison between extracted and expected values."""

from core.config import ALL_FIELD_KEYS
from core.eval.normalize import normalize


def compare_fields(extracted: dict | None, expected: dict) -> dict[str, str]:
    """Compare each field and return a per-field verdict.

    Verdicts:
      - "match"     : values agree (after normalization), both non-empty or both empty
      - "mismatch"  : both sides have values, but they differ
      - "missing"   : ground truth has a value, extraction doesn't (None/null/"")
      - "unexpected": extraction has a value, ground truth doesn't (rare,
                      still counted as mismatch in aggregate)

    `extracted` may be None (extraction failed entirely) — all fields with a
    non-empty expected value are then "missing".
    """
    verdicts: dict[str, str] = {}
    extracted = extracted or {}
    for key in ALL_FIELD_KEYS:
        exp_raw = expected.get(key)
        ext_raw = extracted.get(key)
        exp = normalize(exp_raw, key)
        ext = normalize(ext_raw, key)

        if exp == "" and ext == "":
            verdicts[key] = "match"  # both empty = trivially correct
        elif exp != "" and ext == "":
            verdicts[key] = "missing"
        elif exp == "" and ext != "":
            verdicts[key] = "unexpected"
        elif exp == ext:
            verdicts[key] = "match"
        else:
            verdicts[key] = "mismatch"
    return verdicts
