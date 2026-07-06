"""Launch a configured Trinity session (tasklist 2.12).

Translates a SessionSpec into concrete state on the Hermes engine:

* a dedicated ``trinity`` kanban board (state isolation, 0.6),
* a triage root task carrying the full project brief — exactly the
  shape ``kanban decompose`` expects the Brain to fan out from,
* a persisted session record in ``~/.trinity/sessions/`` (JSON).

Phase 4 wires the Brain decompose + dispatcher on top of this; until
then the launcher reports what it created and how to inspect it.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from . import TRINITY_BOARD, paths
from .session_spec import ROLE_BRAIN, SessionSpec


def launch(spec: SessionSpec) -> Dict[str, Any]:
    """Create board + root task from the spec. Returns a launch report."""
    from hermes_cli import kanban_db as kb

    kb.create_board(
        TRINITY_BOARD,
        name="Trinity",
        description="Trinity pipeline board — isolated from classic Hermes tasks.",
    )

    session_id = time.strftime("%Y%m%d-%H%M%S")
    with kb.connect_closing(board=TRINITY_BOARD) as conn:
        root_id = kb.create_task(
            conn,
            title=f"[trinity] {spec.project_description[:60]}",
            body=spec.brief(),
            assignee=ROLE_BRAIN,
            created_by="trinity-wizard",
            triage=True,  # Brain promotes it by decomposing into specs
            skills=spec.skills or None,
            idempotency_key=f"trinity-root-{session_id}",
            board=TRINITY_BOARD,
        )
        conn.commit()

    record = {
        "session_id": session_id,
        "root_task_id": root_id,
        "board": TRINITY_BOARD,
        "spec": spec.to_dict(),
    }
    paths.write_json(paths.sessions_dir() / f"{session_id}.json", record)
    return record
