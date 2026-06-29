from __future__ import annotations

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.gui.desktop_app import main, run_desktop_app  # noqa: E402,F401


# CLI supports --no-open for operators who want to start the shell first.
if __name__ == "__main__":
    main()
