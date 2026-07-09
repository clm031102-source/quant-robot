from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.factor_batch_readiness_gate import validate_factor_batch_readiness_gate_packet
from quant_robot.storage.dataset_store import DatasetStore


STAGE = "lpr_macro_regime_state_prescreen"
ACTIVE_FACTOR = "lpr_shibor_credit_gap_regime_60"
MACRO_DATASET = "external_macro_rates"
FINAL_HOLDOUT_START = "2026-01-01"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."

REQUIRED_COLUMNS = ["date", "available_date", "lpr_1y", "lpr_5y", "shibor_3m"]
STATE_DISTRIBUTION_COLUMNS = [
    "state",
    "state_type",
    "date_count",
    "pct_of_rows",
    "first_available_date",
    "last_available_date",
]
CANDIDATE_COLUMNS = [
    "factor_name",
    "family",
    "registration_status",
    "state_ready_for_regime_control",
    "state_count",
    "directional_state_count",
    "nonzero_gap_change_count",
    "portfolio_grid_allowed",
    "promotion_allowed",
    "blockers",
]


def run_lpr_macro_regime_state_prescreen(
    *,
    processed_root: str | Path,
    readiness_gate_path: str | Path,
    candidate_plan_path: str | Path,
    output_dir: str | Path,
    market: str = "CN",
    analysis_start_date: str = "2024-07-01",
    analysis_end_date: str = "2025-12-31",
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
    min_state_dates: int = 5,
    min_nonzero_gap_changes: int = 20,
    include_final_holdout: bool = False,
) -> dict[str, Any]:
    readiness_gate = validate_factor_batch_readiness_gate_packet(
        readiness_gate_path,
        context="LPR macro regime state prescreen",
    )
    candidate_plan = json.loads(Path(candidate_plan_path).read_text(encoding="utf-8"))
    macro_rates = _read_processed_dataset(Path(processed_root), MACRO_DATASET, market)
    result = summarize_lpr_macro_regime_state_prescreen(
        macro_rates,
        candidate_plan=candidate_plan,
        processed_root=processed_root,
        readiness_gate_path=readiness_gate_path,
        readiness_gate=readiness_gate,
        candidate_plan_path=candidate_plan_path,
        market=market,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
        min_state_dates=min_state_dates,
        min_nonzero_gap_changes=min_nonzero_gap_changes,
        include_final_holdout=include_final_holdout,
    )
    write_lpr_macro_regime_state_prescreen(output_dir, result)
    return result


def build_lpr_macro_regime_state_frame(
    macro_rates: pd.DataFrame,
    *,
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
    market: str = "CN",
) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in macro_rates.columns]
    if missing:
        raise ValueError(f"external_macro_rates missing required columns: {', '.join(missing)}")
    frame = macro_rates.copy()
    if "market" in frame.columns:
        frame = frame[frame["market"].astype(str) == str(market)]
    for column in ["date", "available_date"]:
        frame[column] = pd.to_datetime(frame[column], errors="coerce").dt.normalize()
    for column in ["lpr_1y", "lpr_5y", "shibor_3m"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=REQUIRED_COLUMNS).sort_values(["available_date", "date"])
    frame = frame.drop_duplicates("available_date", keep="last").reset_index(drop=True)
    if frame.empty:
        return _empty_state_frame()

    output = frame[["date", "available_date", "lpr_1y", "lpr_5y", "shibor_3m"]].copy()
    output["signal_date"] = output["available_date"]
    output["lpr_shibor_3m_gap"] = output["lpr_1y"] - output["shibor_3m"]
    output["lpr_shibor_3m_gap_chg"] = output["lpr_shibor_3m_gap"].diff(int(lookback_days))
    output["lpr_term_premium"] = output["lpr_5y"] - output["lpr_1y"]
    output["lpr_term_premium_chg"] = output["lpr_term_premium"].diff(int(lookback_days))
    output["lpr_shibor_gap_state"] = _classify_gap_state(
        output["lpr_shibor_3m_gap_chg"],
        min_abs_gap_change=float(min_abs_gap_change),
    )
    output["lookback_days"] = int(lookback_days)
    output["min_abs_gap_change"] = float(min_abs_gap_change)
    return output


