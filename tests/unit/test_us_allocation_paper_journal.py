import copy
from datetime import date, datetime, time, timedelta, timezone
from decimal import localcontext
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from quant_robot.ops import us_allocation_paper_journal as journal
from quant_robot.research import us_monthly_rotation as kernel


def sample():
    days = []
    day = date(2000, 1, 3)
    while day <= date(2000, 4, 14):
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    schedule = [dict(date=d.isoformat(), open_at=datetime.combine(d,time(14,30),timezone.utc).isoformat(),
                     close_at=datetime.combine(d,time(21),timezone.utc).isoformat()) for d in days]
    prices = {a:str(10+10*i) for i,a in enumerate(kernel.ASSETS)}
    manifest = dict(schema=journal.SCHEMA,evidence_kind="artificial",constructed_from_market_data=False,
        initial_cash="1000.00",assets=list(kernel.ASSETS),minimum_commission="1.00",slippage_bps=10,
        schedule=schedule,activated_at=schedule[19]["close_at"],
        warmup=[dict(date=r["date"],prices={a:dict(close=p,volume="100000") for a,p in prices.items()})
                for r in schedule[:20]])
    return manifest, prices


def packet(manifest, prices, index, kind, **extra):
    row = manifest["schedule"][index]
    at = row["open_at" if kind == "open" else "close_at"]
    result = dict(kind=kind,date=row["date"],evidence_kind="artificial",constructed_from_market_data=False,
                  effective_at=at,known_at=at,received_at=(datetime.fromisoformat(at)+timedelta(seconds=30)).isoformat())
    if kind == "open":
        result.update(prices={a:dict(open=p) for a,p in prices.items()},
                      execution={a:dict(suspended=False,buy_blocked=False,sell_blocked=False) for a in prices})
    else:
        result["prices"] = {a:dict(close=p,volume="100000") for a,p in prices.items()}
    result.update(extra)
    return result


