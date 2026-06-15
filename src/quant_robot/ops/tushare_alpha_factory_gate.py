from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_6_0_tushare_alpha_factory_gate"


def build_tushare_alpha_factory_gate_pack(
    *,
    readiness: dict[str, Any],
    source: str = "tushare",
    market: str = "CN",
    execute: bool = False,
    data_root: str | Path | None = None,
    ohlcv_ingest: dict[str, Any] | None = None,
    factor_input_ingest: dict[str, Any] | None = None,
    alpha_factory: dict[str, Any] | None = None,
    chain_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_name = source.strip().lower()
    readiness_pack = _dict(readiness)
    ohlcv = _dict(ohlcv_ingest)
    factor_inputs = _dict(factor_input_ingest)
    factory = _dict(alpha_factory)
    summary = _dict(factory.get("summary"))
    readiness_missing = _as_list(readiness_pack.get("missing"))
    readiness_blocked = source_name == "tushare" and not bool(readiness_pack.get("ready", False))
    adjusted_significant = int(_number(summary.get("adjusted_significant"), 0))
    paper_eligible = _paper_eligible_count(factory, summary)
    alpha_completed = bool(summary)

    if readiness_blocked:
        status = "blocked_missing_readiness"
    elif not execute:
        status = "ready_to_execute"
    elif chain_error:
        status = "alpha_factory_chain_failed"
    elif paper_eligible > 0:
        status = "alpha_candidates_found"
    elif adjusted_significant > 0 and alpha_completed:
        status = "no_paper_eligible_alpha"
    elif alpha_completed:
        status = "no_adjusted_significant_alpha"
    else:
        status = "alpha_factory_not_run"

    blockers = _blockers(status, readiness_missing, chain_error)
    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "source": source_name,
        "market": market.upper(),
        "mode": "execute" if execute else "dry_run",
        "data_root": str(data_root) if data_root is not None else None,
        "readiness": readiness_pack,
        "ohlcv_ingest": _ingest_summary(ohlcv),
        "factor_input_ingest": _ingest_summary(factor_inputs),
        "alpha_factory": _alpha_factory_summary(factory),
        "stage_ledger": _stage_ledger(ohlcv, factor_inputs, factory),
        "chain_error": chain_error or {},
        "decision": {
            "tushare_ready": bool(readiness_pack.get("ready", False)) or source_name != "tushare",
            "execute_requested": bool(execute),
            "ohlcv_ingest_completed": bool(ohlcv),
            "factor_input_ingest_completed": bool(factor_inputs),
            "alpha_factory_completed": alpha_completed,
            "adjusted_significant_candidates": adjusted_significant,
            "paper_eligible_candidates": paper_eligible,
            "paper_candidate_allowed": paper_eligible > 0,
            "blockers": blockers,
        },
        "live_boundary_allowed": False,
        "safety": _safety(),
    }
    pack["next_actions"] = _next_actions(pack)
    pack["markdown"] = render_tushare_alpha_factory_gate_markdown(pack)
    return _sanitize(pack)


