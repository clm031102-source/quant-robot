from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DesktopShortcutSpec:
    shortcut_id: str
    filename: str
    page: str
    target_id: str = ""


DEFAULT_DESKTOP_SHORTCUTS = (
    DesktopShortcutSpec(
        shortcut_id="daily_pretrade_check",
        filename="量化机器人-今日交易检查.bat",
        page="daily",
        target_id="daily-pretrade-beginner-cards",
    ),
    DesktopShortcutSpec(
        shortcut_id="factor_leaderboard",
        filename="量化机器人-因子排行榜.bat",
        page="dashboard",
        target_id="factor-leaderboard-table",
    ),
    DesktopShortcutSpec(
        shortcut_id="logs_report",
        filename="量化机器人-日志报告.bat",
        page="logs",
    ),
)


def default_desktop_dir() -> Path:
    return Path.home() / "Desktop"


def build_shortcut_script(repo_root: Path, spec: DesktopShortcutSpec) -> str:
    target_arg = f" --target-id {spec.target_id}" if spec.target_id else ""
    return "\n".join(
        [
            "@echo off",
            "setlocal",
            f'cd /d "{repo_root}"',
            "echo Quant Robot beginner launcher (research-to-paper only; no broker/account/order/live trading).",
            f"python scripts\\run_desktop_app.py --page {spec.page}{target_arg}",
            "pause",
            "",
        ]
    )


def install_desktop_shortcuts(
    output_dir: str | Path | None = None,
    repo_root: str | Path | None = None,
    shortcuts: tuple[DesktopShortcutSpec, ...] = DEFAULT_DESKTOP_SHORTCUTS,
) -> dict[str, object]:
    destination = Path(output_dir) if output_dir is not None else default_desktop_dir()
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    destination.mkdir(parents=True, exist_ok=True)

    written: list[dict[str, str]] = []
    for spec in shortcuts:
        path = destination / spec.filename
        path.write_text(build_shortcut_script(root, spec), encoding="utf-8")
        written.append(
            {
                "shortcut_id": spec.shortcut_id,
                "path": str(path),
                "page": spec.page,
                "target_id": spec.target_id,
            }
        )

    return {
        "stage": "desktop_shortcut_install",
        "output_dir": str(destination),
        "repo_root": str(root),
        "shortcuts": written,
        "safety": {
            "mode": "research-to-paper only",
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
    }


def main(argv: list[str] | None = None) -> dict[str, object]:
    parser = argparse.ArgumentParser(description="Install beginner Quant Robot desktop launchers.")
    parser.add_argument("--output-dir", default=str(default_desktop_dir()), help="Folder where .bat launchers are written.")
    parser.add_argument("--repo-root", default=str(Path.cwd()), help="Repository root used by generated launchers.")
    args = parser.parse_args(argv)
    result = install_desktop_shortcuts(output_dir=args.output_dir, repo_root=args.repo_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    main()
