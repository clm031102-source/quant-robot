"""Independent saved-output verification of the fixed unitless sector screen.

No production screen import, source transport, account or strategy execution.
Each holding interval is valued as an equal-weight mean of endpoint price
ratios, then composed with the stipulated fee multipliers.
"""
from __future__ import annotations

from datetime import date
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
import math
import random


ASSETS = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")
PATHS = ("top3_gross", "top3_primary_proxy", "top3_stress_proxy", "equal9_gross")
FEES = {
    "top3_gross": ("0", "0", "0"),
    "equal9_gross": ("0", "0", "0"),
    "top3_primary_proxy": ("0.0040", "0.0085", "0.0045"),
    "top3_stress_proxy": ("0.0105", "0.0215", "0.0110"),
}
ONE = Decimal(1)
VERIFY_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN,
                         Emin=-999999, Emax=999999, capitals=1, clamp=0)


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _decimal(value):
    _require(type(value) in (str, int, float, Decimal), "numeric_type")
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ValueError("numeric_value") from exc
    _require(result.is_finite(), "finite_value")
    return result


def _same(expected, actual, label):
    a, b = _decimal(expected), _decimal(actual)
    _require(abs(a-b) <= Decimal("2e-10") * max(ONE, abs(a)), label)


def _contract(method):
    fixed = {"schema": "us_sector_momentum_screen_method_v1", "assets": list(ASSETS),
             "source_start": "2005-01-03", "source_end": "2025-12-31",
             "research_start_year": 2006, "research_end_year": 2025,
             "formation_months": 6, "decision_months": [6, 12], "top_count": 3,
             "initial_decision_month": "2005-12", "last_decision_month": "2025-06"}
    for key, expected in fixed.items():
        _require(method.get(key) == expected, "method_"+key)
    _require(set(method["paths"]) == set(PATHS), "method_paths")
    for cost in ("primary", "stress"):
        _require(tuple(method["fee_proxy"][cost][k] for k in ("entry", "rebalance", "exit"))
                 == FEES["top3_"+cost+"_proxy"], "method_costs")
    spec = method["advancement_conditions"]
    _require(spec["stress_terminal_wealth_above_one"] is True and
             spec["stress_vs_equal9_positive_log_relative_growth_in_both_segments"]
             == [[2006, 2015], [2016, 2025]], "method_segments")
    bs = spec["paired_annual_log_relative_bootstrap_lower_bound_above_zero"]
    _require(bs["block_length_years"] == 2 and bs["replications"] == 10000
             and bs["seed"] == 20261107 and bs["one_sided_confidence"] == "0.95",
             "method_statistics")
    qa = method["source_qa"]
    _require((qa["xlf_start"], qa["xlf_end"], qa["issuer_market_total_return"],
              qa["absolute_return_tolerance"]) ==
             ("2015-09-30", "2016-09-30", "0.0742", "0.0100"), "method_qa")


def _schedule(dates, prices):
    # Independently enumerate June/December endpoints from calendar years.
    endpoints = {}
    for i, day in enumerate(dates):
        endpoints[day[:7]] = i
    result = []
    for year in range(2005, 2026):
        for month in (6, 12):
            tag = f"{year:04d}-{month:02d}"
            if not "2005-12" <= tag <= "2025-06":
                continue
            prior = f"{year-1:04d}-12" if month == 6 else f"{year:04d}-06"
            i, j = endpoints[tag], endpoints[prior]
            scores = {a: prices[a][i]/prices[a][j]-ONE for a in ASSETS}
            selected = sorted(ASSETS, key=lambda a: (-scores[a], a))[:3]
            result.append(dict(decision_date=dates[i], formation_start=dates[j],
                               execution_date=dates[i+1], execution_index=i+1,
                               selected=selected, scores=scores))
    _require(len(result) == 40, "forty_periods")
    return result