def summarize_lpr_macro_regime_state_prescreen(
    macro_rates: pd.DataFrame,
    *,
    candidate_plan: dict[str, Any],
    processed_root: str | Path,
    readiness_gate_path: str | Path,
    readiness_gate: dict[str, Any],
    candidate_plan_path: str | Path,
    market: str,
    analysis_start_date: str,
    analysis_end_date: str,
    lookback_days: int,
    min_abs_gap_change: float,
    min_state_dates: int,
    min_nonzero_gap_changes: int,
    include_final_holdout: bool = False,
) -> dict[str, Any]:
    global_blockers: list[str] = []
    state_frame = build_lpr_macro_regime_state_frame(
        macro_rates,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
        market=market,
    )
    windowed, excluded_final_holdout_rows = _analysis_window(
        state_frame,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    if include_final_holdout:
        global_blockers.append("final_holdout_included_in_prescreen")
    if windowed.empty:
        global_blockers.append("no_lpr_macro_rows_after_window_and_holdout_policy")

    pit = _pit_violations(windowed)
    if pit["available_date_violations"]:
        global_blockers.append("available_date_after_signal_date")
    if pit["raw_date_not_before_signal_violations"]:
        global_blockers.append("raw_date_not_before_signal_date")

    active_candidates = _active_candidates(candidate_plan)
    inactive_candidates = _inactive_candidates(candidate_plan)
    unsupported = [candidate for candidate in active_candidates if candidate.get("factor_name") != ACTIVE_FACTOR]
    if not active_candidates:
        global_blockers.append("no_pre_registered_lpr_shibor_gap_candidate")
    if unsupported:
        global_blockers.append("unsupported_active_lpr_macro_candidate")

    state_stats = _state_stats(windowed, min_abs_gap_change=min_abs_gap_change)
    candidate_results = [
        _candidate_result(
            candidate,
            state_stats=state_stats,
            global_blockers=global_blockers,
            min_state_dates=min_state_dates,
            min_nonzero_gap_changes=min_nonzero_gap_changes,
        )
        for candidate in active_candidates
    ]
    ready_count = sum(1 for row in candidate_results if row["state_ready_for_regime_control"])
    decision_blockers = _unique(
        [
            *global_blockers,
            *[blocker for row in candidate_results for blocker in _as_list(row.get("blockers"))],
        ]
    )
    passes = bool(ready_count and not decision_blockers)
    next_direction = (
        "run_lpr_shibor_gap_regime_pairwise_residual_ic_prescreen"
        if passes
        else "repair_or_rotate_lpr_macro_regime_state_before_residual_ic"
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "market": market,
        "processed_root": str(Path(processed_root)),
        "readiness_gate_path": str(Path(readiness_gate_path)),
        "candidate_plan_path": str(Path(candidate_plan_path)),
        "summary": {
            "passes": passes,
            "active_candidate_count": len(active_candidates),
            "inactive_candidate_count": len(inactive_candidates),
            "state_rows": int(len(windowed)),
            "state_count": state_stats["state_count"],
            "directional_state_count": state_stats["directional_state_count"],
            "nonzero_gap_change_count": state_stats["nonzero_gap_change_count"],
            "ready_regime_control_candidate_count": ready_count,
            "portfolio_grid_allowed_candidates": 0,
            "promotion_allowed_candidates": 0,
            "next_direction": next_direction,
        },
        "readiness_gate_summary": readiness_gate.get("summary", {}),
        "data_window": {
            "raw_rows": int(len(macro_rates)),
            "state_rows_before_window": int(len(state_frame)),
            "first_raw_date": _min_date(state_frame, "date"),
            "last_raw_date": _max_date(state_frame, "date"),
            "first_available_date": _min_date(windowed, "available_date"),
            "last_available_date": _max_date(windowed, "available_date"),
            "excluded_final_holdout_rows": int(excluded_final_holdout_rows),
        },
        "holdout_policy": {
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
            "final_holdout_start": FINAL_HOLDOUT_START,
            "final_holdout_included": include_final_holdout,
            "excluded_final_holdout_rows": int(excluded_final_holdout_rows),
            "final_holdout_use": "blocked_for_state_prescreen_and_tuning",
        },
        "feature_definitions": {
            "signal_date": "available_date",
            "lpr_shibor_3m_gap": "lpr_1y - shibor_3m",
            "lpr_shibor_3m_gap_chg": f"diff over {int(lookback_days)} available observations",
            "state_rule": (
                f"gap_widening if change > {float(min_abs_gap_change)}, "
                f"gap_narrowing if change < -{float(min_abs_gap_change)}, otherwise gap_flat"
            ),
            "standalone_stock_rank_allowed": False,
        },
        "state_distribution": state_stats["state_distribution"],
        "candidate_results": candidate_results,
        "inactive_candidates": inactive_candidates,
        "pit_audit": pit,
        "decision": {
            "research_screen_allowed": passes,
            "state_ready_for_regime_control": passes,
            "residual_ic_pairing_allowed_next": passes,
            "standalone_alpha_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "blockers": decision_blockers,
            "next_direction": next_direction,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed_before_residual_ic": False,
            "requires_pre_registered_stock_factor_pair": True,
            "requires_industry_size_liquidity_residual_ic": True,
            "requires_reference_dedup": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "requires_multiple_testing_accounting": True,
            "requires_final_holdout_read_once": True,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_lpr_macro_regime_state_prescreen_markdown(result)
    return result


def write_lpr_macro_regime_state_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "lpr_macro_regime_state_prescreen.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lpr_macro_regime_state_prescreen.md").write_text(
        render_lpr_macro_regime_state_prescreen_markdown(clean),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "lpr_macro_regime_state_distribution.csv",
        clean.get("state_distribution", []),
        STATE_DISTRIBUTION_COLUMNS,
    )
    _write_csv(
        output_path / "lpr_macro_regime_candidate_results.csv",
        clean.get("candidate_results", []),
        CANDIDATE_COLUMNS,
    )


def render_lpr_macro_regime_state_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    decision = result.get("decision", {})
    lines = [
        "# LPR Macro Regime State Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Market: {result.get('market', 'CN')}",
        f"- Active candidates: {summary.get('active_candidate_count', 0)}",
        f"- State rows: {summary.get('state_rows', 0)}",
        f"- Directional states: {summary.get('directional_state_count', 0)}",
        f"- Non-zero gap changes: {summary.get('nonzero_gap_change_count', 0)}",
        f"- Ready regime-control candidates: {summary.get('ready_regime_control_candidate_count', 0)}",
        f"- Portfolio grid allowed: {decision.get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Next direction: `{summary.get('next_direction', '')}`",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Decision Blockers",
        "",
    ]
    blockers = _as_list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## State Distribution",
            "",
            "| State | Type | Dates | Share | First | Last |",
            "|---|---|---:|---:|---|---|",
        ]
    )
    for row in result.get("state_distribution", []):
        lines.append(
            "| {state} | {state_type} | {date_count} | {pct:.1%} | {first} | {last} |".format(
                state=row.get("state", ""),
                state_type=row.get("state_type", ""),
                date_count=row.get("date_count", 0),
                pct=float(row.get("pct_of_rows", 0.0) or 0.0),
                first=row.get("first_available_date", ""),
                last=row.get("last_available_date", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Candidate Results",
            "",
            "| Factor | Ready | Directional States | Non-zero Changes | Blockers |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for row in result.get("candidate_results", []):
        lines.append(
            "| {factor} | {ready} | {states} | {nonzero} | {blockers} |".format(
                factor=row.get("factor_name", ""),
                ready=row.get("state_ready_for_regime_control", False),
                states=row.get("directional_state_count", 0),
                nonzero=row.get("nonzero_gap_change_count", 0),
                blockers=", ".join(_as_list(row.get("blockers"))) or "none",
            )
        )
    return "\n".join(lines) + "\n"


def _read_processed_dataset(root: Path, dataset: str, market: str) -> pd.DataFrame:
    store_root = _normalize_processed_root(root, dataset)
    store = DatasetStore(store_root)
    base = store_root / "processed" / dataset / "frequency=1d" / f"market={market}"
    frames = []
    for year_path in sorted(base.glob("year=*")):
        year = year_path.name.split("=", 1)[1]
        frames.append(store.read_frame(f"processed/{dataset}", {"frequency": "1d", "market": market, "year": year}))
    if not frames:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    return pd.concat(frames, ignore_index=True)


def _normalize_processed_root(root: Path, dataset: str) -> Path:
    if (root / dataset).exists() and not (root / "processed" / dataset).exists():
        return root.parent
    return root


def _classify_gap_state(changes: pd.Series, *, min_abs_gap_change: float) -> pd.Series:
    state = pd.Series("gap_flat", index=changes.index, dtype=object)
    state[changes.isna()] = "insufficient_lookback"
    state[changes > min_abs_gap_change] = "gap_widening"
    state[changes < -min_abs_gap_change] = "gap_narrowing"
    return state


def _analysis_window(
    frame: pd.DataFrame,
    *,
    analysis_start_date: str,
    analysis_end_date: str,
    include_final_holdout: bool,
) -> tuple[pd.DataFrame, int]:
    if frame.empty:
        return frame.copy(), 0
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    output = frame[(frame["available_date"] >= start) & (frame["available_date"] <= end)].copy()
    holdout_start = pd.Timestamp(FINAL_HOLDOUT_START)
    holdout_rows = int((output["available_date"] >= holdout_start).sum())
    if not include_final_holdout:
        output = output[output["available_date"] < holdout_start].copy()
    return output.reset_index(drop=True), holdout_rows


def _pit_violations(frame: pd.DataFrame) -> dict[str, int]:
    if frame.empty:
        return {"available_date_violations": 0, "raw_date_not_before_signal_violations": 0}
    signal = pd.to_datetime(frame["signal_date"], errors="coerce")
    available = pd.to_datetime(frame["available_date"], errors="coerce")
    raw = pd.to_datetime(frame["date"], errors="coerce")
    return {
        "available_date_violations": int((available > signal).sum()),
        "raw_date_not_before_signal_violations": int((raw >= signal).sum()),
    }


def _state_stats(frame: pd.DataFrame, *, min_abs_gap_change: float) -> dict[str, Any]:
    if frame.empty:
        return {
            "state_count": 0,
            "directional_state_count": 0,
            "min_directional_state_date_count": 0,
            "nonzero_gap_change_count": 0,
            "term_premium_unique_count": 0,
            "state_distribution": [],
        }
    rows = []
    total = len(frame)
    for state, group in frame.groupby("lpr_shibor_gap_state", sort=True):
        rows.append(
            {
                "state": str(state),
                "state_type": _state_type(str(state)),
                "date_count": int(group["available_date"].nunique()),
                "pct_of_rows": float(len(group) / total) if total else 0.0,
                "first_available_date": _min_date(group, "available_date"),
                "last_available_date": _max_date(group, "available_date"),
            }
        )
    directional = [row for row in rows if row["state_type"] == "directional"]
    min_directional = min((int(row["date_count"]) for row in directional), default=0)
    nonzero_gap_change_count = int(
        (pd.to_numeric(frame["lpr_shibor_3m_gap_chg"], errors="coerce").abs() > float(min_abs_gap_change)).sum()
    )
    term_premium_unique_count = int(pd.to_numeric(frame["lpr_term_premium"], errors="coerce").dropna().nunique())
    return {
        "state_count": len([row for row in rows if row["state"] != "insufficient_lookback"]),
        "directional_state_count": len(directional),
        "min_directional_state_date_count": min_directional,
        "nonzero_gap_change_count": nonzero_gap_change_count,
        "term_premium_unique_count": term_premium_unique_count,
        "state_distribution": sorted(rows, key=lambda row: (row["state_type"], row["state"])),
    }


def _candidate_result(
    candidate: dict[str, Any],
    *,
    state_stats: dict[str, Any],
    global_blockers: Sequence[str],
    min_state_dates: int,
    min_nonzero_gap_changes: int,
) -> dict[str, Any]:
    blockers = list(global_blockers)
    if candidate.get("factor_name") != ACTIVE_FACTOR:
        blockers.append("unsupported_active_lpr_macro_candidate")
    if int(state_stats["directional_state_count"]) <= 0:
        blockers.append("state_distribution_degenerate")
    if int(state_stats["nonzero_gap_change_count"]) < int(min_nonzero_gap_changes):
        blockers.append("nonzero_gap_change_below_threshold")
    if int(state_stats["min_directional_state_date_count"]) < int(min_state_dates):
        blockers.append("directional_state_dates_below_threshold")
    blockers = _unique(blockers)
    return {
        "factor_name": str(candidate.get("factor_name", "")),
        "family": str(candidate.get("family", "")),
        "registration_status": str(candidate.get("registration_status", "")),
        "state_ready_for_regime_control": not blockers,
        "state_count": int(state_stats["state_count"]),
        "directional_state_count": int(state_stats["directional_state_count"]),
        "min_directional_state_date_count": int(state_stats["min_directional_state_date_count"]),
        "nonzero_gap_change_count": int(state_stats["nonzero_gap_change_count"]),
        "term_premium_unique_count": int(state_stats["term_premium_unique_count"]),
        "portfolio_grid_allowed": False,
        "promotion_allowed": False,
        "blockers": blockers,
    }


def _active_candidates(candidate_plan: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = candidate_plan.get("candidates", [])
    if not isinstance(candidates, list):
        return []
    return [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict) and str(candidate.get("registration_status", "")) == "pre_registered"
    ]


def _inactive_candidates(candidate_plan: dict[str, Any]) -> list[dict[str, str]]:
    candidates = candidate_plan.get("candidates", [])
    if not isinstance(candidates, list):
        return []
    rows = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if str(candidate.get("registration_status", "")) == "pre_registered":
            continue
        rows.append(
            {
                "factor_name": str(candidate.get("factor_name", "")),
                "family": str(candidate.get("family", "")),
                "registration_status": str(candidate.get("registration_status", "")),
            }
        )
    return rows


def _state_type(state: str) -> str:
    if state == "insufficient_lookback":
        return "warmup"
    if state in {"gap_widening", "gap_narrowing"}:
        return "directional"
    return "flat"


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else value.date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else value.date().isoformat()


def _empty_state_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "available_date",
            "lpr_1y",
            "lpr_5y",
            "shibor_3m",
            "signal_date",
            "lpr_shibor_3m_gap",
            "lpr_shibor_3m_gap_chg",
            "lpr_term_premium",
            "lpr_term_premium_chg",
            "lpr_shibor_gap_state",
            "lookback_days",
            "min_abs_gap_change",
        ]
    )


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = dict(row)
            if isinstance(clean.get("blockers"), list):
                clean["blockers"] = "|".join(str(item) for item in clean["blockers"])
            writer.writerow(clean)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value in (None, ""):
        return []
    return [str(value)]


def _unique(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output
