"""Run a fixed synthetic order incident drill; never contacts any provider."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
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


def run_drill(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    journal_path = output_dir / "synthetic_orders.sqlite"
    book = OfflineOrderJournal.create(journal_path, initial_cash="10000",
        initial_positions={"510300.SH": 1000}, commission_bps="5", minimum_commission="5")
    stages = []

    def capture(name):
        stages.append({"name": name, "state": book.snapshot()})

    def reconcile(snapshot_id, statuses=None, wrong_cash=False):
        state = book.snapshot()
        orders = {key: {field: row[field] for field in
            ("status", "filled_quantity", "filled_notional", "commission")} for key, row in state["orders"].items()}
        for key, status in (statuses or {}).items():
            orders[key]["status"] = status
        book.reconcile(snapshot_id=snapshot_id, expected_sequence=state["sequence"],
            cash=str(Decimal(state["cash"]) + int(wrong_cash)), positions=state["positions"], orders=orders)

    try:
        book.register(order_id="buy", idempotency_key="fixture-buy-1", symbol="510300.SH",
            side="BUY", quantity=200, limit_price="10")
        book.report_status("buy", "accepted", "ACCEPTED", 0)
        book.fill("buy", "trade-2", 100, "9.90")
        if book.fill("buy", "trade-2", 100, "9.9000"):
            raise AssertionError("duplicate fill was applied")
        book.request_cancel("buy")
        capture("partial_fill_duplicate_and_cancel_request")
        book.close()
        book = OfflineOrderJournal(journal_path)
        capture("restart_pauses_unknown_order")
        if not book.snapshot()["paused"]:
            raise AssertionError("restart did not pause")
        reconcile("recovery", {"buy": "CANCEL_PENDING"})
        book.fill("buy", "trade-1", 100, "10")
        book.report_status("buy", "late-cancel", "CANCELLED", 200)
        capture("cancel_fill_race_resolves_as_filled")
        book.register(order_id="sell", idempotency_key="fixture-sell-1", symbol="510300.SH",
            side="SELL", quantity=200, limit_price="12")
        book.fill("sell", "trade-3", 100, "12")
        book.report_status("sell", "partial-cancel", "CANCELLED", 100)
        try:
            reconcile("bad-snapshot", wrong_cash=True)
        except ValueError as exc:
            if "reconciliation" not in str(exc):
                raise
        else:
            raise AssertionError("incorrect cash passed reconciliation")
        capture("account_mismatch_pauses_registration")
        reconcile("corrected-snapshot")
        book.set_kill_switch(True, reason="synthetic operator stop")
        reconcile("operator-check")
        if not book.snapshot()["paused"]:
            raise AssertionError("reconciliation released operator stop")
        capture("operator_stop_survives_reconciliation")
        book.set_kill_switch(False, reason="synthetic operator release")
        capture("reconciled_final_state")
        final = book.snapshot()
        if (Decimal(final["cash"]) != Decimal("9200") or final["positions"] != {"510300.SH": 1100}
                or final["paused"] or Decimal(final["reserved_cash"]) != 0):
            raise AssertionError("unexpected final balances")
    finally:
        book.close()
    root = Path(__file__).resolve().parents[1]
    files = [Path(__file__).resolve(), root / "src/quant_robot/execution/offline_journal.py",
        root / "src/quant_robot/execution/offline_order_state.py"]
    result = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic_drill_passed", "mode": "offline_fixture_only",
        "counts_as_forward_paper_days": 0, "qualifies_for_strategy_promotion": False,
        "fee_source": "explicit_synthetic_fixture_not_broker_verified",
        "boundary": build_execution_boundary_status(), "stages": stages,
        "implementation_sha256": {str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        "journal_path": str(journal_path.resolve()),
        "journal_file_sha256": hashlib.sha256(journal_path.read_bytes()).hexdigest()}
    (output_dir / "drill_report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = run_drill(args.output_dir)
    print(json.dumps({"status": result["status"], "stages": len(result["stages"]),
        "report": str((args.output_dir / "drill_report.json").resolve()), "executable": False}))


if __name__ == "__main__":
    main()
