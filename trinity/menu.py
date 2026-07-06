"""Reusable prompt_toolkit menu primitives for Trinity (tasklist 2.2).

Deterministic, code-driven widgets: arrow-key single-select with an
always-available "Other" free-text fallback, yes/no toggle, free-text
and multiline input. All colors come from the active theme's style
classes — nothing hardcoded (tasklist 7.3).

Navigation contract: Escape (or left-arrow) raises :class:`BackNavigation`
so the wizard can step backward; Ctrl-C raises KeyboardInterrupt and
aborts the wizard entirely.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from prompt_toolkit import prompt
from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

OTHER = "__other__"


class BackNavigation(Exception):
    """User asked to go back one wizard step."""


def _fragments(
    title: str,
    options: Sequence[Tuple[str, str]],
    index: int,
    hint: str,
) -> FormattedText:
    frags: List[Tuple[str, str]] = [("class:title", f"  {title}\n\n")]
    for i, (label, desc) in enumerate(options):
        if i == index:
            frags.append(("class:pointer", "  ❯ "))
            frags.append(("class:selected", f" {label} "))
        else:
            frags.append(("class:dim", "    "))
            frags.append(("class:text", f" {label} "))
        if desc:
            frags.append(("class:dim", f" — {desc}"))
        frags.append(("", "\n"))
    frags.append(("class:hint", f"\n  {hint}\n"))
    return FormattedText(frags)


def select(
    title: str,
    options: Sequence[Tuple[str, str]],
    *,
    style: Style,
    allow_other: bool = True,
    other_prompt: str = "Type your answer",
    allow_back: bool = True,
    default_index: int = 0,
) -> str:
    """Arrow-key single-select. Returns the chosen option's label,
    or the free-text the user typed if they picked "Other".
    """
    opts: List[Tuple[str, str]] = list(options)
    if allow_other:
        opts.append(("Other…", "type a custom answer"))

    hint = "↑/↓ move · Enter select"
    if allow_back:
        hint += " · Esc back"

    state = {"index": max(0, min(default_index, len(opts) - 1)), "result": None}
    kb = KeyBindings()

    @kb.add("up")
    def _up(event) -> None:
        state["index"] = (state["index"] - 1) % len(opts)

    @kb.add("down")
    def _down(event) -> None:
        state["index"] = (state["index"] + 1) % len(opts)

    @kb.add("enter")
    def _enter(event) -> None:
        state["result"] = state["index"]
        event.app.exit()

    if allow_back:

        @kb.add("escape", eager=True)
        @kb.add("left")
        def _back(event) -> None:
            state["result"] = "back"
            event.app.exit()

    @kb.add("c-c")
    def _abort(event) -> None:
        event.app.exit(exception=KeyboardInterrupt())

    control = FormattedTextControl(
        lambda: _fragments(title, opts, state["index"], hint)
    )
    app: Application = Application(
        layout=Layout(HSplit([Window(control, always_hide_cursor=True)])),
        key_bindings=kb,
        style=style,
        full_screen=False,
        mouse_support=False,
    )
    app.run()

    if state["result"] == "back":
        raise BackNavigation()
    chosen = opts[state["result"]][0]
    if allow_other and chosen == "Other…":
        answer = text_input(other_prompt, style=style)
        return answer.strip() or select(  # empty "Other" -> re-ask
            title, options, style=style, allow_other=allow_other,
            other_prompt=other_prompt, allow_back=allow_back,
        )
    return chosen


def toggle(
    title: str,
    *,
    style: Style,
    default: bool = True,
    on_label: str = "Yes",
    off_label: str = "No",
    on_desc: str = "",
    off_desc: str = "",
    allow_back: bool = True,
) -> bool:
    """Two-option select rendered with the same widget."""
    choice = select(
        title,
        [(on_label, on_desc), (off_label, off_desc)],
        style=style,
        allow_other=False,
        allow_back=allow_back,
        default_index=0 if default else 1,
    )
    return choice == on_label


def text_input(title: str, *, style: Style, default: str = "") -> str:
    """Single-line free text ("Other" fallback and short answers)."""
    return prompt(
        FormattedText([("class:accent", f"  {title}: ")]),
        style=style,
        default=default,
    )


def multiline_input(title: str, *, style: Style, default: str = "") -> str:
    """Multiline editor for the project description (Esc then Enter submits)."""
    return prompt(
        FormattedText(
            [
                ("class:accent", f"  {title}\n"),
                ("class:hint", "  (finish with Esc followed by Enter)\n"),
                ("class:accent", "  > "),
            ]
        ),
        style=style,
        multiline=True,
        default=default,
    )


def show(lines: List[Tuple[str, str]], *, style: Style) -> None:
    """Print themed static text (summaries, banners) without a widget.

    Falls back to plain stdout when no usable console exists (piped
    output, CI, ``--spec`` headless runs on Windows).
    """
    from prompt_toolkit import print_formatted_text

    try:
        print_formatted_text(FormattedText(lines), style=style)
    except Exception:
        print("".join(text for _, text in lines))
