"""One frozen monthly GPRT cadence calculation, without ETF outcome inputs."""
from decimal import Decimal, InvalidOperation
import json

MONTHS = tuple(f"{y}{m:02d}" for y in range(2022, 2026) for m in range(1, 13)
               if "202203" <= f"{y}{m:02d}" <= "202512")


def window_state(month, window):
    end = int(month[:4]) * 12 + int(month[4:]) - 1
    required = [f"{(n - 1) // 12:04d}-{(n - 1) % 12 + 1:02d}"
                for n in range(end - 12, end + 1)]
    try:
        if [r["month"] for r in window] != required:
            raise ValueError("required thirteen consecutive months missing")
        if any(isinstance(r["GPRT"], bool) for r in window):
            raise ValueError("Boolean is not an index observation")
        values = [Decimal(str(r["GPRT"])) for r in window]
        if any(not v.is_finite() or v < 0 for v in values):
            raise ValueError("required observation invalid")
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return dict(state=None, reason="source_window_unknown", target_GPRT=None, median_prior_12=None)
    ordered = sorted(values[:-1])
    median = (ordered[5] + ordered[6]) / Decimal(2)
    state = int(values[-1] > median)
    return dict(state=state, reason="above_prior_median" if state else "not_above_prior_median",
                target_GPRT=str(values[-1]), median_prior_12=str(median))


def screen(windows):
    if [row["month"] for row in windows] != list(MONTHS):
        raise ValueError("All 46 fixed chronological months, including unknowns, required")
    rows, episode, start = [], 0, None
    for item in windows:
        month = item["month"]
        result = window_state(month, item.get("window", []))
        is_new = result["state"] == 1 and (not rows or rows[-1]["state"] != 1)
        if is_new:
            episode += 1
            start = month
        if result["state"] != 1:
            start = None
        rows.append(dict(month=month, **result, new_source_episode=is_new,
                         source_episode_id=episode if start else None,
                         source_episode_start=start,
                         later_carry_in=bool(start and start < "202401" <= month)))
    later = [r for r in rows if r["month"] >= "202401"]

    def counts(items):
        return dict(months=len(items), selected_months=sum(r["state"] == 1 for r in items),
                    known_cash_months=sum(r["state"] == 0 for r in items),
                    unknown_months=sum(r["state"] is None for r in items),
                    new_source_episodes=sum(r["new_source_episode"] for r in items))

    full_count, later_count = counts(rows), counts(later)
    checks = dict(selected_months_full=full_count["selected_months"] >= 16,
                  selected_months_later=later_count["selected_months"] >= 6,
                  new_source_episodes_full=full_count["new_source_episodes"] >= 6,
                  new_source_episodes_later=later_count["new_source_episodes"] >= 3,
                  known_cash_full=full_count["known_cash_months"] > 0,
                  known_cash_later=later_count["known_cash_months"] > 0)
    passed = all(checks.values())
    return dict(rows=rows, full=full_count, later=later_count, checks=checks, passed=passed,
                status="cadence_passed_account_admission_pending" if passed else "closed_insufficient_source_cadence",
                states_generated=True, returns_computed=False, ETF_outcomes_read=False,
                new_return_studies=0, financial_execution_allowed=False,
                paper_promotion_allowed=False, final_holdout_allowed=False, live_boundary_allowed=False)


def calculate(snapshots):
    expansion = json.loads(snapshots["source_result"])
    windows = {row["month"]: row["window"] for row in expansion["results"]}
    pilots = json.loads(snapshots["pilot_windows"])
    for row in pilots:
        windows[row["vintage"]] = [{"month": r["month"], "GPRT": r["GPRT_decimal"]}
                                   for r in row["records"]]
    return screen([dict(month=month, window=windows.get(month, [])) for month in MONTHS])
