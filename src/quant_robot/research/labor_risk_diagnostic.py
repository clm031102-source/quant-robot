"""One fixed labor-risk contrast: release-timed, conditional gross exploration."""
from bisect import bisect_right
from datetime import date
import io
import json
import math
import numpy as np
import pandas as pd
from quant_robot.research.disclosed_flow_diagnostic import open_return


def event_intervals(sources, sessions):
    if not sessions or sessions != sorted(set(sessions)):
        raise ValueError("Unique ordered exchange calendar required")
    if any(date.fromisoformat(d).isoformat() != d for d in sessions):
        raise ValueError("Canonical session dates required")
    by_month = {}
    release_dates = []
    for row in sources:
        month = row["observation_month"]
        day = date.fromisoformat(row["declared_release_date"])
        expected = f"{day.year-1}-12" if day.month == 1 else f"{day.year}-{day.month-1:02}"
        value = row["rate_tenths_pct"]
        if (day.month == 2 or month != expected or month in by_month
                or type(value) is not int or not 0 <= value <= 1000):
            raise ValueError("Unique prior-month all-age rates in integer tenths required")
        by_month[month] = row
        release_dates.append(row["declared_release_date"])
    if release_dates != sorted(set(release_dates)):
        raise ValueError("Source releases must be ordered and unique")
    anchors = []
    for row in sources:
        day = row["declared_release_date"]
        if sessions[0] <= day < sessions[-1]:
            index = bisect_right(sessions, day)
            if index < len(sessions):
                anchors.append((row, index))
    out = []
    for (row, i), (_, j) in zip(anchors, anchors[1:]):
        month = row["observation_month"]
        prior = by_month.get(f"{int(month[:4])-1}{month[4:]}")
        if not prior or prior["declared_release_date"] >= row["declared_release_date"] or j <= i:
            raise ValueError("Earlier exact prior-year reference and distinct anchors required")
        contrast = row["rate_tenths_pct"] - prior["rate_tenths_pct"]
        out.append(dict(entry_date=sessions[i], exit_date=sessions[j], sessions=j-i,
            observation_month=month, release_date=row["declared_release_date"],
            reference_release_date=prior["declared_release_date"],
            contrast_tenths_pct=contrast, selected=int(contrast > 0)))
    return out


def _description(rows):
    if not rows:
        raise ValueError("Fixed subset is empty")
    z = np.array([r["selected"] for r in rows], dtype=float)
    y = np.array([r["return_value"] for r in rows], dtype=float)
    n = np.array([r["sessions"] for r in rows], dtype=float)
    fraction = float((n*z).sum()/n.sum())
    return dict(intervals=len(rows), selected_intervals=int(z.sum()),
        unselected_intervals=int((z == 0).sum()), session_transitions=int(n.sum()),
        selected_session_fraction=fraction,
        D_daily_log=float(((z-fraction)*np.log1p(y)).sum()/n.sum()),
        selected_mean_gross=float(y[z == 1].mean()) if z.any() else None,
        selected_positive_fraction=float((y[z == 1] > 0).mean()) if z.any() else None,
        unconditional_mean_gross=float(y.mean()),
        internal_state_switches=int(np.count_nonzero(np.diff(z))))


