"""Trinity theming — Matrix by default, customizable via JSON.

Built-in themes live in ``BUILTIN_THEMES``; user themes are JSON files
in ``~/.trinity/themes/<name>.json`` with the same shape (all fields
optional, missing values inherit from ``matrix``). No code changes are
needed to add a theme — mirroring Hermes's data-driven skin ethos, but
JSON per locked decision #12.
"""

from __future__ import annotations

from typing import Dict

from prompt_toolkit.styles import Style

from . import paths

# Every color a Trinity widget may use. Widgets must reference these
# style classes — never hardcoded colors (tasklist 7.3).
BUILTIN_THEMES: Dict[str, Dict[str, str]] = {
    "matrix": {
        "description": "Green-on-black. There is no spoon.",
        "banner": "#00ff41 bold",
        "title": "#00ff41 bold",
        "accent": "#00b32d",
        "text": "#b5ffc8",
        "dim": "#1e7a38",
        "selected": "bg:#003b00 #00ff41 bold",
        "pointer": "#00ff41 bold",
        "ok": "#00ff41",
        "warn": "#c8ff00",
        "error": "#ff4444",
        "hint": "#1e7a38 italic",
        "input": "#b5ffc8",
        "frame": "#00b32d",
    },
    "matrix-amber": {
        "description": "Warm amber phosphor terminal.",
        "banner": "#ffb000 bold",
        "title": "#ffb000 bold",
        "accent": "#cc8400",
        "text": "#ffe0a3",
        "dim": "#8a6a1e",
        "selected": "bg:#3b2a00 #ffb000 bold",
        "pointer": "#ffb000 bold",
        "ok": "#a8ff60",
        "warn": "#ffd700",
        "error": "#ff5555",
        "hint": "#8a6a1e italic",
        "input": "#ffe0a3",
        "frame": "#cc8400",
    },
    "ice": {
        "description": "Cold blue-white.",
        "banner": "#7fdbff bold",
        "title": "#7fdbff bold",
        "accent": "#39a0c8",
        "text": "#d8f4ff",
        "dim": "#2a6478",
        "selected": "bg:#00293b #7fdbff bold",
        "pointer": "#7fdbff bold",
        "ok": "#64ffb4",
        "warn": "#ffd97f",
        "error": "#ff6b6b",
        "hint": "#2a6478 italic",
        "input": "#d8f4ff",
        "frame": "#39a0c8",
    },
}

DEFAULT_THEME = "matrix"

_STYLE_KEYS = [k for k in BUILTIN_THEMES["matrix"] if k != "description"]


def available_themes() -> Dict[str, str]:
    """name -> description, built-ins plus user JSON themes."""
    out = {name: t.get("description", "") for name, t in BUILTIN_THEMES.items()}
    tdir = paths.themes_dir()
    if tdir.is_dir():
        for f in sorted(tdir.glob("*.json")):
            data = paths.read_json(f)
            if data:
                out[f.stem] = data.get("description", "(user theme)")
    return out


def load_theme(name: str) -> Dict[str, str]:
    """Resolve a theme by name; unknown/missing fields inherit from matrix."""
    base = dict(BUILTIN_THEMES[DEFAULT_THEME])
    if name in BUILTIN_THEMES:
        base.update(BUILTIN_THEMES[name])
    else:
        user = paths.read_json(paths.themes_dir() / f"{name}.json")
        if user:
            base.update({k: v for k, v in user.items() if isinstance(v, str)})
    return base


def to_style(theme: Dict[str, str]) -> Style:
    """Build the prompt_toolkit Style all Trinity widgets share."""
    return Style.from_dict({k: theme[k] for k in _STYLE_KEYS if k in theme})


def current_theme_name() -> str:
    return paths.load_config().get("theme", DEFAULT_THEME)


def set_theme(name: str) -> None:
    cfg = paths.load_config()
    cfg["theme"] = name
    paths.save_config(cfg)
