"""Value normalization shared by ground truth and extraction outputs.

Level 2.1: basic normalization — strip whitespace, lowercase, remove trailing
punctuation, collapse null-ish tokens to empty string. Date/number smart
normalization is chantier 2.3.
"""

_NULL_TOKENS = {"", "null", "non detecte", "non détecte", "non détectée", "—", "-", "n/a", "na"}


def normalize_basic(value) -> str:
    """Normalize a single cell value for equality comparison.

    None, empty, or known null-ish strings all collapse to "" so that
    missing-on-both-sides compares equal. Anything else is stripped,
    lowercased, and freed of trailing punctuation.
    """
    if value is None:
        return ""
    s = str(value).strip().lower()
    if s in _NULL_TOKENS:
        return ""
    return s.rstrip(".,;")
