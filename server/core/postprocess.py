"""Post-extraction cleanup: JSON parsing, coherence check, AVOIR sign flip,
SIP AMIENS HQ blacklist, NVINS adjacent-column noise removal."""

import re


def clean_json(raw: str) -> str:
    """Strip markdown fences from a JSON response."""
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return raw


def verifier_coherence_montants(result: dict, is_avoir: bool = False) -> dict:
    """Verify TTC = HT * (1 + TVA/100) within ±5%. Tags `_a_verifier` on mismatch."""
    a_verifier = []

    try:
        ht_raw = result.get("MONTANT_HT")
        ttc_raw = result.get("MONTANT_TTC")
        tva_raw = result.get("TAUX_TVA")

        if not ht_raw or not ttc_raw or not tva_raw:
            return result

        ht = float(str(ht_raw).replace(",", ".").replace(" ", "").replace("€", ""))
        ttc = float(str(ttc_raw).replace(",", ".").replace(" ", "").replace("€", ""))
        tva = float(str(tva_raw).replace("%", "").replace(",", ".").strip())

        ht_abs = abs(ht)
        ttc_abs = abs(ttc)

        if ttc_abs < ht_abs:
            a_verifier.extend(["MONTANT_HT", "MONTANT_TTC"])

        ttc_attendu = ht_abs * (1 + tva / 100)
        ecart = abs(ttc_abs - ttc_attendu) / ttc_attendu if ttc_attendu > 0 else 1
        if ecart > 0.05 and "MONTANT_HT" not in a_verifier:
            a_verifier.extend(["MONTANT_HT", "MONTANT_TTC"])

    except (ValueError, TypeError):
        pass

    if a_verifier:
        result["_a_verifier"] = list(set(a_verifier))

    return result


def inverser_montants_avoir(result: dict) -> dict:
    """Flip MONTANT_HT and MONTANT_TTC to negative for AVOIR documents."""
    for champ in ("MONTANT_HT", "MONTANT_TTC"):
        val = result.get(champ)
        if val and val != "null":
            try:
                num = float(str(val).replace(",", ".").replace(" ", "").replace("€", ""))
                result[champ] = str(round(-abs(num), 2))
            except (ValueError, TypeError):
                pass
    return result


_NVINS_LABELS_VOISINS = [
    r"march[ée]\s*n[°o]?\s*:?",
    r"engagement\s*n[°o]?\s*:?",
    r"ref\.?\s*fourn\.?",
    r"ref\.?\s*interne",
    r"logement\s*:",
    r"b[âa]timent\s*:",
    r"soci[ée]t[ée]\s*:",
    r"programme\s*:",
]
_NVINS_LABELS_RE = re.compile(
    r"\s*(?:" + "|".join(_NVINS_LABELS_VOISINS) + r").*$",
    re.IGNORECASE,
)


def nettoyer_adresse_nvins(adresse):
    """Strip neighbouring SIP-column labels (Engagement n°, Marché n°, ...) glued
    onto the address by OCR for NVINS auto-invoices."""
    if not adresse or not isinstance(adresse, str):
        return adresse
    nettoye = _NVINS_LABELS_RE.sub("", adresse).strip()
    nettoye = nettoye.rstrip(",;:-").strip()
    return nettoye or adresse


_SIP_HQ_RE = re.compile(
    r"(?:"
    r"13\s*place\s*d[',\s]*aguesseau"
    r"|bp\s*511"
    r"|80005\s*amiens(?:\s*cedex(?:\s*\d+)?)?"
    r"|amiens\s*cedex(?:\s*\d+)?"
    r")",
    re.IGNORECASE,
)


def nettoyer_siege_sip(valeur):
    """Universal blacklist: SIP AMIENS HQ (13 place d'Aguesseau, 80005 AMIENS CEDEX)
    is never a worksite. Removes it from address/commune values, including
    pipe-separated lists."""
    if not valeur or not isinstance(valeur, str):
        return valeur
    segments = [s.strip() for s in valeur.split("|")] if "|" in valeur else [valeur]
    nettoyes = []
    for seg in segments:
        cleaned = _SIP_HQ_RE.sub("", seg)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,;:-")
        if cleaned:
            nettoyes.append(cleaned)
    if not nettoyes:
        return None
    return " | ".join(nettoyes) if "|" in valeur else nettoyes[0]


def nettoyer_cp_siege_sip(cp):
    """Remove postal code 80005 (SIP AMIENS HQ) when present alone or in a list."""
    if not cp or not isinstance(cp, str):
        return cp
    segments = [s.strip() for s in cp.split("|")] if "|" in cp else [cp]
    nettoyes = [s for s in segments if s and s.strip() != "80005"]
    if not nettoyes:
        return None
    return " | ".join(nettoyes) if "|" in cp else nettoyes[0]
