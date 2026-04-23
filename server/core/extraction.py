"""High-level extraction orchestration.

Three entry points used by the API:
  - extract_from_precomputed_ocr(filename) -- pre-computed OCR + generic prompt
  - extract_smart(filename, fournisseur)   -- pre-computed OCR + per-supplier prompt
  - process_file_live(file_bytes, suffix, fournisseur) -- live DocTR + per-supplier prompt
"""

import os
import json

import ollama

from core.config import MODEL_NAME, OLLAMA_OPTIONS, ALL_FIELD_KEYS
from core import prompts as _prompts
from core.prompts import PROMPTS_INSTALLATEURS  # mutable dict, safe to bind directly
from core.detection import detect_installateur, detect_avoir
from core.ocr import get_ocr_text, run_doctr_ocr
from core.postprocess import (
    clean_json,
    verifier_coherence_montants,
    inverser_montants_avoir,
    nettoyer_adresse_nvins,
    nettoyer_siege_sip,
    nettoyer_cp_siege_sip,
)


def _apply_sip_cleanup(result: dict) -> dict:
    """Apply universal SIP-AMIENS HQ blacklist on address/commune/postal code."""
    for champ in ("ADRESSE_TRAVAUX", "COMMUNE_TRAVAUX"):
        v = result.get(champ)
        if v and v != "null":
            result[champ] = nettoyer_siege_sip(v)
    cp = result.get("CODE_POSTAL")
    if cp and cp != "null":
        result["CODE_POSTAL"] = nettoyer_cp_siege_sip(cp)
    return result


def extraire_champs(texte: str, installateur: str) -> dict:
    """Call Gemma2:9b with the supplier-specific prompt and clean the result."""
    config = PROMPTS_INSTALLATEURS.get(installateur, PROMPTS_INSTALLATEURS["DEFAULT"])
    prompt = config["prompt"] + texte

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        options=OLLAMA_OPTIONS,
    )

    raw = clean_json(response["message"]["content"])

    try:
        result = json.loads(raw)
        result = verifier_coherence_montants(result)
        if isinstance(installateur, str) and installateur.startswith("nvins_"):
            adr = result.get("ADRESSE_TRAVAUX")
            if adr and adr != "null":
                result["ADRESSE_TRAVAUX"] = nettoyer_adresse_nvins(adr)
        return _apply_sip_cleanup(result)
    except json.JSONDecodeError:
        return {champ: None for champ in ALL_FIELD_KEYS}


def extraire_champs_with_prompt(texte: str, prompt_text: str) -> dict:
    """Run extraction using a prompt passed inline (not looked up by key).

    Used by chantier 4.4 to self-test a generated draft before it's saved
    to disk. No NVINS-specific address cleanup (new suppliers aren't NVINS).
    The universal SIP HQ blacklist still applies.
    """
    prompt = prompt_text + texte
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        options=OLLAMA_OPTIONS,
    )
    raw = clean_json(response["message"]["content"])
    try:
        result = json.loads(raw)
        result = verifier_coherence_montants(result)
        return _apply_sip_cleanup(result)
    except json.JSONDecodeError:
        return {champ: None for champ in ALL_FIELD_KEYS}


def extract_from_precomputed_ocr(filename: str) -> dict:
    """Pre-computed OCR + generic prompt. Returns {fields, error, is_avoir}."""
    texte = get_ocr_text(filename)
    if not texte:
        return {"fields": None, "error": "OCR introuvable pour cette facture", "is_avoir": False}

    is_avoir = detect_avoir(texte)
    prompt = _prompts.PROMPT_TEXTE.format(texte=texte[:3000])
    response = ollama.chat(
        model=MODEL_NAME,
        options=OLLAMA_OPTIONS,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        result = json.loads(clean_json(response["message"]["content"]))
        if is_avoir and result:
            result = inverser_montants_avoir(result)
        if result:
            result = _apply_sip_cleanup(result)
        return {"fields": result, "error": None, "is_avoir": is_avoir}
    except json.JSONDecodeError:
        return {"fields": None, "error": "Reponse JSON invalide", "is_avoir": False}


def extract_smart(filename: str, fournisseur: str = "Auto-detect") -> dict:
    """Pre-computed OCR + per-supplier prompt. Returns {fields, error, installateur, is_avoir}."""
    texte = get_ocr_text(filename)
    if texte is None:
        return {
            "fields": None,
            "error": "OCR introuvable pour cette facture",
            "installateur": None,
            "is_avoir": False,
        }

    if fournisseur == "Auto-detect":
        installateur = detect_installateur(texte)
    elif fournisseur == "DEFAULT":
        installateur = "DEFAULT"
    else:
        installateur = fournisseur.lower()

    is_avoir = detect_avoir(texte)
    fields = extraire_champs(texte, installateur)
    if is_avoir and fields:
        fields = inverser_montants_avoir(fields)

    return {
        "fields": fields,
        "error": None,
        "installateur": installateur,
        "is_avoir": is_avoir,
    }


def process_file_live(file_bytes: bytes, suffix: str, fournisseur: str = "Auto-detect") -> dict:
    """Live DocTR pipeline + per-supplier extraction. Returns same shape as extract_smart."""
    texte = run_doctr_ocr(file_bytes, suffix)
    if not texte.strip():
        return {"fields": None, "error": "Aucun texte OCR", "installateur": None, "is_avoir": False}

    if fournisseur == "Auto-detect":
        installateur = detect_installateur(texte)
    elif fournisseur == "DEFAULT":
        installateur = "DEFAULT"
    else:
        installateur = fournisseur.lower()

    is_avoir = detect_avoir(texte)
    fields = extraire_champs(texte, installateur)
    if is_avoir and fields:
        fields = inverser_montants_avoir(fields)

    return {
        "fields": fields,
        "error": None,
        "installateur": installateur,
        "is_avoir": is_avoir,
    }


def get_fournisseurs_list() -> list[str]:
    """Return supplier keys (excluding DEFAULT), sorted."""
    return sorted(k for k in PROMPTS_INSTALLATEURS.keys() if k != "DEFAULT")
