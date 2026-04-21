"""Supplier and AVOIR detection from OCR text."""

import re

from core.prompts import PROMPTS_INSTALLATEURS


def detect_installateur(texte: str) -> str:
    """Detect the supplier from OCR text via keyword matching.

    NVINS auto-invoices (SIP AMIENS) are detected in two steps: first verify
    `auto-facturation` is present, then identify which sub-installateur
    (KLISZ, PROXISERVE, ...) signed it. Falls back to `nvins_sip_amiens`
    when no sub-installateur matches, then to `DEFAULT`.
    """
    texte_lower = texte.lower()

    is_autofact = (
        "auto-facturation" in texte_lower
        or "auto facturation" in texte_lower
        or "autofacturation" in texte_lower
    )

    if is_autofact:
        for nom, config in PROMPTS_INSTALLATEURS.items():
            if not nom.startswith("nvins_") or nom == "nvins_sip_amiens":
                continue
            for mot in config["detecter"]:
                if mot.lower() in texte_lower:
                    return nom
        return "nvins_sip_amiens"

    for nom, config in PROMPTS_INSTALLATEURS.items():
        if nom == "DEFAULT" or nom.startswith("nvins_"):
            continue
        for mot in config["detecter"]:
            if mot.lower() in texte_lower:
                return nom

    for nom, config in PROMPTS_INSTALLATEURS.items():
        if not nom.startswith("nvins_"):
            continue
        for mot in config["detecter"]:
            if mot.lower() in texte_lower:
                return nom

    return "DEFAULT"


AVOIR_KEYWORDS = ["note de crédit", "note de credit"]

AVOIR_PATTERNS = [
    r"\bavoir\s*n[°o]",
    r"\bavoir\s*:?\s*\d",
    r"\bn[°o]\s*d'?\s*avoir",
    r"\bfacture\s+d'?\s*avoir",
    r"\bavoirs?\b(?!\s+recours)(?!\s+lieu)(?!\s+pu)(?!\s+ete)(?!\s+le\s+droit)",
]


def detect_avoir(texte: str) -> bool:
    """True if the document is an AVOIR (credit note). Avoids false positives
    on the French verb 'avoir' in legal text."""
    texte_lower = texte.lower()
    for mot in AVOIR_KEYWORDS:
        if mot in texte_lower:
            return True
    for pattern in AVOIR_PATTERNS:
        if re.search(pattern, texte_lower):
            return True
    return False
