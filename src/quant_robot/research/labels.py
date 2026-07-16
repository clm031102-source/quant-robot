from __future__ import annotations

import pandas as pd


def make_forward_returns(bars: pd.DataFrame, horizons: tuple[int, ...] = (1, 5, 20), execution_lag: int = 1) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for forward returns: {', '.join(missing)}")

    rows: list[pd.DataFrame] = []
    frame = bars.sort_values(["asset_id", "date"]).copy()
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.reset_index(drop=True)
        for horizon in horizons:
            entry = group["adj_close"].shift(-execution_lag)
            exit_ = group["adj_close"].shift(-(execution_lag + horizon))
            labels = pd.DataFrame(
                {
                    "date": group["date"],
                    "asset_id": group["asset_id"],
                    "market": group["market"],
                    "horizon": horizon,
                    "execution_lag": execution_lag,
                    "forward_return": exit_ / entry - 1.0,
                    "entry_date": group["date"].shift(-execution_lag),
                    "exit_date": group["date"].shift(-(execution_lag + horizon)),
                }
            )
            rows.append(labels.dropna(subset=["forward_return", "entry_date", "exit_date"]))
    if not rows:
        return pd.DataFrame(
            columns=[
                "date",
                "asset_id",
                "market",
                "horizon",
                "execution_lag",
                "forward_return",
                "entry_date",
                "exit_date",
            ]
        )
    return pd.concat(rows, ignore_index=True).sort_values(["asset_id", "date", "horizon"]).reset_index(drop=True)


def filter_market_calendar_aligned_forward_returns(
    labels: pd.DataFrame,
    bars: pd.DataFrame,
) -> pd.DataFrame:
    """Drop labels whose asset-row shifts compress the market-session horizon."""

    label_required = [
        "date",
        "asset_id",
        "market",
        "horizon",
        "execution_lag",
        "entry_date",
        "exit_date",
    ]
    missing_labels = [column for column in label_required if column not in labels.columns]
    if missing_labels:
        raise ValueError(
            "Forward-return labels are missing columns: " + ", ".join(missing_labels)
        )
    bar_required = ["date", "asset_id", "market"]
    missing_bars = [column for column in bar_required if column not in bars.columns]
    if missing_bars:
        raise ValueError("Bars are missing calendar columns: " + ", ".join(missing_bars))
    if labels.empty:
        return labels.copy()

    bar_frame = bars[bar_required].copy()
    bar_frame["_calendar_date"] = pd.to_datetime(bar_frame["date"], errors="coerce")
    if bar_frame["_calendar_date"].isna().any():
        raise ValueError("Bars contain invalid calendar dates")
    if bar_frame.duplicated(["_calendar_date", "asset_id", "market"]).any():
        raise ValueError("Bars contain duplicate asset-market calendar rows")

    frame = labels.copy()
    frame["_row_order"] = range(len(frame))
    frame["_signal_date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["_entry_date"] = pd.to_datetime(frame["entry_date"], errors="coerce")
    frame["_exit_date"] = pd.to_datetime(frame["exit_date"], errors="coerce")
    frame["horizon"] = pd.to_numeric(frame["horizon"], errors="coerce")
    frame["execution_lag"] = pd.to_numeric(frame["execution_lag"], errors="coerce")
    if frame[["_signal_date", "_entry_date", "_exit_date", "horizon", "execution_lag"]].isna().any().any():
        raise ValueError("Forward-return labels contain invalid dates or horizons")
    frame["horizon"] = frame["horizon"].astype(int)
    frame["execution_lag"] = frame["execution_lag"].astype(int)
    if frame["horizon"].lt(1).any() or frame["execution_lag"].lt(0).any():
        raise ValueError("Forward-return label horizons and lags are invalid")
    if frame.duplicated(
        ["_signal_date", "asset_id", "market", "horizon", "execution_lag"]
    ).any():
        raise ValueError("Forward-return labels contain duplicate rows")

    schedules: list[pd.DataFrame] = []
    policies = frame[["market", "horizon", "execution_lag"]].drop_duplicates()
    for market, market_policies in policies.groupby("market", sort=True):
        calendar = pd.DatetimeIndex(
            sorted(
                bar_frame.loc[bar_frame["market"].eq(market), "_calendar_date"].unique()
            )
        )
        for policy in market_policies.itertuples(index=False):
            horizon = int(policy.horizon)
            execution_lag = int(policy.execution_lag)
            usable = len(calendar) - execution_lag - horizon
            if usable <= 0:
                continue
            schedules.append(
                pd.DataFrame(
                    {
                        "market": str(market),
                        "horizon": horizon,
                        "execution_lag": execution_lag,
                        "_signal_date": calendar[:usable],
                        "_expected_entry_date": calendar[
                            execution_lag : execution_lag + usable
                        ],
                        "_expected_exit_date": calendar[
                            execution_lag + horizon : execution_lag + horizon + usable
                        ],
                    }
                )
            )
    if not schedules:
        return labels.iloc[0:0].copy()
    schedule = pd.concat(schedules, ignore_index=True)
    checked = frame.merge(
        schedule,
        on=["market", "horizon", "execution_lag", "_signal_date"],
        how="left",
        validate="many_to_one",
    )
    aligned = checked[
        checked["_entry_date"].eq(checked["_expected_entry_date"])
        & checked["_exit_date"].eq(checked["_expected_exit_date"])
    ]
    selected = aligned["_row_order"].astype(int).sort_values()
    return labels.iloc[selected.to_numpy()].reset_index(drop=True)
