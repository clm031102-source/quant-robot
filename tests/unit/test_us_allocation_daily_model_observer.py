"""Invented provider records, clocks and prices; no external data or release."""
import copy
import hashlib
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal as D, getcontext
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.ops import us_allocation_daily_model_observer as m


def invented_manifest(role="primary"):
    ref=dict(path="invented-authority",sha256="a"*64,bytes=1)
    days=[]; day=date(2000,1,3)
    while day<=date(2000,4,17):
        if day.weekday()<5:
            days.append(dict(date=day.isoformat(),open_at=datetime.combine(day,time(9,30),m.source.NY).astimezone(timezone.utc).isoformat(),
                             close_at=datetime.combine(day,time(16),m.source.NY).astimezone(timezone.utc).isoformat()))
        day+=timedelta(days=1)
    authorities={kind:dict(kind=kind,definition_ref=copy.deepcopy(ref)) for kind in
                 ("provider_daily_completed","corporate_action_coverage")}
    return dict(schema=m.SCHEMA,evidence_kind="artificial",constructed_from_market_data=False,
        method_sha256=m.METHOD_SHA,role=role,initial_cash="1000.00",assets=list(m.ASSETS),
        first_decision_date="2000-01-31",schedule=dict(source_ref=ref,sessions=days),authorities=authorities)


def inputs(manifest, index, purpose, saved):
    sessions=manifest["schedule"]["sessions"]; row=sessions[index]; dates=[r["date"] for r in sessions]
    previous=sessions[index-1]
    received=m._instant(previous["close_at"])+timedelta(minutes=10) if purpose=="warmup" else m._instant(row["close_at"])+timedelta(minutes=15)
    ref=copy.deepcopy(manifest["schedule"]["source_ref"])
    p=dict(schema="us_allocation_source_evidence_v1",purpose=purpose,symbols=list(m.ASSETS),session_date=row["date"],
        calendar_ref=ref,source_ref=copy.deepcopy(ref),received_at=received.isoformat(),records={},
        warmup_dates=dates[index-20:index],previous_observed_session_date=previous["date"],
        previous_committed_decision_ref=saved["committed_ref"],previous_committed_decision_at=saved["committed_at"])
    for s in m.ASSETS:
        p["records"][s]=dict(currency="USD",timezone="America/New_York",source_ref=copy.deepcopy(ref),
            source_authority="provider_daily_completed",definition_ref=copy.deepcopy(ref),complete=True,
            received_at=received.isoformat(),observation_kind="completed_daily",dates=dates[index-20:index],
            session_complete=[True]*20,effective_at=None,provider_available_at=None,
            execution=dict(suspended=None,buy_blocked=None,sell_blocked=None),provider_bar_interval="1d",
            provider_trading_date=row["date"],provider_bucket_timestamp=str(int(m._instant(row["open_at"]).timestamp())),
            finality="provider_snapshot_finality_unknown",session_open_at=row["open_at"],session_close_at=row["close_at"],
            units=dict(prices="USD_per_share",volume="shares",dividend="USD_per_share"),
            corporate_actions=dict(authority="corporate_action_coverage",definition_ref=copy.deepcopy(ref),
                coverage_complete=True,coverage_basis="provider_query_snapshot_only",units="USD_per_share",
                splits_absent=True,capital_gains_absent=True,coverage_dates=dates[index-20:index] if purpose=="warmup" else [row["date"]],
                split_ratio_unit="new_shares_per_old_share"))
    prices={s:dict(open="10",close="10",volume="100000") for s in m.ASSETS}
    payload=(dict(kind="warmup",days=[dict(date=d,prices={s:dict(close="10",volume="100000") for s in m.ASSETS}) for d in p["warmup_dates"]])
        if purpose=="warmup" else dict(kind="daily_model",date=row["date"],prices=prices,dividends=[]))
    return p,payload,(received+timedelta(seconds=1)).isoformat()


def initialized(directory, role="primary"):
    f=invented_manifest(role);ctx=m.artificial_context(f)
    clock=(m._instant(f["schedule"]["sessions"][19]["close_at"])+timedelta(minutes=5)).isoformat()
    saved=m.create(directory,f,context=ctx,injected_at=clock)
    p,v,at=inputs(f,20,"warmup",saved)
    saved=m.advance(directory,p,v,context=ctx,injected_at=at)
    return f,ctx,saved


