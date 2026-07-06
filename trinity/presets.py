"""Presets — saved SessionSpecs as JSON in ~/.trinity/presets/ (Phase 8)."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from . import paths
from .session_spec import SessionSpec


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", name.strip().lower()).strip("-")
    return slug or "preset"


def list_presets() -> List[Dict[str, str]]:
    """[{name, description}] for every readable preset file."""
    out: List[Dict[str, str]] = []
    pdir = paths.presets_dir()
    if pdir.is_dir():
        for f in sorted(pdir.glob("*.json")):
            data = paths.read_json(f)
            if data is not None:
                out.append(
                    {
                        "name": f.stem,
                        "description": data.get("_description", ""),
                    }
                )
    return out


def load_preset(name: str) -> Optional[SessionSpec]:
    data = paths.read_json(paths.presets_dir() / f"{_slug(name)}.json")
    if data is None:
        return None
    spec = SessionSpec.from_dict(data)
    spec.preset_name = name
    # A preset stores configuration, not a concrete project.
    spec.project_description = ""
    spec.grill_answers = []
    return spec


def save_preset(name: str, spec: SessionSpec, description: str = "") -> str:
    slug = _slug(name)
    data = spec.to_dict()
    # Strip per-project fields; presets are reusable configuration.
    data["project_description"] = ""
    data["grill_answers"] = []
    data["preset_name"] = slug
    data["_description"] = description
    paths.write_json(paths.presets_dir() / f"{slug}.json", data)
    return slug


def delete_preset(name: str) -> bool:
    f = paths.presets_dir() / f"{_slug(name)}.json"
    if f.exists():
        f.unlink()
        return True
    return False


def ensure_starter_preset() -> None:
    """Ship the default preset on first run (tasklist 8.3)."""
    if not list_presets():
        save_preset(
            "deepseek-glm-default",
            SessionSpec(),
            "Brain=DeepSeek Pro · Hands=DeepSeek Flash · Judge=GLM (vision)",
        )
