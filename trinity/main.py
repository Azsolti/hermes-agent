"""Trinity entrypoint (tasklist 0.5).

``trinity``            -> mode selector: Trinity pipeline / Classic Hermes
``trinity --classic``  -> straight to untouched classic Hermes
``trinity --spec F``   -> headless: launch from a SessionSpec JSON file
``trinity theme [N]``  -> list or set the active theme

Classic mode is a one-line handoff to ``hermes_cli.main`` — Trinity is
additive and never touches the classic flow.
"""

from __future__ import annotations

import sys
from typing import List, Optional

from . import paths, theme as theme_mod
from .banner import banner_fragments


def _style():
    return theme_mod.to_style(theme_mod.load_theme(theme_mod.current_theme_name()))


def _run_classic(argv: List[str]) -> None:
    """Hand off to untouched classic Hermes (locked decision #5)."""
    sys.argv = ["hermes"] + argv
    from hermes_cli.main import main as hermes_main

    hermes_main()


def _print_launch_report(record: dict, style) -> None:
    from .menu import show

    show(
        [
            ("class:ok", "\n  ✔ Session launched\n\n"),
            ("class:accent", "     session  "),
            ("class:text", record["session_id"] + "\n"),
            ("class:accent", "       board  "),
            ("class:text", record["board"] + "\n"),
            ("class:accent", "   root task  "),
            ("class:text", record["root_task_id"] + "\n\n"),
            ("class:hint",
             "  The Brain decomposes this root into Hand tasks (Phase 4).\n"
             "  Inspect it any time:  hermes kanban show "
             + record["root_task_id"] + "\n\n"),
        ],
        style=style,
    )


def _run_pipeline(theme_name: Optional[str] = None) -> int:
    from .launcher import launch
    from .wizard import run_wizard

    spec = run_wizard(theme_name)
    if spec is None:
        return 1
    record = launch(spec)
    _print_launch_report(record, _style())
    return _run_planning(spec, record, interactive=True)


def _run_planning(spec, record: dict, *, interactive: bool) -> int:
    """Phase 4: role profiles + Brain planning + plan-approval gate."""
    from .menu import BackNavigation, select, show
    from .pipeline import cancel_plan, ensure_role_profiles, plan, plan_summary

    style = _style()
    ensure_role_profiles(spec)
    show([("class:accent", "  ◇ Role profiles ready — Brain is planning…\n")],
         style=style)

    result = plan(record["root_task_id"], spec)
    if not result.ok:
        show(
            [
                ("class:warn", f"  Planning did not run: {result.reason}\n"),
                ("class:hint",
                 "  The Brain plans via the auxiliary LLM client. Configure a\n"
                 "  provider (hermes model) and re-run:  trinity --spec "
                 + str(paths.sessions_dir() / (record['session_id'] + '.json'))
                 + "\n"),
            ],
            style=style,
        )
        return 1

    lines = [("class:title", "\n  The Brain's plan\n\n")]
    for line in plan_summary(result):
        cls = "class:text" if not line.startswith("     ") else "class:dim"
        lines.append((cls, f"  {line}\n"))
    show(lines, style=style)

    if spec.plan_approval_gate and interactive:
        try:
            verdict = select(
                "Approve this plan?",
                [
                    ("Approve", "Hands may start on ready tasks"),
                    ("Reject", "archive these tasks; nothing dispatches"),
                ],
                style=style, allow_other=False, allow_back=False,
            )
        except (KeyboardInterrupt, BackNavigation):
            verdict = "Reject"
        if verdict == "Reject":
            n = cancel_plan(result)
            show([("class:warn",
                   f"  Plan rejected — archived {n} task(s). Root stays on the board.\n")],
                 style=style)
            return 1

    show(
        [
            ("class:ok", "  ✔ Plan approved — tasks are on the board.\n"),
            ("class:hint",
             "  Next (Phase 4 dispatcher wiring): Hands pick up ready tasks.\n"
             "  Watch the board:  hermes kanban board --board trinity\n\n"),
        ],
        style=style,
    )
    return 0


def _cmd_theme(args: List[str]) -> int:
    from .menu import show

    style = _style()
    if args:
        name = args[0]
        if name not in theme_mod.available_themes():
            show([("class:error", f"  Unknown theme: {name}\n")], style=style)
            return 1
        theme_mod.set_theme(name)
        show([("class:ok", f"  Theme set to {name}\n")], style=style)
        return 0
    current = theme_mod.current_theme_name()
    lines = [("class:title", "  Themes\n")]
    for name, desc in theme_mod.available_themes().items():
        marker = "●" if name == current else "○"
        lines.append(("class:pointer" if name == current else "class:dim",
                      f"  {marker} {name:<14}"))
        lines.append(("class:text", f"{desc}\n"))
    show(lines, style=style)
    return 0


def main() -> None:
    paths.ensure_dirs()
    argv = sys.argv[1:]

    if argv and argv[0] == "--classic":
        _run_classic(argv[1:])
        return
    if argv and argv[0] == "theme":
        raise SystemExit(_cmd_theme(argv[1:]))
    if argv and argv[0] == "--spec":
        if len(argv) < 2:
            print("usage: trinity --spec <sessionspec.json>", file=sys.stderr)
            raise SystemExit(2)
        from pathlib import Path

        from .launcher import launch
        from .session_spec import SessionSpec
        from . import bundles

        data = paths.read_json(Path(argv[1]))
        if data is None:
            print(f"could not read spec: {argv[1]}", file=sys.stderr)
            raise SystemExit(2)
        spec = SessionSpec.from_dict(data)
        if not spec.skills:
            spec.skills = bundles.resolve(spec.task_path())
        problems = spec.validate()
        if problems:
            print("invalid spec: " + "; ".join(problems), file=sys.stderr)
            raise SystemExit(2)
        record = launch(spec)
        _print_launch_report(record, _style())
        # Headless: gate can't prompt, so it is skipped (interactive=False).
        raise SystemExit(_run_planning(spec, record, interactive=False))

    # Interactive: banner, then the mode selector (0.5).
    from .menu import BackNavigation, select, show

    style = _style()
    show(banner_fragments(), style=style)
    try:
        mode = select(
            "How do you want to work?",
            [
                ("Trinity pipeline", "Brain/Hands/Judge — configure, then watch it build"),
                ("Classic Hermes chat", "the original hermes conversation flow"),
            ],
            style=style, allow_other=False, allow_back=False,
        )
    except (KeyboardInterrupt, BackNavigation):
        raise SystemExit(1)

    if mode == "Classic Hermes chat":
        _run_classic(argv)
        return
    raise SystemExit(_run_pipeline())


if __name__ == "__main__":
    main()
