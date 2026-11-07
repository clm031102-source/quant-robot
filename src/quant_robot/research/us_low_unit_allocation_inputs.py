"""Pure, staged input adapter. The external caller owns numeric authorization.

Preparation never converts quote/dividend tokens to numbers. QA converts exactly
five closes; fixture construction is available once, only after that fixed QA.
No transport, filesystem reads, strategy import, or automatic source replacement.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Context, Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import hashlib
import json

from .us_monthly_rotation_inputs import _opaque, _day, _require, NUMBER, NY

OLD = ("SPY", "EFA", "IEF", "GLD")
NEW = ("SPYM", "EFA", "IEF", "GLDM")
SYMBOLS = OLD + ("SPYM", "GLDM")
ROLES = tuple(f"{s}_{part}" for s in OLD for part in ("legacy", "2025", "actions")) + tuple(
    f"{s}_{part}" for s in ("SPYM", "GLDM") for part in ("daily", "actions"))
FIELDS = ("open", "high", "low", "close", "volume")
START, FIRST, TERMINAL = "2020-12-01", "2020-12-31", "2025-12-31"
CAPTURE_END = "2026-11-08"
SPLIT_DATE = "2022-02-23"
CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
QA_KEYS = (("GLDM", "2022-02-22"), ("GLDM", "2022-02-23"),
           ("GLD", "2022-02-22"), ("GLD", "2022-02-23"), ("GLDM", "2022-09-19"))


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass
class _Prepared:
    _tokens: dict = field(repr=False)
    _dividends: tuple = field(repr=False)
    _metadata: dict = field(repr=False)
    _identity: str = field(repr=False)
    _qa_started: bool = field(default=False, repr=False)
    _qa: dict | None = field(default=None, repr=False)
    _cache: dict = field(default_factory=dict, repr=False)
    _built: bool = field(default=False, repr=False)

    def __repr__(self):
        return "<private prepared sources; quote tokens withheld>"


def _bound(prepared):
    _require(type(prepared) is _Prepared, "private_prepared_required")
    _require(_digest((prepared._tokens, prepared._dividends, prepared._metadata)) == prepared._identity,
             "prepared_input_changed")


def _row(raw, symbol, interval):
    obj = _opaque(raw)
    _require(type(obj) is dict and type(obj.get("chart")) is dict, "chart_object")
    chart = obj["chart"]
    _require(chart.get("error") is None and type(chart.get("result")) is list
             and len(chart["result"]) == 1, "chart_result")
    row = chart["result"][0]
    _require(type(row) is dict and type(row.get("meta")) is dict, "row_meta")
    meta = row["meta"]
    _require(meta.get("symbol") == symbol and meta.get("currency") == "USD"
             and meta.get("exchangeTimezoneName") == "America/New_York"
             and meta.get("instrumentType") == "ETF" and meta.get("dataGranularity") == interval,
             "source_identity_units_interval")
    events = row.get("events", {})
    _require(type(events) is dict and set(events) <= {"dividends", "splits", "capitalGains"}
             and all(type(v) is dict for v in events.values()), "event_schema")
    return row


def _splits(row, *, monthly):
    facts = []
    for key, event in row.get("events", {}).get("splits", {}).items():
        _require(type(event) is dict and {"date", "numerator", "denominator", "splitRatio"} <= set(event),
                 "split_schema")
        day, key_day = _day(event["date"]), _day(key)
        semantics = "exact_event_timestamp"
        if key != event["date"]:
            bucket = datetime.fromtimestamp(int(key), NY)
            _require(monthly and bucket.day == 1 and (bucket.hour, bucket.minute, bucket.second) == (0, 0, 0)
                     and key_day[:7] == day[:7] and type(row.get("timestamp")) is list
                     and row["timestamp"].count(key) == 1, "split_event_key")
            semantics = "NY_month_start_bucket"
        for name in ("numerator", "denominator"):
            _require(type(event[name]) is str and NUMBER.fullmatch(event[name]), "split_ratio_literal")
        numerator, denominator = Fraction(event["numerator"]), Fraction(event["denominator"])
        _require(numerator > 0 and denominator > 0, "positive_split_ratio")
        ratio = numerator / denominator
        label = event["splitRatio"]
        _require(type(label) is str and label.count(":") == 1, "split_ratio_label")
        left, right = label.split(":")
        _require(left.isdigit() and right.isdigit() and int(right) > 0
                 and Fraction(int(left), int(right)) == ratio, "split_ratio_label_match")
        facts.append(dict(date=day, ratio=f"{ratio.numerator}/{ratio.denominator}",
                          source_key=key, event_timestamp=event["date"], key_semantics=semantics))
    _require(len({f["date"] for f in facts}) == len(facts), "duplicate_split_day")
    return sorted(facts, key=lambda f: f["date"])


def _daily(row):
    timestamps = row.get("timestamp")
    _require(type(timestamps) is list, "daily_timestamps")
    dates = [_day(t) for t in timestamps]
    _require(dates and dates == sorted(set(dates)), "daily_dates_unique_order")
    quote = row.get("indicators", {}).get("quote")
    _require(type(quote) is list and len(quote) == 1 and type(quote[0]) is dict
             and set(quote[0]) == set(FIELDS), "daily_quote_fields")
    _require(all(type(v) is list and len(v) == len(dates) for v in quote[0].values()), "daily_quote_length")
    return dates, quote[0]


def prepare_sources(payloads):
    """Read supplied bytes as opaque JSON tokens; never read a path or decode prices."""
    _require(type(payloads) is dict and set(payloads) == set(ROLES), "exact_sixteen_roles")
    _require(all(type(raw) is bytes for raw in payloads.values()), "immutable_source_bytes")
    rows = {role: _row(raw, role.split("_")[0], "1mo" if role.endswith("_actions") else "1d")
            for role, raw in payloads.items()}
    tokens, dividends, actions, blockers, coverage = {}, [], {}, [], {}
    source_refs = {r: dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)) for r, raw in payloads.items()}
    for symbol in SYMBOLS:
        selected, daily_splits, seen_div = {}, [], set()
        parts = ("legacy", "2025") if symbol in OLD else ("daily",)
        for part in parts:
            role = f"{symbol}_{part}"
            row = rows[role]
            dates, quote = _daily(row)
            lo, hi = (START, "2024-12-31") if part == "legacy" else (
                ("2025-01-01", TERMINAL) if part == "2025" else (START, TERMINAL))
            _require(dates[-1] <= hi and (part == "legacy" or dates[0] >= lo), "daily_source_window")
            picked = [i for i, day in enumerate(dates) if lo <= day <= hi]
            _require(picked and dates[picked[-1]] == hi, "daily_segment_endpoint")
            coverage[role] = dict(first=dates[picked[0]], last=dates[picked[-1]], rows=len(picked))
            for i in picked:
                day = dates[i]
                _require(day not in selected, "overlapping_daily_segments")
                # Values remain strings/null; terminal non-open values are deliberately not inspected.
                selected[day] = tuple(quote[field][i] for field in FIELDS)
            facts = _splits(row, monthly=False)
            daily_splits.extend(f for f in facts if START <= f["date"] <= TERMINAL)
            for key, event in row.get("events", {}).get("dividends", {}).items():
                _require(type(event) is dict and {"date", "amount"} <= set(event)
                         and key == event["date"], "daily_dividend_schema")
                ex = _day(event["date"])
                if FIRST < ex <= TERMINAL:
                    _require(lo <= ex <= hi and ex in selected and ex not in seen_div, "dividend_date_duplicate")
                    seen_div.add(ex)
                    dividends.append((symbol, key, ex, event["amount"]))
            if row.get("events", {}).get("capitalGains"):
                blockers.append(dict(role=role, reason="capital_gains_unsupported"))
            if symbol == "GLDM" and row.get("events", {}).get("dividends"):
                blockers.append(dict(role=role, reason="GLDM_dividend_unit_rule_unknown"))
        tokens[symbol] = selected
        monthly = rows[f"{symbol}_actions"]
        facts = _splits(monthly, monthly=True)
        # Old pre-window actions (e.g. EFA2005) do not affect the selected units.
        relevant = [f for f in facts if f["date"] >= START]
        _require(all(f["date"] < CAPTURE_END for f in relevant), "action_after_capture_boundary")
        signature = lambda ff: sorted((f["date"], f["ratio"]) for f in ff)
        expected = [(SPLIT_DATE, "1/2")] if symbol == "GLDM" else []
        if signature(relevant) != expected:
            blockers.append(dict(role=f"{symbol}_actions", reason="unexpected_split_chain",
                                 observed=[dict(date=d, ratio=r) for d, r in signature(relevant)]))
        if signature(daily_splits) != signature(f for f in relevant if f["date"] <= TERMINAL):
            blockers.append(dict(role=symbol, reason="daily_monthly_split_mismatch"))
        if monthly.get("events", {}).get("capitalGains"):
            blockers.append(dict(role=f"{symbol}_actions", reason="capital_gains_unsupported"))
        if symbol == "GLDM" and monthly.get("events", {}).get("dividends"):
            blockers.append(dict(role=f"{symbol}_actions", reason="GLDM_dividend_unit_rule_unknown"))
        actions[symbol] = dict(daily_selected=daily_splits, monthly_split_metadata=facts,
                               monthly_quote_values_converted=False)
    dates = list(tokens["SPY"])
    _require(all(list(tokens[s]) == dates for s in SYMBOLS), "six_date_sets_must_match_no_intersection")
    _require(dates[0] == START and dates[-1] == TERMINAL and FIRST in dates
             and dates.index(FIRST) >= 20 and dates.index(FIRST)+4 < len(dates)-1, "fixed_window_warmup")
    months = sorted({d[:7] for d in dates})
    _require(months == ["2020-12"] + [f"{y}-{m:02d}" for y in range(2021, 2026) for m in range(1, 13)],
             "complete_month_coverage")
    _require(all(day in tokens[symbol] for symbol, day in QA_KEYS), "fixed_QA_dates_present")
    metadata = dict(schema="us_low_unit_source_metadata_v1", symbols=list(SYMBOLS), dates=dates,
        first_decision_date=FIRST, first_sell_date=dates[dates.index(FIRST)+1],
        first_buy_date=dates[dates.index(FIRST)+4], terminal_date=TERMINAL,
        source_refs=source_refs, selected_coverage=coverage, split_metadata=actions,
        dividend_events=[dict(symbol=s, id=f"{s}:{key}", ex_date=ex) for s, key, ex, _ in dividends],
        blockers=blockers, numeric_decode_started=False)
    dividends = tuple(sorted(dividends, key=lambda v: (v[2], SYMBOLS.index(v[0]), v[1])))
    return _Prepared(tokens, dividends, metadata, _digest((tokens, dividends, metadata)))


def metadata_summary(prepared):
    """Copy of price-free structural metadata, including unsupported-action blockers."""
    _bound(prepared)
    answer = copy.deepcopy(prepared._metadata)
    answer["numeric_decode_started"] = prepared._qa_started
    answer["unit_QA_status"] = prepared._qa["status"] if prepared._qa else "not_run"
    return answer


def _number(token, *, volume=False):
    _require(type(token) is str and NUMBER.fullmatch(token), "numeric_token_required")
    value = Decimal(token)
    _require(value.is_finite() and (value >= 0 if volume else value > 0), "numeric_domain")
    return value


def _ratio(symbol, day):
    # Only reachable after the entire metadata chain matched the exact contract.
    return Decimal("0.5") if symbol == "GLDM" and day < SPLIT_DATE else Decimal(1)


def run_unit_qa(prepared):
    """Numeric operation: external durable marker MUST already exist; no retries."""
    _bound(prepared)
    _require(not prepared._metadata["blockers"], "unsupported_source_actions")
    _require(not prepared._qa_started, "QA_already_attempted")
    prepared._qa_started = True
    prepared._qa = {"status": "started_not_completed"}
    with localcontext(CONTEXT) as context:
        for symbol, day in QA_KEYS:
            raw = _number(prepared._tokens[symbol][day][3])
            prepared._cache[(symbol, day)] = (raw, raw*_ratio(symbol, day))
        close = lambda symbol, day: prepared._cache[(symbol, day)][1]
        gldm = Decimal("0.5")*close("GLDM", "2022-02-23")/close("GLDM", "2022-02-22")-1
        gld = close("GLD", "2022-02-23")/close("GLD", "2022-02-22")-1
        gap = abs(gldm-gld)
        anchor = close("GLDM", "2022-09-19")
        passed = gap <= Decimal("0.01") and abs(anchor-Decimal("33.26")) <= Decimal("0.02")
        prepared._qa = dict(status="passed" if passed else "failed", converted_close_count=5,
            restored_closes=[dict(symbol=s, date=d, close=str(close(s, d))) for s, d in QA_KEYS],
            GLDM_holder_return=str(gldm), GLD_return=str(gld), absolute_return_gap=str(gap),
            return_tolerance="0.01", anchor_reference="33.26", anchor_absolute_gap=str(abs(anchor-Decimal("33.26"))),
            anchor_tolerance="0.02", precision=50, flags={k.__name__: v for k, v in context.flags.items()})
    # Failed QA is saved by the caller and explicitly blocks build; it is not a source retry.
    return copy.deepcopy(prepared._qa)


def build_fixtures(prepared, provenance):
    """Numeric operation after passed QA; creates two pure fixtures, never accounts."""
    _bound(prepared)
    _require(prepared._qa is not None and prepared._qa["status"] == "passed", "passed_QA_required")
    _require(not prepared._built, "fixtures_already_attempted")
    _require(type(provenance) is dict and type(provenance.get("constructed_from_market_data")) is bool,
             "explicit_provenance_identity")
    prepared._built = True
    dates = prepared._metadata["dates"]
    values = {}
    with localcontext(CONTEXT) as context:
        for day in dates:
            terminal = day == TERMINAL
            values[day] = {}
            for symbol in SYMBOLS:
                tokens = prepared._tokens[symbol][day]
                ratio = _ratio(symbol, day)
                prices = {f: None for f in FIELDS}
                for index, name in enumerate(FIELDS):
                    if terminal and name != "open":
                        continue
                    if name == "close" and (symbol, day) in prepared._cache:
                        prices[name] = prepared._cache[(symbol, day)][1]
                    else:
                        number = _number(tokens[index], volume=name == "volume")
                        prices[name] = number if name == "volume" else number*ratio
                if not terminal:
                    _require(prices["low"] <= min(prices["open"], prices["close"])
                             <= max(prices["open"], prices["close"]) <= prices["high"], "restored_OHLC_rectangle")
                capacity = None if terminal else min(prices["volume"], prices["volume"]/ratio)
                values[day][symbol] = (dict((k, str(v) if v is not None else None) for k, v in prices.items()),
                                       str(capacity) if capacity is not None else None)
        dividends = [dict(id=f"{s}:{key}", symbol=s, ex_date=ex, amount_per_share=str(_number(amount, volume=True)))
                     for s, key, ex, amount in prepared._dividends]
        flags = {k.__name__: v for k, v in context.flags.items()}
    prov = copy.deepcopy(provenance)
    prov.update(source_identities=copy.deepcopy(prepared._metadata["source_refs"]),
        unit_QA=copy.deepcopy(prepared._qa), normalization_decimal_precision=50, normalization_decimal_flags=flags,
        historical_OHL_unit_convention="conditional_same_split_adjustment_as_close",
        capacity_volume_convention="min(original_V,V/subsequent_split_ratio)",
        original_volume_is_not_authenticated_as_traded=True,
        dividend_units="unchanged_only_for_assets_without_relevant_split; GLDM_dividends_rejected",
        same_six_provider_date_sets=True, independent_exchange_calendar_certified=False,
        historical_first_publication_verified=False, actions_quote_values_converted=False,
        adjusted_close_values_converted=False, current_quote_metadata_converted=False,
        terminal_non_open_values_converted=False, old_pre_December2020_values_converted=False,
        account_window_dividend_amounts_only=True)
    result = {}
    for label, assets in (("old", OLD), ("new", NEW)):
        days = [dict(date=day, prices={s: copy.deepcopy(values[day][s][0]) for s in assets},
                     capacity_volume={s: values[day][s][1] for s in assets},
                     execution={s: dict(suspended=None, buy_blocked=None, sell_blocked=None) for s in assets},
                     terminal_open_only=day == TERMINAL) for day in dates]
        result[label] = dict(schema="us_low_unit_allocation_fixture_v1", currency="USD", assets=list(assets),
            evidence_kind="known_history_conditional" if prov["constructed_from_market_data"] else "artificial_values_true_calendar",
            provenance=copy.deepcopy(prov), days=days, first_decision_date=FIRST, terminal_date=TERMINAL,
            dividends=[copy.deepcopy(d) for d in dividends if d["symbol"] in assets],
            splits=[dict(id="GLDM:2022-02-23:1:2", symbol="GLDM", effective_date=SPLIT_DATE,
                         numerator=1, denominator=2)] if label == "new" else [])
    return result
