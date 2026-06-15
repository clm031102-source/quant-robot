from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.run_paper_batch import run_paper_batch
    from scripts.run_promotion_report import run_promotion_report
    from scripts.run_risk_candidate_selector import run_risk_candidate_selector
    from scripts.run_walk_forward import run_walk_forward
except ModuleNotFoundError:  # pragma: no cover - exercised when this file is run directly
    from run_paper_batch import run_paper_batch
    from run_promotion_report import run_promotion_report
    from run_risk_candidate_selector import run_risk_candidate_selector
    from run_walk_forward import run_walk_forward


STAGE = "phase_5_2_constrained_candidate_search"
DEFAULT_CONFIG = Path("configs/constrained_candidate_search_cn_etf.json")


@dataclass(frozen=True)
class ConstrainedCandidateSearchConfig:
    source: str = "processed-bars"
    data_root: Path = Path("data/processed/etf_csv")
    walk_forward_config: Path = Path("configs/walk_forward_cn_etf_risk_constrained.json")
    walk_forward_output_dir: Path = Path("data/reports/walk_forward_cn_etf_risk_constrained")
    paper_batch_config: Path = Path("configs/paper_batch_cn_etf_risk_constrained.json")
    paper_batch_output_dir: Path = Path("data/reports/paper_batch_cn_etf_risk_constrained")
    promotion_config: Path = Path("configs/promotion_gate_cn_etf_risk_constrained.json")
    promotion_output_dir: Path = Path("data/reports/promotion_gate_cn_etf_risk_constrained")
    daily_ops_pack: Path = Path("data/reports/daily_ops/daily_ops_pack.json")
    risk_candidate_output_dir: Path = Path("data/reports/risk_candidate_selector_risk_constrained")
    output_dir: Path = Path("data/reports/constrained_candidate_search")
    max_drawdown_limit: float = 0.2
    min_walk_forward_sharpe: float = 0.3
    min_relative_return: float = 0.0
    min_paper_sharpe: float = 0.5
    min_trades: int = 20
    risk_tiers: tuple[dict[str, Any], ...] = ()
    primary_risk_tier: str | None = None
    reuse_existing_artifacts: bool = True


def load_constrained_candidate_search_config(path: str | Path = DEFAULT_CONFIG) -> ConstrainedCandidateSearchConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ConstrainedCandidateSearchConfig(
        source=str(data.get("source", ConstrainedCandidateSearchConfig.source)),
        data_root=Path(data.get("data_root", ConstrainedCandidateSearchConfig.data_root)),
        walk_forward_config=Path(data.get("walk_forward_config", ConstrainedCandidateSearchConfig.walk_forward_config)),
        walk_forward_output_dir=Path(data.get("walk_forward_output_dir", ConstrainedCandidateSearchConfig.walk_forward_output_dir)),
        paper_batch_config=Path(data.get("paper_batch_config", ConstrainedCandidateSearchConfig.paper_batch_config)),
        paper_batch_output_dir=Path(data.get("paper_batch_output_dir", ConstrainedCandidateSearchConfig.paper_batch_output_dir)),
        promotion_config=Path(data.get("promotion_config", ConstrainedCandidateSearchConfig.promotion_config)),
        promotion_output_dir=Path(data.get("promotion_output_dir", ConstrainedCandidateSearchConfig.promotion_output_dir)),
        daily_ops_pack=Path(data.get("daily_ops_pack", ConstrainedCandidateSearchConfig.daily_ops_pack)),
        risk_candidate_output_dir=Path(data.get("risk_candidate_output_dir", ConstrainedCandidateSearchConfig.risk_candidate_output_dir)),
        output_dir=Path(data.get("output_dir", ConstrainedCandidateSearchConfig.output_dir)),
        max_drawdown_limit=float(data.get("max_drawdown_limit", ConstrainedCandidateSearchConfig.max_drawdown_limit)),
        min_walk_forward_sharpe=float(data.get("min_walk_forward_sharpe", ConstrainedCandidateSearchConfig.min_walk_forward_sharpe)),
        min_relative_return=float(data.get("min_relative_return", ConstrainedCandidateSearchConfig.min_relative_return)),
        min_paper_sharpe=float(data.get("min_paper_sharpe", ConstrainedCandidateSearchConfig.min_paper_sharpe)),
        min_trades=int(data.get("min_trades", ConstrainedCandidateSearchConfig.min_trades)),
        risk_tiers=tuple(_risk_tier(value) for value in data.get("risk_tiers", ConstrainedCandidateSearchConfig.risk_tiers)),
        primary_risk_tier=data.get("primary_risk_tier", ConstrainedCandidateSearchConfig.primary_risk_tier),
        reuse_existing_artifacts=bool(data.get("reuse_existing_artifacts", ConstrainedCandidateSearchConfig.reuse_existing_artifacts)),
    )


