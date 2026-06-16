from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.recent_data_refresh import build_workstation_refresh_context


STAGE = "phase_5_12_tushare_activation_gate"


def build_tushare_activation_gate_pack(
    *,
    readiness: dict[str, Any],
    source: str = "tushare",
    market: str = "CN_ETF",
    execute: bool = False,
    recent_data_refresh: dict[str, Any] | None = None,
    post_refresh_replay: dict[str, Any] | None = None,
    observation_sufficiency: dict[str, Any] | None = None,
    iterative_observation_expansion: dict[str, Any] | None = None,
    chain_error: dict[str, Any] | None = None,
    machine: str | None = None,
    workstation_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_name = source.strip().lower()
    readiness_pack = _dict(readiness)
    workstation = build_workstation_refresh_context(machine, workstation_config)
    can_run_data_pipeline = bool(workstation.get("can_run_data_pipeline", True))
    effective_execute = bool(execute and can_run_data_pipeline)
    recent = _dict(recent_data_refresh)
    post = _dict(post_refresh_replay)
    sufficiency = _dict(observation_sufficiency)
    iterative = _dict(iterative_observation_expansion)
    recent_decision = _dict(recent.get("decision"))
    post_decision = _dict(post.get("decision"))
    sufficiency_decision = _dict(sufficiency.get("decision"))
    iterative_decision = _dict(iterative.get("decision"))
    recent_ready = bool(recent_decision.get("recent_data_ready", False) and recent_decision.get("signal_data_stale_cleared", False))
    post_allowed = bool(post_decision.get("post_refresh_replay_allowed", False))
    sufficiency_cleared = bool(sufficiency_decision.get("observation_sufficiency_cleared", False))
    iterative_cleared = bool(iterative_decision.get("iterative_observation_cleared", False))
    paper_ready = bool(recent_ready and (sufficiency_cleared or iterative_cleared))
    readiness_missing = _as_list(readiness_pack.get("missing"))
    readiness_blocked = source_name == "tushare" and not bool(readiness_pack.get("ready", False))

    if readiness_blocked:
        status = "blocked_missing_readiness"
    elif not effective_execute:
        status = "ready_to_execute"
    elif chain_error:
        status = "activation_chain_failed"
    elif paper_ready:
        status = "paper_observation_ready"
    else:
        status = "paper_gate_blocked"

    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "source": source_name,
        "market": market.upper(),
        "mode": "execute" if effective_execute else "dry_run",
        "workstation": workstation,
        "readiness": readiness_pack,
        "recent_data_refresh": _recent_summary(recent),
        "post_refresh_replay": _post_refresh_summary(post),
        "observation_sufficiency": _sufficiency_summary(sufficiency),
        "iterative_observation_expansion": _iterative_summary(iterative),
        "final_observation_sufficiency": _final_sufficiency(sufficiency, iterative),
        "stage_ledger": _stage_ledger(recent, post, sufficiency, iterative),
        "chain_error": chain_error or {},
        "decision": {
            "tushare_ready": bool(readiness_pack.get("ready", False)) or source_name != "tushare",
            "execute_requested": bool(execute),
            "recent_data_ready": recent_ready,
            "post_refresh_replay_allowed": post_allowed,
            "observation_sufficiency_cleared": sufficiency_cleared,
            "iterative_observation_cleared": iterative_cleared,
            "activation_chain_allowed": paper_ready,
            "paper_continuation_allowed": paper_ready,
            "blockers": _blockers(
                status,
                readiness_missing,
                recent_decision,
                post_decision,
                sufficiency_decision,
                iterative_decision,
                chain_error,
            ),
        },
        "live_boundary_allowed": False,
        "safety": _safety(),
    }
    pack["next_actions"] = _next_actions(pack)
    pack["markdown"] = render_tushare_activation_gate_markdown(pack)
    return _sanitize(pack)


