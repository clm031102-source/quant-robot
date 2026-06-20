from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.factor_mining_startup import build_factor_mining_startup_gate


DEFAULT_CONFIG = Path("configs/factor_mining_startup_cn_stock.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/factor_mining_startup_gate")


def run_factor_mining_startup_gate(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    machine: str,
    task: str,
    branch: str | None = None,
    current_branch: str | None = None,
    market: str = "CN",
    asset_type: str = "stock",
    commits_allowed: bool = False,
    pushes_allowed: bool = False,
    confirm_start: bool = False,
) -> dict[str, Any]:
    config = _load_config(config_path)
    confirmations = {name: True for name in _list(config.get("required_confirmations"))} if confirm_start else {}
    resolved_current_branch = current_branch or _current_branch()
    resolved_branch = branch or resolved_current_branch
    packet = build_factor_mining_startup_gate(
        config,
        request={
            "machine": machine,
            "task": task,
            "branch": resolved_branch,
            "market": market,
            "asset_type": asset_type,
            "commits_allowed": commits_allowed,
            "pushes_allowed": pushes_allowed,
            "confirmations": confirmations,
        },
        current_branch=resolved_current_branch,
    )
    _write_packet(output_dir, packet)
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    research_direction = _dict(packet.get("research_direction"))
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    stage_policy = _dict(research_direction.get("stage_policy"))
    rotation = _dict(research_direction.get("factor_family_rotation"))
    lines = [
        "# Factor Mining Startup Gate",
        "",
        f"- Stage: {packet.get('stage', 'factor_mining_startup_gate')}",
        f"- Status: {packet.get('status', 'unknown')}",
        f"- Machine: {summary.get('machine')}",
        f"- Task: {summary.get('task')}",
        f"- Branch: {summary.get('branch')}",
        f"- Current branch: {summary.get('current_branch')}",
        f"- Market: {summary.get('market')}",
        f"- Asset type: {summary.get('asset_type')}",
        f"- Commits allowed: {summary.get('commits_allowed')}",
        f"- Pushes allowed: {summary.get('pushes_allowed')}",
        f"- Live boundary allowed: {packet.get('live_boundary_allowed', False)}",
        f"- Required inputs: {', '.join(_list(packet.get('config_required_inputs')))}",
        "",
        "## Research Direction",
        "",
        f"- Objective: {research_direction.get('objective')}",
        f"- Mandate: {research_direction.get('mandate')}",
        f"- Target: {research_direction.get('target_market')} {research_direction.get('target_asset_type')}",
        f"- Allowed factor families: {', '.join(_list(research_direction.get('allowed_factor_families')))}",
        f"- Forbidden directions: {', '.join(_list(research_direction.get('forbidden_directions')))}",
        f"- Failed-batch rotation limit: {rotation.get('max_failed_batches_before_rotation')}",
        f"- Max single-family share: {rotation.get('max_single_family_share')}",
        "",
        "## Stage Policy",
        "",
        f"- Discovery: {stage_policy.get('discovery')}",
        f"- Validation: {stage_policy.get('validation')}",
        f"- Final holdout: {stage_policy.get('final_holdout')}",
        "",
        "## Repeatable Mining Protocol",
        "",
        f"- Source audit: {protocol.get('source_audit')}",
        f"- Next direction: {protocol.get('next_direction')}",
        f"- Recently rejected directions: {', '.join(_list(protocol.get('recently_rejected_directions')))}",
        f"- Required experiment design: {', '.join(_list(protocol.get('required_experiment_design')))}",
        f"- Confirm before each run: {', '.join(_list(protocol.get('confirm_before_each_run')))}",
        "",
        "## Decision",
        "",
        f"- Cleared: {decision.get('startup_gate_cleared', False)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = _list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Pre-run Checklist", ""])
    lines.extend(f"- {item}" for item in _list(packet.get("pre_run_checklist")))
    lines.extend(["", "## Confirmation Questions", ""])
    lines.extend(f"- {item}" for item in _list(packet.get("confirmation_questions")))
    lines.extend(["", f"Safety: {packet.get('safety', '')}", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Confirm the CN stock factor-mining startup gate before running factor batches.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--machine", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--branch")
    parser.add_argument("--current-branch")
    parser.add_argument("--market", default="CN")
    parser.add_argument("--asset-type", default="stock")
    parser.add_argument("--commits-allowed", action="store_true")
    parser.add_argument("--pushes-allowed", action="store_true")
    parser.add_argument("--confirm-start", action="store_true", help="Mark all required startup confirmations as explicitly accepted.")
    args = parser.parse_args()
    packet = run_factor_mining_startup_gate(
        config_path=args.config,
        output_dir=args.output_dir,
        machine=args.machine,
        task=args.task,
        branch=args.branch,
        current_branch=args.current_branch,
        market=args.market,
        asset_type=args.asset_type,
        commits_allowed=args.commits_allowed,
        pushes_allowed=args.pushes_allowed,
        confirm_start=args.confirm_start,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))


def _load_config(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_packet(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "factor_mining_startup_gate.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "factor_mining_startup_gate.md").write_text(render_markdown(packet), encoding="utf-8")


def _current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


if __name__ == "__main__":
    main()
