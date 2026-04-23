"""Value normalization for evaluation comparisons.

Two levels:
  - normalize_basic(v)              : strip + lowercase + null-token collapse.
  - normalize(v, field_key=None)    : field-aware — picks a specialized
                                      normalizer for dates, numbers,
                                      percentages, or text based on the
                                      FIELD_NORMALIZERS dispatch table.

Specialized normalizers always fall back to normalize_basic on parse
failure, so bad data never crashes the eval pipeline.
"""

import re
import unicodedata
from datetime import date, datetime

from dateutil import parser as dateutil_parser

_NULL_TOKENS = {
    "", "null", "non detecte", "non détecte", "non détectée", "—", "-", "n/a", "na",
}

_FRENCH_MONTHS = {
    "janvier": "01", "février": "02", "fevrier": "02", "mars": "03",
    "avril": "04", "mai": "05", "juin": "06", "juillet": "07",
    "août": "08", "aout": "08", "septembre": "09", "octobre": "10",
    "novembre": "11", "décembre": "12", "decembre": "12",
}
_FRENCH_MONTH_RE = re.compile(
    r"\b(" + "|".join(_FRENCH_MONTHS.keys()) + r")\b", re.IGNORECASE
)

_CURRENCY_RE = re.compile(r"[€$£]|\beur\b|\busd\b", re.IGNORECASE)


# ─────────────────────────────────────────
# Basic (level 2.1)
# ─────────────────────────────────────────

def normalize_basic(value) -> str:
    """Strip whitespace, lowercase, collapse null-ish tokens to ''.
    Strips trailing ., , ; ."""
    if value is None:
        return ""
    s = str(value).strip().lower()
    if s in _NULL_TOKENS:
        return ""
    return s.rstrip(".,;")


# ─────────────────────────────────────────
# Text (strip accents + collapse whitespace)
# ─────────────────────────────────────────

def normalize_text(value) -> str:
    s = normalize_basic(value)
    if not s:
        return s
    # Strip accents via NFKD decomposition
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    # Collapse repeated whitespace
    return " ".join(s.split())


# ─────────────────────────────────────────
# Numbers
# ─────────────────────────────────────────

def _to_float(value) -> float | None:
    """Parse a human number string into a float, or return None on failure.
    Handles French ('1 234,56'), US ('1,234.56'), plain ('1234.56'),
    and currency-decorated values."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    # Strip currency symbols/words, percent sign, thin/non-breaking spaces
    s = _CURRENCY_RE.sub("", s)
    s = s.replace(" ", " ").replace(" ", " ").replace("_", "")
    s = s.replace("%", "").strip()
    if not s:
        return None
    # Pick decimal separator: if both '.' and ',' appear, the LAST one wins.
    has_dot = "." in s
    has_comma = "," in s
    if has_dot and has_comma:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_comma:
        s = s.replace(",", ".")
    # Remove remaining spaces (thousands)
    s = s.replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return None


def normalize_number(value) -> str:
    """Canonical form: float rounded to 2 decimals, trailing zeros stripped.
    '1234.50' → '1234.5' ; '100' → '100.0'. Falls back to normalize_basic on
    parse failure."""
    f = _to_float(value)
    if f is None:
        return normalize_basic(value)
    rounded = round(f, 2)
    # str() drops trailing zeros naturally for Python floats:
    # str(100.0) = '100.0', str(100.50) = '100.5', str(1234.56) = '1234.56'.
    return str(rounded)


def normalize_percent(value) -> str:
    """Same as normalize_number, but tolerates a trailing '%'."""
    if value is None:
        return ""
    s = str(value).replace("%", "")
    return normalize_number(s)


# ─────────────────────────────────────────
# Dates
# ─────────────────────────────────────────

def _replace_french_months(text: str) -> str:
    def repl(m):
        return _FRENCH_MONTHS[m.group(1).lower()]
    return _FRENCH_MONTH_RE.sub(repl, text)


def normalize_date(value) -> str:
    """Canonical form: 'YYYY-MM-DD'. Falls back to normalize_basic on parse failure."""
    if value is None:
        return ""
    # Datetime / date objects (pandas may emit Timestamp, which subclasses datetime)
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    if not s:
        return ""
    # Quick short-circuit for basic null-ish tokens
    basic = normalize_basic(s)
    if not basic:
        return ""
    # Pre-translate French month names
    s_translated = _replace_french_months(basic)
    try:
        dt = dateutil_parser.parse(s_translated, dayfirst=True, fuzzy=False)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, OverflowError, TypeError):
        return basic  # fall back to the basic-normalized string


# ─────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────

FIELD_NORMALIZERS = {
    "NUMERO_FACTURE":   normalize_text,
    "DATE_FACTURE":     normalize_date,
    "MONTANT_HT":       normalize_number,
    "TAUX_TVA":         normalize_percent,
    "MONTANT_TTC":      normalize_number,
    "NOM_INSTALLATEUR": normalize_text,
    "COMMUNE_TRAVAUX":  normalize_text,
    "CODE_POSTAL":      normalize_text,
    "ADRESSE_TRAVAUX":  normalize_text,
}


def normalize(value, field_key: str | None = None) -> str:
    """Dispatch on field_key. Unknown keys fall back to normalize_basic."""
    fn = FIELD_NORMALIZERS.get(field_key) if field_key else None
    if fn is None:
        return normalize_basic(value)
    return fn(value)
