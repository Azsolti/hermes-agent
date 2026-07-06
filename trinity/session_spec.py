"""SessionSpec — the backbone of Trinity.

Every behavioral decision the user makes in the wizard resolves to a
field here; the orchestration reads it once at launch and stays
branch-free at runtime. Presets are just serialized SessionSpecs
(JSON, locked decision #12).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# Roles in the pipeline. Brain thinks once (expensive); Hands execute
# cheaply; Judge is the optional vision outsider.
ROLE_BRAIN = "brain"
ROLE_HAND_FRONTEND = "hand-frontend"
ROLE_HAND_TESTING = "hand-testing"
ROLE_JUDGE = "judge"

# v1 launches with the pure-HTML/CSS/JS path, so frontend+testing Hands
# (locked decision #4). Backend/integration Hands arrive with new task types.
ALL_ROLES = [ROLE_BRAIN, ROLE_HAND_FRONTEND, ROLE_HAND_TESTING, ROLE_JUDGE]

DEFAULT_MODELS: Dict[str, str] = {
    ROLE_BRAIN: "deepseek-pro",
    ROLE_HAND_FRONTEND: "deepseek-flash",
    ROLE_HAND_TESTING: "deepseek-flash",
    ROLE_JUDGE: "glm-4v",
}

JUDGE_SCOPES = ["visual", "visual+functional"]
REVIEW_DEPTHS = ["light", "standard", "thorough"]
UI_EXTREMITY_LEVELS = ["conservative", "standard", "bold", "super-experimental"]

# Appended to the Brain prompt so the chosen extremity level actually
# shapes the design (tasklist 2.6).
UI_EXTREMITY_GUIDANCE: Dict[str, str] = {
    "conservative": (
        "UI style mandate: CONSERVATIVE. Proven, familiar patterns only. "
        "No experimental layouts, no flashy animation. Prioritize clarity "
        "and convention over novelty."
    ),
    "standard": (
        "UI style mandate: STANDARD. Modern, polished, tasteful. Subtle "
        "motion and contemporary layout are welcome; avoid gimmicks."
    ),
    "bold": (
        "UI style mandate: BOLD. Take real visual risks — strong typography, "
        "unusual layout, expressive color and motion — while keeping the "
        "site usable and accessible."
    ),
    "super-experimental": (
        "UI style mandate: SUPER-EXPERIMENTAL. Push as far as the medium "
        "allows: unconventional navigation, generative/interactive visuals, "
        "scroll-driven scenes, WebGL-adjacent canvas tricks. Usability may "
        "bend but must not break; accessibility basics still apply."
    ),
}


@dataclass
class SessionSpec:
    """Complete, self-contained configuration for one Trinity session."""

    # What to build
    task_type: str = "software-engineering"
    specialization: str = "full-stack"
    framework: str = "pure-html-css-js"
    project_description: str = ""
    grill_answers: List[Dict[str, str]] = field(default_factory=list)

    # Who builds it (role -> model id)
    models: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_MODELS))

    # Pipeline behavior
    plan_approval_gate: bool = True          # locked decision #8, default ON
    brain_re_review: str = "hand-reported"   # locked decision #6
    judge_enabled: bool = True
    judge_scope: str = "visual"              # locked decision #10
    review_depth: str = "standard"
    ui_extremity: str = "standard"

    # Guardrails (locked decision #11: tokens universal, $ only if known)
    token_cap: Optional[int] = None

    # Resolved by the bundle mapping at confirm time (tasklist 3.2)
    skills: List[str] = field(default_factory=list)

    # Bookkeeping
    preset_name: Optional[str] = None
    theme: str = "matrix"

    # ---- serialization -------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionSpec":
        """Lenient load: unknown keys ignored, missing keys defaulted."""
        known = {f for f in cls.__dataclass_fields__}  # noqa: C401
        return cls(**{k: v for k, v in (data or {}).items() if k in known})

    # ---- derived -------------------------------------------------------

    def task_path(self) -> str:
        """Dotted path used to resolve the skill bundle."""
        return f"{self.task_type}.{self.specialization}.{self.framework}"

    def ui_extremity_prompt(self) -> str:
        return UI_EXTREMITY_GUIDANCE.get(
            self.ui_extremity, UI_EXTREMITY_GUIDANCE["standard"]
        )

    def brief(self) -> str:
        """The root-task body the Brain decomposes from."""
        lines = [
            f"# Project brief ({self.task_path()})",
            "",
            self.project_description.strip(),
            "",
        ]
        if self.grill_answers:
            lines.append("## Clarifications from the user")
            for qa in self.grill_answers:
                lines.append(f"- **{qa.get('q', '?')}** {qa.get('a', '')}")
            lines.append("")
        lines += [
            "## Constraints",
            f"- {self.ui_extremity_prompt()}",
            f"- Review depth: {self.review_depth}.",
            f"- Judge: {'enabled, scope=' + self.judge_scope if self.judge_enabled else 'disabled'}.",
            f"- Skills in play: {', '.join(self.skills) if self.skills else '(none resolved)'}.",
            "",
            "## Spec discipline (cost lever)",
            "- Brain writes DETAILED specs: design, file layout, interfaces,",
            "  acceptance criteria. Code examples are allowed; full",
            "  implementations are NOT — Hands write the code.",
        ]
        return "\n".join(lines)

    def validate(self) -> List[str]:
        """Return a list of human-readable problems (empty = valid)."""
        problems: List[str] = []
        if not self.project_description.strip():
            problems.append("project description is empty")
        if self.judge_scope not in JUDGE_SCOPES:
            problems.append(f"unknown judge scope: {self.judge_scope!r}")
        if self.review_depth not in REVIEW_DEPTHS:
            problems.append(f"unknown review depth: {self.review_depth!r}")
        if self.ui_extremity not in UI_EXTREMITY_LEVELS:
            problems.append(f"unknown UI extremity: {self.ui_extremity!r}")
        for role in (ROLE_BRAIN, ROLE_HAND_FRONTEND):
            if not self.models.get(role):
                problems.append(f"no model bound for role {role!r}")
        if self.token_cap is not None and self.token_cap <= 0:
            problems.append("token cap must be positive")
        return problems