def write_tushare_activation_gate_pack(report_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(report_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "tushare_activation_gate_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "tushare_activation_gate_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("stage_ledger", [])).to_csv(output_path / "tushare_activation_gate_stage_ledger.csv", index=False)
    pd.DataFrame(pack.get("next_actions", [])).to_csv(output_path / "tushare_activation_gate_next_actions.csv", index=False)


def render_tushare_activation_gate_markdown(pack: dict[str, Any]) -> str:
    decision = _dict(pack.get("decision"))
    final = _dict(pack.get("final_observation_sufficiency"))
    fills = _dict(final.get("fills"))
    lines = [
        "# Phase 5.12 Tushare Activation Gate",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status', 'unknown')}",
        f"- Source: {pack.get('source', 'tushare')}",
        f"- Mode: {pack.get('mode', 'dry_run')}",
        f"- Recent data ready: {decision.get('recent_data_ready', False)}",
        f"- Post-refresh replay allowed: {decision.get('post_refresh_replay_allowed', False)}",
        f"- Observation sufficiency cleared: {decision.get('observation_sufficiency_cleared', False)}",
        f"- Iterative observation cleared: {decision.get('iterative_observation_cleared', False)}",
        f"- Final fills: {fills.get('observed_fills')} / {fills.get('required_fills')}",
        f"- Paper continuation allowed: {decision.get('paper_continuation_allowed', False)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Stage Ledger",
        "",
    ]
    ledger = pack.get("stage_ledger", []) if isinstance(pack.get("stage_ledger"), list) else []
    if ledger:
        lines.extend(
            f"- {row.get('stage')}: {row.get('status')} / cleared={row.get('cleared')} / blockers={row.get('blockers')}"
            for row in ledger
            if isinstance(row, dict)
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Blockers", ""])
    blockers = decision.get("blockers", []) if isinstance(decision.get("blockers"), list) else []
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Next Actions", ""])
    actions = pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else []
    if actions:
        lines.extend(f"- {row.get('action')}: {row.get('reason')}" for row in actions if isinstance(row, dict))
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _blockers(
    status: str,
    readiness_missing: list[str],
    recent_decision: dict[str, Any],
    post_decision: dict[str, Any],
    sufficiency_decision: dict[str, Any],
    iterative_decision: dict[str, Any],
    chain_error: dict[str, Any] | None,
) -> list[str]:
    blockers: list[str] = []
    if status == "ready_to_execute":
        return []
    if status == "paper_observation_ready":
        return []
    blockers.extend(readiness_missing)
    if chain_error:
        blockers.append(f"{chain_error.get('stage', 'tushare_activation_gate')}_failed: {chain_error.get('error', 'unknown error')}")
    blockers.extend(_as_list(recent_decision.get("blockers")))
    blockers.extend(_as_list(post_decision.get("blockers")))
    blockers.extend(_as_list(sufficiency_decision.get("blockers")))
    blockers.extend(_as_list(iterative_decision.get("blockers")))
    if status == "paper_gate_blocked" and not blockers:
        blockers.append("paper_continuation_gate_not_cleared")
    return _unique(blockers)


def _next_actions(pack: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(pack.get("decision"))
    blockers = _as_list(decision.get("blockers"))
    actions: list[dict[str, Any]] = []
    workstation = _dict(pack.get("workstation"))
    if pack.get("status") in {"blocked_missing_readiness", "ready_to_execute", "activation_chain_failed", "paper_gate_blocked"} and not bool(
        workstation.get("can_run_data_pipeline", True)
    ):
        return [_handoff_activation_action(workstation)]
    if any("TUSHARE_TOKEN" in blocker for blocker in blockers):
        actions.append(
            {
                "action": "set_tushare_token_env",
                "command": "setx TUSHARE_TOKEN <your-token>",
                "local_only": True,
                "reason": "Set the Tushare token locally, open a new shell, then rerun the activation gate with --execute.",
            }
        )
    if any("tushare package" in blocker.lower() for blocker in blockers):
        actions.append(
            {
                "action": "install_tushare_package",
                "command": ".\\.venv\\Scripts\\python.exe -m pip install tushare",
                "local_only": True,
                "reason": "The Tushare Python package is required before the real provider refresh can run.",
            }
        )
    if pack.get("status") == "ready_to_execute":
        actions.append(
            {
                "action": "execute_tushare_activation_gate",
                "command": "python scripts\\run_tushare_activation_gate.py --execute",
                "local_only": True,
                "reason": "Readiness is clear; execute the local paper-only activation chain.",
            }
        )
    if pack.get("status") == "paper_observation_ready":
        actions.append(
            {
                "action": "continue_paper_observation_on_validated_window",
                "local_only": True,
                "reason": "Recent data replay and sample sufficiency cleared under the current paper-only policy.",
            }
        )
    if pack.get("status") == "activation_chain_failed":
        actions.append(
            {
                "action": "inspect_activation_chain_error",
                "local_only": True,
                "reason": "A downstream local workflow raised an error during the activation chain.",
            }
        )
    if pack.get("status") == "paper_gate_blocked":
        actions.append(
            {
                "action": "inspect_paper_gate_blockers",
                "local_only": True,
                "reason": "The activation chain ran but a paper-only gate still blocked continuation.",
            }
        )
    if not actions:
        actions.append(
            {
                "action": "resolve_activation_readiness",
                "local_only": True,
                "reason": "The activation gate is blocked before paper continuation can be evaluated.",
            }
        )
    return actions


def _handoff_activation_action(workstation: dict[str, Any]) -> dict[str, Any]:
    recommended = _as_list(workstation.get("data_pipeline_machines"))
    primary_machine = recommended[0] if recommended else "highspec_desktop"
    branch = workstation.get("data_pipeline_branch") or "codex/tushare-data-pipeline"
    return {
        "action": "handoff_tushare_activation_gate",
        "command": f"python scripts\\run_tushare_activation_gate.py --machine {primary_machine} --execute",
        "local_only": False,
        "requires_machine_handoff": True,
        "recommended_machines": recommended,
        "recommended_branch": branch,
        "reason": (
            f"{workstation.get('machine') or 'Current machine'} is not configured for data_pipeline; "
            "run the Tushare activation chain on a data-pipeline workstation."
        ),
    }


def _stage_ledger(
    recent: dict[str, Any],
    post: dict[str, Any],
    sufficiency: dict[str, Any],
    iterative: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "stage": "recent_data_refresh",
            "status": recent.get("status", "not_run"),
            "cleared": bool(_dict(recent.get("decision")).get("recent_data_ready", False)),
            "blockers": " / ".join(_as_list(_dict(recent.get("decision")).get("blockers"))),
        },
        {
            "stage": "post_refresh_replay",
            "status": post.get("status", "not_run"),
            "cleared": bool(_dict(post.get("decision")).get("post_refresh_replay_allowed", False)),
            "blockers": " / ".join(_as_list(_dict(post.get("decision")).get("blockers"))),
        },
        {
            "stage": "observation_sufficiency",
            "status": sufficiency.get("status", "not_run"),
            "cleared": bool(_dict(sufficiency.get("decision")).get("observation_sufficiency_cleared", False)),
            "blockers": " / ".join(_as_list(_dict(sufficiency.get("decision")).get("blockers"))),
        },
        {
            "stage": "iterative_observation_expansion",
            "status": iterative.get("status", "not_run"),
            "cleared": bool(_dict(iterative.get("decision")).get("iterative_observation_cleared", False)),
            "blockers": " / ".join(_as_list(_dict(iterative.get("decision")).get("blockers"))),
        },
    ]


def _recent_summary(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": pack.get("stage"),
        "status": pack.get("status"),
        "source": pack.get("source"),
        "market": pack.get("market"),
        "output_dir": pack.get("output_dir"),
        "coverage": _dict(pack.get("coverage")),
        "target_window": _dict(pack.get("target_window")),
        "decision": _dict(pack.get("decision")),
    }


def _post_refresh_summary(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": pack.get("stage"),
        "status": pack.get("status"),
        "decision": _dict(pack.get("decision")),
        "daily_ops_output_dir": pack.get("daily_ops_output_dir"),
        "profile_observation_output_dir": pack.get("profile_observation_output_dir"),
    }


def _sufficiency_summary(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": pack.get("stage"),
        "status": pack.get("status"),
        "fills": _dict(pack.get("fills")),
        "recommendation": _dict(pack.get("recommendation")),
        "decision": _dict(pack.get("decision")),
    }


def _iterative_summary(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": pack.get("stage"),
        "status": pack.get("status"),
        "round_count": pack.get("round_count"),
        "max_rounds": pack.get("max_rounds"),
        "final_observation_sufficiency": _dict(pack.get("final_observation_sufficiency")),
        "decision": _dict(pack.get("decision")),
    }


def _final_sufficiency(sufficiency: dict[str, Any], iterative: dict[str, Any]) -> dict[str, Any]:
    final = _dict(iterative.get("final_observation_sufficiency"))
    if final:
        return _sufficiency_summary(final)
    return _sufficiency_summary(sufficiency)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _safety() -> str:
    return "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."
