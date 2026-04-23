"""Generate a draft supplier prompt from a handful of sample invoices.

Chantier 4.1: the pure backend piece. Given a list of (ocr_text, expected)
samples, ask Gemma2:9b to produce a {detecter, prompt} draft that follows
the same style as the hand-written prompts in config/prompts/.

The output is a *draft* — a human operator reviews and edits it via /admin
before saving. There is no auto-validation here (that's chantier 4.4).
"""

import json

import ollama

from core.config import ALL_FIELD_KEYS, JSON_TEMPLATE, MODEL_NAME, OLLAMA_OPTIONS
from core.postprocess import clean_json

_MIN_SAMPLES = 2
_MAX_SAMPLES = 5
_OCR_TRUNCATE = 2000


class PromptGenerationError(RuntimeError):
    """Raised on invalid input or any LLM / JSON failure during generation."""


META_PROMPT = """Tu es un expert en prompt engineering pour l'extraction de données de factures BTP francaises.

Ta tâche : à partir d'échantillons d'une nouvelle facture (texte OCR + valeurs attendues), écrire un prompt spécialisé pour le modèle Gemma2:9b. Le prompt final sera utilisé pour extraire automatiquement les 9 champs métier sur toute facture de ce fournisseur.

Voici les échantillons :

{samples}

INSTRUCTIONS :

1. Identifie 3 à 5 MOTS-CLÉS DE DÉTECTION uniques à ce fournisseur (nom d'entreprise, SIRET, email, préfixe de numéro de facture). Ils doivent apparaître littéralement dans le texte OCR ci-dessus et permettre de reconnaître ce fournisseur parmi d'autres.

2. Rédige un PROMPT D'EXTRACTION spécialisé. Il doit :
   - commencer par "Tu es un extracteur de données de factures BTP. Voici le texte OCR d'une facture de <NOM_FOURNISSEUR> (<métier ou activité>, <lieu si connu>)."
   - contenir une section "PARTICULARITÉS <NOM_FOURNISSEUR> :" avec des règles concrètes pour chacun des 9 champs (format des dates, séparateur des nombres, emplacement dans la facture, préfixes, TVA habituelle, etc.) — inspirées directement des échantillons
   - rappeler "Si un champ n'est pas visible, mets null."
   - rappeler "Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après."
   - inclure ce template JSON à la fin :

{json_template}

   - finir par la ligne "TEXTE OCR :" suivie d'un retour à la ligne

Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après, avec exactement cette structure :

{{"detecter": ["mot-clé 1", "mot-clé 2", "..."], "prompt": "Tu es un extracteur ..."}}
"""


def _format_samples(samples: list[dict]) -> str:
    blocks = []
    for i, s in enumerate(samples, start=1):
        ocr_text = str(s["ocr_text"])[:_OCR_TRUNCATE]
        expected_lines = "\n".join(
            f"  {k}: {s['expected'].get(k) or 'null'}"
            for k in ALL_FIELD_KEYS
        )
        blocks.append(
            f"=== ÉCHANTILLON {i} ===\n"
            f"TEXTE OCR :\n{ocr_text}\n\n"
            f"VALEURS ATTENDUES :\n{expected_lines}"
        )
    return "\n\n".join(blocks)


def _build_meta_prompt(samples: list[dict]) -> str:
    return META_PROMPT.format(
        samples=_format_samples(samples),
        json_template=JSON_TEMPLATE,
    )


def _validate_input(samples: list[dict]) -> None:
    if not isinstance(samples, list):
        raise PromptGenerationError(f"samples must be a list, got {type(samples).__name__}")
    if len(samples) < _MIN_SAMPLES:
        raise PromptGenerationError(f"need at least {_MIN_SAMPLES} samples, got {len(samples)}")
    if len(samples) > _MAX_SAMPLES:
        raise PromptGenerationError(f"max {_MAX_SAMPLES} samples, got {len(samples)}")
    for i, s in enumerate(samples):
        if not isinstance(s, dict):
            raise PromptGenerationError(f"sample {i}: must be a dict, got {type(s).__name__}")
        if not s.get("ocr_text") or not isinstance(s["ocr_text"], str):
            raise PromptGenerationError(f"sample {i}: missing or empty 'ocr_text'")
        if not isinstance(s.get("expected"), dict):
            raise PromptGenerationError(f"sample {i}: 'expected' must be a dict of field:value")


def _validate_output(result) -> dict:
    if not isinstance(result, dict):
        raise PromptGenerationError(f"LLM response is not a JSON object (got {type(result).__name__})")
    detecter = result.get("detecter")
    if not isinstance(detecter, list) or not detecter:
        raise PromptGenerationError("LLM response missing 'detecter' as a non-empty list")
    prompt = result.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise PromptGenerationError("LLM response missing 'prompt' as a non-empty string")
    # Coerce detecter to stripped strings
    result["detecter"] = [str(x).strip() for x in detecter if str(x).strip()]
    if not result["detecter"]:
        raise PromptGenerationError("'detecter' collapsed to empty after stripping")
    return result


def generate_prompt_from_samples(samples: list[dict]) -> dict:
    """Generate a {detecter, prompt} draft for a new supplier.

    `samples` is a list of {"ocr_text": str, "expected": dict of field:value}
    between 2 and 5 entries. The `expected` dict should have the 9 field
    keys from `core.config.ALL_FIELD_KEYS`; missing keys are treated as null.

    Returns the parsed dict. Raises PromptGenerationError on any failure.
    """
    _validate_input(samples)
    meta = _build_meta_prompt(samples)

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": meta}],
            options=OLLAMA_OPTIONS,
        )
    except Exception as e:
        raise PromptGenerationError(f"Ollama call failed: {e}") from e

    content = response.get("message", {}).get("content", "")
    if not content:
        raise PromptGenerationError("Ollama returned an empty response")

    raw = clean_json(content)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        preview = raw[:200]
        raise PromptGenerationError(f"LLM returned invalid JSON: {e}. Preview: {preview!r}") from e

    return _validate_output(parsed)
