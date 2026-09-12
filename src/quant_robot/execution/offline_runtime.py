"""Single-owner synthetic execution supervision; no broker or network transport."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, time, timezone
import hashlib
import json
import math
from pathlib import Path
import time as system_time

from .offline_intent_contract import SHANGHAI, day, exact, instant, version
from .offline_journal import OfflineOrderJournal
from .offline_order_state import identity
from .offline_runtime_lease import RuntimeLease


def _observation(value, now):
    if value is None:
        return {"schema_version": 1, "mode": "offline_fixture_only", "snapshot_id": "runtime-missing-feed",
            "source_ref": "runtime-clock-without-price-observation", "as_of": now.isoformat(),
            "session_date": now.astimezone(SHANGHAI).date().isoformat(), "quotes": {}}, "missing"
    required = {"schema_version", "mode", "snapshot_id", "source_ref", "as_of", "session_date", "quotes"}
    optional = {"receipts", "intents", "cancel_requests", "opening"}
    if not isinstance(value, dict) or not required.issubset(value) or set(value) - required - optional:
        raise ValueError("invalid runtime observation fields")
    version(value)
    if value["mode"] != "offline_fixture_only" or not isinstance(value["quotes"], dict):
        raise ValueError("only explicit synthetic quote observations are supported")
    result = deepcopy(value)
    for key in ("snapshot_id", "source_ref"):
        result[key] = identity(value[key])
    result["as_of"] = instant(value["as_of"]).isoformat()
    result["session_date"] = day(value["session_date"]).isoformat()
    for key in ("receipts", "intents", "cancel_requests"):
        if key in value and not isinstance(value[key], list):
            raise ValueError("runtime command groups must be lists")
    if "opening" in value:
        exact(value["opening"], {"instruments", "sellable_positions"}, "runtime opening")
    return result, "present"


class OfflineRuntime:
    def __init__(self, journal_path, *, clock=None):
        path = Path(journal_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.lease, self.book, self.last_tick = RuntimeLease(path), None, None
        try:
            self.rules = OfflineOrderJournal.inspect_configuration(path)
            if not self.rules["admission_policy"] or not self.rules["timeout_policy"]:
                raise ValueError("runtime requires frozen guarded admission and timeout policies")
            self.book = OfflineOrderJournal(path)
        except BaseException:
            self.close()
            raise

    def close(self):
        try:
            if self.book is not None:
                self.book.close()
                self.book = None
        finally:
            self.lease.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def _call(self, name, method, *, retry_anchor=False):
        for attempt in range(2 if retry_anchor else 1):
            try:
                changed = method()
                self.steps.append({"stage": name, "status": "ok", "changed": bool(changed), "anchor_retries": attempt})
                return changed
            except ValueError as exc:
                if retry_anchor and attempt == 0 and "stale journal anchor" in str(exc):
                    continue
                self.steps.append({"stage": name, "status": "rejected", "reason": str(exc)[:500]})
                return None

    def _packet(self, *, opening=False):
        state = self.book.snapshot()
        packet = {key: self.feed[key] for key in ("schema_version", "mode", "snapshot_id", "source_ref", "as_of", "session_date", "quotes")}
        packet.update(journal_sequence=state["sequence"], journal_hash=state["journal_hash"])
        if opening:
            packet.update(self.feed["opening"])
        return packet

    def _receipt(self, value):
        if not isinstance(value, dict):
            raise ValueError("runtime receipt must be an object")
        kind = value.get("kind")
        fields = {
            "fill": {"order_id", "fill_id", "quantity", "price"},
            "status": {"order_id", "report_id", "status", "cumulative_quantity"},
            "dividend_credit": {"event_id", "receipt_id", "cash_amount"},
            "reconcile": {"snapshot_id", "expected_sequence", "cash", "positions", "orders"}}
        if not isinstance(kind, str) or kind not in fields:
            raise ValueError("unsupported explicit runtime receipt")
        exact(value, fields[kind] | {"kind"}, "runtime receipt")
        args = {key: value[key] for key in fields[kind]}
        if kind == "fill": return self.book.fill(**args)
        if kind == "status": return self.book.report_status(**args)
        if kind == "dividend_credit": return self.book.record_dividend_cash_credit(**args, clock=self.clock)
        return self.book.reconcile(**args)

    def _corporate_actions(self, now):
        date, local_time = now.astimezone(SHANGHAI).date().isoformat(), now.astimezone(SHANGHAI).time()
        for policy_key, state_key, capture, apply, applied_key, effective_key in (
                ("conversion_policy", "conversions", self.book.record_conversion_entitlements, self.book.apply_share_conversions, "applied", "conversion_date"),
                ("dividend_policy", "dividends", self.book.record_dividend_entitlements, self.book.accrue_dividends, "accrued", "ex_date")):
            rule = self.rules[policy_key]
            if rule is None:
                continue
            state = self.book.snapshot()[state_key]
            if (local_time >= time.fromisoformat(rule["record_cutoff"])
                    and any(row["record_date"] == date and row["event_id"] not in state["entitlements"] for row in rule["events"])):
                self._call(state_key + "_record", lambda capture=capture: capture(clock=self.clock))
            if any(row[effective_key] <= date and row["event_id"] not in state[applied_key] for row in rule["events"]):
                self._call(state_key + "_apply", lambda apply=apply: apply(clock=self.clock))

    def tick(self, observation):
        now = instant(self.clock())
        if self.last_tick is not None and now < self.last_tick:
            raise ValueError("runtime clock moved backward")
        self.last_tick, self.steps = now, []
        try:
            self.feed, feed_status = _observation(observation, now)
        except ValueError as exc:
            self.steps.append({"stage": "observation", "status": "rejected", "reason": str(exc)[:500]})
            self.feed, feed_status = _observation(None, now)[0], "invalid"
        for row in self.feed.get("receipts", []):
            if self._call("receipt", lambda row=row: self._receipt(row)) is None:
                self.book.note_unusable_runtime_receipt(self.steps[-1]["reason"])
        for key in self.feed.get("cancel_requests", []):
            self._call("cancel_request", lambda key=key: self.book.request_cancel(key, clock=self.clock))
        self._call("timeouts", lambda: self.book.monitor_timeouts(clock=self.clock))
        self._corporate_actions(now)
        session = self.book.snapshot()["risk_session"]
        if "opening" in self.feed and (session is None or session["session_date"] != self.feed["session_date"]):
            self._call("opening", lambda: self.book.begin_session(self._packet(opening=True), clock=self.clock), retry_anchor=True)
        self._call("valuation", lambda: self.book.record_valuation(self._packet(), clock=self.clock), retry_anchor=True)
        for row in self.feed.get("intents", []):
            state = self.book._read()
            key = row.get("client_intent_id") if isinstance(row, dict) else None
            if isinstance(key, str) and (key in state["orders"] or key in state["attempted_intent_ids"]):
                self.steps.append({"stage": "intent", "status": "already_attempted"})
                continue
            self._call("intent", lambda row=row: self.book.admit(row, self._packet(), clock=self.clock))
        state = self.book._read()
        if not self.book.snapshot()["paused"]:
            for key, order in state["orders"].items():
                if order["status"] != "PENDING" or order["filled_quantity"] or "dispatch" in order:
                    continue
                attempt_id = "runtime-" + hashlib.sha256(json.dumps([key, self.feed["snapshot_id"], self.feed["as_of"]]).encode()).hexdigest()
                if attempt_id in state["attempted_dispatch_ids"]:
                    continue
                self._call("dispatch", lambda key=key, attempt_id=attempt_id: self.book.prepare_dispatch(key, attempt_id, self._packet(), clock=self.clock))
        state = self.book.snapshot()
        if any(row["stage"] in {"intent", "dispatch"} and row.get("changed") for row in self.steps):
            self._call("post_order_valuation", lambda: self.book.record_valuation(self._packet(), clock=self.clock), retry_anchor=True)
            state = self.book.snapshot()
        current_session = (state["risk_session"] or {}).get("session_date") == now.astimezone(SHANGHAI).date().isoformat()
        attention = feed_status != "present" or state["paused"] or not current_session or any(row["status"] == "rejected" for row in self.steps)
        return {"schema_version": 1, "mode": "offline_fixture_only", "executable": False,
            "status": "attention" if attention else "ready", "observed_at": now.isoformat(), "feed_status": feed_status,
            "feed_snapshot_id": self.feed["snapshot_id"], "feed_as_of": self.feed["as_of"], "feed_source_ref": self.feed["source_ref"],
            "counts_as_forward_paper_days": 0, "qualifies_for_strategy_promotion": False,
            "journal_sequence": state["sequence"], "journal_hash": state["journal_hash"],
            "paused": state["paused"], "faults": state["faults"], "steps": self.steps}


def read_observation(path, *, max_bytes=2_000_000):
    with Path(path).open("rb") as source:
        payload = source.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError("runtime observation exceeds the file size limit")
    return json.loads(payload.decode("utf-8-sig"))


def validate_loop_limits(interval_seconds, max_ticks):
    if (isinstance(interval_seconds, bool) or not isinstance(interval_seconds, (int, float))
            or not math.isfinite(interval_seconds) or not 0.01 <= interval_seconds <= 60):
        raise ValueError("runtime interval must be between 0.01 and 60 seconds")
    if max_ticks is not None and (type(max_ticks) is not int or max_ticks <= 0):
        raise ValueError("max_ticks must be a positive integer or None")


def run_loop(runtime, supplier, *, interval_seconds=1.0, max_ticks=None, sleep=system_time.sleep, on_tick=None):
    validate_loop_limits(interval_seconds, max_ticks)
    ticks, last = 0, None
    while max_ticks is None or ticks < max_ticks:
        started = system_time.monotonic()
        error = None
        try:
            feed = supplier()
        except (OSError, ValueError, UnicodeError) as exc:
            feed, error = None, str(exc)[:500]
        last = runtime.tick(feed)
        last["tick_duration_seconds"] = system_time.monotonic() - started
        last["cadence_overrun"] = last["tick_duration_seconds"] > interval_seconds
        if last["cadence_overrun"]:
            last["status"] = "attention"
        if error:
            last["feed_read_error"] = error
        ticks += 1
        if on_tick is not None:
            on_tick(last)
        if max_ticks is None or ticks < max_ticks:
            sleep(max(0, interval_seconds - (system_time.monotonic() - started)))
    return {"ticks": ticks, "last_report": last}