def _period_path(dates, prices, schedule, path):
    """Closed-form interval ratios; deliberately no units or trading loop."""
    entry, rebalance, exit_fee = map(Decimal, FEES[path])
    carried = ONE
    values, charges = {}, []
    terminal = len(dates)-1
    for k, event in enumerate(schedule):
        start = event["execution_index"]
        end = schedule[k+1]["execution_index"] if k+1 < len(schedule) else terminal
        selected = ASSETS if path == "equal9_gross" else event["selected"]
        fee = entry if k == 0 else rebalance
        charges.append(dict(date=dates[start], kind="entry" if k == 0 else "rebalance",
                            fraction=fee, index_wealth_deducted=carried*fee))
        principal = carried*(ONE-fee)
        denominators = {a: prices[a][start] for a in selected}
        for i in range(start, end+1):
            ratio = sum((prices[a][i]/denominators[a] for a in selected), Decimal(0))/len(selected)
            values[i] = principal*ratio
        carried = values[end]
    charges.append(dict(date=dates[terminal], kind="exit", fraction=exit_fee,
                        index_wealth_deducted=carried*exit_fee))
    values[terminal] = carried*(ONE-exit_fee)
    return values, charges


def _bootstrap(values):
    # Independently resample paired two-year blocks; no production helper.
    rng = random.Random(20261107)
    estimates = []
    for _ in range(10000):
        starts = [rng.randrange(20) for _ in range(10)]
        sample = [values[(start+offset) % 20] for start in starts for offset in (0, 1)]
        estimates.append(math.fsum(sample)/20)
    return sorted(estimates)[499]


def verify(prepared, method, result):
    """Read only an already admitted, saved input and its completed screen."""
    with localcontext(VERIFY_CONTEXT):
        return _verify(prepared, method, result)


def verify_recorded_screen(prepared, method, result):
    """Controller-compatible alias; no other execution is performed."""
    return verify(prepared, method, result)


