"""Prompt definitions loaded from config/prompts/*.yaml at import time.

Each YAML file is one supplier (or texte.yaml = generic, default.yaml = fallback).
Schema is validated by Pydantic at load time — a malformed file raises a clear
PromptConfigError naming the offending file.

The public API is unchanged:
  - PROMPTS_INSTALLATEURS: dict[str, {"detecter": list[str], "prompt": str}]
  - PROMPT_TEXTE: str (generic prompt for the /texte page)
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "config" / "prompts"


class PromptFile(BaseModel):
    """Schema for one YAML file in config/prompts/."""

    prompt: str = Field(min_length=1)
    detecter: list[str] = Field(default_factory=list)


class PromptConfigError(RuntimeError):
    """Raised when a YAML file in config/prompts/ is missing, unreadable,
    malformed, or violates the schema. Always names the offending file."""


def _load_one(path: Path) -> PromptFile:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise PromptConfigError(f"{path.name}: invalid YAML — {e}") from e

    if raw is None:
        raise PromptConfigError(f"{path.name}: file is empty")
    if not isinstance(raw, dict):
        raise PromptConfigError(f"{path.name}: top-level must be a mapping, got {type(raw).__name__}")

    try:
        return PromptFile.model_validate(raw)
    except ValidationError as e:
        raise PromptConfigError(f"{path.name}: schema validation failed — {e}") from e


def _load_all() -> tuple[dict, str]:
    if not PROMPTS_DIR.is_dir():
        raise PromptConfigError(f"prompts directory not found: {PROMPTS_DIR}")

    files = sorted(PROMPTS_DIR.glob("*.yaml"))
    if not files:
        raise PromptConfigError(f"no .yaml files found in {PROMPTS_DIR}")

    prompts: dict = {}
    generic = ""

    for path in files:
        parsed = _load_one(path)
        key = path.stem

        if key == "texte":
            generic = parsed.prompt
            continue

        if key == "default":
            key = "DEFAULT"

        prompts[key] = {
            "detecter": parsed.detecter,
            "prompt": parsed.prompt,
        }

    if not generic:
        raise PromptConfigError(f"texte.yaml is missing or has empty 'prompt' in {PROMPTS_DIR}")
    if "DEFAULT" not in prompts:
        raise PromptConfigError(f"default.yaml is missing in {PROMPTS_DIR}")

    return prompts, generic


PROMPTS_INSTALLATEURS, PROMPT_TEXTE = _load_all()


def reload() -> dict:
    """Re-read config/prompts/*.yaml and swap the in-memory state atomically.

    Returns a summary dict {"prompts_count": int, "files": list[str]} on success.
    Raises PromptConfigError if the new state fails validation; in that case
    PROMPTS_INSTALLATEURS and PROMPT_TEXTE remain unchanged (atomic-or-nothing).

    Consumers that imported PROMPTS_INSTALLATEURS via `from core.prompts import ...`
    will see the new content because the dict is mutated in place. Consumers of
    PROMPT_TEXTE must access it via `core.prompts.PROMPT_TEXTE` (module attribute)
    rather than re-binding it locally — see core/extraction.py for the pattern.
    """
    new_prompts, new_texte = _load_all()  # raises BEFORE any state mutation
    PROMPTS_INSTALLATEURS.clear()
    PROMPTS_INSTALLATEURS.update(new_prompts)
    global PROMPT_TEXTE
    PROMPT_TEXTE = new_texte

    files = sorted(p.name for p in PROMPTS_DIR.glob("*.yaml"))
    return {"prompts_count": len(PROMPTS_INSTALLATEURS), "files": files}
