from __future__ import annotations

from datetime import date as calendar_date

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


ETF_MONEYFLOW_BASKET_FACTOR_NAMES = (
    "etf_net_mf_amount_ratio",
    "etf_net_mf_amount_ratio_low",
    "etf_large_order_net_amount_ratio",
    "etf_large_order_net_amount_ratio_low",
    "etf_extra_large_order_net_amount_ratio",
    "etf_extra_large_order_net_amount_ratio_low",
    "etf_small_order_sell_pressure",
    "etf_small_order_sell_pressure_low",
    "etf_net_mf_positive_weight",
    "etf_net_mf_positive_weight_low",
)

_MONEYFLOW_AMOUNT_COLUMNS = [
    "buy_sm_amount",
    "sell_sm_amount",
    "buy_md_amount",
    "sell_md_amount",
    "buy_lg_amount",
    "sell_lg_amount",
    "buy_elg_amount",
    "sell_elg_amount",
]


def aggregate_etf_moneyflow_basket_inputs(moneyflow_inputs: pd.DataFrame, baskets: pd.DataFrame) -> pd.DataFrame:
    """Aggregate only complete mapped memberships on observed input dates.

    This guard does not certify the supplied basket as a complete fund holding,
    or detect an entire market session absent from the input date universe.
    Source qualification and the independent calendar audit remain required.
    """
    _require_columns(
        moneyflow_inputs,
        ["date", "asset_id", *_MONEYFLOW_AMOUNT_COLUMNS, "net_mf_amount"],
        "Moneyflow inputs",
    )
    _require_columns(baskets, ["etf_asset_id", "stock_asset_id", "weight", "known_date"], "ETF moneyflow baskets")
    moneyflow = moneyflow_inputs.copy()
    moneyflow["date"] = pd.to_datetime(moneyflow["date"]).dt.date
    if moneyflow["date"].isna().any():
        raise ValueError("Moneyflow inputs contain missing dates")
    if moneyflow.duplicated(["date", "asset_id"]).any():
        raise ValueError("duplicate stock/date moneyflow observations")
    moneyflow = _with_stock_moneyflow_ratios(moneyflow)
    basket = baskets.copy()
    basket["known_date"] = pd.to_datetime(basket["known_date"], errors="coerce").dt.date
    raw_end = basket["end_date"].copy() if "end_date" in basket else pd.Series(pd.NaT, index=basket.index)
    basket["end_date"] = (
        pd.to_datetime(basket["end_date"], errors="coerce").dt.date
        if "end_date" in basket.columns
        else pd.NaT
    )
    if (raw_end.notna() & basket["end_date"].isna()).any():
        raise ValueError("ETF moneyflow baskets contain invalid end_date values")
    boolean_weights = basket["weight"].map(lambda value: isinstance(value, (bool, np.bool_)))
    basket["weight"] = pd.to_numeric(basket["weight"], errors="coerce")
    weight_values = basket["weight"].to_numpy(dtype=float, na_value=np.nan)
    if boolean_weights.any() or not np.isfinite(weight_values).all() or (weight_values <= 0).any():
        raise ValueError("finite positive basket weights required")
    if "etf_symbol" not in basket.columns:
        basket["etf_symbol"] = basket["etf_asset_id"]
    else:
        symbol = basket["etf_symbol"].astype("string")
        basket["etf_symbol"] = symbol.where(symbol.str.strip().ne("") & symbol.notna(), basket["etf_asset_id"])
    if basket["known_date"].isna().any():
        raise ValueError("ETF moneyflow baskets contain missing known_date values")
    basket["_coverage_end"] = basket["end_date"].where(basket["end_date"].notna(), calendar_date.max)
    if (basket["_coverage_end"] < basket["known_date"]).any():
        raise ValueError("ETF moneyflow basket end_date precedes known_date")
    for frame, columns in ((moneyflow, ["asset_id"]), (basket, ["etf_asset_id", "stock_asset_id"])):
        for column in columns:
            if not frame[column].map(lambda value: isinstance(value, str) and bool(value.strip()) and value == value.strip()).all():
                raise ValueError("nonempty unambiguous asset identities required")
    _check_membership_intervals(basket)
    expected = _expected_constituent_counts(basket, sorted(moneyflow["date"].unique()))
    joined = moneyflow.merge(
        basket,
        left_on="asset_id",
        right_on="stock_asset_id",
        how="inner",
        suffixes=("_stock", "_basket"),
    )
    date = pd.to_datetime(joined["date"]).dt.date
    known = pd.to_datetime(joined["known_date"]).dt.date
    end = pd.to_datetime(joined["end_date"], errors="coerce").dt.date
    active = (known <= date) & (pd.isna(end) | (date <= end))
    joined = joined[active].copy()
    actual = joined.groupby(["date", "etf_asset_id"]).size()
    if (actual.reindex(expected.index, fill_value=0) != expected).any():
        raise ValueError("incomplete active constituent moneyflow coverage; no reweighting permitted")
    if joined.empty:
        return _empty_aggregated()
    raw_amounts = joined[_MONEYFLOW_AMOUNT_COLUMNS].apply(pd.to_numeric, errors="coerce")
    ratios = joined[["stock_net_mf_amount_ratio", "stock_large_order_net_amount_ratio",
                     "stock_extra_large_order_net_amount_ratio", "stock_small_order_sell_pressure"]]
    with np.errstate(over="ignore"):
        flow_totals = raw_amounts.to_numpy(dtype=float, na_value=np.nan).sum(axis=1)
    if (not np.isfinite(raw_amounts.to_numpy(dtype=float, na_value=np.nan)).all()
            or (raw_amounts < 0).any().any() or not np.isfinite(flow_totals).all() or (flow_totals <= 0).any()
            or not np.isfinite(ratios.to_numpy(dtype=float, na_value=np.nan)).all()):
        raise ValueError("invalid active constituent moneyflow; missing values cannot be neutralized")
    joined["positive_net_mf_weight"] = np.where(joined["stock_net_mf_amount_ratio"] > 0.0, joined["weight"], 0.0)
    ratio_columns = [
        "stock_net_mf_amount_ratio",
        "stock_large_order_net_amount_ratio",
        "stock_extra_large_order_net_amount_ratio",
        "stock_small_order_sell_pressure",
    ]
    for column in ratio_columns:
        joined[f"weighted_{column}"] = joined["weight"] * joined[column]
    grouped = joined.groupby(["date", "etf_asset_id"], as_index=False, sort=True)
    rows = grouped.agg(
        basket_weight_sum=("weight", "sum"),
        constituent_count=("stock_asset_id", "nunique"),
        etf_symbol=("etf_symbol", _first_text),
        weighted_net_mf=("weighted_stock_net_mf_amount_ratio", "sum"),
        weighted_large=("weighted_stock_large_order_net_amount_ratio", "sum"),
        weighted_extra=("weighted_stock_extra_large_order_net_amount_ratio", "sum"),
        weighted_small_sell=("weighted_stock_small_order_sell_pressure", "sum"),
        positive_net_mf_weight=("positive_net_mf_weight", "sum"),
    )
    denominator = pd.to_numeric(rows["basket_weight_sum"], errors="coerce").where(rows["basket_weight_sum"] > 0)
    if not np.isfinite(rows[["basket_weight_sum", "weighted_net_mf", "weighted_large", "weighted_extra",
                             "weighted_small_sell", "positive_net_mf_weight"]].to_numpy(dtype=float)).all():
        raise ValueError("nonfinite basket aggregate after weighting")
    rows["asset_id"] = rows["etf_asset_id"]
    rows["symbol"] = rows["etf_symbol"]
    rows["market"] = "CN_ETF"
    rows["source"] = "etf_moneyflow_basket"
    rows["etf_net_mf_amount_ratio"] = rows["weighted_net_mf"] / denominator
    rows["etf_large_order_net_amount_ratio"] = rows["weighted_large"] / denominator
    rows["etf_extra_large_order_net_amount_ratio"] = rows["weighted_extra"] / denominator
    rows["etf_small_order_sell_pressure"] = rows["weighted_small_sell"] / denominator
    rows["etf_net_mf_positive_weight"] = rows["positive_net_mf_weight"] / denominator
    output_columns = [
        "date",
        "asset_id",
        "symbol",
        "market",
        "source",
        "basket_weight_sum",
        "constituent_count",
        "etf_net_mf_amount_ratio",
        "etf_large_order_net_amount_ratio",
        "etf_extra_large_order_net_amount_ratio",
        "etf_small_order_sell_pressure",
        "etf_net_mf_positive_weight",
    ]
    return rows[output_columns].sort_values(["asset_id", "date"]).reset_index(drop=True)


