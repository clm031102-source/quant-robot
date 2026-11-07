import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D, Inexact, getcontext, setcontext
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.ops import us_low_unit_model_journal as m
from quant_robot.research import us_low_unit_allocation as core
from quant_robot.research import us_passive_drift_allocation as drift
from tests.unit.test_us_low_unit_allocation import fixture


def inputs(*, split=True, end="2001-05-31", last=None, trim=0):
    f = fixture(split=split, end=end)
    f["days"] = f["days"][trim:]
    schedule = [dict(date=r["date"], open_at=r["date"]+"T14:30:00+00:00",
                     close_at=r["date"]+"T21:00:00+00:00") for r in f["days"]]
    last = last or schedule[-2]["date"]
    warmup = [dict(date=r["date"], prices={a:{k:r["prices"][a][k] for k in ("close", "volume")}
                                             for a in m.ASSETS}, capacity_volume=r["capacity_volume"])
              for r in f["days"][:20]]
    manifest = dict(schema=m.SCHEMA, evidence_kind="artificial", constructed_from_market_data=False,
        assets=list(m.ASSETS), currency="USD", initial_cash_each="1000.00", scenarios=list(m.SCENARIOS),
        schedule=schedule, warmup=warmup, warmup_received_at=schedule[19]["date"]+"T22:00:00+00:00",
        activated_at=schedule[19]["date"]+"T22:01:00+00:00",
        first_decision_date=next(schedule[i]["date"] for i in range(20, len(schedule)-1)
                                 if schedule[i]["date"][:7] != schedule[i+1]["date"][:7]),
        last_observation_date=last, observation_sessions=[s["date"] for s in schedule].index(last)-19,
        allowed_splits=[a for a in f["splits"] if a["effective_date"] <= last])
    return f, manifest


def event(f, manifest, i):
    row = f["days"][i]
    return dict(schema="artificial_low_unit_completed_session_v1", evidence_kind="artificial",
        constructed_from_market_data=False, date=row["date"], session_close_at=manifest["schedule"][i]["close_at"],
        source_received_at=row["date"]+"T22:00:00+00:00", prices=copy.deepcopy(row["prices"]),
        capacity_volume=copy.deepcopy(row["capacity_volume"]), execution=copy.deepcopy(row["execution"]),
        action_snapshot_checked=True, capital_gains=[],
        dividends=[copy.deepcopy(x) for x in f["dividends"] if x["ex_date"] == row["date"]],
        splits=[copy.deepcopy(x) for x in manifest["allowed_splits"] if x["effective_date"] == row["date"]])


def stamp(f, i): return f["days"][i]["date"]+"T22:01:00+00:00"


def strip_labels(value):
    return {k:v for k,v in value.items() if k not in
            ("model_only", "execution_certified", "source_received_at", "modeled_open_at", "clock_kind")}


