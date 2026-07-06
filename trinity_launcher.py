#!/usr/bin/env python3
"""
Trinity launcher.

Mirrors the ``hermes`` wrapper at the repo root: makes ``python
trinity_launcher.py`` (or an installed ``trinity`` console script)
behave like the packaged command. Classic Hermes is untouched —
``trinity --classic`` or the mode selector hands off to it.
"""

if __name__ == "__main__":
    # Fail fast with guidance if this interpreter lacks the Hermes engine
    # deps — better than crashing after the user finishes the wizard.
    import sys
    try:
        import yaml  # noqa: F401  (stand-in for the full engine dep set)
        import prompt_toolkit  # noqa: F401
    except ImportError as exc:
        sys.stderr.write(
            f"Missing dependency: {exc.name}.\n"
            "Run Trinity with the Hermes virtualenv python, e.g.:\n"
            "  <hermes-install>\\venv\\Scripts\\python.exe trinity_launcher.py\n"
        )
        sys.exit(2)
    from trinity.main import main
    main()
