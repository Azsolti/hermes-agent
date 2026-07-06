# Trinity — Implementation Tasklist

> A multi-agent **orchestration harness** built on the Hermes Agent engine (MIT).
> **North star: reduce the cost of using state-of-the-art LLMs.** One expensive "Brain" model does the thinking (architecture, engineering, detailed specs) *once*; many cheap "Hand" models do the high-volume token work of writing code by following those specs exactly.
> **#1 product feature: total transparency.** The user must see everything happening under the hood — every task delegated, received, in-progress, and done, per agent, in real time.

## The cost thesis (why this exists)

SOTA models are expensive per token. Most of an engineering session's tokens are spent *writing code*, not *deciding what to write*. Trinity splits those:

- **Brain** (best/most expensive model) — architects the system and writes **detailed specs** (design, file layout, interfaces, acceptance criteria, *code examples but never full implementations*). High value-per-token, low volume.
- **Hands** (cheap models) — junior executors that turn specs into code. High volume, low cost-per-token. They self-help (web search) before asking, and follow the spec exactly.
- **Brain re-review** (optional) — Brain inspects Hand output, corrects course, adds tasks.
- **Judge** (optional, **vision-based**) — an outsider that screenshots the delivered UI and meticulously checks it against the intended task: misalignments, displaced elements, spacing, anything that makes a UI bad.

Every phase below should be evaluated against: *does this preserve the Brain-thinks-once / Hands-execute-cheaply economics, and is it transparent?*

## What the Hermes engine already gives us (leverage, don't rebuild)

| Trinity concept | Existing Hermes primitive | File(s) |
|---|---|---|
| Brain → decompose into a task graph on the board | `kanban decompose` (reads profile roster, LLM fans out linked children) | `hermes_cli/kanban_decompose.py` |
| Brain → tighten a single detailed spec | `kanban specify` | `hermes_cli/kanban_specify.py` |
| Brain→Hands→verify→synthesize topology | Kanban **swarm** (root → parallel workers → verifier → synthesizer + JSON blackboard) | `hermes_cli/kanban_swarm.py` |
| Auto-spawn Hand workers when tasks go ready | Kanban dispatcher loop | `hermes_cli/kanban*.py` |
| Hand specialization + per-role models | Multi-profile system | `hermes_cli/profiles.py`, `profile_describer.py` |
| Agentic "grill" questionnaire | `clarify()` tool (AI-initiated multiple choice) | `hermes_cli/tools_config.py`, `callbacks.py` |
| Judge vision review | Model vision/image input + screenshot handling + browser tools | `agent/image_routing.py`, `browser_provider.py`, adapters |
| Skill loading per task type | Skills system | `hermes_cli/skills_config.py`, `skills_hub.py` |
| Themeable TUI (Matrix) | Data-driven YAML skin engine | `hermes_cli/skin_engine.py` |
| Board persistence | Kanban SQLite | `hermes_cli/kanban_db.py` |
| Streaming tool output / existing TUI | Console engine | `hermes_cli/console_engine.py`, `curses_ui.py` |

**Implication:** the genuinely new work is (1) the **session configurator** (deterministic menus + agentic grill), (2) the **Brain/Hands/Brain/Judge orchestration + cost economics**, (3) the **vision Judge**, and (4) the **transparency dashboard**. The rest is wiring + rebrand.

---

## Decisions (locked)

