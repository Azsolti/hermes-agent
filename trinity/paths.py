"""Trinity filesystem layout + JSON config helpers.

Everything Trinity owns lives under ``~/.trinity/`` as JSON
(locked decision #12). Secrets stay in Hermes's existing ``.env``
handling — Trinity never writes API keys.

Dual-read: if a value is missing from Trinity config we may fall
back to ``~/.hermes/`` equivalents, but we only ever *write* to
``~/.trinity/``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def trinity_home() -> Path:
    """Root of Trinity-owned state (override with TRINITY_HOME for tests)."""
    override = os.environ.get("TRINITY_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".trinity"


def hermes_home() -> Path:
    """Classic Hermes config dir, used read-only for fallbacks."""
    override = os.environ.get("HERMES_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".hermes"


def presets_dir() -> Path:
    return trinity_home() / "presets"


def sessions_dir() -> Path:
    return trinity_home() / "sessions"


def themes_dir() -> Path:
    return trinity_home() / "themes"


def config_path() -> Path:
    return trinity_home() / "config.json"


def ensure_dirs() -> None:
    for d in (trinity_home(), presets_dir(), sessions_dir(), themes_dir()):
        d.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Lenient JSON read: missing or corrupt file -> None, never raises."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def write_json(path: Path, data: Dict[str, Any]) -> None:
    """Atomic-ish JSON write (tmp file + replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def load_config() -> Dict[str, Any]:
    return read_json(config_path()) or {}


def save_config(cfg: Dict[str, Any]) -> None:
    write_json(config_path(), cfg)