def summarize(rows):
    if len(rows) <= 12:
        raise ValueError("More intervals than the fixed block length required")
    for row in rows:
        if (type(row["selected"]) is not int or row["selected"] not in (0, 1)
                or type(row["sessions"]) is not int or row["sessions"] <= 0
                or not math.isfinite(row["return_value"]) or row["return_value"] <= -1):
            raise ValueError("Binary states, positive durations and finite gross returns required")
    full = _description(rows)
    later = _description([r for r in rows if r["entry_date"] >= "2023-01-01"])
    z, y, days = (np.array([r[k] for r in rows]) for k in ("selected", "return_value", "sessions"))
    count = len(rows)
    starts = np.random.default_rng(20260921).integers(0, count, size=(5000, math.ceil(count/12)))
    ids = ((starts[:, :, None]+np.arange(12)) % count).reshape(5000, -1)[:, :count]
    zr, nr, lr = z[ids], days[ids], np.log1p(y[ids])
    exposures = (zr*nr).sum(axis=1)/nr.sum(axis=1)
    effects = ((zr-exposures[:, None])*lr).sum(axis=1)/nr.sum(axis=1)
    interval = [float(x) for x in np.quantile(effects, [.025, .975])]
    checks = dict(selected_count=full["selected_intervals"] >= 6,
        later_selected_count=later["selected_intervals"] >= 3,
        nonconstant=full["unselected_intervals"] > 0, effect_lower_positive=interval[0] > 0,
        selected_mean_positive=full["selected_mean_gross"] is not None and full["selected_mean_gross"] > 0,
        later_mean_positive=later["selected_mean_gross"] is not None and later["selected_mean_gross"] > 0,
        later_effect_positive=later["D_daily_log"] > 0)
    return dict(full=full, later_2023_onward=later, bootstrap_D_daily_log_2_5_97_5=interval,
        bootstrap_replications=5000, block_release_intervals=12, seed=20260921,
        checks=checks, gross_screen_passed=all(checks.values()),
        annual={year: _description([r for r in rows if r["entry_date"].startswith(year)])
                for year in sorted({r["entry_date"][:4] for r in rows})},
        net_positive_EV_verified=False, fresh_OOS=False, multiple_testing_adjusted=False,
        historical_vintage_verified=False, completed_account_trade_count=None)


def calculate(snapshots):
    from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot
    from quant_robot.paper.corporate_actions import validate_corporate_action_dataset
    from quant_robot.research.monthly_diagnostic_registration import sha256
    sources = json.loads(snapshots["source_rows"])["rows"]
    if len(sources) != 60:
        raise ValueError("All60 frozen source observations required")
    for i, row in enumerate(sources):
        if row["raw_sha256"] != sha256(snapshots[f"release_{i}"]):
            raise ValueError("Source observation differs from its pinned original")
    calendar = calendar_rows_from_snapshot(snapshots["calendar"], snapshots["calendar_manifest"],
        start=date(2020, 1, 2), end=date(2024, 6, 28))
    sessions = [str(d) for d, opened in calendar if opened]
    rows = event_intervals(sources, sessions)
    if len(rows) != 48 or rows[0]["entry_date"] != "2020-01-20" or rows[-1]["exit_date"] != "2024-06-18":
        raise ValueError("Frozen release interval universe differs")
    anchors = sorted({r[k] for r in rows for k in ("entry_date", "exit_date")})
    opens = {}
    for year in range(2020, 2025):
        days = [date.fromisoformat(d) for d in anchors if d.startswith(str(year))]
        bars = pd.read_parquet(io.BytesIO(snapshots[f"bars_{year}"]),
            columns=["date", "asset_id", "market", "currency", "open"],
            filters=[("date", "in", days), ("asset_id", "==", "CN_ETF_XSHG_510300")])
        for row in bars.to_dict("records"):
            d = str(row["date"])
            if d not in anchors or d in opens or row["market"] != "CN_ETF" or row["currency"] != "CNY":
                raise ValueError("Unique scoped CN_ETF/CNY price anchors required")
            opens[d] = row["open"]
    if sorted(opens) != anchors:
        raise ValueError("Complete price anchors required")
    actions = json.loads(snapshots["actions"])
    validate_corporate_action_dataset(actions, {"CN_ETF_XSHG_510300"}, [date.fromisoformat(d) for d in sessions])
    for event in actions["events"]:
        if (event["asset_id"] != "CN_ETF_XSHG_510300" or event["record_date"] not in sessions
                or event["ex_date"] not in sessions or sessions.index(event["record_date"])+1 != sessions.index(event["ex_date"])):
            raise ValueError("Reviewed record/ex session ordering required")
    for row in rows:
        row["return_value"] = open_return(row["entry_date"], row["exit_date"],
            opens[row["entry_date"]], opens[row["exit_date"]], actions["events"])
    return dict(diagnostic=summarize(rows), observations=rows, net_account_run=False,
        new_forward_paper_days=0, ETF_open_values_decoded=len(opens),
        price_basis="one_share_open_to_open_declared_cash_gross_v1")

