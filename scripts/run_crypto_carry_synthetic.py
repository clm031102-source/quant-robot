"""Run fixed fictional event-ledger cases; accepts no market-input files or URLs."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.research.crypto_carry_model import CarryModel, FeeScenario, Leg, TradingRule

D = Decimal
START = datetime(2001, 1, 1, tzinfo=timezone.utc)
REPORT_ROOT = Path(__file__).resolve().parents[1] / "data/reports/campaign_72h_20261106/manager"


def new_model(fees=None):
    result = CarryModel(start=START, spot_rule=TradingRule("0.001", "0.001", "10"),
                        futures_rule=TradingRule("0.001", "0.001", "10"),
                        fees=fees or FeeScenario("0", "0", "0"))
    result.queue_quote(START, spot="1000")
    result.run(START)
    return result


def open_hedge(model, quantity="0.4"):
    if not model.register_plan((Leg("spot_buy", quantity), Leg("short_open", quantity))):
        raise ValueError("Synthetic fixture setup rejected")
    model.run(START + timedelta(minutes=2))


def run_synthetic():
    cases = []

    def keep(name, model, checks, **extra):
        if not all(checks.values()):
            raise ValueError("Synthetic invariant failed: " + name)
        cases.append({"case": name, "checks": checks, "state": model.snapshot(), **extra})

    fee_model = new_model(FeeScenario("0.001", "0.0005", "0"))
    fee_model.register_plan((Leg("spot_buy", "0.05"), Leg("short_open", "0.049")))
    fee_model.run(START + timedelta(minutes=2))
    keep("BTC_fee_and_residual", fee_model, {
        "net_BTC_0_04995": fee_model.spot_btc == D("0.04995"),
        "short_BTC_0_049": fee_model.short_btc == D("0.049"),
        "residual_0_00095_not_deleted": fee_model.delta_btc == D("0.00095"),
        "fees_reduce_NAV": fee_model.nav == D("999.9255"),
    })

    low = new_model()
    open_hedge(low, "0.02")
    low.queue_quote(START + timedelta(minutes=3), spot="100")
    low.run(START + timedelta(minutes=3))
    rejected = not low.request_exit()
    keep("below_minimum_notional_exit", low, {
        "paired_exit_rejected_before_mutation": rejected and low.plan is None,
        "both_positions_preserved": low.spot_btc == low.short_btc == D("0.02"),
    })

    jump = new_model()
    open_hedge(jump)
    jump.queue_quote(START + timedelta(minutes=3), spot="2000")
    jump.run(START + timedelta(minutes=3))
    keep("global_NAV_does_not_protect_margin_wallet", jump, {
        "NAV_still_1000": jump.nav == D("1000"),
        "gross_now_1600": jump.gross == D("1600"),
        "futures_equity_now_100": jump.futures_equity == D("100"),
        "both_boundaries_failed": {"gross_over_100_percent", "futures_wallet_below_1x"} <= jump.failures,
    })

    transfer = new_model()
    transfer.request_transfer("spot", "100")
    pending = transfer.snapshot()
    transfer.run(START + timedelta(minutes=5) - timedelta(microseconds=1))
    not_early = transfer.futures_cash == D("500")
    transfer.run(START + timedelta(minutes=5))
    keep("five_minute_segregated_transfer", transfer, {
        "pending_not_duplicated": D(pending["nav"]) == D("1000") and D(pending["in_transit"]) == D("100"),
        "not_available_early": not_early,
        "confirmed_once": transfer.futures_cash == D("600") and transfer.transfer is None,
        "NAV_conserved": transfer.nav == D("1000"),
    }, pending_state=pending)

    event = new_model()
    event.register_plan((Leg("spot_buy", "0.1"), Leg("short_open", "0.1")))
    at = START + timedelta(minutes=2)
    event.queue_funding(at, rate="0.01", mark="1000")
    event.queue_funding(at + timedelta(milliseconds=15), rate="0.01", mark="1000")
    event.queue_funding(at + timedelta(hours=1), rate="-0.002", mark="1000")
    event.run(at + timedelta(hours=1))
    funding = [row for row in event.journal if row["event"] == "funding"]
    keep("funding_exact_time_and_sign", event, {
        "same_time_old_quantity_zero": D(funding[0]["quantity_before"]) == 0,
        "fifteen_ms_later_new_quantity": D(funding[1]["quantity_before"]) == D("0.1"),
        "negative_funding_is_paid": D(funding[2]["cash_delta"]) == D("-0.2"),
        "net_funding_0_8": event.funding_cash == D("0.8"),
    }, funding_events=funding)

    repair = new_model(FeeScenario("0.001", "0", "0"))
    repair.register_plan((Leg("spot_buy", "0.05"), Leg("short_open", "0.049")))
    repair.queue_quote(START + timedelta(minutes=2), spot="1000", future="100", mark="1000")
    repair.run(START + timedelta(minutes=2))
    failed_second_leg = repair.snapshot()
    repair.run(START + timedelta(minutes=3))
    keep("failed_second_leg_and_paid_repair", repair, {
        "first_fill_was_not_rolled_back": D(failed_second_leg["spot_btc"]) == D("0.04995"),
        "repair_fee_and_loss_kept": repair.nav == D("999.901"),
        "dust_kept_and_not_flat": repair.spot_btc == D("0.00095") and not repair.actually_flat,
    }, after_second_leg_rejection=failed_second_leg)
    terminal = repair.finish()
    keep("terminal_dust_haircut_not_inventory_deletion", repair, {
        "book_NAV_999_901": D(terminal["book_nav"]) == D("999.901"),
        "conservative_NAV_998_951": D(terminal["conservative_terminal_nav"]) == D("998.951"),
        "inventory_still_0_00095": repair.spot_btc == D("0.00095"),
    }, terminal_report=terminal)

    recovery = new_model()
    open_hedge(recovery)
    hit = START + timedelta(hours=12)
    recovery.queue_funding(hit, rate="-1.025", mark="1000")
    recovery.run(hit + timedelta(minutes=2))
    after_stop = recovery.snapshot()
    for day in range(6):
        recovery.queue_day_end(START + timedelta(days=day + 1) - timedelta(microseconds=1))
    recovery.run(START + timedelta(days=6))
    counted = recovery.cooldown_days
    resume = START + timedelta(days=6, minutes=2)
    recovery.queue_resume(resume)
    recovery.run(resume)
    keep("40_percent_latch_diagnostic_recovery", recovery, {
        "flat_NAV_590_after_stop": D(after_stop["nav"]) == D("590") and after_stop["actually_flat"],
        "five_complete_days_only": counted == 5,
        "recovered_without_repeated_same_DD_event": not recovery.paused and recovery.dd_events == 1,
        "peak_and_failed_verdict_preserved": recovery.peak == D("1000") and recovery.financial_verdict == "failed",
    }, stopped_state=after_stop)

    for short_quantity, eligible in (("0.049", True), ("0.048", False)):
        dust = CarryModel(start=START,
                          spot_rule=TradingRule("0.00001", "0.00001", "10"),
                          futures_rule=TradingRule("0.001", "0.001", "10"),
                          fees=FeeScenario("0.001", "0", "0"))
        dust.queue_quote(START, spot="1000")
        dust.run(START)
        if not dust.register_plan((Leg("spot_buy", "0.05"), Leg("short_open", short_quantity))):
            raise ValueError("Synthetic dust fixture entry rejected")
        dust.run(START + timedelta(minutes=2))
        if not dust.register_plan((Leg("short_close", short_quantity), Leg("spot_sell", short_quantity)), kind="rebalance"):
            raise ValueError("Synthetic dust fixture reduction rejected")
        dust.queue_funding(START + timedelta(minutes=3), rate="-0.5", mark="1000")
        dust.run(START + timedelta(minutes=4))
        after_risk_exit = dust.snapshot()
        for day in range(6):
            dust.queue_day_end(START + timedelta(days=day + 1) - timedelta(microseconds=1))
        dust.run(START + timedelta(days=6))
        counted_days = dust.cooldown_days
        at = START + timedelta(days=6, minutes=2)
        dust.queue_resume(at)
        dust.run(at)
        keep("funding_risk_exit_" + ("eligible" if eligible else "excess") + "_dust", dust, {
            "actual_negative_funding_triggered_pause": D(after_risk_exit["funding_cash"]) < -20 and after_risk_exit["paused"],
            "main_short_closed_dust_preserved": dust.short_btc == 0 and dust.spot_btc > 0 and not dust.actually_flat,
            "no_fictitious_illegal_dust_exit": "exit_constraints" not in dust.unresolved,
            "complete_day_count_respects_dust_gate": counted_days == (5 if eligible else 0),
            "recovery_respects_dust_gate": dust.paused is not eligible,
        }, after_actual_risk_exit=after_risk_exit)

    return {"status": "synthetic_kernel_cases_passed", "synthetic_only": True,
            "synthetic_receipt_version": 2,
            "qualified": False, "real_forward": 0, "historical_returns_computed": False,
            "real_market_files_read": 0, "network_requests": 0,
            "input_description": "Hard-coded fictional prices, rates and rules dated 2001. Zero-fee cases isolate accounting identities, not actual exchange costs.",
            "diagnostic_engine_incomplete": fee_model.snapshot()["diagnostic_engine_incomplete"],
            "case_count": len(cases), "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON destination inside the campaign manager report directory")
    args = parser.parse_args()
    result = run_synthetic()
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        path = args.output.resolve()
        if not path.is_relative_to(REPORT_ROOT.resolve()):
            raise ValueError("Synthetic report must stay in the campaign manager directory")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "case_count": result["case_count"],
                          "qualified": False, "real_forward": 0, "report": str(path)}))
    else:
        print(text)


if __name__ == "__main__":
    main()