class USAllocationPaperTests(unittest.TestCase):
    def test_independent_phases_match_unchanged_kernel_before_terminal(self):
        manifest, prices = sample()
        with localcontext(kernel.CONTEXT):
            session = journal._Session(manifest)
            for i in range(20,len(manifest["schedule"])-1):
                # A fixed shock exercises stop, settlement and five flat days.
                live = prices if i < 35 else {a:str(int(p)*.8) for a,p in prices.items()}
                dividend = [dict(id="test_dividend",symbol="IEF",ex_date=manifest["schedule"][29]["date"],
                                 known_at=manifest["schedule"][28]["close_at"],amount_per_share=".50")] if i == 29 else []
                session.apply(packet(manifest,live,i,"open",dividends=dividend))
                session.apply(packet(manifest,live,i,"close"))
            normalized = copy.deepcopy(session.normalized)
            normalized["first"] = 20
            normalized["terminal"] = len(normalized["dates"])-1
            normalized["bars"][-1] = {a:dict(open=kernel.D(p)*kernel.D('.8'),close=None,volume=None) for a,p in prices.items()}
            normalized["execution"][-1] = {a:dict(suspended=False,buy_blocked=False,sell_blocked=False) for a in prices}
            baseline = kernel._Account(SimpleNamespace(normalized=normalized),"fixed_quarters","1.00",10).run()
            expected = baseline["days"][-2]
            actual = session.snapshot()
            self.assertEqual(actual["previous_NAV"],str(expected["NAV"]))
            self.assertEqual(actual["balances"],kernel.serial(expected["after"]))
            self.assertEqual(actual["maxDD"],str(expected["observed_maxDD"]))
            self.assertEqual(actual["cooldown"],expected["cooldown"])
            self.assertTrue(any(a["kind"] == "dividend_payment" for a in actual["actions"]))
            self.assertTrue(any(a["kind"] == "sale_cash_release" for a in actual["actions"]))
            self.assertTrue(any(f["phase"] == "risk_exit" for f in actual["fills"]))
            self.assertTrue(all(f["observed_full_day_volume"] is None for f in actual["fills"]))

    def test_restart_restores_cash_positions_fifo_and_pending_intents(self):
        manifest, prices = sample()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"account"
            journal.create(path,manifest)
            for i in range(20,25):
                journal.advance(path,packet(manifest,prices,i,"open"))
                current = journal.advance(path,packet(manifest,prices,i,"close"))
            expected = journal.status(path)
            self.assertEqual(current,expected)
            env = dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]/"src"))
            result = subprocess.run([sys.executable,"-c",
                "import json,sys;from quant_robot.ops.us_allocation_paper_journal import status;print(json.dumps(status(sys.argv[1]),sort_keys=True))",str(path)],
                env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout),expected)
            self.assertGreater(len(expected["fills"]),0)
            self.assertEqual(expected["real_forward_days"],0)

    def test_gap_cannot_resize_or_move_other_assets_frozen_budgets(self):
        manifest,prices=sample()
        with localcontext(kernel.CONTEXT):
            state=journal._Session(manifest)
            for i in range(20,24):
                state.apply(packet(manifest,prices,i,"open"))
                state.apply(packet(manifest,prices,i,"close"))
            orders=copy.deepcopy(state.account.pending["buy_orders"])
            gap=dict(prices,SPY="1000")
            state.apply(packet(manifest,gap,24,"open"))
            self.assertEqual(state.account.q["SPY"],0)
            self.assertTrue(any(r["reason"]=="frozen_budget_or_spendable_cash" for r in state.account.rejections))
            self.assertEqual(state.account.intents[-4:], [dict(o,intent_id=4+j) for j,o in enumerate(orders)])

    def test_late_unknown_future_or_wrong_phase_packet_does_not_append(self):
        manifest,prices=sample()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"account"
            journal.create(path,manifest)
            before=journal.status(path)
            base=packet(manifest,prices,20,"open")
            bad=[packet(manifest,prices,20,"close"),packet(manifest,prices,21,"open")]
            late=copy.deepcopy(base);late["received_at"]=(datetime.fromisoformat(late["received_at"])+timedelta(minutes=6)).isoformat();bad.append(late)
            unknown=copy.deepcopy(base);unknown["execution"]["SPY"]["suspended"]=None;bad.append(unknown)
            future=copy.deepcopy(base);future["prices"]["SPY"]["close"]="11";bad.append(future)
            effective=copy.deepcopy(base);effective["effective_at"]=effective["received_at"];bad.append(effective)
            for item in bad:
                with self.assertRaises(ValueError):journal.advance(path,item)
                self.assertEqual(journal.status(path),before)
            journal.advance(path,base)
            with self.assertRaises(ValueError):journal.advance(path,base)
            self.assertEqual(journal.status(path)["recorded_events"],1)

    def test_changed_or_missing_prior_event_cannot_restore(self):
        manifest,prices=sample()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"account"
            journal.create(path,manifest)
            journal.advance(path,packet(manifest,prices,20,"open"))
            event=path/"event_000000.json"
            text=event.read_text()
            event.write_text(text.replace('"open":"10"','"open":"11"'))
            with self.assertRaises(ValueError):journal.status(path)
            event.write_text(text)
            event.rename(path/"event_000001.json")
            with self.assertRaises(ValueError):journal.status(path)

    def test_actual_source_or_real_dates_cannot_activate(self):
        manifest,_=sample()
        for updated in (dict(manifest,evidence_kind="forward"),dict(manifest,constructed_from_market_data=True),
                        dict(manifest,initial_cash="10000.00"),dict(manifest,minimum_commission="0.35")):
            with self.assertRaises(ValueError):journal._Session(updated)
        changed=copy.deepcopy(manifest);changed["schedule"][0]["date"]="2026-01-03"
        with self.assertRaises(ValueError):journal._Session(changed)

    def test_changed_accounting_code_binding_blocks_even_empty_account(self):
        manifest,_=sample()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"account"
            journal.create(path,manifest)
            with patch.object(journal,"_runtime",return_value={}):
                with self.assertRaises(ValueError):journal.status(path)

    def test_deleted_committed_tail_and_incomplete_head_never_revert_state(self):
        manifest,prices=sample()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"account"
            journal.create(path,manifest)
            journal.advance(path,packet(manifest,prices,20,"open"))
            event=path/"event_000000.json"
            raw=event.read_bytes()
            event.unlink()
            with self.assertRaises(ValueError):journal.status(path)
            event.write_bytes(raw)
            self.assertEqual(journal.status(path)["recorded_events"],1)
            (path/"head.next").write_text('{}')
            with self.assertRaises(ValueError):journal.status(path)


if __name__ == "__main__":
    unittest.main()
