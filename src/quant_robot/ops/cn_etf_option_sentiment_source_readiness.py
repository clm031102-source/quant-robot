from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from quant_robot.storage.atomic import atomic_write_json, atomic_write_text


STAGE = "cn_etf_option_sentiment_source_readiness"
STATUS_READY = "ready_for_option_sentiment_preregistration"
SAFETY_BOUNDARIES = (
    "factor_generation_allowed",
    "forward_return_read",
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "final_holdout_allowed",
    "promotion_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_boundary_allowed",
)


def build_cn_etf_option_sentiment_source_readiness(
    *,
    contracts: pd.DataFrame,
    daily_probes: Mapping[str, pd.DataFrame],
    config: Mapping[str, Any],
    config_sha256: str,
) -> dict[str, Any]:
    analysis = config["analysis"]
    thresholds = config["thresholds"]
    expected_dates = [
        pd.Timestamp(value).date().isoformat()
        for value in config["probes"]["dates"]
    ]
    contract_frame = normalise_option_contracts(
        contracts,
        start=pd.Timestamp(analysis["start_date"]),
        end=pd.Timestamp(analysis["end_date"]),
    )
    underlying = _underlying_summary(contract_frame)
    probe_rows, probe_blockers = _summarize_probes(
        daily_probes,
        contracts=contract_frame,
        expected_dates=expected_dates,
        minimum_positive_close_ratio=float(
            thresholds["minimum_positive_close_ratio_per_probe"]
        ),
    )
    blockers = list(probe_blockers)
    minimum_underlyings = int(thresholds["minimum_etf_underlyings"])
    if len(underlying) < minimum_underlyings:
        blockers.append("etf_option_underlying_count_below_minimum")
    if not contract_frame["call_put"].isin(["C", "P"]).all():
        blockers.append("invalid_option_call_put_identity")
    result: dict[str, Any] = {
        "stage": STAGE,
        "review_date": config.get("review_date"),
        "status": "blocked" if blockers else STATUS_READY,
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_option_sentiment",
        "configuration": {"sha256": config_sha256},
        "analysis": dict(analysis),
        "thresholds": dict(thresholds),
        "summary": {
            "contract_rows": int(len(contract_frame)),
            "contract_count": int(contract_frame["ts_code"].nunique()),
            "underlying_count": int(len(underlying)),
            "sse_underlyings": int(
                underlying["exchange"].eq("SSE").sum()
            ) if not underlying.empty else 0,
            "szse_underlyings": int(
                underlying["exchange"].eq("SZSE").sum()
            ) if not underlying.empty else 0,
            "probe_count": int(len(probe_rows)),
            "minimum_required_underlyings": minimum_underlyings,
        },
        "underlyings": underlying.to_dict("records"),
        "daily_probes": probe_rows,
        "gate": {
            "cleared": not blockers,
            "blockers": list(dict.fromkeys(blockers)),
        },
        "allowed_role_if_blocked": "market_regime_or_risk_control_only",
        "next_direction": (
            "preregister_one_option_sentiment_prescreen"
            if not blockers
            else "rotate_to_another_orthogonal_cn_etf_source_family"
        ),
    }
    for field in SAFETY_BOUNDARIES:
        result[field] = False
    result["markdown"] = render_cn_etf_option_sentiment_source_readiness(result)
    return result