def run_constrained_candidate_search(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config = load_constrained_candidate_search_config(config_path)
    walk_forward = _reuse_or_run(
        config.reuse_existing_artifacts,
        config.walk_forward_output_dir / "manifest.json",
        lambda: run_walk_forward(
            config_path=config.walk_forward_config,
            source=config.source,
            data_root=config.data_root,
            output_dir=config.walk_forward_output_dir,
        ),
    )
    paper_batch = _reuse_or_run(
        config.reuse_existing_artifacts,
        config.paper_batch_output_dir / "paper_batch_summary.json",
        lambda: run_paper_batch(config_path=config.paper_batch_config, output_dir=config.paper_batch_output_dir),
    )
    promotion = _reuse_or_run(
        config.reuse_existing_artifacts,
        config.promotion_output_dir / "promotion_report.json",
        lambda: run_promotion_report(config_path=config.promotion_config, output_dir=config.promotion_output_dir),
    )
    risk_candidates = _reuse_or_run(
        config.reuse_existing_artifacts,
        config.risk_candidate_output_dir / "risk_candidate_pack.json",
        lambda: run_risk_candidate_selector(
            promotion_report=config.promotion_output_dir / "promotion_report.json",
            daily_ops_pack=config.daily_ops_pack,
            output_dir=config.risk_candidate_output_dir,
            max_drawdown_limit=config.max_drawdown_limit,
            min_walk_forward_sharpe=config.min_walk_forward_sharpe,
            min_relative_return=config.min_relative_return,
            min_paper_sharpe=config.min_paper_sharpe,
            min_trades=config.min_trades,
            risk_tiers=list(config.risk_tiers),
            primary_risk_tier=config.primary_risk_tier,
        ),
    )
    pack = build_constrained_candidate_search_pack(config, walk_forward, paper_batch, promotion, risk_candidates)
    write_constrained_candidate_search_pack(config.output_dir, pack)
    return pack


def build_constrained_candidate_search_pack(
    config: ConstrainedCandidateSearchConfig,
    walk_forward: dict[str, Any],
    paper_batch: dict[str, Any],
    promotion: dict[str, Any],
    risk_candidates: dict[str, Any],
) -> dict[str, Any]:
    selected = risk_candidates.get("selected_candidate") if isinstance(risk_candidates.get("selected_candidate"), dict) else None
    frontier = _frontier_candidates(risk_candidates)
    pack = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        "live_boundary_allowed": False,
        "selection_status": risk_candidates.get("selection_status", "unknown"),
        "selected_candidate": selected,
        "frontier_candidates": frontier,
        "config": _config_dict(config),
        "outputs": {
            "walk_forward": str(config.walk_forward_output_dir),
            "paper_batch": str(config.paper_batch_output_dir),
            "promotion_report": str(config.promotion_output_dir / "promotion_report.json"),
            "risk_candidate_pack": str(config.risk_candidate_output_dir / "risk_candidate_pack.json"),
        },
        "summary": _summary(walk_forward, paper_batch, promotion, risk_candidates),
        "next_actions": _next_actions(risk_candidates),
    }
    pack["markdown"] = render_constrained_candidate_search_markdown(pack)
    return _sanitize(pack)


def write_constrained_candidate_search_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "constrained_candidate_search_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "constrained_candidate_search_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")