def _check_membership_intervals(basket: pd.DataFrame) -> None:
    for _, rows in basket.groupby(["etf_asset_id", "stock_asset_id"], sort=False):
        previous_end = None
        for start, end in rows.sort_values("known_date")[["known_date", "_coverage_end"]].itertuples(index=False, name=None):
            if previous_end is not None and start <= previous_end:
                raise ValueError("overlapping ETF constituent membership intervals")
            previous_end = end


def _expected_constituent_counts(basket: pd.DataFrame, dates: list) -> pd.Series:
    # Expand window COUNTS, not every constituent against every historical day.
    # This also retains an expected ETF/day when all of its flows are missing.
    pieces = []
    windows = basket.groupby(["etf_asset_id", "known_date", "_coverage_end"], sort=False).size()
    for (etf, start, end), count in windows.items():
        active_dates = [value for value in dates if start <= value <= end]
        if active_dates:
            pieces.append(pd.DataFrame({"date": active_dates, "etf_asset_id": etf, "expected": count}))
    if not pieces:
        index = pd.MultiIndex.from_arrays([[], []], names=["date", "etf_asset_id"])
        return pd.Series(index=index, dtype="int64")
    return pd.concat(pieces, ignore_index=True).groupby(["date", "etf_asset_id"])["expected"].sum()


