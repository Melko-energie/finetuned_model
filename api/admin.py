"""Admin endpoints for managing prompt files under config/prompts/.

All routes are gated behind _require_localhost until chantier 3 ships a real
auth dependency. Every mutation (POST/PUT/DELETE) triggers reload() so the
change is visible to the extraction pipeline immediately.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.prompts import PROMPTS_DIR, PromptConfigError, reload as reload_prompts

router = APIRouter(prefix="/api/admin")

KEY_PATTERN = r"^[a-z][a-z0-9_]*$"
RESERVED_KEYS = {"texte", "default"}


# ─────────────────────────────────────────
# Dependencies
# ─────────────────────────────────────────

def _require_localhost(request: Request):
    """Minimal protection until chantier 3 (auth) ships. Replace with a real
    auth dependency (Depends(current_admin_user)) when available."""
    client_host = request.client.host if request.client else None
    if client_host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=403, detail="Admin endpoints are localhost-only")


# ─────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────

class PromptCreate(BaseModel):
    key: str = Field(pattern=KEY_PATTERN, max_length=50)
    detecter: list[str] = Field(default_factory=list)
    prompt: str = Field(min_length=1)


class PromptUpdate(BaseModel):
    detecter: list[str] = Field(default_factory=list)
    prompt: str = Field(min_length=1)


# ─────────────────────────────────────────
# YAML I/O helpers
# ─────────────────────────────────────────

class _BlockStr(str):
    """Marker to force PyYAML to emit multi-line strings as block scalars (|)."""


def _block_str_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(_BlockStr, _block_str_representer)


def _wrap_multiline(value):
    if isinstance(value, str) and "\n" in value:
        return _BlockStr(value)
    return value


def _path_for(key: str) -> Path:
    return PROMPTS_DIR / f"{key}.yaml"


def _classify(key: str) -> Literal["supplier", "system"]:
    return "system" if key in RESERVED_KEYS else "supplier"


def _write_yaml_atomic(path: Path, payload: dict) -> None:
    wrapped = {k: _wrap_multiline(v) for k, v in payload.items()}
    rendered = yaml.dump(
        wrapped,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=10_000,
    )
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(rendered, encoding="utf-8")
    os.replace(tmp, path)


def _read_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _reload_or_500():
    try:
        reload_prompts()
    except PromptConfigError as e:
        raise HTTPException(
            status_code=500,
            detail=f"File written but reload failed: {e}. Fix the offending file and call /api/admin/reload-prompts manually.",
        )


# ─────────────────────────────────────────
# Reload (moved from api/routes.py — chantier 1.3)
# ─────────────────────────────────────────

@router.post("/reload-prompts", dependencies=[Depends(_require_localhost)])
async def reload_prompts_endpoint():
    """Re-read config/prompts/*.yaml and swap the in-memory state."""
    try:
        reload_prompts()
    except PromptConfigError as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "error": str(e)},
        )
    files = sorted(p.name for p in PROMPTS_DIR.glob("*.yaml"))
    # Count non-texte entries (the dict exposes 31 suppliers; the metric
    # here is aligned with /api/fournisseurs which excludes DEFAULT).
    from core.prompts import PROMPTS_INSTALLATEURS
    return {
        "status": "ok",
        "loaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prompts_count": len(PROMPTS_INSTALLATEURS),
        "files": files,
    }


# ─────────────────────────────────────────
# CRUD on prompts
# ─────────────────────────────────────────

@router.get("/prompts", dependencies=[Depends(_require_localhost)])
async def list_prompts():
    items = []
    for path in sorted(PROMPTS_DIR.glob("*.yaml")):
        key = path.stem
        data = _read_yaml(path)
        items.append({
            "key": key,
            "type": _classify(key),
            "detecter_count": len(data.get("detecter") or []),
            "prompt_chars": len(data.get("prompt") or ""),
        })
    return {"prompts": items}


@router.get("/prompts/{key}", dependencies=[Depends(_require_localhost)])
async def get_prompt(key: str):
    path = _path_for(key)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"prompt '{key}' not found")
    data = _read_yaml(path)
    return {
        "key": key,
        "type": _classify(key),
        "detecter": data.get("detecter") or [],
        "prompt": data.get("prompt") or "",
    }


@router.post("/prompts", status_code=201, dependencies=[Depends(_require_localhost)])
async def create_prompt(payload: PromptCreate):
    if payload.key in RESERVED_KEYS:
        raise HTTPException(status_code=400, detail=f"'{payload.key}' is a reserved key")
    path = _path_for(payload.key)
    if path.exists():
        raise HTTPException(status_code=409, detail=f"prompt '{payload.key}' already exists")

    _write_yaml_atomic(path, {
        "detecter": list(payload.detecter),
        "prompt": payload.prompt,
    })
    _reload_or_500()

    return {
        "key": payload.key,
        "type": _classify(payload.key),
        "detecter": payload.detecter,
        "prompt": payload.prompt,
    }


@router.put("/prompts/{key}", dependencies=[Depends(_require_localhost)])
async def update_prompt(key: str, payload: PromptUpdate):
    path = _path_for(key)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"prompt '{key}' not found")

    if key == "texte":
        detecter: list[str] = []
        body = {"prompt": payload.prompt}
    else:
        detecter = list(payload.detecter)
        body = {"detecter": detecter, "prompt": payload.prompt}

    _write_yaml_atomic(path, body)
    _reload_or_500()

    return {
        "key": key,
        "type": _classify(key),
        "detecter": detecter,
        "prompt": payload.prompt,
    }


@router.delete("/prompts/{key}", dependencies=[Depends(_require_localhost)])
async def delete_prompt(key: str):
    if key in RESERVED_KEYS:
        raise HTTPException(status_code=400, detail=f"'{key}' is a reserved key, cannot delete")
    path = _path_for(key)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"prompt '{key}' not found")

    path.unlink()
    _reload_or_500()

    return {"status": "deleted", "key": key}
