"""Run ten explicit synthetic observations through the real supervision loop."""
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

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_runtime import OfflineRuntime, run_loop
from quant_robot.storage.atomic import atomic_write_json


def run_drill(config_path, output):
    original = config_path.read_bytes()
    cfg = json.loads(original.decode("utf-8-sig"))
    if cfg["schema_version"] != 1 or cfg["mode"] != "offline_fixture_only":
        raise ValueError("only explicit synthetic fixtures are supported")
    output.mkdir(parents=True, exist_ok=False)
    path = output/"runtime.sqlite"
    with OfflineOrderJournal.create(path, initial_cash=cfg["initial_cash"], initial_positions=cfg["initial_positions"],
            commission_bps=cfg["commission_bps"], minimum_commission=cfg["minimum_commission"], admission_policy=cfg["policy"],
            timeout_policy=cfg["timeout_policy"], dividend_policy=cfg["dividend_policy"], conversion_policy=cfg["conversion_policy"]):
        pass
    start = datetime.fromisoformat(cfg["logical_clock_start"])
    clocks = [start, start+timedelta(seconds=10), start+timedelta(seconds=41), start+timedelta(seconds=42),
        start.replace(hour=15), (start+timedelta(days=1)).replace(hour=9), start+timedelta(days=1), start+timedelta(days=2),
        start+timedelta(days=2, seconds=10), start+timedelta(days=2, seconds=20)]
    names = ["opening_and_preparation", "explicit_buy_fill", "missing_feed", "fresh_feed_recovery", "record_day_capture",
        "scheduled_conversion_and_receivable_without_feed", "premature_unlock_rejected", "resume_and_explicit_cash_credit",
        "sale_prepared", "explicit_sale_fill"]
    now, index, stages, inputs = start, 0, [], []
    with OfflineRuntime(path, clock=lambda: now) as runtime:
        def supply():
            nonlocal now, index
            step, index = index, index+1
            now = clocks[step]
            if step in (2, 5):
                inputs.append({"name": names[step], "observed_at": now.isoformat(), "feed": None})
                return None
            state = runtime.book.snapshot()
            price = "4" if step < 5 else "6.8"
            packet = {"schema_version": 1, "mode": "offline_fixture_only", "snapshot_id": "runtime-fixture-"+str(step),
                "source_ref": "explicit-synthetic-observation", "as_of": now.isoformat(), "session_date": now.date().isoformat(),
                "quotes": {code: {"symbol": code, "exchange": row["exchange"], "timestamp": now.isoformat(), "bid": price if code == "510300.SH" else "4",
                    "ask": price if code == "510300.SH" else "4", "trade_status": "TRADING", "source_ref": "synthetic-quote",
                    **({"price_basis_id": state["price_basis"][code]} if code in state["price_basis"] else {})}
                    for code, row in cfg["instruments"].items()}}
            if step in (0, 6, 7):
                packet["opening"] = {"instruments": cfg["instruments"], "sellable_positions": {"510300.SH": 100}}
            if step in (0, 8):
                key, side = ("buy", "BUY") if step == 0 else ("sell", "SELL")
                packet["intents"] = [{"schema_version": 1, "client_intent_id": key, "idempotency_key": "fixture-"+key,
                    "strategy_id": cfg["policy"]["strategy_id"], "strategy_version": cfg["policy"]["strategy_version"],
                    "signal_timestamp": now.isoformat(), "symbol": "510300.SH", "exchange": "SSE", "side": side, "quantity": 100,
                    "order_type": "LIMIT", "limit_price": price, "time_in_force": "DAY", "max_slippage_bps": cfg["policy"]["max_slippage_bps"],
                    "expires_at": (now+timedelta(minutes=2)).isoformat()}]
            if step in (1, 9):
                key = "buy" if step == 1 else "sell"
                packet["receipts"] = [{"kind": "fill", "order_id": key, "fill_id": "explicit-"+key, "quantity": 100, "price": price}]
            if step == 7:
                packet["receipts"] = [{"kind": "dividend_credit", "event_id": "synthetic-distribution", "receipt_id": "explicit-cash-credit", "cash_amount": "120"}]
            inputs.append({"name": names[step], "observed_at": now.isoformat(), "feed": packet})
            return packet

        def record(report):
            stages.append({"name": names[len(stages)], "report": report, "state": runtime.book.snapshot()})

        run_loop(runtime, supply, interval_seconds=60, max_ticks=10, sleep=lambda _: None, on_tick=record)
        final = runtime.book.snapshot()
    expected = ["ready", "ready", "attention", "ready", "ready", "attention", "attention", "ready", "ready", "ready"]
    if [s["report"]["status"] for s in stages] != expected:
        raise AssertionError("unexpected runtime stage status")
    if (Decimal(final["cash"]) != Decimal("2990") or final["positions"] or final["paused"]
            or Decimal(final["dividends"]["receivable_total"]) != 0
            or any(row["status"] != "FILLED" for row in final["orders"].values())):
        raise AssertionError("runtime final accounting is incorrect")
    if config_path.read_bytes() != original:
        raise ValueError("fixture config changed during execution")
    root = Path(__file__).resolve().parents[1]
    files = [Path(__file__).resolve(), root/"scripts/bootstrap.py", *sorted((root/"src/quant_robot/execution").glob("offline_*.py"))]
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(), "mode": "offline_fixture_only",
        "status": "synthetic_runtime_drill_passed", "executable": False, "counts_as_forward_paper_days": 0,
        "qualifies_for_strategy_promotion": False, "config_sha256": hashlib.sha256(original).hexdigest(),
        "input_observations": inputs, "stages": stages, "journal_path": str(path.resolve()),
        "journal_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "implementation_sha256": {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    atomic_write_json(output/"runtime_drill_report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/offline_runtime_drill_20260912.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_drill(args.config, args.output_dir)
    print(json.dumps({"status":report["status"], "ticks":len(report["stages"]), "executable":False,
        "report":str((args.output_dir/"runtime_drill_report.json").resolve())}))


if __name__ == "__main__":
    main()
