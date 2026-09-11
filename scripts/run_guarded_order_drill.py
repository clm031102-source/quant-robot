"""Exercise synthetic admission, dispatch, order-independent valuation and recovery."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.execution.boundary import build_execution_boundary_status
from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.storage.atomic import atomic_write_json


def run_drill(config_path: Path, output_dir: Path):
    original = config_path.read_bytes()
    cfg = json.loads(original.decode("utf-8-sig"))
    if cfg["schema_version"] != 1 or cfg["mode"] != "offline_fixture_only":
        raise ValueError("only the versioned synthetic fixture is allowed")
    now = datetime.fromisoformat(cfg["logical_clock_start"])
    journal_path = output_dir / "guarded_synthetic_orders.sqlite"
    book = OfflineOrderJournal.create(journal_path, initial_cash=cfg["initial_cash"], initial_positions=cfg["initial_positions"],
        commission_bps=cfg["commission_bps"], minimum_commission=cfg["minimum_commission"], admission_policy=cfg["policy"])
    stages, rejected, dispatch_rejections, valuation_rejections = [], [], [], []

    def packet():
        state = book.snapshot()
        return {"schema_version": 1, "mode": "offline_fixture_only", "snapshot_id": "fixture-context-" + str(state["sequence"]),
            "source_ref": "synthetic-snapshot", "as_of": now.isoformat(), "session_date": now.date().isoformat(),
            "journal_sequence": state["sequence"], "journal_hash": state["journal_hash"],
            "quotes": {code: {"symbol": code, "exchange": row["exchange"], "timestamp": now.isoformat(),
                "bid": cfg["fixture_price"], "ask": cfg["fixture_price"], "trade_status": "TRADING", "source_ref": "synthetic-quote"}
                for code, row in cfg["instruments"].items()}}

    def start(sellable):
        value = packet()
        value.update(instruments=cfg["instruments"], sellable_positions=sellable)
        book.begin_session(value, clock=lambda: now)

    def order(key, side="BUY", quantity=100, code="510300.SH"):
        return {"schema_version": 1, "client_intent_id": key, "idempotency_key": "fixture-" + key,
            "strategy_id": cfg["policy"]["strategy_id"], "strategy_version": cfg["policy"]["strategy_version"],
            "signal_timestamp": now.isoformat(), "symbol": code, "exchange": cfg["instruments"][code]["exchange"],
            "side": side, "quantity": quantity, "order_type": "LIMIT", "limit_price": cfg["fixture_price"],
            "time_in_force": "DAY", "max_slippage_bps": cfg["policy"]["max_slippage_bps"],
            "expires_at": (now + timedelta(minutes=2)).isoformat()}

    def expect_rejection(value, context, reason):
        try:
            book.admit(value, context, clock=lambda: now)
        except ValueError as exc:
            if reason not in str(exc):
                raise
            rejected.append({"intent_id": value["client_intent_id"], "reason": str(exc)})
        else:
            raise AssertionError("unsafe fixture intent was admitted")

    def capture(name):
        stages.append({"name": name, "state": book.snapshot()})

    try:
        start(cfg["opening_sellable_positions"])
        capture("frozen_policy_and_opening_sellable_shares")
        stale = packet()
        stale["quotes"]["510300.SH"]["timestamp"] = (now - timedelta(seconds=31)).isoformat()
        expect_rejection(order("stale"), stale, "stale")
        expect_rejection(order("split-oddlot", "SELL", 50), packet(), "odd-lot")
        capture("stale_quote_and_incomplete_oddlot_rejected")
        book.admit(order("sell-available", "SELL", 80), packet(), clock=lambda: now)
        book.prepare_dispatch("sell-available", "prepare-sell", packet(), clock=lambda: now)
        book.fill("sell-available", "f1", 80, cfg["fixture_price"])
        book.admit(order("buy-t1"), packet(), clock=lambda: now)
        expired_quote = packet()
        expired_quote["quotes"]["510300.SH"]["timestamp"] = (now - timedelta(seconds=31)).isoformat()
        try:
            book.prepare_dispatch("buy-t1", "prepare-stale-buy", expired_quote, clock=lambda: now)
        except ValueError as exc:
            if "stale" not in str(exc):
                raise
            dispatch_rejections.append({"order_id": "buy-t1", "reason": str(exc)})
        else:
            raise AssertionError("stale dispatch was prepared")
        book.prepare_dispatch("buy-t1", "prepare-fresh-buy", packet(), clock=lambda: now)
        book.fill("buy-t1", "f2", 100, cfg["fixture_price"])
        expect_rejection(order("same-day-sell", "SELL"), packet(), "sellable")
        capture("only_available_shares_sold_and_t1_buy_locked")
        book.close()
        book = OfflineOrderJournal(journal_path)
        expect_rejection(order("restart-sell", "SELL"), packet(), "sellable")
        capture("restart_preserves_same_day_lock")
        now += timedelta(days=1)
        start(book.snapshot()["positions"])
        book.admit(order("settled-sell", "SELL"), packet(), clock=lambda: now)
        book.prepare_dispatch("settled-sell", "prepare-settled-sell", packet(), clock=lambda: now)
        book.fill("settled-sell", "f3", 100, cfg["fixture_price"])
        capture("new_session_explicit_settlement_and_sale")
        book.record_valuation(packet(), clock=lambda: now)
        capture("book_valued_without_a_new_order")
        now += timedelta(seconds=31)
        missing = packet()
        missing["quotes"].pop("510300.SH")
        try:
            book.record_valuation(missing, clock=lambda: now)
        except ValueError as exc:
            if "missing" not in str(exc):
                raise
            valuation_rejections.append(str(exc))
        else:
            raise AssertionError("missing holding quote was accepted")
        if not book.snapshot()["paused"]:
            raise AssertionError("quote outage did not pause the journal")
        capture("missing_quote_pauses_and_preserves_previous_valuation")
        book.record_valuation(packet(), clock=lambda: now)
        if book.snapshot()["paused"]:
            raise AssertionError("fresh valuation did not resolve the quote-only fault")
        capture("fresh_quote_restores_book_visibility")
        loss = packet()
        loss["quotes"]["510300.SH"].update(bid="3.1", ask="3.1")
        book.record_valuation(loss, clock=lambda: now)
        if "daily_loss" not in book.snapshot()["portfolio_valuation"]["last_valid"]["breaches"]:
            raise AssertionError("order-independent daily loss was not detected")
        capture("daily_loss_triggers_before_any_new_order")
        expect_rejection(order("loss-check", code="159915.SZ"), packet(), "risk stop")
        book.set_kill_switch(True, reason="synthetic operator stop during continuing valuation")
        book.record_valuation(packet(), clock=lambda: now)
        if not book.snapshot()["kill_switch"]:
            raise AssertionError("valuation cleared the operator stop")
        book.set_kill_switch(False, reason="synthetic operator switch cannot clear risk stop")
        expect_rejection(order("rebound", code="159915.SZ"), packet(), "risk stop")
        capture("daily_loss_stop_survives_quote_rebound_and_operator_switch")
        final = book.snapshot()
        if (not final["paused"] or Decimal(final["cash"]) != Decimal("2305")
                or final["positions"] != {"510300.SH": 70} or len(final["orders"]) != 3):
            raise AssertionError("unexpected final guarded journal state")
    finally:
        book.close()
    if config_path.read_bytes() != original:
        raise ValueError("fixture config changed during drill")
    root = Path(__file__).resolve().parents[1]
    files = [Path(__file__).resolve(), root / "scripts/bootstrap.py", *[
        root / "src/quant_robot/execution" / name for name in ("offline_journal.py", "offline_order_state.py",
            "offline_admission.py", "offline_dispatch.py", "offline_timeouts.py", "offline_portfolio_risk.py",
            "offline_valuation.py", "offline_intent_contract.py", "boundary.py")]]
    result = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic_admission_drill_passed", "mode": "offline_fixture_only", "executable": False,
        "counts_as_forward_paper_days": 0, "qualifies_for_strategy_promotion": False,
        "fee_and_instrument_source": "synthetic_fixture_not_broker_or_source_verified",
        "config_sha256": hashlib.sha256(original).hexdigest(), "boundary": build_execution_boundary_status(),
        "rejected_intents": rejected, "rejected_dispatches": dispatch_rejections,
        "rejected_valuations": valuation_rejections, "stages": stages,
        "implementation_sha256": {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        "journal_path": str(journal_path.resolve()), "journal_sha256": hashlib.sha256(journal_path.read_bytes()).hexdigest()}
    atomic_write_json(output_dir / "guarded_drill_report.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/offline_order_admission_drill_20260912.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run_drill(args.config, args.output_dir)
    print(json.dumps({"status": result["status"], "stages": len(result["stages"]),
        "rejected_intents": len(result["rejected_intents"]), "executable": False,
        "report": str((args.output_dir / "guarded_drill_report.json").resolve())}))


if __name__ == "__main__":
    main()
