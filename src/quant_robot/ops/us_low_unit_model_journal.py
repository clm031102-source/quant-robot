"""Four-scenario, after-close journal; no network or trading IO.

Every day is one shared input and one atomic publication for four independent
USD1000 models. Historical account.run is never called. Public entries reject
market-derived inputs. Separate admitted entries bind a finite source authority.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D, localcontext
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from quant_robot.research import us_low_unit_allocation as core
from quant_robot.research import us_passive_drift_allocation as drift
from quant_robot.research import us_monthly_rotation as arithmetic
from quant_robot.ops import us_allocation_source_contract as source

ASSETS = core.NEW_ASSETS
SCENARIOS = ("monthly_primary", "monthly_stress", "drift_primary", "drift_stress")
SCHEMA = "us_low_unit_four_model_artificial_v1"
REAL_SCHEMA = "us_low_unit_four_model_admitted_state_v1"
REAL_EVIDENCE = "conditional_provider_observation"
PRODUCTION_DIRECTORY = Path("F:/lhjqr/data/reports/us_low_unit_models_20261109_20261207")
ZERO = D(0)
check = core._require


def _bytes(value):
    return (json.dumps(core.serial(value), ensure_ascii=False, sort_keys=True,
                       allow_nan=False, separators=(",", ":"))+"\n").encode()


def _sha(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _instant(value):
    check(type(value) is str, "explicit_injected_clock")
    stamp = datetime.fromisoformat(value)
    check(stamp.tzinfo is not None and stamp.utcoffset() == timedelta(0), "UTC_clock")
    return stamp


def _artificial(value):
    check(value.get("evidence_kind") == "artificial"
          and value.get("constructed_from_market_data") is False,
          "artificial_values_only_no_real_source_admission")


def _runtime():
    return dict(python=list(sys.version_info[:3]), files={
        m.__name__: hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
        for m in (sys.modules[__name__], core, drift, arithmetic, source)})


def _utcnow():
    return datetime.now(timezone.utc)


def _bound(reference):
    check(source._ref(reference), "exact_file_reference")
    path = Path(reference["path"])
    check(path.is_absolute(), "absolute_reference_path")
    raw = path.read_bytes()
    check(len(raw) == reference["bytes"] and hashlib.sha256(raw).hexdigest() == reference["sha256"],
          "bound_file_changed")
    return raw


def _reference(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def _fixed_dates():
    days = [date(2026, 10, 12)+timedelta(days=i) for i in range(58)]
    return [d.isoformat() for d in days if d.weekday() < 5 and d != date(2026, 11, 26)]


def _operation_manifest(manifest):
    dates = _fixed_dates()
    check(manifest["schema"] == "us_low_unit_four_model_manifest_v1"
          and manifest["evidence_kind"] == REAL_EVIDENCE and "warmup" not in manifest,
          "prospective_plan_without_warmup_values")
    check(Path(manifest["production_directory"]).resolve() == PRODUCTION_DIRECTORY.resolve(), "production_directory")
    check(manifest["assets"] == list(ASSETS) and manifest["scenarios"] == list(SCENARIOS)
          and manifest["currency"] == "USD" and manifest["initial_cash_each"] == "1000.00"
          and manifest["startup_mode"] == "once_after_complete_warmup", "fixed_real_scenarios")
    check(manifest["warmup_dates"] == dates[:20] and manifest["operation_dates"] == dates[20:40]
          and manifest["first_decision_date"] == "2026-11-30"
          and manifest["last_observation_date"] == "2026-12-07"
          and type(manifest["observation_sessions"]) is int and manifest["observation_sessions"] == 20
          and manifest["allowed_splits"] == [], "finite_real_window_and_startup")
    schedule = manifest["schedule"]
    check([s["date"] for s in schedule["sessions"]] == dates, "fixed_complete_calendar")
    for item in schedule["sessions"]:
        for field, local_time in (("open_at", "09:30:00"),
                                   ("close_at", "13:00:00" if item["date"] == "2026-11-27" else "16:00:00")):
            expected = datetime.fromisoformat(item["date"]+"T"+local_time).replace(tzinfo=source.NY)
            check(_instant(item[field]) == expected.astimezone(timezone.utc), "NYSE_frozen_calendar_clock")
    _bound(schedule["source_ref"])
    check(type(manifest["authorities"]) is dict and bool(manifest["authorities"]), "source_authorities")
    for authority in manifest["authorities"].values(): _bound(authority["definition_ref"])


@dataclass(frozen=True)
class _AdmittedContext:
    references: bytes
    manifest: bytes
    release: bytes


def admitted_context(manifest_ref, runtime_ref, release_ref, root_review_ref, manager_review_ref):
    """Validate exact operational authority; this never grants a source request."""
    refs = dict(manifest=manifest_ref, runtime=runtime_ref, release=release_ref,
                root_review=root_review_ref, manager_review=manager_review_ref)
    raw = {name: _bound(ref) for name, ref in refs.items()}
    values = {name: json.loads(value) for name, value in raw.items()}
    manifest, runtime, release = (values[k] for k in ("manifest", "runtime", "release"))
    _operation_manifest(manifest)
    check(runtime["schema"] == "us_low_unit_four_model_runtime_v1"
          and runtime["python"] == list(sys.version_info[:3]), "exact_runtime_environment")
    files = runtime["files"]
    check(type(files) is list and bool(files), "runtime_files")
    pins = {}
    for ref in files:
        _bound(ref); path = str(Path(ref["path"]).resolve())
        check(path not in pins, "unique_runtime_files"); pins[path] = ref["sha256"]
    for module in (sys.modules[__name__], core, drift, arithmetic, source):
        path = Path(module.__file__).resolve()
        check(pins.get(str(path)) == hashlib.sha256(path.read_bytes()).hexdigest(), "loaded_runtime_origin")
    for name, reviewer in (("root_review", "root"), ("manager_review", "quant_manager_72h")):
        review = values[name]
        check(review["status"] == "accepted" and review["stage"] == "operations"
              and review["reviewer"] == reviewer and review["manifest_sha256"] == manifest_ref["sha256"]
              and review["runtime_sha256"] == runtime_ref["sha256"], "exact_dual_operational_review")
    check(release["schema"] == "us_low_unit_four_model_release_v1" and release["status"] == "accepted"
          and release["manifest_sha256"] == manifest_ref["sha256"]
          and release["runtime_sha256"] == runtime_ref["sha256"]
          and release["root_review_sha256"] == root_review_ref["sha256"]
          and release["manager_review_sha256"] == manager_review_ref["sha256"]
          and Path(release["production_directory"]).resolve() == PRODUCTION_DIRECTORY.resolve(),
          "exact_operational_release")
    check(_instant(release["not_before"]) < _instant("2026-11-09T14:30:00+00:00")
          and _instant(release["expires_at"]) == _instant("2026-12-08T14:30:00+00:00"), "fixed_release_window")
    return _AdmittedContext(_bytes(refs), raw["manifest"], raw["release"])


def _context(context, directory, *, writing=False):
    check(type(context) is _AdmittedContext, "operational_admitted_context_required")
    refs = json.loads(context.references)
    current = admitted_context(*(refs[k] for k in ("manifest", "runtime", "release", "root_review", "manager_review")))
    check(current == context, "admitted_context_changed")
    check(Path(directory).resolve() == PRODUCTION_DIRECTORY.resolve()/"journal", "fixed_journal_directory")
    now = _utcnow()
    if writing:
        release = json.loads(context.release)
        check(_instant(release["not_before"]) <= now < _instant(release["expires_at"]), "operational_release_time")
    return json.loads(context.manifest), now


def _normalization(reference, context, purpose):
    """Consume a saved normalization, never reopen raw JSON or normalize twice."""
    normalized = json.loads(_bound(reference))
    refs = json.loads(context.references); manifest = json.loads(context.manifest)
    check(normalized["schema"] == "us_low_unit_source_normalized_packet_v1"
          and normalized["purpose"] == purpose and normalized["evidence_kind"] == REAL_EVIDENCE
          and normalized["assets"] == list(ASSETS) and normalized["qualified"] is False
          and normalized["real_forward"] == 0 and normalized["model_accounts_advanced"] == 0
          and normalized["journal_admission_granted"] is False, "normalized_identity")
    packet = normalized["source_metadata"]; identity = normalized["context_identity"]
    source_refs = {s:packet["records"][s]["source_ref"] for s in ASSETS}
    check(packet["purpose"] == purpose and identity["purpose"] == purpose
          and identity["evidence_kind"] == REAL_EVIDENCE and identity["test_values"] is False
          and identity["release_sha256"] == refs["release"]["sha256"]
          and identity["packet_sha256"] == source._digest(packet)
          and identity["source_refs_sha256"] == source._digest(source_refs)
          and normalized["source_refs"] == source_refs, "normalization_source_binding")
    assessment = source.assess_source_metadata(packet, manifest["schedule"],
                                              authorities=manifest["authorities"], assets=ASSETS)
    check(assessment["requirements_met"] and normalized["assessment"] == assessment, "source_metadata_not_admissible")
    marker = json.loads(_bound(normalized["numeric_decode_marker"]))
    check(marker["release_sha256"] == refs["release"]["sha256"]
          and marker["source_packet_sha256"] == source._digest(packet) and marker["purpose"] == purpose,
          "durable_numeric_marker_identity")
    for ref in source_refs.values(): _bound(ref)  # Raw bytes hash only, never JSON/price decoding.
    _bound(packet["source_ref"])
    check(normalized["splits"] == [] and normalized["capital_gains"] == []
          and normalized["capacity_basis"] == "nominal_provider_volume_no_split_in_query",
          "unsupported_future_action_or_capacity")
    for day in normalized["days"]:
        check(day["capacity_volume"] == {a:day["prices"][a]["volume"] for a in ASSETS}, "no_split_capacity_volume")
    return normalized


def _numeric_row(row, *, warmup=False):
    check(set(row["prices"]) == set(ASSETS)
          and set(row["capacity_volume"]) == set(ASSETS), "four_complete_asset_prices")
    prices, capacity = {}, {}
    for a in ASSETS:
        names = ("close", "volume") if warmup else ("open", "high", "low", "close", "volume")
        check(set(row["prices"][a]) == set(names), "exact_price_fields")
        prices[a] = {k: core._number(row["prices"][a][k], positive=k != "volume") for k in names}
        capacity[a] = core._number(row["capacity_volume"][a])
        check(capacity[a] <= prices[a]["volume"], "conservative_capacity_not_above_reported_volume")
        if not warmup:
            p = prices[a]
            check(p["low"] <= min(p["open"], p["close"]) <= max(p["open"], p["close"]) <= p["high"],
                  "OHLC_rectangle")
    return prices, capacity


def _manifest(manifest, *, decode_warmup=True, admitted=False):
    if admitted:
        check(manifest.get("evidence_kind") == REAL_EVIDENCE
              and manifest.get("constructed_from_market_data") is True, "real_evidence_identity")
    else:
        _artificial(manifest)
    check(manifest["schema"] == (REAL_SCHEMA if admitted else SCHEMA) and manifest["assets"] == list(ASSETS)
          and manifest["currency"] == "USD" and manifest["initial_cash_each"] == "1000.00",
          "four_independent_fixed_USD_accounts")
    check(manifest["scenarios"] == list(SCENARIOS), "fixed_four_scenarios")
    startup = manifest.get("startup_mode", "normal_month_end")
    check(startup in ("normal_month_end", "once_after_complete_warmup"), "fixed_startup_mode")
    schedule = manifest["schedule"]
    dates = [s["date"] for s in schedule]
    check(len(dates) >= 26 and dates == sorted(set(dates)), "complete_ordered_schedule")
    previous_close = None
    for s in schedule:
        day = date.fromisoformat(s["date"])
        check(day.isoformat() == s["date"] and (day.year == 2026 if admitted else 2000 <= day.year <= 2004),
              "admitted_or_artificial_dates_only")
        opening, closing = _instant(s["open_at"]), _instant(s["close_at"])
        check(opening.date() == day == closing.date() and opening < closing
              and (previous_close is None or previous_close < opening), "session_clock_order")
        previous_close = closing
    warmup = manifest["warmup"]
    check(len(warmup) == 20 and [r["date"] for r in warmup] == dates[:20], "twenty_completed_warmup_sessions")
    if decode_warmup:
        for row in warmup:
            _numeric_row(row, warmup=True)
    received, activated = _instant(manifest["warmup_received_at"]), _instant(manifest["activated_at"])
    check(_instant(schedule[19]["close_at"]) <= received <= activated < _instant(schedule[20]["open_at"]),
          "warmup_available_before_first_observation")
    first_decision = dates.index(manifest["first_decision_date"])
    end = dates.index(manifest["last_observation_date"])
    check(20 <= first_decision <= end < len(dates)-1 and first_decision+4 < len(dates)
          and dates[first_decision][:7] != dates[first_decision+1][:7], "normal_completed_month_end_entry")
    check(first_decision == next(i for i in range(20, len(dates)-1)
                                if dates[i][:7] != dates[i+1][:7]), "first_normal_month_end_not_shifted")
    if startup == "once_after_complete_warmup":
        check(first_decision >= 23, "startup_plan_overlaps_normal_month_end")
    check(type(manifest["observation_sessions"]) is int
          and manifest["observation_sessions"] == end-19, "fixed_observation_window")
    seen = set()
    for action in manifest["allowed_splits"]:
        check(type(action["id"]) is str and action["id"] not in seen
              and action["symbol"] == "GLDM" and action["effective_date"] in dates[20:end+1]
              and type(action["numerator"]) is int and action["numerator"] == 1
              and type(action["denominator"]) is int and action["denominator"] == 2,
              "declared_artificial_reverse_split_only")
        seen.add(action["id"])
    check(len(manifest["allowed_splits"]) <= 1, "one_declared_unit_transition")


class _State:
    def __init__(self, manifest, *, admitted=False):
        _manifest(manifest, admitted=admitted)
        self.manifest = deepcopy(manifest)
        self.dates = [s["date"] for s in manifest["schedule"]]
        self.index, self.observed, self.blocked, self.reason = 19, 0, False, None
        self.accounts = {}
        for name in SCENARIOS:
            policy, cost = name.split("_")
            p = dict(dates=self.dates, bars=[None for _ in self.dates],
                     capacity_volume=[None for _ in self.dates], execution=[None for _ in self.dates],
                     dividends=[], splits=[], signals={}, first=19, terminal=len(self.dates))
            for i, row in enumerate(manifest["warmup"]):
                p["bars"][i], p["capacity_volume"][i] = _numeric_row(row, warmup=True)
            prepared = SimpleNamespace(normalized=p, assets=ASSETS, role="new_"+cost)
            cls = drift._DriftAccount if policy == "drift" else core._Account
            self.accounts[name] = cls(prepared, "fixed_quarters", "2.50" if cost == "stress" else "1.00",
                                      30 if cost == "stress" else 10)
        self.last_received = _instant(manifest["warmup_received_at"])
        if manifest.get("startup_mode", "normal_month_end") == "once_after_complete_warmup":
            for account in self.accounts.values():
                account.p["signals"][19] = dict(index=19, date=self.dates[19],
                    weights={"fixed_quarters":dict.fromkeys(ASSETS, D(".25"))}, ordinary_execution_possible=True)
                account.decision(19)
                account.events[-1].update(decision_origin="unique_initial_configuration",
                    decision_recorded_at=manifest["activated_at"],
                    market_asof=manifest["schedule"][19]["close_at"],
                    source_received_at=manifest["warmup_received_at"], clock_kind=_clock_kind(manifest))

    def apply(self, event, recorded_at):
        check(not self.blocked, "blocked_requires_review_no_backfill")
        admitted = self.manifest["schema"] == REAL_SCHEMA
        if admitted:
            check(event.get("evidence_kind") == REAL_EVIDENCE
                  and event.get("constructed_from_market_data") is True, "real_daily_identity")
        else:
            _artificial(event)
        i = self.index+1
        check(self.observed < self.manifest["observation_sessions"], "observation_window_finished")
        check(event["schema"] == ("conditional_low_unit_completed_session_v1" if admitted
                                   else "artificial_low_unit_completed_session_v1")
              and event["date"] == self.dates[i], "next_complete_session_only")
        scheduled = self.manifest["schedule"][i]
        received, recorded = _instant(event["source_received_at"]), _instant(recorded_at)
        check(_instant(event["session_close_at"]) == _instant(scheduled["close_at"])
              and self.last_received < received
              and _instant(scheduled["close_at"])+timedelta(minutes=15) <= received <= recorded
              < _instant(self.manifest["schedule"][i+1]["open_at"]), "completed_daily_clock_no_backfill")
        check(event["action_snapshot_checked"] is True and not event["capital_gains"], "unknown_actions_block")
        expected = [a for a in self.manifest["allowed_splits"] if a["effective_date"] == event["date"]]
        check(event["splits"] == expected, "exact_declared_unit_action")
        prices, capacities = _numeric_row(event)
        check(set(event["execution"]) == set(ASSETS), "four_execution_records")
        for flags in event["execution"].values():
            check(set(flags) == {"suspended", "buy_blocked", "sell_blocked"}
                  and all(type(v) is bool or v is None for v in flags.values()), "explicit_execution_unknowns")
        dividends = []
        seen = {x["id"] for x in self.accounts[SCENARIOS[0]].p["dividends"]}
        for item in event["dividends"]:
            check(type(item["id"]) is str and item["id"] not in seen
                  and item["symbol"] in ("SPYM", "EFA", "IEF") and item["ex_date"] == event["date"],
                  "current_unique_supported_dividend")
            seen.add(item["id"])
            dividends.append(dict(id=item["id"], symbol=item["symbol"], ex_index=i,
                amount_per_share=core._number(item["amount_per_share"]),
                earliest_payment_date=(date.fromisoformat(item["ex_date"])+timedelta(days=45)).isoformat()))
        for account in self.accounts.values():
            p = account.p
            p["bars"][i], p["capacity_volume"][i] = deepcopy(prices), deepcopy(capacities)
            p["execution"][i] = deepcopy(event["execution"])
            p["dividends"].extend(deepcopy(dividends))
            p["splits"].extend(dict(id=x["id"], symbol=x["symbol"], index=i, ratio=D(".5")) for x in expected)
            _step(account, i, self.manifest, event, recorded_at)
        self.index, self.observed, self.last_received = i, self.observed+1, received

    def snapshot(self):
        admitted = self.manifest["schema"] == REAL_SCHEMA
        accounts = {}
        for name, a in self.accounts.items():
            policy, cost = name.split("_")
            accounts[name] = dict(scenario_id=name, strategy_id=drift.STRATEGY_ID if policy == "drift" else "us_low_unit_monthly_v1",
                holding_policy=drift.HOLDING_POLICY if policy == "drift" else "ordinary_monthly_fixed_quarters",
                entry_allocation_policy="fixed_quarters", role="new_"+cost, scenario_role=cost,
                minimum_commission=a.minimum, slippage_bps=a.slip, initial_cash="1000.00", currency="USD",
                ledger=dict(date=self.dates[a.i], balances=a.balances(), NAV=a.previous,
                    marked_model_PnL=a.previous-core.INITIAL, peak=a.peak, previous_DD=a.previous_dd,
                    maxDD=a.max_dd, paused=a.paused, cooldown=a.cooldown, risk_due=a.risk_due,
                    pending=a.pending, FIFO=a.lots, split_factors=a.split_factors, day_CIL=a.day_cil,
                    CIL_delay_days=a.cil_delay, total_CIL_cost=a.total_cil_cost,
                    total_commission=a.total_fee, total_slippage=a.total_slip, total_sell_levy=a.total_levy,
                    total_net_dividend=a.total_net_dividend, days=a.days, fills=a.fills,
                    actions=a.actions, risks=a.risks, observations=a.observations, monthly_events=a.events,
                    signals=list(a.p["signals"].values()), intents=a.intents, rejections=a.rejections,
                    unknown_execution_constraints=a.unknowns, annual=a.annual))
        status = ("blocked" if self.blocked else "window_finished_no_liquidation"
                  if self.observed == self.manifest["observation_sessions"] else
                  ("initialized_unique_entry_pending" if self.manifest.get("startup_mode") == "once_after_complete_warmup"
                   else "initialized_cash_waiting_normal_month_end") if not self.observed else
                  "conditional_model_observed" if admitted else "artificial_model_observed")
        return core.serial(dict(schema="us_low_unit_four_model_snapshot_v1",
            evidence_kind=REAL_EVIDENCE if admitted else "artificial",
            constructed_from_market_data=admitted, qualified=False, strict_forward_days=0,
            model_forward_days=self.observed if admitted else 0,
            artificial_model_days=0 if admitted else self.observed, status=status, reason=self.reason,
            startup_mode=self.manifest.get("startup_mode", "normal_month_end"),
            date=self.dates[self.index], assets=list(ASSETS), accounts=accounts,
            last_source_received_at=self.last_received.isoformat(),
            independent_scenarios_not_one_4000USD_portfolio=True,
            observation_window_end_action="stop_without_liquidation_or_terminal_profit",
            limitations=["Conditional after-close model; open-price risk cancellation is not executable auction evidence.",
                         ("Provider receipts are real; fills, fees, taxes and payment delays remain model assumptions."
                          if admitted else "All clocks and values are artificial; no real initialization or scheduler authority.")]))


def _clock_kind(manifest):
    return "actual_receipt_conditional_after_close" if manifest["schema"] == REAL_SCHEMA else "injected_artificial"


def _step(a, i, manifest, event, recorded_at):
    """One nonterminal session; reuse frozen wallet/risk/price/action methods."""
    a.i = i
    a.split_factors, a.day_cil = dict.fromkeys(ASSETS, D(1)), []
    a.reference = a.previous
    start, prior_q = a.balances(), dict(a.q)
    prior_marks = {s: a.p["bars"][i-1][s]["close"] for s in ASSETS}
    a.day_active, a.triggered = bool(any(a.q.values())), False
    if a.paused and a.cooldown >= 5 and not any(a.q.values()):
        a.paused, a.cooldown = False, 0
        a.risks.append(dict(index=i, kind="resume_only_at_next_monthly_decision"))
    carried_risk = a.risk_due is not None and a.risk_due <= i
    first_fill, first_action, first_obs = len(a.fills), len(a.actions), len(a.observations)
    entitled = a.opening_actions()
    a.observe(a.marks("open"), "prior_held_open")
    if carried_risk:
        if a.pending: a.pending["status"] = "cancelled_by_terminal_or_prior_risk"
        a.pending = None
        a.exit_orders("risk_exit")
        a.risk_due = i+1 if any(a.q.values()) else None
    elif a.pending:
        plan = a.pending
        if i == plan["sell_index"]:
            for order in plan["sell_orders"]: a.fill(order)
        if i == plan["buy_index"]:
            for order in plan["buy_orders"]: a.fill(order)
            if plan["status"] != "cancelled_increases_by_risk": plan["status"] = "completed_monthly_attempt"
            a.pending = None
    if not any(a.q.values()) and a.risk_due is not None: a.risk_due = None
    marks = a.marks("close")
    nav = a.observe(marks, "completed_close")
    no_increase = a.pending is None or not any(o["quantity"] for o in a.pending.get("buy_orders", []))
    if a.paused:
        a.cooldown = a.cooldown+1 if not a.day_active and not a.triggered and no_increase and not any(a.q.values()) else 0
    if a.pending and i == a.pending["plan_index"]: a.plan_buys(a.pending)
    fills = a.fills[first_fill:]
    attribution = dict(
        carried_exposure=sum((prior_q[s]*(a.split_factors[s]*marks[s]-prior_marks[s]) for s in ASSETS), ZERO),
        trade_timing=sum(((f["quantity"] if f["side"] == "buy" else -f["quantity"])*(marks[f["asset"]]-f["raw_open"]) for f in fills), ZERO),
        cash_in_lieu_timing=-sum((x["fractional_right"]*(marks[x["asset"]]-x["raw_open"]) for x in a.day_cil), ZERO),
        cash_in_lieu_cost=-sum((x["NAV_cost"] for x in a.day_cil), ZERO),
        net_dividend_entitlement=entitled, commissions=-sum((f["fee"] for f in fills), ZERO),
        sell_levies=-sum((f["sell_levy"] for f in fills), ZERO), slippage=-sum((f["slippage_cost"] for f in fills), ZERO))
    check(sum(attribution.values(), ZERO) == nav-a.previous, "daily_NAV_attribution_identity")
    a.annual[a.p["dates"][i][:4]] = a.annual.get(a.p["dates"][i][:4], ZERO)+nav-a.previous
    for fill in fills:
        fill.update(model_only=True, execution_certified=False, source_received_at=event["source_received_at"],
                    modeled_open_at=manifest["schedule"][i]["open_at"], clock_kind=_clock_kind(manifest))
    for action in a.actions[first_action:]:
        action.update(model_only=True, source_received_at=event["source_received_at"], clock_kind=_clock_kind(manifest))
    a.days.append(dict(index=i, date=a.p["dates"][i], terminal_open_only=False, before=start, after=a.balances(),
        previous_marks=prior_marks, marks=marks, previous_NAV=a.previous, NAV=nav, PnL=nav-a.previous,
        split_factors=dict(a.split_factors), peak=a.peak, observed_maxDD=a.max_dd, paused=a.paused,
        cooldown=a.cooldown, risk_exit_due_index=a.risk_due, observation_range=[first_obs, len(a.observations)],
        attribution=attribution, source_received_at=event["source_received_at"], recorded_at=recorded_at,
        model_only=True, execution_certified=False, clock_kind=_clock_kind(manifest)))
    a.previous = nav
    dates = a.p["dates"]
    if dates[i] >= manifest["first_decision_date"] and dates[i][:7] != dates[i+1][:7]:
        a.p["signals"][i] = dict(index=i, date=dates[i], weights={"fixed_quarters":dict.fromkeys(ASSETS, D(".25"))},
                                 ordinary_execution_possible=i+4 < len(dates))
        a.decision(i)


_ACCOUNT_FIELDS = frozenset((
    "p assets role cil_delay total_cil_cost split_factors day_cil policy minimum slip cash q locks receivables "
    "peak reference previous previous_dd max_dd paused cooldown risk_due days fills intents rejections risks "
    "actions events observations unknowns annual lots total_fee total_levy total_slip total_net_dividend "
    "i day_active triggered").split())


def _encode(value):
    """Only JSON primitives and explicitly tagged Decimal/map/tuple values."""
    if isinstance(value, D):
        check(value.is_finite(), "finite_state_decimal")
        return {"decimal": str(value)}
    if type(value) is dict:
        check(all(type(k) in (str, int) for k in value), "state_key_types")
        return {"map": [[k, _encode(v)] for k, v in value.items()]}
    if type(value) is tuple:
        return {"tuple": [_encode(v) for v in value]}
    if type(value) is list:
        return [_encode(v) for v in value]
    check(value is None or type(value) in (str, bool, int), "state_value_types")
    return value


def _decode(value):
    if type(value) is dict:
        if set(value) == {"decimal"}:
            check(type(value["decimal"]) is str, "state_decimal_string")
            result = D(value["decimal"]); check(result.is_finite(), "finite_state_decimal")
            return result
        if set(value) == {"tuple"}:
            check(type(value["tuple"]) is list, "state_tuple_items")
            return tuple(_decode(v) for v in value["tuple"])
        check(set(value) == {"map"} and type(value["map"]) is list, "state_codec_tag")
        result = {}
        for pair in value["map"]:
            check(type(pair) is list and len(pair) == 2 and type(pair[0]) in (str, int)
                  and pair[0] not in result, "unique_state_map_keys")
            result[pair[0]] = _decode(pair[1])
        return result
    if type(value) is list:
        return [_decode(v) for v in value]
    check(value is None or type(value) in (str, int, bool), "state_codec_primitive")
    return value


def _pack_state(state):
    accounts = {}
    for name, account in state.accounts.items():
        check(set(vars(account)) == _ACCOUNT_FIELDS | {"pending"}, "explicit_account_state_fields")
        pending = account.pending
        if pending is not None:
            check(any(pending is e for e in account.events), "pending_event_alias")
        accounts[name] = dict(values=_encode({k:v for k,v in vars(account).items() if k != "pending"}),
                              pending_decision_index=None if pending is None else pending["decision_index"])
    return dict(codec="low_unit_four_state_v1", index=state.index, observed=state.observed,
                blocked=state.blocked, reason=state.reason,
                last_received=state.last_received.isoformat(), accounts=accounts)


def _unpack_state(manifest, saved, *, admitted=False):
    _manifest(manifest, decode_warmup=False, admitted=admitted)
    check(saved["codec"] == "low_unit_four_state_v1" and set(saved["accounts"]) == set(SCENARIOS), "fixed_state_codec")
    state = _State.__new__(_State)  # Fixed class, never a class name from JSON.
    state.manifest, state.dates = deepcopy(manifest), [s["date"] for s in manifest["schedule"]]
    state.index, state.observed = saved["index"], saved["observed"]
    state.blocked, state.reason = saved["blocked"], saved["reason"]
    check(type(state.index) is int and type(state.observed) is int and type(state.blocked) is bool
          and state.index == 19+state.observed and 0 <= state.observed <= manifest["observation_sessions"], "state_progress")
    check((state.blocked and state.reason == "invalid_or_unknown_completed_day")
          or (not state.blocked and state.reason is None), "state_block_reason")
    state.last_received, state.accounts = _instant(saved["last_received"]), {}
    for name in SCENARIOS:
        policy, cost = name.split("_")
        item = saved["accounts"][name]; values = _decode(item["values"])
        check(type(values) is dict and set(values) == _ACCOUNT_FIELDS, "restored_account_fields")
        check(values["assets"] == ASSETS and values["role"] == "new_"+cost
              and values["policy"] == "fixed_quarters"
              and (values["minimum"], values["slip"], values["cil_delay"]) ==
              (("2.50", 30, 90) if cost == "stress" else ("1.00", 10, 45)), "restored_scenario_identity")
        check(values["i"] == state.index and values["p"]["dates"] == state.dates
              and values["p"]["first"] == 19 and values["p"]["terminal"] == len(state.dates)
              and len(values["days"]) == state.observed, "restored_common_date")
        cls = drift._DriftAccount if policy == "drift" else core._Account
        account = cls.__new__(cls)
        for key, value in values.items(): setattr(account, key, value)
        pending_index = item["pending_decision_index"]
        matches = [e for e in account.events if e["decision_index"] == pending_index]
        check(pending_index is None or type(pending_index) is int and len(matches) == 1, "pending_event_identity")
        account.pending = None if pending_index is None else matches[0]
        state.accounts[name] = account
    return state


def _save(path, value):
    data = _bytes(value)
    with path.open("xb") as handle:
        handle.write(data); handle.flush(); os.fsync(handle.fileno())
    check(path.read_bytes() == data, "published_bytes_changed")
    return hashlib.sha256(data).hexdigest()


def _head(root, head):
    _save(root/"head.next", head)
    os.replace(root/"head.next", root/"head.json")
    check((root/"head.json").read_bytes() == _bytes(head), "head_publication_changed")


def _restore(root, *, context=None):
    check(not (root/"head.next").exists(), "incomplete_head_requires_review")
    definition = json.loads((root/"definition.json").read_bytes())
    check(definition["runtime"] == _runtime(), "runtime_changed")
    if context is not None:
        check(definition.get("admission") == json.loads(context.references), "stored_admission_changed")
        _bound(definition["normalization_ref"])
    else:
        check("admission" not in definition, "admitted_status_required")
    head = json.loads((root/"head.json").read_bytes())
    check(head["definition_sha256"] == _sha(definition), "definition_changed")
    count = head["count"]
    check(type(count) is int and count >= 0
          and len(list(root.glob("record_*.json"))) == count, "journal_tail_requires_review")
    prior_hash, prior_clock = None, definition.get("committed_at", definition["manifest"]["activated_at"])
    last_state = definition["initial_state"]
    for n in range(1, count+1):
        raw = (root/f"record_{n:06d}.json").read_bytes(); record = json.loads(raw)
        check(record["index"] == n and record["previous_record_sha256"] == prior_hash
              and _instant(record["recorded_at"]) > _instant(prior_clock), "record_chain_or_clock_changed")
        check(record["state_sha256"] == _sha(record["state"]), "saved_state_changed")
        last_state = record["state"]
        prior_hash, prior_clock = hashlib.sha256(raw).hexdigest(), record["recorded_at"]
    state = _unpack_state(definition["manifest"], last_state, admitted=context is not None)
    check(head["last_record_sha256"] == prior_hash and head["recorded_at"] == prior_clock
          and head["snapshot_sha256"] == _sha(state.snapshot()), "head_state_changed")
    return state, head


def create(directory, manifest):
    """Create four artificial scenarios with the declared single startup policy."""
    with localcontext(core.CONTEXT):
        state = _State(manifest)
        root = Path(directory).resolve(); root.mkdir(parents=True, exist_ok=False)
        definition = dict(manifest=deepcopy(manifest), runtime=_runtime(), initial_state=_pack_state(state))
        _save(root/"definition.json", definition)
        _head(root, dict(count=0, definition_sha256=_sha(definition), last_record_sha256=None,
                         snapshot_sha256=_sha(state.snapshot()), recorded_at=manifest["activated_at"]))
        return state.snapshot()


def status(directory):
    """Verify the hash chain and decode the latest state; never replay strategy."""
    with localcontext(core.CONTEXT):
        root = Path(directory).resolve()
        check(not (root/"writer.lock").exists(), "unfinished_writer_requires_review")
        return _restore(root)[0].snapshot()


def append(directory, event, *, recorded_at):
    """Stage all four states, then publish one day or a shared blocked record."""
    _artificial(event)
    return _append(directory, event, recorded_at=recorded_at)


def _append(directory, event, *, recorded_at, context=None):
    root = Path(directory).resolve(); lock = root/"writer.lock"
    with lock.open("xb"): pass
    published = False; completed = False
    try:
        with localcontext(core.CONTEXT):
            state, head = _restore(root, context=context)
            if context is not None:
                check(event["previous_committed_ref"] == _admitted_snapshot(root, state, head)["committed_ref"],
                      "prior_head_changed")
            check(not state.blocked, "blocked_requires_review_no_backfill")
            check(state.observed < state.manifest["observation_sessions"], "observation_window_finished")
            check(_instant(recorded_at) > _instant(head["recorded_at"]), "monotonic_record_clock")
            candidate, failure = deepcopy(state), None
            try:
                candidate.apply(deepcopy(event), recorded_at)
            except (ValueError, KeyError, TypeError, ArithmeticError):
                candidate, failure = deepcopy(state), "invalid_or_unknown_completed_day"
                candidate.blocked, candidate.reason = True, failure
            if context is not None:
                _, committed = _context(context, directory, writing=True)
                check(_instant(recorded_at) <= committed
                      < _instant(state.manifest["schedule"][state.index+2]["open_at"]), "commit_before_next_open")
                recorded_at = committed.isoformat()
                _bound(event["normalization_ref"])
                if failure is None:
                    for account in candidate.accounts.values():
                        account.days[-1]["recorded_at"] = recorded_at
                        if account.events and account.events[-1]["decision_index"] == candidate.index:
                            account.events[-1].update(decision_origin="normal_month_end",
                                decision_recorded_at=recorded_at,
                                market_asof=event["session_close_at"], source_received_at=event["source_received_at"],
                                clock_kind=_clock_kind(candidate.manifest))
            count = head["count"]+1
            packed = _pack_state(candidate)
            record = dict(index=count, previous_record_sha256=head["last_record_sha256"],
                event=deepcopy(event), recorded_at=recorded_at, failure_code=failure,
                state=packed, state_sha256=_sha(packed), snapshot_sha256=_sha(candidate.snapshot()))
            # From here any interrupted write leaves the lock for explicit review.
            published = True
            digest = _save(root/f"record_{count:06d}.json", record)
            _head(root, dict(count=count, definition_sha256=head["definition_sha256"],
                last_record_sha256=digest, snapshot_sha256=record["snapshot_sha256"], recorded_at=recorded_at))
            restored, _ = _restore(root, context=context)
            check(_sha(restored.snapshot()) == record["snapshot_sha256"], "committed_state_differs")
            completed = True
            return restored.snapshot()
    finally:
        if completed or not published: lock.unlink()


def _admitted_snapshot(root, state, head):
    result = state.snapshot()
    name = "definition.json" if head["count"] == 0 else f"record_{head['count']:06d}.json"
    reference = _reference(root/name)
    check(reference["sha256"] == (head["definition_sha256"] if head["count"] == 0
                                  else head["last_record_sha256"]), "committed_reference_changed")
    result.update(committed_ref=reference, committed_at=head["recorded_at"])
    return result


def create_admitted(directory, normalized_ref, *, context):
    """Create only the released four-scenario model from its saved warmup."""
    manifest, _ = _context(context, directory, writing=True)
    normalized = _normalization(normalized_ref, context, "warmup")
    packet = normalized["source_metadata"]
    check(packet["session_date"] == "2026-11-09" and packet["warmup_dates"] == manifest["warmup_dates"]
          and [d["date"] for d in normalized["days"]] == manifest["warmup_dates"]
          and normalized["dividends"] == [], "exact_startup_warmup")
    _, activated = _context(context, directory, writing=True)
    check(_instant(packet["received_at"]) <= activated < _instant("2026-11-09T14:30:00+00:00"),
          "startup_before_first_open")
    internal = {k:deepcopy(manifest[k]) for k in ("assets", "scenarios", "currency", "initial_cash_each",
        "startup_mode", "first_decision_date", "last_observation_date", "observation_sessions", "allowed_splits")}
    internal.update(schema=REAL_SCHEMA, evidence_kind=REAL_EVIDENCE, constructed_from_market_data=True,
        schedule=deepcopy(manifest["schedule"]["sessions"]), warmup=deepcopy(normalized["days"]),
        warmup_received_at=packet["received_at"], activated_at=activated.isoformat())
    with localcontext(core.CONTEXT):
        state = _State(internal, admitted=True)
        _, committed = _context(context, directory, writing=True)
        check(activated <= committed < _instant("2026-11-09T14:30:00+00:00"), "startup_commit_before_first_open")
        root = Path(directory).resolve(); root.mkdir(parents=True, exist_ok=False)
        definition = dict(manifest=internal, runtime=_runtime(), initial_state=_pack_state(state),
                          admission=json.loads(context.references), normalization_ref=deepcopy(normalized_ref),
                          committed_at=committed.isoformat())
        _bound(normalized_ref)
        _save(root/"definition.json", definition)
        head = dict(count=0, definition_sha256=_sha(definition), last_record_sha256=None,
                    snapshot_sha256=_sha(state.snapshot()), recorded_at=committed.isoformat())
        _head(root, head)
        return _admitted_snapshot(root, state, head)


def status_admitted(directory, *, context):
    """Read the latest state after expiry too; no new day or old decisions run."""
    _context(context, directory)
    with localcontext(core.CONTEXT):
        root = Path(directory).resolve()
        check(not (root/"writer.lock").exists(), "unfinished_writer_requires_review")
        state, head = _restore(root, context=context)
        return _admitted_snapshot(root, state, head)


def append_normalized(directory, normalized_ref, *, context):
    """Append the next saved source snapshot once with internal production clocks."""
    manifest, _ = _context(context, directory, writing=True)
    before = status_admitted(directory, context=context)
    check(before["model_forward_days"] < 20, "observation_window_finished")
    normalized = _normalization(normalized_ref, context, "daily_model")
    packet = normalized["source_metadata"]
    check(packet["previous_observed_session_date"] == before["date"]
          and packet["previous_committed_decision_ref"] == before["committed_ref"]
          and _instant(packet["previous_committed_decision_at"]) == _instant(before["committed_at"]),
          "actual_prior_committed_state")
    target = manifest["operation_dates"][before["model_forward_days"]]
    check(packet["session_date"] == target and len(normalized["days"]) == 1
          and normalized["days"][0]["date"] == target, "next_real_completed_session")
    schedule = {r["date"]:r for r in manifest["schedule"]["sessions"]}
    _, recorded = _context(context, directory, writing=True)
    event = dict(schema="conditional_low_unit_completed_session_v1", evidence_kind=REAL_EVIDENCE,
        constructed_from_market_data=True, date=target, session_close_at=schedule[target]["close_at"],
        source_received_at=packet["received_at"], prices=deepcopy(normalized["days"][0]["prices"]),
        capacity_volume=deepcopy(normalized["days"][0]["capacity_volume"]),
        execution={a:deepcopy(packet["records"][a]["execution"]) for a in ASSETS},
        action_snapshot_checked=True, splits=[], capital_gains=[], dividends=deepcopy(normalized["dividends"]),
        normalization_ref=deepcopy(normalized_ref), previous_committed_ref=deepcopy(before["committed_ref"]))
    _bound(normalized_ref)
    _append(directory, event, recorded_at=recorded.isoformat(), context=context)
    return status_admitted(directory, context=context)
