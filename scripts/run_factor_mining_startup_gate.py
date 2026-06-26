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
    round_state = _dict(packet.get("round_state"))
    quality_gate = _dict(packet.get("quality_gate"))
    control_contract = _dict(packet.get("pre_mining_control_contract"))
    method_contract = _dict(packet.get("method_optimization_contract"))
    quality_summary = _dict(quality_gate.get("summary"))
    quality_decision = _dict(quality_gate.get("decision"))
    governance = _dict(packet.get("round_governance"))
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
        "## Current Round State",
        "",
        f"- Last completed round: {round_state.get('last_completed_round')}",
        f"- Next round: {round_state.get('next_round')}",
        f"- Last three-round review: {round_state.get('last_three_round_review')}",
        f"- Last three-round decision: {round_state.get('last_three_round_decision')}",
        f"- Family rotation required: {round_state.get('family_rotation_required', False)}",
        f"- Next direction: {round_state.get('next_direction')}",
        f"- Blocked reentry families: {', '.join(_list(round_state.get('blocked_reentry_families'))) or 'none'}",
        f"- Required before next round: {', '.join(_list(round_state.get('required_before_next_round')))}",
        "",
        "## Round142 Quality Gate",
        "",
        f"- Status: {quality_gate.get('status', 'not_configured')}",
        f"- Startup cleared: {quality_decision.get('startup_gate_cleared', False)}",
        f"- Promotion cleared: {quality_decision.get('promotion_gate_cleared', False)}",
        f"- Implemented controls: {quality_summary.get('implemented_controls', 0)}",
        f"- Partial controls: {quality_summary.get('partial_controls', 0)}",
        f"- Planned controls: {quality_summary.get('planned_controls', 0)}",
        f"- Missing controls: {quality_summary.get('missing_controls', 0)}",
        f"- Areas: {', '.join(area.get('id', '') for area in _list_of_dicts(quality_gate.get('quality_areas')))}",
        "",
        "## Pre-mining Control Contract",
        "",
        f"- Scope: {control_contract.get('scope', '')}",
        f"- Direct factor generation allowed: {control_contract.get('direct_factor_generation_allowed', False)}",
        f"- Allowed next work modes: {', '.join(_list(control_contract.get('allowed_next_work_modes')))}",
        f"- Blocked next work modes: {', '.join(_list(control_contract.get('blocked_next_work_modes')))}",
        "",
        "| Area | Direct-ready | Blockers | Required outputs |",
        "|---|---:|---|---|",
    ]
    for area in _list_of_dicts(control_contract.get("areas")):
        lines.append(
            "| {area} | {ready} | {blockers} | {outputs} |".format(
                area=area.get("area_id", ""),
                ready=area.get("direct_mining_ready", False),
                blockers=", ".join(_list(area.get("direct_mining_blockers"))) or "none",
                outputs=", ".join(_list(area.get("required_outputs"))) or "none",
            )
        )
    method_stop_loss = _dict(method_contract.get("family_stop_loss"))
    lines.extend(
        [
            "",
            "## Method Optimization Contract",
            "",
            f"- Source audit: {method_contract.get('source_audit', '')}",
            f"- Next allowed direction: {method_contract.get('next_allowed_direction', '')}",
            f"- Promotion without contract allowed: {method_contract.get('promotion_allowed_without_contract', False)}",
            f"- Direct TopN expansion allowed: {method_contract.get('direct_topn_expansion_allowed_without_contract', False)}",
            f"- Hibernated families: {', '.join(_list(method_contract.get('hibernated_families'))) or 'none'}",
            f"- Zero-accepted walk-forward hibernates family: {method_stop_loss.get('hibernate_after_zero_accepted_walk_forward', False)}",
            f"- Reentry requires new orthogonal hypothesis: {method_stop_loss.get('reentry_requires_new_orthogonal_hypothesis', False)}",
            "",
            "| Area | Blocking | Required outputs |",
            "|---|---:|---|",
        ]
    )
    for area in _list_of_dicts(method_contract.get("optimization_areas")):
        lines.append(
            "| {area} | {blocking} | {outputs} |".format(
                area=area.get("area_id", ""),
                blocking=area.get("blocking_for_profit_claim", False),
                outputs=", ".join(_list(area.get("required_outputs"))) or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Round Governance",
            "",
            f"- Round unit: {governance.get('round_unit')}",
            f"- Review cadence: every {governance.get('review_every_n_rounds')} rounds",
            f"- GitHub sync cadence: every {governance.get('sync_every_n_rounds')} rounds",
            f"- Three-round review actions: {', '.join(_list(governance.get('three_round_review_required_actions')))}",
            f"- Ten-round sync actions: {', '.join(_list(governance.get('ten_round_sync_required_actions')))}",
            f"- Public reference projects: {', '.join(_list(governance.get('public_reference_projects')))}",
            f"- Profitability guardrails: {', '.join(_list(governance.get('profitability_guardrails')))}",
            "",
            "## Decision",
            "",
            f"- Cleared: {decision.get('startup_gate_cleared', False)}",
            "",
            "## Blockers",
            "",
        ]
    )
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


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


if __name__ == "__main__":
    main()
