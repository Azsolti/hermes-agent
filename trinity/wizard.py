"""The Trinity session wizard (Phase 2).

Deterministic, code-driven step sequence — fixed menus in fixed order,
each with an "Other" free-text fallback. The only agentic part is the
grill session (2.10), which in v1 is a deterministic essentials-only
questionnaire; the clarify()-driven version arrives with Phase 4 wiring.

Escape steps backward; Ctrl-C aborts. Returns a validated SessionSpec
or None if the user aborted.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from prompt_toolkit.styles import Style

from . import bundles, presets, theme as theme_mod
from .menu import BackNavigation, multiline_input, select, show, text_input, toggle
from .session_spec import (
    ALL_ROLES,
    JUDGE_SCOPES,
    REVIEW_DEPTHS,
    ROLE_BRAIN,
    ROLE_HAND_FRONTEND,
    ROLE_HAND_TESTING,
    ROLE_JUDGE,
    SessionSpec,
    UI_EXTREMITY_LEVELS,
)

# Curated model choices per role; "Other" always allows any model id.
MODEL_CHOICES = {
    ROLE_BRAIN: [
        ("deepseek-pro", "default Brain — strong architect, expensive"),
        ("claude-opus-4-8", "Anthropic flagship"),
    ],
    ROLE_HAND_FRONTEND: [
        ("deepseek-flash", "default Hand — cheap, fast executor"),
        ("claude-haiku-4-5", "Anthropic small model"),
    ],
    ROLE_HAND_TESTING: [
        ("deepseek-flash", "default Hand — cheap, fast executor"),
        ("claude-haiku-4-5", "Anthropic small model"),
    ],
    ROLE_JUDGE: [
        ("glm-4v", "default Judge — vision-capable, different family"),
        ("claude-sonnet-5", "Anthropic, vision-capable"),
    ],
}

ROLE_TITLES = {
    ROLE_BRAIN: "Brain (architect — plans and writes specs)",
    ROLE_HAND_FRONTEND: "Frontend Hand (writes the code)",
    ROLE_HAND_TESTING: "Testing Hand (verifies the code)",
    ROLE_JUDGE: "Judge (vision review of the result)",
}

_VAGUE_WORD_THRESHOLD = 12  # descriptions shorter than this get grilled

Step = Callable[[SessionSpec, Style], None]


# --------------------------------------------------------------------------
# Steps (each mutates the spec in place; BackNavigation bubbles up)
# --------------------------------------------------------------------------

def step_preset(spec: SessionSpec, style: Style) -> None:
    presets.ensure_starter_preset()
    saved = presets.list_presets()
    options: List[Tuple[str, str]] = [("New session", "configure from scratch")]
    options += [(p["name"], p["description"]) for p in saved]
    choice = select(
        "Start from a preset?", options,
        style=style, allow_other=False, allow_back=False,
    )
    if choice != "New session":
        loaded = presets.load_preset(choice)
        if loaded is not None:
            # Copy preset fields onto the live spec (edit-after-load, 8.2).
            for k, v in loaded.to_dict().items():
                setattr(spec, k, v)


def step_task_type(spec: SessionSpec, style: Style) -> None:
    spec.task_type = _slugify(select(
        "What kind of task is this?",
        [("Software Engineering", "the only built-in type for now")],
        style=style, other_prompt="Describe the task type",
    ))


def step_specialization(spec: SessionSpec, style: Style) -> None:
    spec.specialization = _slugify(select(
        "Specialization?",
        [("Full-stack development", "front-to-back web work")],
        style=style, other_prompt="Describe the specialization",
    ))


def step_framework(spec: SessionSpec, style: Style) -> None:
    spec.framework = _slugify(select(
        "Framework / stack?",
        [("Pure HTML/CSS/JS (no framework)", "hand-rolled, zero dependencies")],
        style=style, other_prompt="Name the framework/stack",
    ))
    if spec.framework.startswith("pure-html"):
        spec.framework = "pure-html-css-js"


def step_models(spec: SessionSpec, style: Style) -> None:
    for role in ALL_ROLES:
        current = spec.models.get(role, "")
        choices = MODEL_CHOICES.get(role, [])
        default_index = next(
            (i for i, (m, _) in enumerate(choices) if m == current), 0
        )
        spec.models[role] = select(
            f"Model for {ROLE_TITLES[role]}",
            choices,
            style=style,
            other_prompt="Enter a model id",
            default_index=default_index,
        )


def step_pipeline_options(spec: SessionSpec, style: Style) -> None:
    spec.plan_approval_gate = toggle(
        "Pause for your approval after the Brain writes the plan?",
        style=style, default=spec.plan_approval_gate,
        on_desc="review specs before any Hand spends tokens (recommended)",
        off_desc="fully autonomous — watch live on the dashboard",
    )
    spec.judge_enabled = toggle(
        "Enable the Judge (vision review of the final result)?",
        style=style, default=spec.judge_enabled,
        on_desc="an outsider model screenshots and critiques the result",
        off_desc="skip — cheapest option",
    )
    if spec.judge_enabled:
        spec.judge_scope = select(
            "Judge scope?",
            [
                ("visual", "screenshots vs. intent only — cheaper"),
                ("visual+functional", "also links/console/interactions — costs more"),
            ],
            style=style, allow_other=False,
            default_index=JUDGE_SCOPES.index(spec.judge_scope)
            if spec.judge_scope in JUDGE_SCOPES else 0,
        )
    spec.review_depth = select(
        "Review depth?",
        [
            ("light", "Brain glances at completed work"),
            ("standard", "Brain checks acceptance criteria"),
            ("thorough", "Brain re-reads everything — costs more"),
        ],
        style=style, allow_other=False,
        default_index=REVIEW_DEPTHS.index(spec.review_depth)
        if spec.review_depth in REVIEW_DEPTHS else 1,
    )
    spec.ui_extremity = select(
        "How experimental may the UI get?",
        [
            ("conservative", "proven, familiar patterns only"),
            ("standard", "modern and polished"),
            ("bold", "real visual risks"),
            ("super-experimental", "push the medium as far as it goes"),
        ],
        style=style, allow_other=False,
        default_index=UI_EXTREMITY_LEVELS.index(spec.ui_extremity)
        if spec.ui_extremity in UI_EXTREMITY_LEVELS else 1,
    )
    cap = text_input(
        "Token cap for this session (empty = none)",
        style=style,
        default=str(spec.token_cap) if spec.token_cap else "",
    ).strip()
    spec.token_cap = int(cap) if cap.isdigit() and int(cap) > 0 else None


def step_description(spec: SessionSpec, style: Style) -> None:
    while True:
        spec.project_description = multiline_input(
            "Describe what you want to build",
            style=style, default=spec.project_description,
        ).strip()
        if spec.project_description:
            return
        show([("class:warn", "  The description can't be empty.\n")], style=style)


def step_grill(spec: SessionSpec, style: Style) -> None:
    """Essentials-only grill (2.10). v1 is deterministic; agentic
    clarify() takes over in Phase 4. Always ends with the open question.
    """
    spec.grill_answers = []
    vague = len(spec.project_description.split()) < _VAGUE_WORD_THRESHOLD
    essentials = [
        ("Who is the audience for this?", vague),
        ("What are the 2-3 most important things a visitor should be able to do?", vague),
        ("Any content you already have (texts, images, brand colors)?", vague),
        ("Anything you'd like to add?", True),  # always asked, always last
    ]
    for question, ask in essentials:
        if not ask:
            continue
        answer = text_input(question, style=style).strip()
        if answer:
            spec.grill_answers.append({"q": question, "a": answer})


def _slugify(value: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower()).strip("-")
    return slug or "other"


# --------------------------------------------------------------------------
# Wizard driver
# --------------------------------------------------------------------------

STEPS: List[Step] = [
    step_preset,
    step_task_type,
    step_specialization,
    step_framework,
    step_models,
    step_pipeline_options,
    step_description,
    step_grill,
]


def _summary_lines(spec: SessionSpec) -> List[Tuple[str, str]]:
    rows = [
        ("Build", spec.task_path()),
        ("Brain", spec.models.get(ROLE_BRAIN, "?")),
        ("Frontend Hand", spec.models.get(ROLE_HAND_FRONTEND, "?")),
        ("Testing Hand", spec.models.get(ROLE_HAND_TESTING, "?")),
        ("Judge", (spec.models.get(ROLE_JUDGE, "?") + f" ({spec.judge_scope})")
                  if spec.judge_enabled else "disabled"),
        ("Plan approval", "on" if spec.plan_approval_gate else "off (autonomous)"),
        ("Review depth", spec.review_depth),
        ("UI extremity", spec.ui_extremity),
        ("Token cap", f"{spec.token_cap:,}" if spec.token_cap else "none"),
        ("Skills", ", ".join(spec.skills) or "(none)"),
    ]
    lines: List[Tuple[str, str]] = [("class:title", "\n  Session summary\n\n")]
    for label, value in rows:
        lines.append(("class:accent", f"  {label:>14}  "))
        lines.append(("class:text", f"{value}\n"))
    desc = spec.project_description
    lines.append(("class:accent", "\n  Project\n"))
    lines.append(("class:text", f"  {desc[:300]}{'…' if len(desc) > 300 else ''}\n\n"))
    return lines


def run_wizard(theme_name: Optional[str] = None) -> Optional[SessionSpec]:
    """Run all steps; returns a validated SessionSpec or None on abort."""
    name = theme_name or theme_mod.current_theme_name()
    style = theme_mod.to_style(theme_mod.load_theme(name))
    spec = SessionSpec(theme=name)

    i = 0
    while i < len(STEPS):
        try:
            STEPS[i](spec, style)
            i += 1
        except BackNavigation:
            i = max(0, i - 1)
        except KeyboardInterrupt:
            return None

    # Resolve the skill bundle from the chosen path (2.12 / 3.2).
    spec.skills = bundles.resolve(spec.task_path())

    while True:
        show(_summary_lines(spec), style=style)
        problems = spec.validate()
        if problems:
            show([("class:error", "  Problems: " + "; ".join(problems) + "\n")],
                 style=style)
        try:
            action = select(
                "Launch with this configuration?",
                [
                    ("Launch", "start the pipeline"),
                    ("Save as preset, then launch", "reuse this setup later"),
                    ("Start over", "discard and reconfigure"),
                ],
                style=style, allow_other=False, allow_back=False,
            )
        except KeyboardInterrupt:
            return None
        if action == "Start over":
            return run_wizard(theme_name)
        if problems:
            continue  # can't launch an invalid spec; loop back to summary
        if action == "Save as preset, then launch":
            pname = text_input("Preset name", style=style).strip()
            if pname:
                presets.save_preset(pname, spec)
                spec.preset_name = pname
        return spec