def write_cn_etf_option_sentiment_source_readiness(
    output_dir: str | Path,
    result: Mapping[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / f"{STAGE}.json",
        "markdown": output / f"{STAGE}.md",
        "underlyings": output / "underlyings.csv",
        "daily_probes": output / "daily_probes.csv",
    }
    atomic_write_json(
        paths["json"],
        _sanitize({key: value for key, value in result.items() if key != "markdown"}),
    )
    atomic_write_text(
        paths["markdown"],
        render_cn_etf_option_sentiment_source_readiness(result),
    )
    _stable_frame(result.get("underlyings", [])).to_csv(paths["underlyings"], index=False)
    _stable_frame(result.get("daily_probes", [])).to_csv(paths["daily_probes"], index=False)
    return paths


def render_cn_etf_option_sentiment_source_readiness(
    result: Mapping[str, Any],
) -> str:
    summary = result.get("summary", {})
    gate = result.get("gate", {})
    return "\n".join(
        [
            "# CN ETF Option-Sentiment Source Readiness",
            "",
            f"- Status: `{result.get('status', 'blocked')}`",
            f"- Analysis contracts: {summary.get('contract_count', 0)}",
            f"- ETF underlyings: {summary.get('underlying_count', 0)}",
            f"- Minimum required: {summary.get('minimum_required_underlyings', 0)}",
            f"- Probe dates: {summary.get('probe_count', 0)}",
            f"- Blockers: {', '.join(gate.get('blockers', []) or []) or 'none'}",
            "- Factor generation: false",
            "- Forward-return read: false",
            "- Final holdout: sealed",
            "- Live boundary: false",
            "",
        ]
    )


def normalise_option_contracts(
    contracts: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    required = (
        "ts_code",
        "exchange",
        "opt_code",
        "call_put",
        "list_date",
        "delist_date",
    )
    missing = sorted(set(required) - set(contracts.columns))
    if missing:
        raise ValueError(f"option contracts are missing columns: {', '.join(missing)}")
    frame = contracts[list(required)].copy()
    frame["ts_code"] = frame["ts_code"].astype(str)
    frame["exchange"] = frame["exchange"].astype(str).str.upper()
    frame["opt_code"] = frame["opt_code"].astype(str).str.upper()
    frame["call_put"] = frame["call_put"].astype(str).str.upper()
    frame["list_date"] = pd.to_datetime(frame["list_date"], errors="coerce")
    frame["delist_date"] = pd.to_datetime(frame["delist_date"], errors="coerce")
    if frame.duplicated("ts_code").any():
        raise ValueError("option contracts contain duplicate contract codes")
    frame = frame[
        frame["exchange"].isin(["SSE", "SZSE"])
        & frame["opt_code"].str.match(r"^OP\d{6}\.(SH|SZ)$", na=False)
        & frame["list_date"].le(end)
        & frame["delist_date"].ge(start)
    ].copy()
    frame["underlying_symbol"] = frame["opt_code"].str.extract(
        r"^OP(\d{6}\.(?:SH|SZ))$",
        expand=False,
    )
    if frame.empty or frame["underlying_symbol"].isna().any():
        raise ValueError("option contract source has no valid ETF underlyings")
    return frame.sort_values(["exchange", "underlying_symbol", "ts_code"]).reset_index(drop=True)


def _underlying_summary(contracts: pd.DataFrame) -> pd.DataFrame:
    return (
        contracts.groupby(["underlying_symbol", "exchange"], as_index=False)
        .agg(
            contract_count=("ts_code", "nunique"),
            first_list_date=("list_date", "min"),
            last_delist_date=("delist_date", "max"),
            call_count=("call_put", lambda values: int((values == "C").sum())),
            put_count=("call_put", lambda values: int((values == "P").sum())),
        )
        .sort_values(["exchange", "underlying_symbol"])
        .reset_index(drop=True)
    )


def _summarize_probes(
    daily_probes: Mapping[str, pd.DataFrame],
    *,
    contracts: pd.DataFrame,
    expected_dates: list[str],
    minimum_positive_close_ratio: float,
) -> tuple[list[dict[str, Any]], list[str]]:
    contract_codes = set(contracts["ts_code"])
    rows = []
    blockers = []
    normalized = {
        pd.Timestamp(key).date().isoformat(): value
        for key, value in daily_probes.items()
    }
    for date in expected_dates:
        frame = normalized.get(date)
        if frame is None or frame.empty:
            blockers.append(f"missing_option_daily_probe:{date}")
            continue
        required = {"ts_code", "trade_date", "exchange", "close", "vol", "amount", "oi"}
        missing = sorted(required - set(frame.columns))
        if missing:
            blockers.append(f"invalid_option_daily_probe_schema:{date}")
            continue
        item = frame.copy()
        item["ts_code"] = item["ts_code"].astype(str)
        item["trade_date"] = pd.to_datetime(item["trade_date"], errors="coerce")
        item["close"] = pd.to_numeric(item["close"], errors="coerce")
        if item.duplicated(["ts_code", "trade_date"]).any():
            blockers.append(f"duplicate_option_daily_probe_rows:{date}")
        positive_ratio = float((item["close"] > 0.0).mean())
        mapped_ratio = float(item["ts_code"].isin(contract_codes).mean())
        if positive_ratio < minimum_positive_close_ratio:
            blockers.append(f"option_daily_positive_close_ratio_below_minimum:{date}")
        if mapped_ratio < 0.99:
            blockers.append(f"option_daily_contract_mapping_below_minimum:{date}")
        rows.append(
            {
                "date": date,
                "rows": int(len(item)),
                "contracts": int(item["ts_code"].nunique()),
                "positive_close_ratio": positive_ratio,
                "contract_mapping_ratio": mapped_ratio,
                "sse_rows": int(item["exchange"].astype(str).str.upper().eq("SSE").sum()),
                "szse_rows": int(item["exchange"].astype(str).str.upper().eq("SZSE").sum()),
            }
        )
    return rows, blockers


def _stable_frame(rows: Any) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    sort = [
        column
        for column in ("exchange", "underlying_symbol", "date")
        if column in frame.columns
    ]
    return frame.sort_values(sort).reset_index(drop=True) if sort and not frame.empty else frame


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value