def normalized_invented(f, packet):
    """Four invented raw responses through the real pure decoder; no I/O."""
    raws={};packet=copy.deepcopy(packet)
    dates=packet["warmup_dates"] if packet["purpose"]=="warmup" else [packet["session_date"]]
    for symbol in m.ASSETS:
        stamps=[int(datetime.combine(date.fromisoformat(d),time(9,30),m.source.NY).timestamp()) for d in dates]
        quote={k:[v]*len(dates) for k,v in dict(open="10",close="10",volume="100000",high="UNREAD",low="UNREAD").items()}
        row=dict(meta=dict(symbol=symbol,currency="USD",exchangeTimezoneName="America/New_York",instrumentType="ETF",dataGranularity="1d"),
                 timestamp=stamps,indicators=dict(quote=[quote]),events={})
        raw=json.dumps(dict(chart=dict(error=None,result=[row]))).encode();raws[symbol]=raw
        packet["records"][symbol]["source_ref"]=dict(path="invented/"+symbol,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    refs={s:packet["records"][s]["source_ref"] for s in m.ASSETS}
    ctx=m.source._SourceDecodeContext(packet["purpose"],m.source._digest(packet),m.source._digest(refs),"c"*64,"artificial_source_values",True)
    return m.source.normalize_yahoo_sources(raws,packet,f["schedule"],authorities=f["authorities"],context=ctx,
                                           before_numeric_decode=lambda:dict(artificial_marker=True))


class DailyModelObserverTests(unittest.TestCase):
    def test_waiting_and_warmup_are_not_forward_or_early_orders(self):
        with tempfile.TemporaryDirectory() as t:
            f=invented_manifest();ctx=m.artificial_context(f);root=Path(t)/"journal"
            at=(m._instant(f["schedule"]["sessions"][19]["close_at"])+timedelta(minutes=5)).isoformat()
            saved=m.create(root,f,context=ctx,injected_at=at)
            self.assertIsNone(saved["ledger"])
            p,v,at=inputs(f,20,"warmup",saved);v["days"][0]["prices"]["SPY"]["close"]="not_a_number"
            p["records"]["SPY"]["complete"]=False
            waiting=m.advance(root,p,v,context=ctx,injected_at=at)
            self.assertEqual(waiting["status"],"source_waiting");self.assertIsNone(waiting["ledger"])
            p,v,at=inputs(f,20,"warmup",waiting);at=(m._instant(at)+timedelta(seconds=1)).isoformat()
            saved=m.advance(root,p,v,context=ctx,injected_at=at)
            self.assertEqual(saved["ledger"]["balances"]["spendable_cash"],"1000.00")
            self.assertEqual(saved["ledger"]["fills"],[]);self.assertEqual(saved["ledger"]["monthly_events"],[])
            self.assertEqual(saved["model_forward_days"],0);self.assertEqual(saved["artificial_model_days"],0)

    def test_durable_D_D3_orders_gap_and_model_only_D4(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"journal";f,ctx,saved=initialized(root)
            for i in range(20,24):
                p,v,at=inputs(f,i,"daily_model",saved);saved=m.advance(root,p,v,context=ctx,injected_at=at)
            orders=copy.deepcopy(saved["ledger"]["pending"]["buy_orders"])
            p,v,at=inputs(f,24,"daily_model",saved);v["prices"]["SPY"]["open"]="1000"
            v["prices"]["GLD"]["volume"]="0"
            saved=m.advance(root,p,v,context=ctx,injected_at=at)
            self.assertEqual(saved["ledger"]["balances"]["quantities"]["SPY"],0)
            self.assertEqual([{k:v for k,v in x.items() if k!="intent_id"} for x in saved["ledger"]["intents"][-4:]],orders)
            self.assertTrue(all(x["model_only"] and not x["execution_certified"] for x in saved["ledger"]["fills"]))
            self.assertTrue(saved["ledger"]["unknown_execution_constraints"])
            self.assertEqual(saved["real_forward_days"],0);self.assertEqual(saved["model_forward_days"],0)
            self.assertEqual(saved["artificial_model_days"],5)
            self.assertEqual(saved,m.status(root,context=ctx))

    def test_late_missing_or_old_head_blocks_and_restart_never_refills(self):
        for kind in ("late","missing","head","unknown"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as t:
                root=Path(t)/"journal";f,ctx,saved=initialized(root)
                i=21 if kind=="missing" else 20
                p,v,at=inputs(f,i,"daily_model",saved)
                if kind=="late":at=f["schedule"]["sessions"][i+1]["open_at"]
                if kind=="head":p["previous_committed_decision_ref"]["sha256"]="b"*64
                if kind=="unknown":p["records"]["SPY"]["corporate_actions"]["splits_absent"]=None
                blocked=m.advance(root,p,v,context=ctx,injected_at=at)
                self.assertEqual(blocked["status"],"blocked_continuity_no_backfill")
                self.assertEqual(blocked,m.status(root,context=ctx));self.assertEqual(blocked["ledger"]["fills"],[])
                with self.assertRaises(ValueError):m.advance(root,p,v,context=ctx,injected_at=at)

    def test_current_ex_entitlement_is_conditionally_rebuilt_past_ex_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"journal";f,ctx,saved=initialized(root)
            for i in range(20,25):
                p,v,at=inputs(f,i,"daily_model",saved);saved=m.advance(root,p,v,context=ctx,injected_at=at)
            q=saved["ledger"]["balances"]["quantities"]["SPY"]
            p,v,at=inputs(f,25,"daily_model",saved)
            v["dividends"]=[dict(id="invented_cash",symbol="SPY",ex_date=v["date"],amount_per_share=".10")]
            saved=m.advance(root,p,v,context=ctx,injected_at=at)
            action=next(a for a in saved["ledger"]["actions"] if a["kind"]=="ex_entitlement")
            self.assertEqual(D(action["item"]["amount"]),D(q)*D(".07"))
            self.assertFalse(action["entitlement_known_before_open"]);self.assertEqual(action["source_received_at"],p["received_at"])
            before=copy.deepcopy(saved["ledger"])
            p,v,at=inputs(f,26,"daily_model",saved)
            v["dividends"]=[dict(id="late_old",symbol="SPY",ex_date=f["schedule"]["sessions"][25]["date"],amount_per_share=".10")]
            blocked=m.advance(root,p,v,context=ctx,injected_at=at)
            self.assertEqual(blocked["status"],"blocked_continuity_no_backfill")
            self.assertEqual(blocked["ledger"],before);self.assertEqual(blocked,m.status(root,context=ctx))

    def test_context_flags_tail_and_identity_cannot_be_silently_changed(self):
        before=m.kernel.context_record(getcontext())
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"journal";f,ctx,saved=initialized(root)
            p,v,at=inputs(f,20,"daily_model",saved);v["prices"]["SPY"]["open"]="bad"
            blocked=m.advance(root,p,v,context=ctx,injected_at=at)
            self.assertEqual(blocked["status"],"blocked_continuity_no_backfill")
            self.assertEqual(m.kernel.context_record(getcontext()),before)
            tail=root/"input_000002.json";raw=tail.read_bytes();tail.unlink()
            with self.assertRaises(ValueError):m.status(root,context=ctx)
            tail.write_bytes(raw);self.assertEqual(blocked,m.status(root,context=ctx))
            bad=copy.deepcopy(f);bad["evidence_kind"]="conditional_forward_model"
            with self.assertRaises(ValueError):m.artificial_context(bad)
            with self.assertRaises(ValueError):m._Context("conditional_forward_model","x","y",(),None,None,None,None,True)

    def test_normalized_result_routes_without_real_evidence_relabel(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"journal";f,ctx,saved=initialized(root)
            p,v,at=inputs(f,20,"daily_model",saved)
            normalized=dict(schema="us_source_normalized_packet_v1",evidence_kind="artificial_source_values",
                numeric_decode_marker={"artificial":True},source_metadata=p,
                days=[dict(date=v["date"],prices=v["prices"])],dividends=[])
            result=m.advance_normalized(root,normalized,context=ctx,injected_at=at)
            self.assertEqual(result["artificial_model_days"],1)
            normalized["evidence_kind"]="conditional_provider_observation"
            with self.assertRaises(ValueError):m.advance_normalized(root,normalized,context=ctx,injected_at=at)

    def test_bound_source_normalizer_warmup_then_first_day_cash_and_provenance(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"journal";f=invented_manifest();ctx=m.artificial_context(f)
            # First observation is midmonth, before the first normal month-end decision.
            f["first_decision_date"]="2000-02-29";ctx=m.artificial_context(f)
            at=(m._instant(f["schedule"]["sessions"][19]["close_at"])+timedelta(minutes=5)).isoformat()
            saved=m.create(root,f,context=ctx,injected_at=at)
            for purpose in ("warmup","daily_model"):
                p,_,at=inputs(f,20,purpose,saved);normalized=normalized_invented(f,p)
                saved=m.advance_normalized(root,normalized,context=ctx,injected_at=at)
                self.assertEqual(saved["ledger"]["balances"]["spendable_cash"],"1000.00")
                self.assertEqual(saved["ledger"]["fills"],[]);self.assertEqual(saved["ledger"]["monthly_events"],[])
                self.assertEqual(saved["source_receipts"][-1]["received_at"],p["received_at"])
                for row in saved["source_receipts"][-1]["records"].values():
                    self.assertTrue(all(value is None for value in row["execution"].values()))
                    self.assertIsNone(row["effective_at"]);self.assertIsNone(row["provider_available_at"])
            self.assertEqual(saved["artificial_model_days"],1);self.assertEqual(saved["model_forward_days"],0)
            self.assertEqual(saved,m.status(root,context=ctx));self.assertNotIn("UNREAD",json.dumps(saved))

    def test_exact_two_role_factory_with_artificial_authority_files_and_expiry(self):
        # Metadata-only factory test; no production directory or account is created.
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            def save(name,value):
                path=root/name;path.write_bytes(m._bytes(value));return m._ref(path)
            authority=save("artificial_definition.json",dict(artificial_authority_fixture=True))
            f=invented_manifest();f.update(evidence_kind="conditional_forward_model",first_decision_date="2026-11-30",
                last_observation_date="2026-12-07",authorization_fixture_only=True)
            sessions=[];day=date(2026,10,12)
            while day<=date(2026,12,8):
                if day.weekday()<5 and day!=date(2026,11,26):
                    close_hour=13 if day==date(2026,11,27) else 16
                    sessions.append(dict(date=day.isoformat(),open_at=datetime.combine(day,time(9,30),m.source.NY).astimezone(timezone.utc).isoformat(),
                                         close_at=datetime.combine(day,time(close_hour),m.source.NY).astimezone(timezone.utc).isoformat()))
                day+=timedelta(days=1)
            f["schedule"]=dict(source_ref=authority,sessions=sessions)
            for entry in f["authorities"].values():entry["definition_ref"]=authority
            manifests={};bindings={}
            for role in m.ROLES:
                one=dict(f,role=role);ref=save(role+"_artificial_manifest.json",one);manifests[role]=ref
                bindings[role]=dict(canonical_sha256=m._sha(one),file_sha256=ref["sha256"])
            normalizer=m._ref(m.source.__file__)
            binding=dict(method_sha256=m.METHOD_SHA,manifests=bindings,runtime_sha256=m._sha(m._runtime()),
                         source_authorities_sha256=m._sha(f["authorities"]),normalizer_sha256=normalizer["sha256"])
            reviews={role:save(role+"_artificial_fixture.json",dict(schema="us_daily_model_review_v1",role=role,
                status="accepted",binding=binding,artificial_authority_fixture=True)) for role in ("manager_review","root_review")}
            now=datetime.now(timezone.utc)
            release=dict(schema="us_daily_model_release_v1",role="root_release",status="admitted_conditional_model",binding=binding,
                manifests=manifests,normalizer=normalizer,manager_review_sha256=reviews["manager_review"]["sha256"],
                root_review_sha256=reviews["root_review"]["sha256"],not_before=(now-timedelta(minutes=1)).isoformat(),
                expires_at=(now+timedelta(minutes=1)).isoformat(),artificial_authority_fixture=True)
            ref=save("artificial_release_fixture.json",release)
            # Fix the UTC validation clock for reproducible CI without weakening production.
            fixed_now=datetime(2026,11,7,18,0,tzinfo=timezone.utc)
            release.update(not_before=(fixed_now-timedelta(minutes=1)).isoformat(),expires_at=(fixed_now+timedelta(minutes=1)).isoformat())
            ref=save("artificial_release_fixture.json",release)
            with patch.object(m,"datetime",wraps=datetime) as fake_clock:
                fake_clock.now.return_value=fixed_now
                contexts=[m.admitted_context(root,manifests[role],ref,reviews["manager_review"],reviews["root_review"]) for role in m.ROLES]
                self.assertEqual(len({c.release_sha256 for c in contexts}),1)
                self.assertNotEqual(contexts[0].manifest_sha256,contexts[1].manifest_sha256)
                with self.assertRaises(ValueError):m.create(root/"forbidden_real_instance",dict(f,role="primary"),context=contexts[0])
                invalid=dict(schema="us_source_normalized_packet_v1",evidence_kind="conditional_provider_observation",
                    numeric_decode_marker=authority,source_metadata=dict(purpose="warmup",records={s:dict(source_ref=authority) for s in m.ASSETS}),
                    context_identity=dict(test_values=True))
                with patch.object(m,"status",side_effect=AssertionError("journal_access_before_provenance_guard")):
                    with self.assertRaisesRegex(ValueError,"Normalizer context/source binding"):
                        m.advance_normalized(root/"not_created",invalid,context=contexts[0])
                release["expires_at"]=(fixed_now-timedelta(seconds=1)).isoformat()
                expired=save("expired_artificial_release_fixture.json",release)
                with self.assertRaises(ValueError):m.admitted_context(root,manifests["primary"],expired,reviews["manager_review"],reviews["root_review"])
                with self.assertRaises(ValueError):m.admitted_context(root,manifests["primary"],ref,reviews["root_review"],reviews["manager_review"])


if __name__=="__main__":unittest.main()