def write_tushare_alpha_factory_gate_pack(report_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(report_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "tushare_alpha_factory_gate_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "tushare_alpha_factory_gate_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("stage_ledger", [])).to_csv(output_path / "tushare_alpha_factory_gate_stage_ledger.csv", index=False)
    pd.DataFrame(pack.get("next_actions", [])).to_csv(output_path / "tushare_alpha_factory_gate_next_actions.csv", index=False)


def render_tushare_alpha_factory_gate_markdown(pack: dict[str, Any]) -> str:
    decision = _dict(pack.get("decision"))
    factory = _dict(pack.get("alpha_factory"))
    summary = _dict(factory.get("summary"))
    lines = [
        "# Phase 6.0 Tushare Alpha Factory Gate",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status', 'unknown')}",
        f"- Source: {pack.get('source', 'tushare')}",
        f"- Market: {pack.get('market', 'CN')}",
        f"- Mode: {pack.get('mode', 'dry_run')}",
        f"- Alpha factory completed: {decision.get('alpha_factory_completed', False)}",
        f"- Hypotheses tested: {summary.get('hypothesis_count', 0)}",
        f"- Adjusted significant candidates: {decision.get('adjusted_significant_candidates', 0)}",
        f"- Paper candidate allowed: {decision.get('paper_candidate_allowed', False)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Stage Ledger",
        "",
    ]
    ledger = pack.get("stage_ledger", []) if isinstance(pack.get("stage_ledger"), list) else []
    if ledger:
        lines.extend(
            f"- {row.get('stage')}: {row.get('status')} / rows={row.get('rows')} / cleared={row.get('cleared')}"
            for row in ledger
            if isinstance(row, dict)
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Blockers", ""])
    blockers = decision.get("blockers", []) if isinstance(decision.get("blockers"), list) else []
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Next Actions", ""])
    actions = pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else []
    lines.extend(f"- {row.get('action')}: {row.get('reason')}" for row in actions if isinstance(row, dict)) if actions else lines.append("- none")
    return "\n".join(lines) + "\n"


def _blockers(status: str, readiness_missing: list[str], chain_error: dict[str, Any] | None) -> list[str]:
    blockers: list[str] = []
    if status == "ready_to_execute" or status == "alpha_candidates_found":
        return []
    blockers.extend(readiness_missing)
    if chain_error:
        blockers.append(f"{chain_error.get('stage', 'tushare_alpha_factory_gate')}_failed: {chain_error.get('error', 'unknown error')}")
    if status == "no_adjusted_significant_alpha":
        blockers.append("no_adjusted_significant_alpha")
    if status == "no_paper_eligible_alpha":
        blockers.append("no_directionally_valid_paper_alpha")
    if status == "alpha_factory_not_run" and not blockers:
        blockers.append("alpha_factory_not_run")
    return _unique(blockers)


def _next_actions(pack: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(pack.get("decision"))
    blockers = _as_list(decision.get("blockers"))
    actions: list[dict[str, Any]] = []
    if any("TUSHARE_TOKEN" in blocker for blocker in blockers):
        actions.append(
            {
                "action": "set_tushare_token_env",
                "command": "setx TUSHARE_TOKEN <your-token>",
                "local_only": True,
                "reason": "Set the Tushare token locally or in ignored .env, then rerun the alpha factory gate with --execute.",
            }
        )
    if any("tushare package" in blocker.lower() for blocker in blockers):
        actions.append(
            {
                "action": "install_tushare_package",
                "command": "python -m pip install .[data,parquet]",
                "local_only": True,
                "reason": "The Tushare package and Parquet support are required before real provider research can run.",
            }
        )
    if pack.get("status") == "ready_to_execute":
        actions.append(
            {
                "action": "execute_tushare_alpha_factory_gate",
                "command": "python scripts\\run_tushare_alpha_factory_gate.py --execute",
                "local_only": True,
                "reason": "Readiness is clear; run OHLCV ingest, daily_basic ingest, and the alpha factory.",
            }
        )
    if pack.get("status") == "alpha_candidates_found":
        actions.append(
            {
                "action": "run_paper_batch_for_alpha_candidates",
                "command": "python scripts\\run_paper_batch.py --config configs\\paper_batch_tushare_alpha_factory.json",
                "local_only": True,
                "reason": "At least one candidate survived multiple-testing correction; route it into paper-only validation.",
            }
        )
    if pack.get("status") == "no_adjusted_significant_alpha":
        actions.append(
            {
                "action": "expand_factor_hypotheses_under_multiple_testing_control",
                "local_only": True,
                "reason": "No daily_basic candidate survived adjusted IC significance; expand hypotheses without relaxing the gate.",
            }
        )
    if pack.get("status") == "no_paper_eligible_alpha":
        actions.append(
            {
                "action": "inspect_negative_ic_and_directional_variants",
                "local_only": True,
                "reason": "Adjusted-significant candidates exist, but none are directionally valid for long-only paper validation.",
            }
        )
    if pack.get("status") == "alpha_factory_chain_failed":
        actions.append(
            {
                "action": "inspect_alpha_factory_chain_error",
                "local_only": True,
                "reason": "A local ingest or alpha-factory step failed before paper validation.",
            }
        )
    if not actions:
        actions.append(
            {
                "action": "resolve_alpha_factory_readiness",
                "local_only": True,
                "reason": "The alpha factory gate is blocked before research execution can run.",
            }
        )
    return actions


def _stage_ledger(
    ohlcv_ingest: dict[str, Any],
    factor_input_ingest: dict[str, Any],
    alpha_factory: dict[str, Any],
) -> list[dict[str, Any]]:
    alpha_summary = _dict(alpha_factory.get("summary"))
    return [
        {
            "stage": "tushare_ohlcv_ingest",
            "status": "completed" if ohlcv_ingest else "not_run",
            "rows": int(_number(ohlcv_ingest.get("processed_rows"), 0)),
            "cleared": bool(ohlcv_ingest),
        },
        {
            "stage": "tushare_daily_basic_ingest",
            "status": "completed" if factor_input_ingest else "not_run",
            "rows": int(_number(factor_input_ingest.get("processed_rows"), 0)),
            "cleared": bool(factor_input_ingest),
        },
        {
            "stage": "tushare_alpha_factory",
            "status": "completed" if alpha_summary else "not_run",
            "rows": int(_number(alpha_summary.get("hypothesis_count"), 0)),
            "cleared": int(_number(alpha_summary.get("paper_eligible"), 0)) > 0,
        },
    ]


def _ingest_summary(pack: dict[str, Any]) -> dict[str, Any]:
    if not pack:
        return {"present": False}
    return {
        "present": True,
        "source": pack.get("source"),
        "dataset": pack.get("dataset"),
        "market": pack.get("market"),
        "processed_rows": int(_number(pack.get("processed_rows"), 0)),
        "downloaded_trade_dates": _as_list(pack.get("downloaded_trade_dates")),
        "skipped_trade_dates": _as_list(pack.get("skipped_trade_dates")),
    }


def _alpha_factory_summary(pack: dict[str, Any]) -> dict[str, Any]:
    if not pack:
        return {"present": False, "summary": {}}
    leaderboard = pack.get("candidate_leaderboard", [])
    if not isinstance(leaderboard, list):
        leaderboard = []
    return {
        "present": True,
        "summary": _dict(pack.get("summary")),
        "top_candidates": leaderboard[:10],
    }


def _paper_eligible_count(factory: dict[str, Any], summary: dict[str, Any]) -> int:
    if "paper_eligible" in summary:
        return int(_number(summary.get("paper_eligible"), 0))
    leaderboard = factory.get("candidate_leaderboard", [])
    if not isinstance(leaderboard, list):
        return 0
    return sum(1 for row in leaderboard if isinstance(row, dict) and bool(row.get("paper_candidate_allowed")))


def _safety() -> dict[str, Any]:
    return {
        "research_only": True,
        "paper_only_next_step": True,
        "live_boundary_allowed": False,
        "secrets_not_serialized": True,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return [str(value)]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    return value