1. **Rebrand depth** → Display-name + contained `trinity/` package; keep `hermes_cli` internals; `trinity` entrypoint, `~/.trinity/` config, Matrix banner. Optimizes upstream mergeability.
2. **TUI foundation** → Extend `console_engine.py`/`curses_ui.py`; reuse streaming/theming/keybindings.
3. **Default models** → Brain = DeepSeek Pro, Hands = DeepSeek Flash, Judge = GLM (vision-capable). Providers confirmed wireable.
4. **First task type (only one at launch)** → software-engineering → full-stack → **pure HTML/CSS/JS, no framework.**
5. **Dual-mode coexistence** → Classic Hermes stays fully intact. `hermes` entrypoint = untouched classic flow. `trinity` entrypoint = first-screen **mode selector**: **① Trinity pipeline** (default) or **② Classic Hermes chat** (one-line handoff to the existing `hermes_cli.main` conversation loop). Trinity is *additive* — it calls Hermes primitives as a library, deletes nothing, so classic flow cannot regress and upstream merges stay clean.
6. **Brain re-review trigger** → **Hand-reported only.** Brain re-reviews when a Hand reports uncertainty/escalation, not on a fixed schedule and not (initially) as a Judge-failure loop.
7. **Validation timing** → The Hands-follow-specs cost thesis (Phase 4.9) is tested once the whole system is built end-to-end, not gated earlier.
8. **Plan-approval gate** → **User-configurable toggle.** Session config offers "approve Brain's plan before Hands execute" ON (cost gate + control) or OFF (fully autonomous). Default ON.
9. **Hand workspace** → **Shared project dir + task dependencies.** All Hands write into one project folder; Brain sequences tasks with kanban dependencies so parallel Hands touch different files (e.g. structure Hand vs. styles Hand).
10. **Judge scope** → **User-configurable, cost-labeled.** Session config offers *Visual only* (cheaper) or *Visual + functional checks* (broader, pricier), with the cost implication shown at selection time.
11. **Budget guardrail** → Track **tokens universally** (always available); derive **cost estimates only where provider pricing is known** (provider-dependent — no reliable direct price/task otherwise). Optional cap can be token-based, or cost-based where pricing exists.
12. **Config format** → **JSON** for Trinity config + presets (`~/.trinity/config.json`, `~/.trinity/presets/*.json`); **`.env`** only for secrets/API keys (reusing Hermes's existing env handling). No YAML for Trinity-owned config.

## Still open (decide during build)

- **Judge mapping** — reuse swarm's verifier/synthesizer slot vs. a distinct vision stage. (Phase 5)
- **Config dir migration** — hard switch to `~/.trinity/` vs. dual-read `~/.hermes/` fallback (leaning dual-read).
- **State isolation** — Trinity profiles (`brain`/`hand-*`/`judge`) and kanban board should be namespaced / on their own board so Trinity mode never pollutes a user's classic Hermes profiles or tasks. (Phase 0)

---

## Phase 0 — Fork skeleton & rebrand

- [x] **0.1** `trinity_launcher.py` wrapper at repo root (mirrors `hermes` wrapper). *TODO: register `trinity` console_script in packaging.*
- [x] **0.2** Contained `trinity/` package created (`paths`, `theme`, `session_spec`, `menu`, `wizard`, `bundles`, `presets`, `launcher`, `banner`, `main`).
- [x] **0.3** `~/.trinity/` JSON config (`config.json`, `presets/`, `sessions/`, `themes/`, `bundles/`) with `TRINITY_HOME` override; `hermes_home()` helper for read-only fallbacks.
- [x] **0.4** Matrix banner in `trinity/banner.py`. *Broader string rebrand deferred — classic mode intentionally keeps Hermes branding.*
- [x] **0.5** Mode selector live: bare `trinity` → ① Trinity pipeline / ② Classic Hermes chat (one-line handoff to `hermes_cli.main`); `trinity --classic` skips the menu.
- [x] **0.6** State isolation: dedicated `trinity` kanban board (via `create_board`), root tasks assigned to `brain`, sandbox-tested with `HERMES_KANBAN_HOME`.
- [x] **0.7** Headless smoke test: 21/21 checks pass (spec round-trip, presets, themes, board creation, triage root, isolation); menu widget driven via pipe-input (arrows/enter/escape/back); classic handoff target verified.

## Phase 1 — Cost instrumentation (build this early — it's the whole point)

- [ ] **1.1** Per-role **token** accounting (universal, always available): attribute tokens to Brain vs. each Hand vs. Judge (hook into existing `account_usage.py`/`credits_tracker.py`).
- [ ] **1.2** **Cost estimation where pricing is known**: map tokens → $ using per-provider pricing metadata when available; otherwise show tokens only (cost is provider-dependent — no reliable direct price/task). Never fabricate a price.
- [ ] **1.3** Live readout in the dashboard (Phase 6): running tokens (+ $ estimate when known), split by role.
- [ ] **1.4** "Savings" estimate: actual token spend vs. a hypothetical all-Brain baseline — the headline metric that justifies the harness (expressed in tokens, and $ where pricing is known).
- [ ] **1.5** **Optional guardrail**: token-based cap (always) or cost-based cap (where pricing known); pause-and-ask near the limit. Configurable per session, default off/generous.
- [ ] **1.6** Per-session usage log persisted for comparison across presets/models.

## Phase 2 — Session configurator (deterministic menus + agentic grill)

> Hybrid: fixed menus where choices are predefined; agentic `clarify()`-driven questionnaire where they're open-ended ("Other", vague project, UI extremity). Arrow keys + always-present "Other".

- [x] **2.1** `SessionSpec` dataclass (`trinity/session_spec.py`) — all fields incl. plan gate, judge scope, token cap, UI-extremity guidance map, `brief()` generator with spec-discipline clause, `validate()`, JSON round-trip.
- [x] **2.2** Menu primitives (`trinity/menu.py`): arrow-key single-select with always-on "Other" free-text, toggle, single/multiline input, themed static text; Escape = back (`BackNavigation`), Ctrl-C = abort. Pipe-input tested.
- [x] **2.3** Task type menu (Software Engineering + "Other").
- [x] **2.4** Specialization menu (Full-stack + "Other").
- [x] **2.5** Framework menu (Pure HTML/CSS/JS + "Other") → resolves skill bundle at confirm.
- [x] **2.6** UI-extremity menu (conservative/standard/bold/super-experimental) → guidance text lands in the Brain brief.
- [x] **2.7** Per-role model menus with curated defaults + "Other" manual id. *TODO: source live list from provider config; enforce vision-capable Judge list.*
- [x] **2.8** Plan-gate toggle (default ON), Judge toggle + scope (cost-labeled), review depth, optional token cap.
- [x] **2.9** Multiline project description (Esc+Enter submits; empty rejected).
- [x] **2.10** Grill session v1 — deterministic essentials-only questionnaire triggered by vague descriptions, always ends with "anything you'd like to add?". *TODO Phase 4: swap in agentic `clarify()`-driven version.*
- [x] **2.11** Confirm summary screen (launch / save-preset-then-launch / start over); invalid specs can't launch; back-nav between all steps.
- [x] **2.12** Launcher (`trinity/launcher.py`): SessionSpec → `trinity` board + triage root task assigned to `brain` carrying the full brief + skills; session record persisted to `~/.trinity/sessions/`. *Dashboard drop-in comes with Phase 6; profile binding with Phase 4.*
- [x] **2.13** Configurator is the default `trinity` flow (after mode selector); `--spec file.json` headless path for automation/tests.

## Phase 3 — Skills per option (professional approach, shared across agents)

- [ ] **3.1** Author the skill bundle for `software-eng / fullstack / pure-html-css-js` (best practices: semantic HTML, responsive CSS, vanilla JS patterns, accessibility, no-framework project structure).
- [x] **3.2** Data-driven mapping (`trinity/bundles/*.json` + user `~/.trinity/bundles/*.json`): dotted task path → skill bundle; no code changes for new options.
- [ ] **3.3** Load the bundle into the **Brain and every Hand** so all agents share the same standards ("on the same page").
- [x] **3.4** "Other" framework → prefix fallback + single-sibling best-effort match in `bundles.resolve()`. *Manual skill pick UI still TODO.*

## Phase 4 — Brain / Hands / Brain / Judge orchestration

- [x] **4.0** Providers confirmed wireable by user (DeepSeek Pro/Flash, GLM). *Doc task remains: per-role API-key setup guide (9.3).*
- [x] **4.1** Trinity profiles implemented (`trinity/roles.py` + `pipeline.ensure_role_profiles`): namespaced `trinity-brain`/`trinity-hand-frontend`/`trinity-hand-testing`/`trinity-judge` Hermes profiles, each with role SOUL, roster description (drives decomposer assignee matching), and the session's model in config.yaml. Idempotent. *Tool allowlists TODO.*
- [x] **4.2** Brain planning wired: `pipeline.plan()` runs `kanban_decompose` on the `trinity` board (`scoped_current_board`); decomposer prompt already enforces parent-index dependencies → verified first-task `ready`, dependents `todo`.
- [x] **4.2a** Plan-approval gate live in `trinity/main.py`: plan shown per-task (assignee, title, spec first line); Reject archives all children (`cancel_plan`), root stays for re-plan; skipped when gate off or headless `--spec`.
- [ ] **4.2b** **Shared workspace**: one project dir per session; Hands read/write there; kanban ready-gating (deps from 4.2) prevents collisions. No git-worktree isolation for v1.
- [x] **4.3** Spec discipline encoded in the Brain SOUL ("full implementations are FORBIDDEN", standalone specs, dependency expression) + root-task brief carries the same clause. *Schema-level enforcement in decompose output TODO.*
- [ ] **4.4** **Hands = executors**: cheap models self-select ready tasks (dispatcher auto-spawns). Policy: follow the spec exactly, self-help via web search before asking, then escalate.
- [ ] **4.5** **Structured Hand reporting**: standard completion schema (what changed, files, self-test result, open questions) as JSON blackboard comments. *Schema defined and mandated in the Hand SOUL (`trinity/roles.py`); enforcement/parsing on completion TODO.*
- [ ] **4.6** **Brain re-review (hand-reported trigger)**: Brain re-reviews when a Hand reports uncertainty/escalation (not on a fixed schedule). On such a report Brain judges the work, corrects, adds follow-up tasks, or advances. On clean completion the root still wakes to advance toward Judge.
- [ ] **4.7** Hand → Brain escalation path (via clarify/comment) instead of blocking.
- [ ] **4.8** Dispatcher tuning: concurrency per Hand type, max runtime, retry/backoff (swarm supports `max_runtime_seconds`).
- [ ] **4.9** End-to-end (headless) test: portfolio-site brief → Brain specs → Hands build → Brain review → done on the board.

## Phase 5 — Judge (optional, vision-based UI review)

- [ ] **5.1** Serve/open the built HTML/CSS/JS and **capture screenshots** (reuse browser/preview tooling; multiple viewports for responsive checks).
- [ ] **5.2** Feed screenshots + the original task/spec to a **vision-capable outsider model** (GLM), different family from Brain/Hands to avoid implementation bias.
- [ ] **5.3** Judge prompt: meticulous checklist — does delivered match intended? misalignments, displaced/overlapping elements, spacing, contrast, broken layout, UI-extremity adherence.
- [ ] **5.3a** **Configurable scope** (from `SessionSpec`): *Visual only* (screenshots vs. intent) or *Visual + functional* (also links work / no console errors / basic interactions). Functional adds cost — the scope choice is shown with its cost implication at config time.
- [ ] **5.4** Judge output → structured findings on the board (pass / issues-with-locations).
- [ ] **5.5** Feedback loop: Judge findings become new Hand tasks (or Brain re-review), gated by review depth.
- [ ] **5.6** Judge is fully **optional** (wizard toggle) and clearly cost-attributed (Phase 1).

## Phase 6 — Transparency dashboard (the #1 feature)

- [ ] **6.1** Full-screen view (extending `console_engine`/`curses_ui`): kanban columns (triage/todo/ready/in-progress/done) with live state from `kanban_db`.
- [ ] **6.2** **Per-agent activity feed**: for every agent show *delegated task*, *received task*, *in-progress*, *done* — the core "see everything under the hood" requirement.
- [ ] **6.3** Worker pane: active Hands, their task, model, elapsed time; Brain and Judge status.
- [ ] **6.4** Live log/stream pane: tail each agent's tool output (reuse streaming plumbing).
- [ ] **6.5** Live **cost readout** (Phase 1): running spend split by role + "cost saved vs. all-Brain" estimate.
- [ ] **6.6** Inspect a task (spec + comments + Judge findings); answer a pending grill/escalation; pause/resume dispatcher; switch theme.
- [ ] **6.7** Wizard → dashboard handoff; graceful empty/all-done/blocked states.

## Phase 7 — Matrix theme & theming

- [x] **7.1** `matrix` theme (green-on-black, JSON per decision #12) is the built-in Trinity default (`trinity/theme.py`).
- [x] **7.2** `matrix-amber` + `ice` built-ins; `trinity theme [name]` lists/sets; user themes = JSON files in `~/.trinity/themes/` (all fields optional, inherit from matrix). *Wizard-driven custom-hex flow still TODO.*
- [x] **7.3** All widgets use theme style classes only — zero hardcoded colors in menu/wizard/banner.

## Phase 8 — Presets (save/load full session config)

- [x] **8.1** Preset = serialized `SessionSpec` as **JSON** in `~/.trinity/presets/` (project-specific fields stripped).
- [x] **8.2** Save-as-preset on the confirm screen; load-preset is wizard step 1; edit-after-load works (later steps default to loaded values).
- [x] **8.3** Starter preset `deepseek-glm-default` auto-created on first run.
- [ ] **8.4** `trinity preset list|show|delete` CLI subcommand (module functions exist in `trinity/presets.py`; CLI surface TODO).

## Phase 9 — Docs & upstream-merge

- [ ] **9.1** Trinity README: cost thesis, wizard-first flow, dashboard screenshots.
- [ ] **9.2** Maintainer doc: how Brain/Hands/Judge map onto kanban swarm/decompose.
- [ ] **9.3** Provider setup (DeepSeek, GLM) per role.
- [ ] **9.4** Upstream-merge notes: keep Trinity code in `trinity/` + rebrand isolated so Hermes updates pull cleanly.

---

## Suggested build order (fastest path to a provable demo)

Phase 0 → **4.0 provider check** → **Phase 4** (Brain/Hands on swarm+decompose, spec discipline) validated headless → **Phase 1** (cost instrumentation, so the demo *proves* the thesis) → **Phase 2/3** (configurator + skills, the front door) → **Phase 6** (transparency dashboard, the payoff) → **Phase 5** (vision Judge) → **7/8/9** (theme, presets, docs).

**Riskiest assumptions to de-risk first:** (a) DeepSeek/GLM are wireable as providers (4.0); (b) cheap Hand models actually follow Brain's detailed specs well enough that Brain-thinks-once holds — validate with a real portfolio-site run before investing in UI.