def render_constrained_candidate_search_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    selected = pack.get("selected_candidate") if isinstance(pack.get("selected_candidate"), dict) else None
    lines = [
        "# Phase 5.2 Constrained Candidate Search",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Selection: {pack.get('selection_status', 'unknown')}",
        f"- Walk-forward accepted: {summary.get('walk_forward_accepted', 0)} / {summary.get('walk_forward_cases', 0)}",
        f"- Paper completed: {summary.get('paper_completed', 0)}",
        f"- Risk eligible candidates: {summary.get('risk_eligible_candidates', 0)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', '')}",
        "",
        "## Selected Candidate",
        "",
    ]
    if selected:
        lines.extend(
            [
                f"- Case: {selected.get('case_id')}",
                f"- Market: {selected.get('market')}",
                f"- Factor: {selected.get('factor_name')}",
                f"- Walk-forward drawdown: {selected.get('walk_forward_max_drawdown')}",
                f"- Paper drawdown: {selected.get('paper_max_drawdown')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Outputs", ""])
    outputs = pack.get("outputs", {}) if isinstance(pack.get("outputs"), dict) else {}
    for key, value in outputs.items():
        lines.append(f"- {key}: `{value}`")
    frontier = pack.get("frontier_candidates", []) if isinstance(pack.get("frontier_candidates"), list) else []
    lines.extend(["", "## Frontier Candidates", ""])
    if frontier:
        lines.append("| Case | Paper Sharpe | Paper Gap | Paper Drawdown | Drawdown Headroom | Rejections |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for row in frontier[:10]:
            if isinstance(row, dict):
                lines.append(
                    "| "
                    f"{row.get('case_id', '')} | "
                    f"{row.get('paper_sharpe', '')} | "
                    f"{row.get('paper_sharpe_gap', '')} | "
                    f"{row.get('paper_max_drawdown', '')} | "
                    f"{row.get('paper_drawdown_headroom', '')} | "
                    f"{', '.join(row.get('rejection_reasons', [])) if isinstance(row.get('rejection_reasons'), list) else ''} |"
                )
    else:
        lines.append("- none")
    lines.extend(["", "## Next Actions", ""])
    for action in pack.get("next_actions", []):
        if isinstance(action, dict):
            lines.append(f"- {action.get('action')}: {action.get('reason')}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local risk-constrained candidate search pipeline.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    pack = run_constrained_candidate_search(Path(args.config))
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "selection_status": pack["selection_status"],
                "summary": pack["summary"],
                "selected_candidate": pack["selected_candidate"],
                "output_dir": pack["config"]["output_dir"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _summary(
    walk_forward: dict[str, Any],
    paper_batch: dict[str, Any],
    promotion: dict[str, Any],
    risk_candidates: dict[str, Any],
) -> dict[str, Any]:
    walk_summary = _mapping(walk_forward.get("summary"))
    paper_summary = _mapping(paper_batch.get("summary"))
    promotion_summary = _mapping(promotion.get("summary"))
    risk_summary = _mapping(risk_candidates.get("summary"))
    return {
        "walk_forward_cases": _int(walk_summary.get("cases")),
        "walk_forward_accepted": _int(walk_summary.get("accepted")),
        "walk_forward_rejected": _int(walk_summary.get("rejected")),
        "paper_cases": _int(paper_summary.get("cases")),
        "paper_completed": _int(paper_summary.get("completed")),
        "paper_skipped": _int(paper_summary.get("skipped")),
        "promotion_candidates": _int(promotion_summary.get("candidates")),
        "promotion_paper_ready": _int(promotion_summary.get("paper_ready")),
        "risk_candidates": _int(risk_summary.get("candidates")),
        "risk_eligible_candidates": _int(risk_summary.get("risk_eligible_candidates")),
        "rejected_candidates": _int(risk_summary.get("rejected_candidates")),
        "frontier_candidates": len(_frontier_candidates(risk_candidates)),
    }


def _next_actions(risk_candidates: dict[str, Any]) -> list[dict[str, Any]]:
    if risk_candidates.get("selection_status") in {"risk_candidate_selected", "risk_tier_candidate_selected"}:
        return [
            {
                "action": "run_daily_ops_for_selected_candidate",
                "reason": "A risk-eligible candidate exists; refresh Daily Ops before any paper observation.",
                "local_only": True,
            }
        ]
    return [
        {
            "action": "tighten_or_expand_constrained_grid",
            "reason": "No risk-eligible candidate exists under the strict drawdown and paper-quality policy.",
            "local_only": True,
        },
        {
            "action": "inspect_factor_families_with_low_drawdown",
            "reason": "Separate low drawdown from positive relative return to identify whether exposure or signal quality is the bottleneck.",
            "local_only": True,
        },
    ]


def _config_dict(config: ConstrainedCandidateSearchConfig) -> dict[str, Any]:
    return {
        "source": config.source,
        "data_root": str(config.data_root),
        "walk_forward_config": str(config.walk_forward_config),
        "walk_forward_output_dir": str(config.walk_forward_output_dir),
        "paper_batch_config": str(config.paper_batch_config),
        "paper_batch_output_dir": str(config.paper_batch_output_dir),
        "promotion_config": str(config.promotion_config),
        "promotion_output_dir": str(config.promotion_output_dir),
        "daily_ops_pack": str(config.daily_ops_pack),
        "risk_candidate_output_dir": str(config.risk_candidate_output_dir),
        "output_dir": str(config.output_dir),
        "max_drawdown_limit": config.max_drawdown_limit,
        "min_walk_forward_sharpe": config.min_walk_forward_sharpe,
        "min_relative_return": config.min_relative_return,
        "min_paper_sharpe": config.min_paper_sharpe,
        "min_trades": config.min_trades,
        "risk_tiers": list(config.risk_tiers),
        "primary_risk_tier": config.primary_risk_tier,
        "reuse_existing_artifacts": config.reuse_existing_artifacts,
    }


def _risk_tier(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("risk_tiers entries must be JSON objects")
    return dict(value)


def _frontier_candidates(risk_candidates: dict[str, Any]) -> list[dict[str, Any]]:
    policy = _mapping(risk_candidates.get("policy"))
    max_drawdown_limit = _float(policy.get("max_drawdown_limit"), -0.2)
    min_paper_sharpe = _float(policy.get("min_paper_sharpe"), 0.5)
    allowed_reasons = {"paper_sharpe_below_min", "daily_ops_current_candidate_blocked"}
    frontier: list[dict[str, Any]] = []
    for row in risk_candidates.get("candidates", []):
        if not isinstance(row, dict):
            continue
        reasons = _reason_list(row.get("rejection_reasons"))
        tier_eligible = row.get("tier_status") == "tier_eligible"
        hard_reasons = [reason for reason in reasons if reason not in allowed_reasons]
        if hard_reasons and not tier_eligible:
            continue
        if row.get("duplicate_of"):
            continue
        if row.get("walk_forward_status") != "accepted":
            continue
        if not row.get("paper_matched"):
            continue
        risk_tier = row.get("risk_tier")
        tier_policy = _tier_policy(policy, str(risk_tier)) if risk_tier else {}
        drawdown_limit = _float(tier_policy.get("max_drawdown_limit"), max_drawdown_limit)
        tier_min_paper_sharpe = _float(tier_policy.get("min_paper_sharpe"), min_paper_sharpe)
        walk_drawdown = _float(row.get("walk_forward_max_drawdown"))
        paper_drawdown = _float(row.get("paper_max_drawdown"))
        if not tier_eligible and (walk_drawdown < drawdown_limit or paper_drawdown < drawdown_limit):
            continue
        paper_sharpe = _float(row.get("paper_sharpe"))
        frontier.append(
            {
                "case_id": row.get("case_id"),
                "market": row.get("market"),
                "factor_name": row.get("factor_name"),
                "risk_tier": risk_tier,
                "tier_status": row.get("tier_status"),
                "walk_forward_sharpe": _round(row.get("walk_forward_sharpe")),
                "walk_forward_relative_return": _round(row.get("walk_forward_relative_return")),
                "walk_forward_max_drawdown": _round(walk_drawdown),
                "paper_sharpe": _round(paper_sharpe),
                "paper_sharpe_gap": _round(max(tier_min_paper_sharpe - paper_sharpe, 0.0)),
                "paper_max_drawdown": _round(paper_drawdown),
                "paper_drawdown_headroom": _round(paper_drawdown - drawdown_limit),
                "paper_total_return": _round(row.get("paper_total_return")),
                "paper_calmar": _round(row.get("paper_calmar")),
                "rejection_reasons": reasons,
            }
        )
    return sorted(
        frontier,
        key=lambda row: (
            _float(row.get("paper_sharpe_gap")),
            -_float(row.get("paper_drawdown_headroom")),
            -_float(row.get("paper_total_return")),
            str(row.get("case_id")),
        ),
    )


def _reuse_or_run(reuse_existing: bool, artifact_path: Path, runner: Any) -> dict[str, Any]:
    if reuse_existing and artifact_path.exists():
        return _read_json(artifact_path)
    result = runner()
    if not isinstance(result, dict):
        raise ValueError(f"Pipeline stage returned non-object result for {artifact_path}")
    return result


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _reason_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _tier_policy(policy: dict[str, Any], tier_id: str) -> dict[str, Any]:
    tiers = policy.get("risk_tiers", []) if isinstance(policy.get("risk_tiers"), list) else []
    for tier in tiers:
        if isinstance(tier, dict) and str(tier.get("tier_id")) == tier_id:
            return tier
    return {}


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _round(value: Any) -> float:
    return round(_float(value), 6)


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    main()
