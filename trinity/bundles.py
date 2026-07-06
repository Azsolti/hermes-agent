"""Task-path -> skill-bundle resolution (tasklist 3.2, data-driven).

Bundles are JSON files: built-ins ship in ``trinity/bundles/*.json``,
users can add ``~/.trinity/bundles/*.json`` with the same shape — new
task types need no code changes. Each file maps dotted task paths
(``task_type.specialization.framework``) to skill lists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from . import paths

_BUILTIN_DIR = Path(__file__).parent / "bundles"


def _load_all() -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    user_dir = paths.trinity_home() / "bundles"
    for directory in (_BUILTIN_DIR, user_dir):  # user files override built-ins
        if not directory.is_dir():
            continue
        for f in sorted(directory.glob("*.json")):
            data = paths.read_json(f) or {}
            bundles = data.get("bundles")
            if not isinstance(bundles, dict):
                continue
            for task_path, skills in bundles.items():
                if isinstance(skills, list):
                    mapping[task_path] = [str(s) for s in skills]
    return mapping


def resolve(task_path: str) -> List[str]:
    """Skills for a dotted task path; falls back to progressively
    shorter prefixes (``a.b.c`` -> ``a.b`` -> ``a``) so an "Other"
    framework still inherits its specialization's bundle (tasklist 3.4).
    """
    mapping = _load_all()
    parts = task_path.split(".")
    while parts:
        prefix = ".".join(parts)
        hit = mapping.get(prefix)
        if hit:
            return hit
        # No exact bundle at this prefix — if exactly one known bundle
        # lives under it, that's the best-effort match (e.g. an "Other"
        # framework inherits its specialization's only bundle).
        under = [k for k in mapping if k.startswith(prefix + ".")]
        if len(under) == 1:
            return mapping[under[0]]
        parts.pop()
    return []


def known_paths() -> List[str]:
    return sorted(_load_all())
