"""Fixed unitless industry-momentum screen. No account, transport or orders.

Adjusted-close units are index units, never historical tradable shares. The
controller must persist admission/claim before the first financial conversion.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Context, Decimal, InvalidOperation, localcontext
from fractions import Fraction
import json
import math
import random
import re
from zoneinfo import ZoneInfo

ASSETS = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")
NY = ZoneInfo("America/New_York")
NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def opaque(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    return json.loads(raw, parse_int=str, parse_float=str, object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False, "nonstandard_number"))


def day(token):
    require(type(token) is str and re.fullmatch(r"[0-9]+", token), "timestamp_integer")
    return datetime.fromtimestamp(int(token), NY).date().isoformat()


def number(token):
    require(type(token) is str and NUMBER.fullmatch(token), "numeric_literal")
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError("numeric_literal") from exc
    require(value.is_finite() and value > 0, "positive_finite_adjusted_close")
    return value


def inspect_sources(raw_by_symbol, method):
    """Dates/actions only. Price and dividend amount literals stay opaque."""
    require(tuple(method["assets"]) == ASSETS and set(raw_by_symbol) == set(ASSETS), "exact_nine_assets")
    all_dates, rows, actions = {}, {}, []
    known = method["source_qa"]["known_true_splits"]
    for symbol in ASSETS:
        obj = opaque(raw_by_symbol[symbol])
        chart = obj.get("chart", {})
        require(chart.get("error") is None and type(chart.get("result")) is list
                and len(chart["result"]) == 1, "one_chart_result")
        row = chart["result"][0]
        meta = row.get("meta", {})
        require(meta.get("symbol") == symbol and meta.get("currency") == "USD"
                and meta.get("instrumentType") == "ETF"
                and meta.get("exchangeTimezoneName") == "America/New_York"
                and meta.get("dataGranularity") == "1d", "identity_units_interval")
        require(type(row.get("timestamp")) is list, "timestamps")
        dates = [day(t) for t in row["timestamp"]]
        require(dates == sorted(set(dates)) and dates
                and dates[0] == method["source_start"] and dates[-1] == method["source_end"], "date_bounds_order")
        require(all(method["source_start"] <= d <= method["source_end"] for d in dates), "date_outside_window")
        adjusted = row.get("indicators", {}).get("adjclose")
        require(type(adjusted) is list and len(adjusted) == 1
                and set(adjusted[0]) == {"adjclose"}
                and type(adjusted[0]["adjclose"]) is list
                and len(adjusted[0]["adjclose"]) == len(dates), "adjusted_close_shape")
        events = row.get("events", {})
        require(type(events) is dict and set(events) <= {"dividends", "splits", "capitalGains"}, "event_types")
        require(not events.get("capitalGains"), "unrecognized_capital_gains")
        seen_splits, xlf_special_seen = set(), False
        for kind, entries in events.items():
            require(type(entries) is dict, "event_container")
            seen_dates = set()
            for key, event in entries.items():
                require(type(event) is dict and key == event.get("date"), "event_key_date")
                d = day(key)
                require(d in dates and d not in seen_dates, "event_session_or_duplicate")
                seen_dates.add(d)
                item = {"symbol": symbol, "type": kind, "date": d}
                if kind == "splits":
                    require({"date", "numerator", "denominator", "splitRatio"} <= set(event), "split_fields")
                    n, den = event["numerator"], event["denominator"]
                    require(type(n) is str and type(den) is str and NUMBER.fullmatch(n) and NUMBER.fullmatch(den), "split_ratio_literal")
                    require(Fraction(n) > 0 and Fraction(den) > 0, "positive_split_parts")
                    ratio = Fraction(n) / Fraction(den)
                    parts = event["splitRatio"].split(":")
                    require(len(parts) == 2 and Fraction(parts[0]) > 0 and Fraction(parts[1]) > 0
                            and Fraction(parts[0]) / Fraction(parts[1]) == ratio, "split_ratio_consistency")
                    if symbol == "XLF" and d == "2016-09-19":
                        require(1 < ratio < 2, "xlf_vendor_adjustment_range")
                        item["classification"] = "vendor_adjustment_for_in_kind_distribution_not_share_split"
                        xlf_special_seen = True
                    else:
                        require(known.get(symbol) == d and ratio == 2, "unexpected_split")
                        seen_splits.add(d)
                        item["classification"] = "official_two_for_one_share_split"
                    item["source_ratio"] = event["splitRatio"]
                elif kind == "dividends":
                    require({"date", "amount"} <= set(event) and type(event["amount"]) is str
                            and NUMBER.fullmatch(event["amount"]) and not event["amount"].startswith("-"), "dividend_amount_literal")
                    if symbol == "XLF" and d == "2016-09-19":
                        xlf_special_seen = True
                    item["amount_converted"] = False
                actions.append(item)
        require(seen_splits == ({known[symbol]} if symbol in known else set()), "known_true_split_missing")
        if symbol == "XLF":
            require(xlf_special_seen, "xlf_special_event_evidence_missing")
        all_dates[symbol], rows[symbol] = dates, adjusted[0]["adjclose"]
    dates = all_dates[ASSETS[0]]
    require(all(d == dates for d in all_dates.values()), "exact_date_sets_no_intersection")
    months = sorted({d[:7] for d in dates})
    expected = [f"{y}-{m:02d}" for y in range(2005, 2026) for m in range(1, 13)]
    require(months == expected, "missing_calendar_month")
    require(all(sum(d.startswith(str(y)) for d in dates) >= 200 for y in range(2005, 2026)), "sparse_year")
    return {"dates": dates, "opaque_adjusted_close": rows, "events": actions,
            "calendar_basis": "same_provider_exact_nine_session_sets_not_independent_exchange_certification"}


def source_qa(prepared, method):
    """The first financial read: exactly two XLF adjusted close values."""
    spec = method["source_qa"]
    dates = prepared["dates"]
    values = prepared["opaque_adjusted_close"]["XLF"]
    a = number(values[dates.index(spec["xlf_start"])])
    b = number(values[dates.index(spec["xlf_end"])])
    with localcontext(Context(prec=50)):
        actual = b / a - 1
    target, tolerance = Decimal(spec["issuer_market_total_return"]), Decimal(spec["absolute_return_tolerance"])
    with localcontext(Context(prec=50)):
        difference = abs(actual - target)
    return {"status": "passed" if difference <= tolerance else "failed",
            "start": spec["xlf_start"], "end": spec["xlf_end"], "adjusted_close_start": str(a),
            "adjusted_close_end": str(b), "provider_total_return": str(actual),
            "issuer_market_total_return": str(target), "absolute_difference": str(difference), "decimal_precision": 50,
            "fixed_tolerance": str(tolerance), "financial_values_converted": 2,
            "qualification": "coarse_major_action_omission_check_only"}


def decisions(dates, prices, method):
    last = {}
    for i, d in enumerate(dates):
        last[d[:7]] = i
    result = []
    for month, index in last.items():
        if not method["initial_decision_month"] <= month <= method["last_decision_month"]:
            continue
        y, m = map(int, month.split("-"))
        if m not in method["decision_months"]:
            continue
        ordinal = y * 12 + m - 1 - method["formation_months"]
        lookback = f"{ordinal // 12:04d}-{ordinal % 12 + 1:02d}"
        start = last[lookback]
        ranking = sorted(ASSETS, key=lambda s: (-prices[s][index] / prices[s][start], s))
        require(index + 1 < len(dates), "next_close_required")
        result.append({"decision_date": dates[index], "formation_start": dates[start],
                       "execution_date": dates[index + 1], "execution_index": index + 1,
                       "selected": ranking[:method["top_count"]],
                       "scores": {s: float(prices[s][index] / prices[s][start] - 1) for s in ASSETS}})
    require(len(result) == 40, "fixed_forty_decisions")
    return result


def path_values(dates, prices, schedule, policy, fees):
    """Mark old index units, charge once, then change units at the next close."""
    events = {r["execution_index"]: r for r in schedule}
    start = schedule[0]["execution_index"]
    units, daily, charges = {}, [], []
    for i in range(start, len(dates)):
        wealth = math.fsum(units[s] * prices[s][i] for s in units) if units else 1.0
        if i in events:
            kind = "entry" if i == start else "rebalance"
            fee = fees[kind]
            charges.append({"date": dates[i], "kind": kind, "fraction": fee, "index_wealth_deducted": wealth * fee})
            wealth *= 1 - fee
            selected = ASSETS if policy == "equal9" else events[i]["selected"]
            units = {s: wealth / len(selected) / prices[s][i] for s in selected}
        if i == len(dates) - 1:
            fee = fees["exit"]
            charges.append({"date": dates[i], "kind": "exit", "fraction": fee, "index_wealth_deducted": wealth * fee})
            wealth *= 1 - fee
        require(math.isfinite(wealth) and wealth > 0, "positive_finite_index_wealth")
        daily.append({"date": dates[i], "wealth": wealth})
    prior, annual, peak, max_dd = 1.0, {}, 1.0, 0.0
    ends = {}
    for row in daily:
        ends[int(row["date"][:4])] = row["wealth"]
        peak = max(peak, row["wealth"])
        max_dd = max(max_dd, 1 - row["wealth"] / peak)
    for year, value in ends.items():
        annual[str(year)] = value / prior - 1
        prior = value
    years = (datetime.fromisoformat(dates[-1]) - datetime.fromisoformat(daily[0]["date"])).days / 365.25
    return {"terminal_wealth": daily[-1]["wealth"], "total_return": daily[-1]["wealth"] - 1,
            "annualized_return": daily[-1]["wealth"] ** (1 / years) - 1,
            "max_drawdown": max_dd, "annual_returns": annual, "daily": daily,
            "charges": charges, "account_count": 0, "tradable_share_units": False}


def bootstrap_lower(values, *, seed, length, replications):
    rng = random.Random(seed)
    n = len(values)
    require(n >= length and n % length == 0, "whole_bootstrap_blocks")
    estimates = []
    for _ in range(replications):
        draw = []
        for _ in range(n // length):
            start = rng.randrange(n)
            draw.extend(values[(start + j) % n] for j in range(length))
        estimates.append(math.fsum(draw) / n)
    estimates.sort()
    return estimates[math.floor(0.05 * (replications - 1))]


def screen(prepared, method, qa):
    require(qa["status"] == "passed", "source_qa_must_pass_before_full_decode")
    dates = prepared["dates"]
    decimal_prices = {s: [number(v) for v in prepared["opaque_adjusted_close"][s]] for s in ASSETS}
    prices = {s: [float(v) for v in decimal_prices[s]] for s in ASSETS}
    require(all(math.isfinite(v) and v > 0 for a in prices.values() for v in a), "float_domain")
    with localcontext(Context(prec=50)):
        schedule = decisions(dates, decimal_prices, method)
    zero = dict(entry=0.0, rebalance=0.0, exit=0.0)
    paths = {"top3_gross": path_values(dates, prices, schedule, "top3", zero),
             "equal9_gross": path_values(dates, prices, schedule, "equal9", zero)}
    for name in ("primary", "stress"):
        fees = {k: float(v) for k, v in method["fee_proxy"][name].items()}
        paths[f"top3_{name}_proxy"] = path_values(dates, prices, schedule, "top3", fees)
    stress, benchmark = paths["top3_stress_proxy"], paths["equal9_gross"]
    annual_relative = {str(y): math.log1p(stress["annual_returns"][str(y)])
                       - math.log1p(benchmark["annual_returns"][str(y)]) for y in range(2006, 2026)}
    segment_values = [math.fsum(annual_relative[str(y)] for y in range(a, b + 1))
                      for a, b in method["advancement_conditions"]["stress_vs_equal9_positive_log_relative_growth_in_both_segments"]]
    spec = method["advancement_conditions"]["paired_annual_log_relative_bootstrap_lower_bound_above_zero"]
    lower = bootstrap_lower(list(annual_relative.values()), seed=spec["seed"],
                            length=spec["block_length_years"], replications=spec["replications"])
    checks = {"stress_terminal_positive": stress["terminal_wealth"] > 1,
              "positive_relative_growth_both_decades": all(x > 0 for x in segment_values),
              "annual_relative_bootstrap_lower_positive": lower > 0}
    return {"schema": "us_sector_momentum_screen_result_v1", "evidence_kind": "known_history_provider_adjusted_total_return_proxy",
            "status": "screen_passed_requires_implementation_validation" if all(checks.values()) else "screen_rejected",
            "paths": paths, "decisions": schedule, "annual_log_relative_stress_vs_equal9": annual_relative,
            "segment_log_relative_stress_vs_equal9": segment_values, "bootstrap_lower_mean_annual_log_relative": lower,
            "checks": checks, "source_qa": qa, "source_actions": prepared["events"],
            "unique_adjusted_close_values_decoded": len(dates) * len(ASSETS),
            "qualified": False, "real_forward_days": 0, "account_count": 0,
            "limitations": method["fee_proxy"]["unmodelled"] + ["known history not blind", "provider adjusted series not complete action certification", "calendar not independently certified", "bootstrap not a probability of future profits", "no market-wide profitability inference"]}
