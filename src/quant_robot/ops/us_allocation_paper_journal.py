"""Incremental USD allocation journal, currently restricted to invented sessions.

No quote acquisition, qualification, activation of real-time accounts or orders.
The frozen historical kernel supplies accounting; this adapter never calls run().
Restart replays immutable input events rather than accepting editable balances.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from quant_robot.research import us_monthly_rotation as kernel


SCHEMA = "us_allocation_artificial_paper_journal_v1"
ASSETS = kernel.ASSETS


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _instant(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _check(result.tzinfo is not None and result.utcoffset() == timedelta(0), "UTC timestamp required")
    return result


def _number(value, *, positive=False):
    _check(type(value) is str, "Decimal strings required")
    result = Decimal(value)
    _check(result.is_finite() and (result > 0 if positive else result >= 0), "Invalid financial value")
    return result


def _bytes(value):
    return json.dumps(kernel.serial(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _require_artificial(value):
    _check(value.get("evidence_kind") == "artificial"
           and value.get("constructed_from_market_data") is False, "Only invented engineering inputs admitted")


def _runtime():
    return dict(adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                kernel_sha256=hashlib.sha256(Path(kernel.__file__).read_bytes()).hexdigest(),
                python=list(sys.version_info[:3]), decimal=kernel.context_record(kernel.CONTEXT))


class _Session:
    def __init__(self, manifest):
        _require_artificial(manifest)
        _check(manifest.get("schema") == SCHEMA and manifest.get("initial_cash") == "1000.00", "Exact USD paper identity required")
        _check(manifest.get("assets") == list(ASSETS), "Four fixed assets required")
        _check((manifest.get("minimum_commission"), manifest.get("slippage_bps")) in
               (("1.00", 10), ("2.50", 30)), "Two fixed cost identities required")
        self.manifest = copy.deepcopy(manifest)
        self.schedule = manifest["schedule"]
        dates = [row["date"] for row in self.schedule]
        _check(len(dates) >= 26 and dates == sorted(set(dates)), "Ordered complete calendar required")
        last_close = None
        for row in self.schedule:
            parsed = date.fromisoformat(row["date"])
            _check(2000 <= parsed.year <= 2004 and parsed.isoformat() == row["date"], "Invented 2000-2004 sessions only")
            opening, closing = _instant(row["open_at"]), _instant(row["close_at"])
            _check(opening.date() == parsed and closing.date() == parsed and opening < closing
                   and (last_close is None or last_close < opening), "Invalid session timestamps")
            last_close = closing
        warmup = manifest["warmup"]
        _check(len(warmup) >= 20 and len(warmup)+5 < len(dates)
               and [r["date"] for r in warmup] == dates[:len(warmup)], "Completed leading warmup required")
        bars = [None for _ in dates]
        for i, row in enumerate(warmup):
            _check(set(row["prices"]) == set(ASSETS), "All warmup assets required")
            bars[i] = {a: dict(close=_number(row["prices"][a]["close"], positive=True),
                               volume=_number(row["prices"][a]["volume"])) for a in ASSETS}
        self.normalized = dict(dates=dates, bars=bars, execution=[None for _ in dates],
                               dividends=[], signals={}, first=len(warmup)-1, terminal=len(dates))
        self.account = kernel._Account(SimpleNamespace(normalized=self.normalized), "fixed_quarters",
                                      manifest["minimum_commission"], manifest["slippage_bps"])
        self.phase = "closed"
        self.last_received = _instant(manifest["activated_at"])
        _check(_instant(self.schedule[len(warmup)-1]["close_at"]) <= self.last_received
               < _instant(self.schedule[len(warmup)]["open_at"]), "Activation must precede next session")
        self.current_day = None

    def apply(self, event):
        _require_artificial(event)
        _check(event.get("kind") in ("open", "close"), "Unknown event phase")
        a = self.account
        opening = event["kind"] == "open"
        _check(self.phase == ("closed" if opening else "open"), "One open then one close required")
        i = a.i+1 if opening else a.i
        _check(i < len(self.schedule) and event["date"] == self.schedule[i]["date"], "Next exact session required; no backfill")
        scheduled = _instant(self.schedule[i]["open_at" if opening else "close_at"])
        known, received = _instant(event["known_at"]), _instant(event["received_at"])
        delay = timedelta(minutes=5 if opening else 30)
        _check(_instant(event["effective_at"]) == scheduled
               and scheduled <= known <= received <= scheduled+delay and self.last_received < received,
               "Late, future-known or nonmonotonic packet")
        _check(set(event["prices"]) == set(ASSETS), "All four contemporaneous prices required")
        if opening:
            self._open(event, i, scheduled)
        else:
            self._close(event, i)
        self.last_received = received

    def _open(self, event, i, scheduled):
        a, p = self.account, self.normalized
        _check(not event.get("splits") and not event.get("capital_gains"), "Unsupported corporate action")
        flags = event["execution"]
        _check(set(flags) == set(ASSETS), "Explicit execution flags required")
        for f in flags.values():
            _check(set(f) == {"suspended", "buy_blocked", "sell_blocked"}
                   and all(type(v) is bool for v in f.values()), "Unknown execution status cannot produce paper fills")
        p["bars"][i] = {}
        for asset, values in event["prices"].items():
            _check(set(values) == {"open"}, "Open packet must not contain later prices or volume")
            p["bars"][i][asset] = dict(open=_number(values["open"], positive=True), close=None, volume=None)
        p["execution"][i] = copy.deepcopy(flags)
        ids = {d["id"] for d in p["dividends"]}
        for item in event.get("dividends", []):
            _check(type(item["id"]) is str and item["id"] not in ids and item["symbol"] in ASSETS
                   and item["ex_date"] == event["date"] and _instant(item["known_at"]) <= scheduled,
                   "Unique dividend known by ex-open required")
            ids.add(item["id"])
            p["dividends"].append(dict(id=item["id"], symbol=item["symbol"], ex_index=i,
                amount_per_share=_number(item["amount_per_share"]),
                earliest_payment_date=(date.fromisoformat(item["ex_date"])+timedelta(days=45)).isoformat()))
        a.i = i
        a.reference = a.previous
        self.current_day = dict(start=a.balances(), prior_q=dict(a.q),
                                prior_marks={s:p["bars"][i-1][s]["close"] for s in ASSETS},
                                first_fill=len(a.fills), first_obs=len(a.observations))
        a.day_active, a.triggered = bool(any(a.q.values())), False
        if a.paused and a.cooldown >= 5 and not any(a.q.values()):
            a.paused, a.cooldown = False, 0
            a.risks.append(dict(index=i, kind="resume_only_at_next_monthly_decision"))
        carried_risk = a.risk_due is not None and a.risk_due <= i
        self.current_day["entitled"] = a.opening_actions()
        a.observe(a.marks("open"), "prior_held_open")
        if carried_risk:
            if a.pending:
                a.pending["status"] = "cancelled_by_terminal_or_prior_risk"
            a.pending = None
            a.exit_orders("risk_exit")
            a.risk_due = i+1 if any(a.q.values()) else None
        elif a.pending:
            plan = a.pending
            if i == plan["sell_index"]:
                for order in plan["sell_orders"]:
                    a.fill(order)
            if i == plan["buy_index"]:
                for order in plan["buy_orders"]:
                    a.fill(order)
                if plan["status"] != "cancelled_increases_by_risk":
                    plan["status"] = "completed_monthly_attempt"
                a.pending = None
        if not any(a.q.values()) and a.risk_due is not None:
            a.risk_due = None
        for fill in a.fills[self.current_day["first_fill"]:]:
            fill["volume_observation_clock"] = "not_available_at_open"
        self.phase = "open"

    def _close(self, event, i):
        a, p, before = self.account, self.normalized, self.current_day
        for asset, values in event["prices"].items():
            _check(set(values) == {"close", "volume"}, "Completed close and volume only")
            p["bars"][i][asset].update(close=_number(values["close"], positive=True), volume=_number(values["volume"]))
        marks = a.marks("close")
        nav = a.observe(marks, "completed_close")
        no_increase = a.pending is None or not any(o["quantity"] for o in a.pending.get("buy_orders", []))
        if a.paused:
            a.cooldown = a.cooldown+1 if not a.day_active and not a.triggered and no_increase and not any(a.q.values()) else 0
        if a.pending and i == a.pending["plan_index"]:
            a.plan_buys(a.pending)
        fills = a.fills[before["first_fill"]:]
        attribution = dict(carried_exposure=sum((before["prior_q"][s]*(marks[s]-before["prior_marks"][s]) for s in ASSETS), kernel.ZERO),
            trade_timing=sum(((f["quantity"] if f["side"] == "buy" else -f["quantity"])*(marks[f["asset"]]-f["raw_open"]) for f in fills), kernel.ZERO),
            net_dividend_entitlement=before["entitled"], commissions=-sum((f["fee"] for f in fills), kernel.ZERO),
            sell_levies=-sum((f["sell_levy"] for f in fills), kernel.ZERO), slippage=-sum((f["slippage_cost"] for f in fills), kernel.ZERO))
        _check(sum(attribution.values(), kernel.ZERO) == nav-a.previous, "Daily reconciliation failed")
        a.days.append(dict(index=i, date=p["dates"][i], before=before["start"], after=a.balances(),
                           NAV=nav, PnL=nav-a.previous, peak=a.peak, observed_maxDD=a.max_dd,
                           paused=a.paused, cooldown=a.cooldown, attribution=attribution))
        year = p["dates"][i][:4]
        a.annual[year] = a.annual.get(year, kernel.ZERO)+nav-a.previous
        a.previous = nav
        if i+1 < len(p["dates"]) and p["dates"][i][:7] != p["dates"][i+1][:7]:
            p["signals"][i] = dict(index=i, date=p["dates"][i], model="fixed_calendar_quarters",
                weights={"fixed_quarters":dict.fromkeys(ASSETS, Decimal(".25"))},
                ordinary_execution_possible=i+4 < len(p["dates"]))
            a.decision(i)
        self.phase, self.current_day = "closed", None

    def snapshot(self):
        a = self.account
        return kernel.serial(dict(schema=SCHEMA, evidence_kind="artificial", qualified=False,
            real_forward_days=0, live_trading_allowed=False, phase=self.phase,
            last_received_at=self.last_received.isoformat(), date=self.schedule[a.i]["date"],
            balances=a.balances(), previous_NAV=a.previous, peak=a.peak, maxDD=a.max_dd,
            previous_DD=a.previous_dd, paused=a.paused, cooldown=a.cooldown, risk_due=a.risk_due,
            pending=a.pending, FIFO=a.lots, days=a.days, fills=a.fills, actions=a.actions,
            risks=a.risks, observations=a.observations, monthly_events=a.events,
            intents=a.intents, rejections=a.rejections, annual=a.annual,
            total_commission=a.total_fee, total_slippage=a.total_slip, total_sell_levy=a.total_levy))


def _publish(path, value):
    raw = _bytes(value)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    _check(path.read_bytes() == raw, "Published bytes not confirmed")


def _head(directory, manifest_sha, count, last_sha, *, initial=False):
    record = dict(manifest_sha256=manifest_sha, event_count=count, last_sha256=last_sha)
    if initial:
        _publish(directory/"head.json", record)
    else:
        _publish(directory/"head.next", record)
        os.replace(directory/"head.next", directory/"head.json")
        _check((directory/"head.json").read_bytes() == _bytes(record), "Committed head not confirmed")


def create(directory, manifest):
    with localcontext(kernel.CONTEXT):
        bound = dict(copy.deepcopy(manifest), runtime=_runtime())
        state = _Session(bound)
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=False)
        _publish(target/"manifest.json", bound)
        _head(target, _sha(bound), 0, _sha(bound), initial=True)
        return state.snapshot()


def _restore(directory):
    root = Path(directory)
    _check(not (root/"head.next").exists(), "Incomplete head publication requires review")
    manifest = json.loads((root/"manifest.json").read_bytes())
    _check(manifest.get("runtime") == _runtime(), "Frozen accounting code or environment changed")
    state = _Session(manifest)
    previous = _sha(manifest)
    head = json.loads((root/"head.json").read_bytes())
    files = sorted(root.glob("event_*.json"))
    _check(type(head.get("event_count")) is int and len(files) == head["event_count"]
           and head.get("manifest_sha256") == previous, "Committed journal tail missing or changed")
    for index, path in enumerate(files):
        _check(path.name == f"event_{index:06d}.json", "Missing or noncanonical event sequence")
        record = json.loads(path.read_bytes())
        expected = record.pop("sha256")
        _check(record["previous_sha256"] == previous and _sha(record) == expected, "Event chain changed")
        state.apply(record["event"])
        _check(_sha(state.snapshot()) == record["snapshot_sha256"], "Restored account diverged")
        previous = expected
    _check(head.get("last_sha256") == previous, "Committed tail hash differs")
    return state, previous, len(files)


def status(directory):
    with localcontext(kernel.CONTEXT):
        _check(not (Path(directory)/"writer.lock").exists(), "Unfinished writer requires review")
        state, _, count = _restore(directory)
        return dict(state.snapshot(), recorded_events=count)


def advance(directory, event):
    """Validate one new invented packet, append once, and confirm by fresh replay."""
    root = Path(directory)
    lock = root/"writer.lock"
    with lock.open("xb"):
        pass
    completed = False
    try:
        with localcontext(kernel.CONTEXT):
            state, previous, count = _restore(root)
            state.apply(event)
            snapshot = state.snapshot()
            record = dict(previous_sha256=previous, event=event, snapshot_sha256=_sha(snapshot))
            _publish(root/f"event_{count:06d}.json", dict(record, sha256=_sha(record)))
            _head(root, _sha(state.manifest), count+1, _sha(record))
            restored, _, restored_count = _restore(root)
            _check(restored_count == count+1 and _sha(restored.snapshot()) == _sha(snapshot), "Post-write confirmation failed")
            completed = True
            return dict(snapshot, recorded_events=count+1)
    finally:
        # Validation failure before publication has no state effect. Partial writes
        # keep the lock and visible broken file for explicit recovery inspection.
        if completed or not any(root.glob(f"event_{locals().get('count', -1):06d}.json")):
            lock.unlink()
