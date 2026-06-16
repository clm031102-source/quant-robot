from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

try:
    from scripts.run_walk_forward import assert_walk_forward_succeeded, run_walk_forward
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from run_walk_forward import assert_walk_forward_succeeded, run_walk_forward


DEFAULT_CONFIG_PATH = Path("configs/walk_forward_tushare_moneyflow_residual_regime.json")
DEFAULT_DATA_ROOT = Path("data/processed")


def run_desktop_factor_validation(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    source: str = "processed-bars",
    data_root: str | Path = DEFAULT_DATA_ROOT,
    output_dir: str | Path | None = None,
    require_accepted: bool = False,
) -> dict[str, object]:
    result = run_walk_forward(
        config_path=Path(config_path),
        source=source,
        data_root=Path(data_root),
        output_dir=Path(output_dir) if output_dir is not None else None,
    )
    assert_walk_forward_succeeded(result, allow_no_accepted=not require_accepted)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the desktop strict residual-regime factor validation profile."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="processed-bars")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--output-dir")
    parser.add_argument(
        "--require-accepted",
        action="store_true",
        help="Fail when validation completes but every candidate is rejected.",
    )
    args = parser.parse_args()
    result = run_desktop_factor_validation(
        config_path=Path(args.config),
        source=args.source,
        data_root=Path(args.data_root),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        require_accepted=args.require_accepted,
    )
    print(json.dumps({"summary": result["summary"], "top": result["leaderboard"][:20]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