class FourModelJournalTests(unittest.TestCase):
    def test_explicit_initial_configuration_is_created_once_and_never_replayed(self):
        f, manifest = inputs(split=False, trim=5)
        manifest["startup_mode"] = "once_after_complete_warmup"
        self.assertEqual(manifest["warmup"][-1]["date"], "2001-02-02")
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/"journal"; created = m.create(path, manifest)
            self.assertEqual(created["status"], "initialized_unique_entry_pending")
            for s in created["accounts"].values():
                e = s["ledger"]["monthly_events"][0]
                self.assertEqual(e["decision_index"], 19)
                self.assertEqual(e["market_asof"], "2001-02-02T21:00:00+00:00")
                self.assertEqual(e["decision_recorded_at"], manifest["activated_at"])
                self.assertNotEqual(e["decision_recorded_at"], e["market_asof"])
                self.assertEqual((e["sell_index"], e["plan_index"], e["buy_index"]), (20, 22, 23))
            with patch.object(core._Account, "decision", side_effect=AssertionError("duplicate initial decision")):
                self.assertEqual(m.status(path), created)
            for i in range(20, 24): m.append(path, event(f, manifest, i), recorded_at=stamp(f, i))
            saved = m.status(path)
            for s in saved["accounts"].values():
                self.assertEqual(len(s["ledger"]["monthly_events"]), 1)
                self.assertEqual({x["date"] for x in s["ledger"]["fills"]}, {"2001-02-08"})
                self.assertEqual(len(s["ledger"]["fills"]), 4)
                self.assertIsNone(s["ledger"]["pending"])
        _, overlap = inputs(split=False)
        overlap["startup_mode"] = "once_after_complete_warmup"
        with TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, "overlaps_normal_month_end"):
            m.create(Path(tmp)/"rejected", overlap)

    def test_four_incremental_prefixes_match_frozen_artificial_accounts(self):
        f, manifest = inputs()
        f["dividends"] = [dict(id="invented_EFA", symbol="EFA", ex_date="2001-02-08", amount_per_share="2")]
        for row in f["days"]:
            if row["date"] >= "2001-02-20":
                for k in ("open", "high", "low", "close"):
                    if row["prices"]["SPYM"][k] is not None: row["prices"]["SPYM"][k] = "120"
        expected = {name:(drift.run_artificial(f, name.split("_")[1]) if name.startswith("drift")
                    else core.run_artificial(f, "new_"+name.split("_")[1])) for name in m.SCENARIOS}
        with m.localcontext(core.CONTEXT):
            state = m._State(manifest)
            for i in range(20, len(f["days"])-1):
                state.apply(event(f, manifest, i), stamp(f, i))
                if f["days"][i]["date"] in ("2001-02-01", "2001-02-05", "2001-02-06", "2001-02-14", "2001-04-02"):
                    before = state.snapshot()
                    state = m._unpack_state(manifest, json.loads(json.dumps(m._pack_state(state))))
                    self.assertEqual(before, state.snapshot())
                if f["days"][i]["date"] <= f["first_decision_date"]: continue
                for name, account in state.accounts.items():
                    ref = next(d for d in expected[name]["days"] if d["index"] == i)
                    self.assertEqual(core.serial(account.balances()), ref["after"])
                    self.assertEqual(core.serial(account.previous), ref["NAV"])
                    self.assertEqual(core.serial(account.peak), ref["peak"])
                    self.assertEqual(account.paused, ref["paused"])
                    self.assertEqual(account.cooldown, ref["cooldown"])
                    self.assertEqual([strip_labels(x) for x in core.serial(account.fills)],
                                     [x for x in expected[name]["fills"] if x["index"] <= i])
            snap = state.snapshot()
            self.assertGreater(snap["accounts"]["drift_primary"]["ledger"]["total_CIL_cost"], "0")
            self.assertNotEqual(snap["accounts"]["monthly_primary"]["ledger"]["fills"],
                                snap["accounts"]["drift_primary"]["ledger"]["fills"])
            self.assertEqual(snap["status"], "window_finished_no_liquidation")

    def test_pending_alias_survives_D1_split_D3_D4_restarts(self):
        f, manifest = inputs()
        f["splits"][0]["effective_date"] = "2001-02-02"
        manifest["allowed_splits"] = copy.deepcopy(f["splits"])
        for row in f["days"]:
            if row["date"] >= "2001-02-02":
                for k in ("open", "high", "low", "close"):
                    if row["prices"]["GLDM"][k] is not None: row["prices"]["GLDM"][k] = "140"
        with m.localcontext(core.CONTEXT), TemporaryDirectory() as tmp:
            path = Path(tmp)/"journal"; m.create(path, manifest)
            for i in range(20, 27):
                m.append(path, event(f, manifest, i), recorded_at=stamp(f, i))
                state, _ = m._restore(path)
                for account in state.accounts.values():
                    if account.pending is not None:
                        self.assertIs(account.pending, account.events[-1])
                        if f["days"][i]["date"] >= "2001-02-02":
                            self.assertEqual(account.events[-1]["targets"]["GLDM"], 1)
                if f["days"][i]["date"] == "2001-02-05":
                    self.assertTrue(all(a.pending["buy_orders"] for a in state.accounts.values()))
            snap = m.status(path)
            self.assertTrue(all(a["ledger"]["pending"] is None for a in snap["accounts"].values()))
            self.assertTrue(all(a["ledger"]["balances"]["quantities"]["GLDM"] == 1 for a in snap["accounts"].values()))

    def test_restore_does_not_run_old_decisions_or_steps(self):
        f, manifest = inputs(split=False)
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/"journal"; m.create(path, manifest)
            for i in range(20, 23): m.append(path, event(f, manifest, i), recorded_at=stamp(f, i))
            with patch.object(m, "_step", side_effect=AssertionError("old step replay")), \
                 patch.object(core._Account, "decision", side_effect=AssertionError("old decision replay")), \
                 patch.object(core._Account, "run", side_effect=AssertionError("historical run")):
                snap = m.status(path)
                self.assertEqual(snap["artificial_model_days"], 3)
            with patch.object(m, "_step", wraps=m._step) as step:
                m.append(path, event(f, manifest, 23), recorded_at=stamp(f, 23))
                self.assertEqual(step.call_count, 4)

    def test_any_account_failure_preserves_all_four_prior_balances(self):
        f, manifest = inputs(split=False)
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/"journal"; initial = m.create(path, manifest)
            original = m._step
            def fail_second(a, *args):
                if a.minimum == "2.50": raise ValueError("invented_second_account_failure")
                original(a, *args)
            with patch.object(m, "_step", side_effect=fail_second):
                blocked = m.append(path, event(f, manifest, 20), recorded_at=stamp(f, 20))
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["accounts"], initial["accounts"])
            self.assertEqual(blocked["artificial_model_days"], 0)
            self.assertEqual(m.status(path), blocked)
            with self.assertRaisesRegex(ValueError, "blocked_requires_review"):
                m.append(path, event(f, manifest, 20), recorded_at=stamp(f, 20))

    def test_missing_prices_actions_dates_and_late_clock_block_without_partial_advance(self):
        f, manifest = inputs(split=False)
        changes = [lambda e:e["prices"]["SPYM"].pop("close"),
                   lambda e:e.update(date=f["days"][21]["date"]),
                   lambda e:e.update(action_snapshot_checked=False),
                   lambda e:e.update(source_received_at=manifest["schedule"][21]["open_at"]),
                   lambda e:e.update(source_received_at=e["date"]+"T21:14:59+00:00"),
                   lambda e:e.update(session_close_at=e["date"]+"T20:59:59+00:00"),
                   lambda e:e.update(capital_gains=[{"unknown":True}]),
                   lambda e:e["execution"].pop("IEF")]
        for n, change in enumerate(changes):
            with self.subTest(case=n), TemporaryDirectory() as tmp:
                path = Path(tmp)/"journal"; initial = m.create(path, manifest)
                e = event(f, manifest, 20); change(e)
                blocked = m.append(path, e, recorded_at=stamp(f, 20))
                self.assertEqual(blocked["status"], "blocked")
                self.assertEqual(blocked["accounts"], initial["accounts"])

    def test_risk_recovery_and_continuous_peak_survive_state_restore(self):
        f, manifest = inputs(split=False)
        for row in f["days"]:
            if row["date"] >= "2001-02-08":
                for prices in row["prices"].values():
                    for k in ("open", "high", "low", "close"):
                        if prices[k] is not None: prices[k] = "30"
        with m.localcontext(core.CONTEXT):
            state = m._State(manifest)
            for i in range(20, [r["date"] for r in f["days"]].index("2001-03-07")+1):
                state.apply(event(f, manifest, i), stamp(f, i))
                state = m._unpack_state(manifest, m._pack_state(state))
                day = f["days"][i]["date"]
                for a in state.accounts.values():
                    if day == "2001-02-16": self.assertEqual(a.cooldown, 5)
                    if day == "2001-02-19": self.assertFalse(a.paused)
                    if day == "2001-03-06":
                        self.assertTrue(a.paused)
                        self.assertEqual(a.peak, 1000)
                        self.assertGreater(a.previous_dd, D(".4"))

    def test_twenty_sessions_stop_with_holdings_and_without_terminal_profit(self):
        f, manifest = inputs(last="2001-02-23")
        self.assertEqual(manifest["observation_sessions"], 20)
        with m.localcontext(core.CONTEXT):
            state = m._State(manifest)
            for i in range(20, 40): state.apply(event(f, manifest, i), stamp(f, i))
            snap = state.snapshot()
            self.assertEqual(snap["status"], "window_finished_no_liquidation")
            self.assertEqual(snap["model_forward_days"], 0)
            self.assertEqual(snap["strict_forward_days"], 0)
            self.assertFalse(snap["qualified"])
            for account in snap["accounts"].values():
                self.assertTrue(any(account["ledger"]["balances"]["quantities"].values()))
                self.assertFalse(any(x["phase"] == "terminal" for x in account["ledger"]["fills"]))
                self.assertNotIn("terminal_profit", account)
                self.assertTrue(all(x["model_only"] and not x["execution_certified"] for x in account["ledger"]["fills"]))
            with self.assertRaisesRegex(ValueError, "observation_window_finished"):
                state.apply(event(f, manifest, 40), stamp(f, 40))

    def test_torn_commit_and_modified_chain_require_review(self):
        f, manifest = inputs(split=False)
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/"torn"; m.create(path, manifest)
            before = (path/"head.json").read_bytes()
            with patch.object(m.os, "replace", side_effect=OSError("injected publish failure")):
                with self.assertRaises(OSError): m.append(path, event(f, manifest, 20), recorded_at=stamp(f, 20))
            self.assertEqual((path/"head.json").read_bytes(), before)
            with self.assertRaisesRegex(ValueError, "unfinished_writer"):
                m.status(path)
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/"modified"; m.create(path, manifest)
            m.append(path, event(f, manifest, 20), recorded_at=stamp(f, 20))
            record = path/"record_000001.json"
            record.write_bytes(record.read_bytes()+b" ")
            with self.assertRaisesRegex(ValueError, "head_state_changed"):
                m.status(path)

    def test_identity_codec_and_context_are_closed(self):
        f, manifest = inputs(split=False)
        original = copy.deepcopy(manifest)
        with TemporaryDirectory() as tmp:
            for n, mutate in enumerate([lambda x:x.update(evidence_kind="conditional_forward_model"),
                                       lambda x:x.update(constructed_from_market_data=True),
                                       lambda x:x.update(assets=["SPY", "EFA", "IEF", "GLD"]),
                                       lambda x:x.update(initial_cash_each="4000.00")]):
                wrong = copy.deepcopy(manifest); mutate(wrong)
                with self.assertRaises(ValueError): m.create(Path(tmp)/str(n), wrong)
            saved = getcontext().copy()
            try:
                getcontext().prec = 7; getcontext().traps[Inexact] = True; getcontext().clear_flags()
                before = getcontext().copy()
                m.create(Path(tmp)/"valid", manifest)
                m.append(Path(tmp)/"valid", event(f, manifest, 20), recorded_at=stamp(f, 20))
                self.assertEqual(getcontext().prec, before.prec)
                self.assertEqual(getcontext().flags, before.flags)
                self.assertEqual(getcontext().traps, before.traps)
            finally: setcontext(saved)
        self.assertEqual(manifest, original)
        for bad in ({"class":"anything"}, {"decimal":"NaN"}, {"map":[[1,0],[1,2]]}):
            with self.assertRaises(ValueError): m._decode(bad)

    def test_separate_CLI_processes_restore_one_shared_day(self):
        f, manifest = inputs(split=False)
        script = Path(__file__).resolve().parents[2]/"scripts/run_us_low_unit_model_journal.py"
        with TemporaryDirectory() as tmp:
            root = Path(tmp); target = root/"journal"
            (root/"manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (root/"event.json").write_text(json.dumps(event(f, manifest, 20)), encoding="utf-8")
            def call(*args):
                result = subprocess.run([sys.executable, "-P", str(script), *args, "--directory", str(target)],
                                        capture_output=True, text=True, check=True, timeout=30)
                return json.loads(result.stdout)
            self.assertEqual(call("create", "--manifest", str(root/"manifest.json"))["artificial_model_days"], 0)
            advanced = call("append", "--event", str(root/"event.json"), "--recorded-at", stamp(f, 20))
            self.assertEqual(advanced["artificial_model_days"], 1)
            self.assertEqual(call("status"), advanced)


class AdmittedArtificialBundle:
    """Invented prices/authority in a temporary directory, never actual sources."""
    def __init__(self, root):
        self.root = Path(root).resolve(); self.journal = self.root/"journal"; self.serial = 0
        self.calendar_ref = self.save("calendar", {"artificial_calendar_fixture":True})
        self.definition_ref = self.save("source_definition", {"artificial_source_definition":True})
        dates = m._fixed_dates()
        self.schedule = dict(source_ref=self.calendar_ref, sessions=[])
        for day in dates:
            def clock(t):
                return datetime.fromisoformat(day+"T"+t).replace(tzinfo=m.source.NY).astimezone(timezone.utc).isoformat()
            self.schedule["sessions"].append(dict(date=day, open_at=clock("09:30:00"),
                close_at=clock("13:00:00" if day == "2026-11-27" else "16:00:00")))
        self.authorities = {k:dict(kind=v,definition_ref=self.definition_ref) for k,v in
                            (("daily","provider_daily_completed"),("actions","corporate_action_coverage"))}
        self.manifest = dict(schema="us_low_unit_four_model_manifest_v1", evidence_kind=m.REAL_EVIDENCE,
            production_directory=str(self.root), assets=list(m.ASSETS), scenarios=list(m.SCENARIOS), currency="USD",
            initial_cash_each="1000.00", startup_mode="once_after_complete_warmup", schedule=self.schedule,
            authorities=self.authorities, warmup_dates=dates[:20], operation_dates=dates[20:40],
            first_decision_date="2026-11-30", last_observation_date="2026-12-07", observation_sessions=20,
            allowed_splits=[])
        self.manifest_ref = self.save("manifest",self.manifest)
        runtime=dict(schema="us_low_unit_four_model_runtime_v1",python=list(sys.version_info[:3]),
            files=[m._reference(Path(sys.modules[name].__file__)) for name in m._runtime()["files"]])
        self.runtime_ref=self.save("runtime",runtime)
        review=dict(status="accepted",stage="operations",manifest_sha256=self.manifest_ref["sha256"],
                    runtime_sha256=self.runtime_ref["sha256"])
        self.root_review=self.save("root_review",dict(review,reviewer="root"))
        self.manager_review=self.save("manager_review",dict(review,reviewer="quant_manager_72h"))
        self.release=dict(schema="us_low_unit_four_model_release_v1",status="accepted",
            manifest_sha256=self.manifest_ref["sha256"],runtime_sha256=self.runtime_ref["sha256"],
            root_review_sha256=self.root_review["sha256"],manager_review_sha256=self.manager_review["sha256"],
            production_directory=str(self.root),not_before="2026-11-07T00:00:00+00:00",
            expires_at="2026-12-08T14:30:00+00:00")
        self.release_ref=self.save("release",self.release)

    def save(self, name, value):
        self.serial+=1; path=self.root/f"{self.serial}_{name}.json"; m._save(path,value)
        return m._reference(path)

    def context(self):
        return m.admitted_context(self.manifest_ref,self.runtime_ref,self.release_ref,self.root_review,self.manager_review)

    def normalized(self, day=None, prior=None, *, mutate=None):
        warmup=day is None; purpose="warmup" if warmup else "daily_model"
        target="2026-11-09" if warmup else day
        session=next(s for s in self.schedule["sessions"] if s["date"]==target)
        received="2026-11-07T02:00:00+00:00" if warmup else (
            m._instant(session["close_at"])+timedelta(minutes=16)).isoformat()
        dates=self.manifest["warmup_dates"] if warmup else [day]
        refs={a:self.save("opaque_"+a,{"artificial_symbol":a}) for a in m.ASSETS}
        batch_ref=self.save("batch",refs)
        packet=dict(schema="us_allocation_source_evidence_v1",purpose=purpose,symbols=list(m.ASSETS),
            session_date=target,calendar_ref=self.calendar_ref,source_ref=batch_ref,received_at=received,records={})
        if warmup:packet["warmup_dates"]=dates
        else:packet.update(previous_observed_session_date=prior["date"],
            previous_committed_decision_at=prior["committed_at"],previous_committed_decision_ref=prior["committed_ref"])
        for a in m.ASSETS:
            actions=dict(authority="actions",definition_ref=self.definition_ref,coverage_complete=True,
                units="USD_per_share",splits_absent=True,capital_gains_absent=True,coverage_dates=dates,
                coverage_basis="provider_query_snapshot_only",split_ratio_unit="new_shares_per_old_share")
            row=dict(currency="USD",timezone="America/New_York",source_ref=refs[a],complete=True,
                received_at=received,observation_kind="completed_daily",source_authority="daily",
                definition_ref=self.definition_ref,corporate_actions=actions,
                execution=dict(suspended=None,buy_blocked=None,sell_blocked=None))
            if warmup:row.update(dates=dates,session_complete=[True]*20)
            else:row.update(provider_bar_interval="1d",provider_trading_date=day,
                provider_bucket_timestamp=str(int(m._instant(session["open_at"]).timestamp())),
                session_open_at=session["open_at"],session_close_at=session["close_at"],
                effective_at=None,provider_available_at=None,finality="provider_snapshot_finality_unknown",
                units=dict(prices="USD_per_share",volume="shares",dividend="USD_per_share"))
            packet["records"][a]=row
        assessment=m.source.assess_source_metadata(packet,self.schedule,authorities=self.authorities,assets=m.ASSETS)
        assert assessment["requirements_met"],assessment
        marker=self.save("marker",dict(release_sha256=self.release_ref["sha256"],
            source_packet_sha256=m.source._digest(packet),purpose=purpose))
        names=("close","volume") if warmup else ("open","high","low","close","volume")
        values=dict(schema="us_low_unit_source_normalized_packet_v1",purpose=purpose,evidence_kind=m.REAL_EVIDENCE,
            assets=list(m.ASSETS),qualified=False,real_forward=0,model_accounts_advanced=0,journal_admission_granted=False,
            source_metadata=packet,assessment=assessment,source_refs=refs,numeric_decode_marker=marker,
            context_identity=dict(purpose=purpose,packet_sha256=m.source._digest(packet),
                source_refs_sha256=m.source._digest(refs),release_sha256=self.release_ref["sha256"],
                evidence_kind=m.REAL_EVIDENCE,test_values=False),splits=[],capital_gains=[],dividends=[],
            capacity_basis="nominal_provider_volume_no_split_in_query",
            days=[dict(date=d,prices={a:{k:"1000000" if k=="volume" else "70" for k in names} for a in m.ASSETS},
                       capacity_volume=dict.fromkeys(m.ASSETS,"1000000")) for d in dates])
        if mutate:mutate(values)
        return self.save("normalization",values)

    def initialize(self, context):
        ref=self.normalized()
        with patch.object(m,"_utcnow",return_value=m._instant("2026-11-07T03:00:00+00:00")):
            return m.create_admitted(self.journal,ref,context=context)


class AdmittedJournalTests(unittest.TestCase):
    def test_fixed_future_calendar_internal_clocks_and_no_replay(self):
        with TemporaryDirectory() as tmp,patch.object(m,"PRODUCTION_DIRECTORY",Path(tmp)):
            b=AdmittedArtificialBundle(tmp);c=b.context();snap=b.initialize(c)
            self.assertEqual(snap["date"],"2026-11-06");self.assertEqual(snap["model_forward_days"],0)
            self.assertEqual(snap["committed_ref"]["path"],str(b.journal/"definition.json"))
            for row in snap["accounts"].values():
                e=row["ledger"]["pending"]
                self.assertEqual(e["market_asof"],"2026-11-06T21:00:00+00:00")
                self.assertEqual(e["decision_recorded_at"],"2026-11-07T03:00:00+00:00")
                self.assertEqual((e["sell_index"],e["plan_index"],e["buy_index"]),(20,22,23))
            for day in b.manifest["operation_dates"][:4]:
                ref=b.normalized(day,snap)
                with patch.object(m,"_utcnow",return_value=m._instant(day+"T21:17:00+00:00")):
                    snap=m.append_normalized(b.journal,ref,context=c)
            self.assertEqual(snap["date"],"2026-11-12");self.assertEqual(snap["model_forward_days"],4)
            for account in snap["accounts"].values():
                self.assertEqual(len(account["ledger"]["fills"]),4)
                self.assertTrue(all(x["model_only"] and not x["execution_certified"] for x in account["ledger"]["fills"]))
                self.assertEqual(len(account["ledger"]["unknown_execution_constraints"]),8)
            self.assertEqual(snap["strict_forward_days"],0);self.assertFalse(snap["qualified"])
            with patch.object(m,"_utcnow",return_value=m._instant("2027-01-01T00:00:00+00:00")), \
                    patch.object(m,"_step",side_effect=AssertionError("old steps")), \
                    patch.object(core._Account,"decision",side_effect=AssertionError("old decision")):
                self.assertEqual(m.status_admitted(b.journal,context=c),snap)
                with self.assertRaisesRegex(ValueError,"release_time"):
                    m.append_normalized(b.journal,ref,context=c)
            with self.assertRaisesRegex(ValueError,"admitted_status_required"):m.status(b.journal)

    def test_exact_authority_bindings_directory_and_initialization_time(self):
        with TemporaryDirectory() as tmp,patch.object(m,"PRODUCTION_DIRECTORY",Path(tmp)):
            b=AdmittedArtificialBundle(tmp);c=b.context();warmup=b.normalized()
            with patch.object(m,"_utcnow",return_value=m._instant("2026-11-09T14:30:00+00:00")):
                with self.assertRaisesRegex(ValueError,"startup_before_first_open"):
                    m.create_admitted(b.journal,warmup,context=c)
            self.assertFalse(b.journal.exists())
            with self.assertRaisesRegex(ValueError,"fixed_journal_directory"):
                m.status_admitted(Path(tmp)/"other",context=c)
            for key, value in (("root_review_sha256","0"*64),("runtime_sha256","0"*64),
                               ("expires_at","2026-12-09T14:30:00+00:00")):
                wrong=b.save("wrong_release",dict(b.release,**{key:value}))
                with self.assertRaises(ValueError):
                    m.admitted_context(b.manifest_ref,b.runtime_ref,wrong,b.root_review,b.manager_review)
            Path(b.release_ref["path"]).write_bytes(m._bound(b.release_ref)+b" ")
            with self.assertRaisesRegex(ValueError,"bound_file_changed"):m.status_admitted(b.journal,context=c)

    def test_marker_identity_unknown_actions_and_forged_provider_clock_reject(self):
        mutations=[lambda n:n["context_identity"].update(test_values=True),
                   lambda n:n["context_identity"].update(release_sha256="0"*64),
                   lambda n:n.update(capital_gains=[{"unreviewed":True}]),
                   lambda n:n["source_metadata"]["records"]["GLDM"].update(effective_at="2026-11-09T14:30:00+00:00")]
        for mutation in mutations:
            with self.subTest(mutation=mutation),TemporaryDirectory() as tmp,patch.object(m,"PRODUCTION_DIRECTORY",Path(tmp)):
                b=AdmittedArtificialBundle(tmp);c=b.context();snap=b.initialize(c)
                ref=b.normalized("2026-11-09",snap,mutate=mutation)
                before=(b.journal/"head.json").read_bytes()
                with patch.object(m,"_utcnow",return_value=m._instant("2026-11-09T21:17:00+00:00")):
                    with self.assertRaises(ValueError):m.append_normalized(b.journal,ref,context=c)
                self.assertEqual((b.journal/"head.json").read_bytes(),before)

    def test_duplicate_prior_head_and_late_arrival_never_create_an_extra_day(self):
        with TemporaryDirectory() as tmp,patch.object(m,"PRODUCTION_DIRECTORY",Path(tmp)):
            b=AdmittedArtificialBundle(tmp);c=b.context();snap=b.initialize(c)
            ref=b.normalized("2026-11-09",snap)
            with patch.object(m,"_utcnow",return_value=m._instant("2026-11-09T21:17:00+00:00")):
                first=m.append_normalized(b.journal,ref,context=c)
                with self.assertRaisesRegex(ValueError,"actual_prior_committed_state"):
                    m.append_normalized(b.journal,ref,context=c)
            self.assertEqual(m.status_admitted(b.journal,context=c),first)
            ref=b.normalized("2026-11-10",first)
            with patch.object(m,"_utcnow",return_value=m._instant("2026-11-11T14:30:00+00:00")):
                with self.assertRaisesRegex(ValueError,"commit_before_next_open"):
                    m.append_normalized(b.journal,ref,context=c)
            self.assertEqual(m.status_admitted(b.journal,context=c),first)

    def test_normalization_marker_cannot_be_rebound_to_another_packet(self):
        with TemporaryDirectory() as tmp,patch.object(m,"PRODUCTION_DIRECTORY",Path(tmp)):
            b=AdmittedArtificialBundle(tmp);c=b.context();snap=b.initialize(c)
            ref=b.normalized("2026-11-09",snap)
            normalized=json.loads(m._bound(ref));marker=json.loads(m._bound(normalized["numeric_decode_marker"]))
            marker["source_packet_sha256"]="0"*64
            normalized["numeric_decode_marker"]=b.save("wrong_marker",marker)
            altered=b.save("wrong_normalization",normalized)
            before=(b.journal/"head.json").read_bytes()
            with patch.object(m,"_utcnow",return_value=m._instant("2026-11-09T21:17:00+00:00")):
                with self.assertRaisesRegex(ValueError,"durable_numeric_marker_identity"):
                    m.append_normalized(b.journal,altered,context=c)
            self.assertEqual((b.journal/"head.json").read_bytes(),before)

    def test_twenty_real_identity_model_days_stop_without_liquidation_using_only_invented_values(self):
        with TemporaryDirectory() as tmp,patch.object(m,"PRODUCTION_DIRECTORY",Path(tmp)):
            b=AdmittedArtificialBundle(tmp);c=b.context();snap=b.initialize(c)
            for day in b.manifest["operation_dates"]:
                ref=b.normalized(day,snap)
                session=next(s for s in b.schedule["sessions"] if s["date"]==day)
                with patch.object(m,"_utcnow",return_value=m._instant(session["close_at"])+timedelta(minutes=17)):
                    snap=m.append_normalized(b.journal,ref,context=c)
            self.assertEqual(snap["status"],"window_finished_no_liquidation")
            self.assertEqual(snap["model_forward_days"],20);self.assertEqual(snap["strict_forward_days"],0)
            for row in snap["accounts"].values():
                self.assertTrue(any(row["ledger"]["balances"]["quantities"].values()))
                self.assertFalse(any(f["phase"]=="terminal" for f in row["ledger"]["fills"]))
            self.assertEqual(snap["committed_ref"]["path"],str(b.journal/"record_000020.json"))


if __name__ == "__main__": unittest.main()
