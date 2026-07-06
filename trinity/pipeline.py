"""Trinity pipeline orchestration (Phase 4).

Wires a launched session onto the Hermes engine:

* :func:`ensure_role_profiles` — namespaced ``trinity-*`` Hermes
  profiles per role, each with the session's model, a role SOUL, and a
  roster description the kanban decomposer matches assignees against.
* :func:`plan` — the Brain planning step: decompose the session's
  triage root into a dependency graph of detailed Hand tasks on the
  ``trinity`` board.
* :func:`plan_summary` — the transparency view of what the Brain
  created, used by the plan-approval gate (4.2a) and the dashboard.

The decomposer's LLM comes from the auxiliary-client config; Trinity
binds the Brain model to it via the ``auxiliary.kanban_decomposer.model``
override in the active profile's config.yaml (documented in 4.0/9.3).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import TRINITY_BOARD
from .roles import ROLE_DESCRIPTIONS, profile_name, roles_for, soul_for
from .session_spec import SessionSpec

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Role profiles (4.1)
# --------------------------------------------------------------------------

def ensure_role_profiles(spec: SessionSpec) -> Dict[str, Path]:
    """Create/refresh a Hermes profile per enabled role.

    Idempotent: existing profiles are updated in place (model, SOUL,
    description) so a new session's choices always win.
    Returns role -> profile dir.
    """
    from hermes_cli import profiles as hp

    out: Dict[str, Path] = {}
    for role in roles_for(spec):
        name = profile_name(role)
        if hp.profile_exists(name):
            pdir = hp.get_profile_dir(name)
        else:
            # no_alias: no wrapper scripts; no_skills: role profiles are
            # lean — session skills are attached to tasks, not profiles.
            pdir = hp.create_profile(
                name, no_alias=True, no_skills=True,
                description=ROLE_DESCRIPTIONS[role],
            )
        hp.write_profile_meta(
            pdir, description=ROLE_DESCRIPTIONS[role], description_auto=False,
        )
        _write_role_config(pdir, role, spec)
        (pdir / "SOUL.md").write_text(soul_for(role, spec), encoding="utf-8")
        out[role] = pdir
    return out


def _write_role_config(pdir: Path, role: str, spec: SessionSpec) -> None:
    """Set the role's model in its profile config.yaml (merge, not clobber)."""
    import yaml

    cfg_path = pdir / "config.yaml"
    cfg: dict = {}
    if cfg_path.is_file():
        try:
            loaded = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cfg = loaded
        except Exception:
            cfg = {}
    cfg["model"] = spec.models.get(role) or cfg.get("model")
    cfg_path.write_text(
        yaml.safe_dump(cfg, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


# --------------------------------------------------------------------------
# Brain planning (4.2)
# --------------------------------------------------------------------------

@dataclass
class PlannedTask:
    task_id: str
    title: str
    assignee: str
    status: str
    body: str


@dataclass
class PlanResult:
    ok: bool
    reason: str = ""
    root_id: str = ""
    fanout: bool = False
    children: List[PlannedTask] = field(default_factory=list)


def plan(root_id: str, spec: SessionSpec) -> PlanResult:
    """Run the Brain planning step: decompose the triage root into a
    dependency graph of detailed child specs on the trinity board.
    """
    from hermes_cli import kanban_db as kb
    from hermes_cli.kanban_decompose import decompose_task

    with kb.scoped_current_board(TRINITY_BOARD):
        outcome = decompose_task(root_id, author=profile_name("brain"))
        if not outcome.ok:
            return PlanResult(False, outcome.reason, root_id)
        children: List[PlannedTask] = []
        if outcome.child_ids:
            with kb.connect_closing() as conn:
                for cid in outcome.child_ids:
                    t = kb.get_task(conn, cid)
                    if t is not None:
                        children.append(PlannedTask(
                            task_id=t.id,
                            title=t.title or "",
                            assignee=t.assignee or "?",
                            status=t.status or "?",
                            body=t.body or "",
                        ))
        return PlanResult(
            True, outcome.reason, root_id,
            fanout=outcome.fanout, children=children,
        )


def cancel_plan(result: PlanResult) -> int:
    """Plan-gate rejection: archive the Brain's children so nothing can
    dispatch; the root stays on the board for a re-plan. Returns the
    number of tasks archived.
    """
    from hermes_cli import kanban_db as kb

    archived = 0
    with kb.scoped_current_board(TRINITY_BOARD):
        with kb.connect_closing() as conn:
            for child in result.children:
                try:
                    if kb.archive_task(conn, child.task_id):
                        archived += 1
                except Exception:
                    logger.exception("cancel_plan: failed on %s", child.task_id)
    return archived


def plan_summary(result: PlanResult) -> List[str]:
    """Human-readable plan lines for the approval gate / dashboard."""
    if not result.children:
        return [f"(no fanout) {result.reason}"]
    lines = []
    for i, c in enumerate(result.children, 1):
        first = (c.body.strip().splitlines() or [""])[0]
        lines.append(f"{i}. [{c.assignee}] {c.title}  ({c.status})")
        if first:
            lines.append(f"     {first[:100]}")
    return lines