def compute_etf_moneyflow_basket_factors(inputs: pd.DataFrame) -> pd.DataFrame:
    required = [
        "date",
        "asset_id",
        "market",
        "etf_net_mf_amount_ratio",
        "etf_large_order_net_amount_ratio",
        "etf_extra_large_order_net_amount_ratio",
        "etf_small_order_sell_pressure",
        "etf_net_mf_positive_weight",
    ]
    _require_columns(inputs, required, "ETF moneyflow basket inputs")
    frame = inputs.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    factor_values = {
        "etf_net_mf_amount_ratio": _number(frame["etf_net_mf_amount_ratio"]),
        "etf_net_mf_amount_ratio_low": -_number(frame["etf_net_mf_amount_ratio"]),
        "etf_large_order_net_amount_ratio": _number(frame["etf_large_order_net_amount_ratio"]),
        "etf_large_order_net_amount_ratio_low": -_number(frame["etf_large_order_net_amount_ratio"]),
        "etf_extra_large_order_net_amount_ratio": _number(frame["etf_extra_large_order_net_amount_ratio"]),
        "etf_extra_large_order_net_amount_ratio_low": -_number(frame["etf_extra_large_order_net_amount_ratio"]),
        "etf_small_order_sell_pressure": _number(frame["etf_small_order_sell_pressure"]),
        "etf_small_order_sell_pressure_low": -_number(frame["etf_small_order_sell_pressure"]),
        "etf_net_mf_positive_weight": _number(frame["etf_net_mf_positive_weight"]),
        "etf_net_mf_positive_weight_low": -_number(frame["etf_net_mf_positive_weight"]),
    }
    pieces = [_factor_frame(frame, name, values) for name, values in factor_values.items()]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _with_stock_moneyflow_ratios(frame: pd.DataFrame) -> pd.DataFrame:
    source = frame.copy()
    denominator = _total_flow_amount(source)
    source["stock_net_mf_amount_ratio"] = _ratio(source["net_mf_amount"], denominator)
    source["stock_large_order_net_amount_ratio"] = _ratio(
        _number(source["buy_lg_amount"])
        + _number(source["buy_elg_amount"])
        - _number(source["sell_lg_amount"])
        - _number(source["sell_elg_amount"]),
        denominator,
    )
    source["stock_extra_large_order_net_amount_ratio"] = _ratio(
        _number(source["buy_elg_amount"]) - _number(source["sell_elg_amount"]),
        denominator,
    )
    source["stock_small_order_sell_pressure"] = _ratio(
        _number(source["sell_sm_amount"]) - _number(source["buy_sm_amount"]),
        denominator,
    )
    return source


def _total_flow_amount(frame: pd.DataFrame) -> pd.Series:
    total = sum(_number(frame[column]).abs() for column in _MONEYFLOW_AMOUNT_COLUMNS)
    return total.where(total > 0)


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return (_number(numerator) / denominator).replace([np.inf, -np.inf], np.nan)


def _number(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce")


def _first_text(values: pd.Series) -> str:
    valid = values.dropna().astype(str)
    return valid.iloc[0] if not valid.empty else ""


def _factor_frame(inputs: pd.DataFrame, name: str, values: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": inputs["date"].to_numpy(),
            "asset_id": inputs["asset_id"].to_numpy(),
            "market": inputs["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": 1,
        }
    )


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} are missing columns: {', '.join(missing)}")


def _empty_aggregated() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "asset_id",
            "symbol",
            "market",
            "source",
            "basket_weight_sum",
            "constituent_count",
            "etf_net_mf_amount_ratio",
            "etf_large_order_net_amount_ratio",
            "etf_extra_large_order_net_amount_ratio",
            "etf_small_order_sell_pressure",
            "etf_net_mf_positive_weight",
        ]
    )
