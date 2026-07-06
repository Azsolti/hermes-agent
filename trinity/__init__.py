"""Trinity — multi-agent orchestration harness on the Hermes engine.

Brain (expensive model) architects and writes detailed specs once;
Hands (cheap models) execute them; an optional vision Judge reviews
the result. Everything is configured up-front via the session wizard,
and everything that happens is transparent on the kanban board.

Trinity is additive: it calls Hermes primitives (kanban, profiles,
agent loop) as a library and modifies nothing, so the classic
``hermes`` flow keeps working untouched.
"""

__version__ = "0.1.0"
PRODUCT_NAME = "Trinity"
TRINITY_BOARD = "trinity"  # dedicated kanban board slug (state isolation)