def _verify(prepared, method, result):
    _contract(method)
    _require(result.get("schema") == "us_sector_momentum_screen_result_v1", "result_schema")
    _require(result.get("evidence_kind") in (
        "known_history_provider_adjusted_total_return_proxy", "artificial_unitless_screen_fixture"),
        "result_evidence_kind")
    dates = prepared["dates"]
    _require(type(dates) is list and dates == sorted(set(dates)) and dates[0] == "2005-01-03"
             and dates[-1] == "2025-12-31", "input_dates")
    for day in dates:
        _require(date.fromisoformat(day).isoformat() == day, "canonical_date")
    _require({d[:7] for d in dates} == {f"{y}-{m:02d}" for y in range(2005, 2026)
                                     for m in range(1, 13)}, "all_months")
    _require(set(prepared["opaque_adjusted_close"]) == set(ASSETS), "input_assets")
    prices = {a: [_decimal(v) for v in prepared["opaque_adjusted_close"][a]] for a in ASSETS}
    _require(all(len(v) == len(dates) and all(p > 0 for p in v) for v in prices.values()), "input_prices")
    qa = result["source_qa"]
    a = prices["XLF"][dates.index("2015-09-30")]
    b = prices["XLF"][dates.index("2016-09-30")]
    observed = b/a-ONE
    _require(abs(observed-Decimal("0.0742")) <= Decimal("0.0100") and qa["status"] == "passed", "qa_pass")
    for key, expected in {"adjusted_close_start": a, "adjusted_close_end": b,
                          "provider_total_return": observed, "issuer_market_total_return": "0.0742",
                          "absolute_difference": abs(observed-Decimal("0.0742")),
                          "fixed_tolerance": "0.0100"}.items():
        _same(expected, qa[key], "qa_"+key)
    _require(qa["start"] == "2015-09-30" and qa["end"] == "2016-09-30"
             and qa["financial_values_converted"] == 2, "qa_identity")
    schedule = _schedule(dates, prices)
    _require(len(result["decisions"]) == 40, "decision_count")
    for expected, actual in zip(schedule, result["decisions"]):
        for key in ("decision_date", "formation_start", "execution_date", "execution_index", "selected"):
            _require(actual[key] == expected[key] and type(actual[key]) is type(expected[key]), "decision_"+key)
        _require(set(actual["scores"]) == set(ASSETS), "score_assets")
        for asset in ASSETS:
            _same(expected["scores"][asset], actual["scores"][asset], "formation_score")
    _require(set(result["paths"]) == set(PATHS), "four_paths")
    years = {}
    terminals = {}
    daily_checked = 0
    for name in PATHS:
        values, charges = _period_path(dates, prices, schedule, name)
        actual = result["paths"][name]
        indices = sorted(values)
        _require(len(actual["daily"]) == len(indices), "daily_count")
        peak, max_dd = ONE, Decimal(0)
        year_ends = {}
        for i, row in zip(indices, actual["daily"]):
            _require(row["date"] == dates[i], "daily_date")
            _same(values[i], row["wealth"], "daily_wealth")
            peak = max(peak, values[i]); max_dd = max(max_dd, ONE-values[i]/peak)
            year_ends[dates[i][:4]] = values[i]
        prior, annual = ONE, {}
        for year, wealth in year_ends.items():
            annual[year] = wealth/prior-ONE
            prior = wealth
        _require(set(actual["annual_returns"]) == set(annual), "annual_years")
        for year, value in annual.items():
            _same(value, actual["annual_returns"][year], "annual_return")
        terminal = values[indices[-1]]
        elapsed = (date.fromisoformat(dates[-1])-date.fromisoformat(dates[indices[0]])).days/365.25
        for key, value in {"terminal_wealth": terminal, "total_return": terminal-ONE,
                           "annualized_return": float(terminal)**(1/elapsed)-1,
                           "max_drawdown": max_dd}.items():
            _same(value, actual[key], "path_"+key)
        _require(len(actual["charges"]) == len(charges), "charge_count")
        for expected, charge in zip(charges, actual["charges"]):
            _require(charge["date"] == expected["date"] and charge["kind"] == expected["kind"], "charge_identity")
            for key in ("fraction", "index_wealth_deducted"):
                _same(expected[key], charge[key], "charge_"+key)
        _require(actual["account_count"] == 0 and actual["tradable_share_units"] is False, "unitless_path")
        years[name], terminals[name] = annual, terminal
        daily_checked += len(indices)
    relative = {str(y): math.log1p(float(years["top3_stress_proxy"][str(y)]))
                - math.log1p(float(years["equal9_gross"][str(y)])) for y in range(2006, 2026)}
    _require(set(result["annual_log_relative_stress_vs_equal9"]) == set(relative), "relative_years")
    for y, value in relative.items():
        _same(value, result["annual_log_relative_stress_vs_equal9"][y], "annual_log_relative")
    segments = [math.fsum(relative[str(y)] for y in range(a, b+1)) for a,b in ((2006,2015),(2016,2025))]
    _require(len(result["segment_log_relative_stress_vs_equal9"]) == 2, "segment_count")
    for expected, actual in zip(segments, result["segment_log_relative_stress_vs_equal9"]):
        _same(expected, actual, "relative_segment")
    lower = _bootstrap(list(relative.values()))
    _same(lower, result["bootstrap_lower_mean_annual_log_relative"], "bootstrap_lower")
    checks = {"stress_terminal_positive": terminals["top3_stress_proxy"] > ONE,
              "positive_relative_growth_both_decades": all(v > 0 for v in segments),
              "annual_relative_bootstrap_lower_positive": lower > 0}
    _require(result["checks"] == checks and all(type(v) is bool for v in result["checks"].values()), "economic_checks")
    expected_status = "screen_passed_requires_implementation_validation" if all(checks.values()) else "screen_rejected"
    _require(result["status"] == expected_status, "screen_status")
    _require(result["source_actions"] == prepared["events"], "saved_source_actions")
    _require(result["unique_adjusted_close_values_decoded"] == len(dates)*9, "decoded_count")
    _require(result["qualified"] is False and result["real_forward_days"] == 0
             and result["account_count"] == 0, "no_account_or_qualification")
    return {"schema": "us_sector_momentum_independent_verification_v1", "status": "passed",
            "evidence_kind": result["evidence_kind"], "periods_checked": 40,
            "paths_checked": 4, "daily_values_checked": daily_checked, "annual_values_checked": 80,
            "source_qa_recomputed": True, "ranking_and_next_close_checked": True,
            "bootstrap_replications": 10000, "checks": checks, "screen_status": expected_status,
            "formula": "per-period arithmetic mean of selected adjusted-price ratios times fixed fee multipliers",
            "verification_decimal_precision": 50, "production_screen_imported": False,
            "strategy_or_account_rerun": False, "new_source_calls": 0, "qualified": False,
            "limitations": ["Does not independently certify provider corporate actions or price accuracy",
                            "Unitless proxy only; no share, tax, fill or brokerage verification"]}
