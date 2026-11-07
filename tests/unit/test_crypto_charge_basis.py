from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

from quant_robot.research.crypto_charge_basis import load_charge_basis_fixture, run_charge_basis_fixture
from quant_robot.research.crypto_carry_driver import audit_minute
from quant_robot.research.crypto_carry_model import (
    CHARGE_BASIS_FUNDING, LEGACY_FUNDING, CarryModel, FeeScenario, FundingChargeEvent, Leg, MINUTE, TradingRule,
)
from quant_robot.research.crypto_carry_policy import CompletedPrices, OHLCMinute, VolumeMinute
from quant_robot.research.crypto_carry_scheduler import CompletedPrefix, SyntheticCarryScheduler
from quant_robot.research.crypto_monthly_diagnostic import (
    START, _archive, _csv, load_raw_month, run_account, synthetic_raw_fixture,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {'spot': 'invented:spot.csv', 'mark': 'invented:mark.csv'}


def model(*, paired=True):
    m = CarryModel(start=START, spot_rule=TradingRule('.001','.001','10'),
        futures_rule=TradingRule('.001','.001','10'), fees=FeeScenario('0','0','0'),
        spot_cash='100' if paired else '500', futures_cash='500',
        funding_mode=CHARGE_BASIS_FUNDING, audit_event_states=True)
    if paired:
        m.spot_btc = m.short_btc = D('.4')
        m.entry_vwap = D('1000'); m.spot_cost = D('400')
        m.peak = m.daily_reference = D('1000')
    return m


def opening(m, at=START, *, spot='1000', mark='1000', future='1000'):
    m.queue_quote(at, spot=spot, future=future, mark=mark, market_sources=SOURCES)


def prefix(at, *, mark='1000', volume='100'):
    prices = CompletedPrices(at, at, D('1000'), D('1000'), D(mark))
    rows = tuple(VolumeMinute(at-(19-i)*MINUTE, at-(19-i)*MINUTE, D(volume)) for i in range(20))
    return CompletedPrefix(prices, rows, rows)


def change_basis(raw, value):
    tool=json.loads(raw.funding_tool_return)
    for event in tool['structuredContent']['result']: event['markPrice']=value
    tool['content'][0]['text']=json.dumps(tool['structuredContent'])
    return replace(raw,funding_tool_return=json.dumps(tool).encode())


class ChargeKernelTests(unittest.TestCase):
    def test_only_basis_changes_cash_not_market_or_execution_prices(self):
        for basis,amount in (('1200','.48'),('1500','.60')):
            with self.subTest(basis=basis):
                m=model(); opening(m)
                m.queue_funding_charge(START,rate='.001',charge_basis=basis); m.run(START)
                self.assertEqual(m.funding_cash,D(amount))
                self.assertEqual((m.spot_price,m.mark_price,m.future_price),(D(1000),)*3)
                self.assertEqual(m.nav,D(1000)+D(amount))
                self.assertEqual(m.peak,m.nav)
                self.assertEqual(m.short_btc,D('.4'))

    def test_negative_cash_alone_crosses_daily_and_wallet_limits(self):
        m=model(); opening(m)
        m.queue_funding_charge(START,rate='-.3',charge_basis='1000'); m.run(START)
        self.assertEqual(m.nav,D('880'))
        self.assertEqual(m.futures_equity,D('380'))
        self.assertTrue(m.paused)
        self.assertIn('futures_wallet_below_1x',m.failures)
        self.assertEqual(m.plan.kind,'risk_exit')
        self.assertEqual(m.mark_price,D(1000))

    def test_positive_cash_does_not_erase_old_breach_or_max_drawdown(self):
        m=model(); opening(m,mark='1200')
        m.queue_funding_charge(START,rate='.1',charge_basis='2500'); m.run(START)
        self.assertEqual(m.nav,D('1020'))
        self.assertTrue(m.paused)
        self.assertIn('futures_wallet_below_1x',m.failures)
        self.assertEqual(m.max_drawdown,D('.08'))
        rows=[r for r in m.journal if r['event']=='risk_observation']
        self.assertTrue(any(r['nav']=='920.0' for r in rows))

    def test_fractional_event_uses_original_clock_no_future_close(self):
        m=model(); opening(m,mark='1010')
        event_at=START+timedelta(milliseconds=15)
        m.queue_completed_close(closed_at=START+MINUTE,available_at=START+MINUTE,
            spot='500',future='500',mark='500',market_sources=SOURCES)
        m.queue_funding_charge(event_at,rate='.001',charge_basis='1500'); m.run(event_at)
        row=next(r for r in m.journal if r['event']=='funding')
        self.assertEqual(row['time'],event_at.isoformat())
        self.assertEqual(m.nav,D('996.60'))
        for market in ('spot','mark'):
            self.assertEqual(row['valuation'][market]['age_model_ms'],15)
            self.assertEqual(row['valuation'][market]['source'],SOURCES[market])
            self.assertEqual(row['valuation'][market]['market_observed_at'],START.isoformat())
            self.assertEqual(row['valuation'][market]['model_available_at'],START.isoformat())
            self.assertFalse(row['valuation'][market]['instantaneous_at_event_certified'])
        self.assertEqual(m.mark_price,D(1010))

    def test_same_time_funding_precedes_new_short_fill(self):
        m=model(paired=False); opening(m); m.run(START)
        self.assertTrue(m.register_plan((Leg('short_open',D('.1'),D(1)),)))
        at=START+MINUTE; opening(m,at)
        m.queue_funding_charge(at,rate='.001',charge_basis='1200')
        m.queue_funding_charge(at+timedelta(milliseconds=15),rate='.001',charge_basis='1500')
        m.run(at+timedelta(milliseconds=15))
        rows=[r for r in m.journal if r['event']=='funding']
        self.assertEqual([D(r['quantity_before']) for r in rows],[D(0),D('.1')])
        self.assertEqual([D(r['cash_delta']) for r in rows],[D(0),D('.15')])
        order=[r['event'] for r in m.journal if r['event'] in ('funding','leg_filled')]
        self.assertEqual(order,['funding','leg_filled','funding'])

    def test_modes_cannot_mix_even_at_different_timestamps(self):
        m=model()
        with self.assertRaisesRegex(ValueError,'queue_funding_charge'):
            m.queue_funding(START+MINUTE,rate='0',mark='1000')
        legacy=CarryModel(start=START,spot_rule=m.spot_rule,futures_rule=m.futures_rule)
        with self.assertRaisesRegex(ValueError,'explicit model mode'):
            legacy.queue_funding_charge(START,rate='0',charge_basis='1000')
        self.assertFalse(m._events); self.assertFalse(legacy._events)

    def test_missing_current_opening_or_mutated_valuation_blocks_before_cash(self):
        for changed in (False,True):
            with self.subTest(changed=changed):
                m=model(); opening(m); m.run(START)
                at=START+MINUTE if not changed else START+timedelta(milliseconds=15)
                if changed: m.mark_price=D('1001')
                m.queue_funding_charge(at,rate='.001',charge_basis='1500')
                with self.assertRaisesRegex(ValueError,'current minute'):
                    m.run(at)
                self.assertEqual(m.funding_cash,0)
                self.assertFalse(any(r['event']=='funding' for r in m.journal))

    def test_queued_and_processed_new_wallet_event_prevent_late_close(self):
        for processed in (False,True):
            with self.subTest(processed=processed):
                m=model(); opening(m)
                at=START+timedelta(milliseconds=15)
                m.queue_funding_charge(at,rate='.001',charge_basis='1200')
                if processed: m.run(at)
                with self.assertRaisesRegex(ValueError,'Late completed close'):
                    m.queue_completed_close(closed_at=START,available_at=START+timedelta(seconds=30),
                        spot='999',future='999',mark='999',market_sources=SOURCES)
                self.assertFalse(any(e[3]=='completed_close' for e in m._events))

    def test_new_basis_does_not_become_envelope_point_and_both_cash_states_survive(self):
        m=model(); opening(m)
        at=START+timedelta(milliseconds=15)
        event=FundingChargeEvent(at,D('-.3'),D('1200'))
        m.queue_funding_charge(at,rate=event.rate,charge_basis=event.charge_basis); m.run(at)
        _,states=m.audit_states_since()
        before=next(r for r in states if r.event=='funding_charge' and r.stage=='before')
        after=next(r for r in states if r.event=='funding_charge' and r.stage=='after')
        self.assertEqual(before.futures_cash-after.futures_cash,D('144'))
        candle=OHLCMinute(START,START+MINUTE,START+MINUTE,*[D(1000)]*4)
        result=audit_minute(rows=states,spot=candle,mark=candle,funding={at:event})
        self.assertEqual(result['state_count'],len(states))
        self.assertFalse(any(r['at']==at for r in result['known_points']))
        self.assertFalse(any(r['mark']==D(1200) for r in result['known_points']))
        self.assertEqual(result['envelope']['status'],'confirmed_breach')

    def test_existing_partial_reduction_second_leg_is_not_starved(self):
        m=model(); opening(m); m.run(START)
        m.register_plan((Leg('short_close',D('.05'),D(1)),Leg('spot_sell',D('.05'),D(1))),kind='rebalance')
        number=m.plan.number
        opening(m,START+MINUTE)
        m.queue_funding_charge(START+MINUTE+timedelta(milliseconds=15),rate='-.1',charge_basis='1000')
        m.run(START+MINUTE+timedelta(milliseconds=15))
        self.assertEqual((m.plan.number,m.plan.index,m.plan.kind),(number,1,'risk_exit'))
        opening(m,START+2*MINUTE); m.run(START+2*MINUTE)
        fills=[r for r in m.journal if r['event']=='leg_filled']
        self.assertEqual([r['side'] for r in fills],['short_close','spot_sell'])
        self.assertEqual(D(fills[1]['quantity']),D('.05'))
        self.assertEqual(m.short_btc,D('.35'))
        self.assertTrue(m.paused)

    def test_five_full_days_still_required_before_fixed_resume(self):
        m=model(paired=False); opening(m); m.run(START)
        m.paused=True; m._refresh_cooldown()
        for day in range(1,6):
            at=START+timedelta(days=day)
            m.queue_completed_close(closed_at=at,available_at=at,spot='1000',future='1000',mark='1000',market_sources=SOURCES)
            m.queue_day_end(at,completed_close=True)
            opening(m,at); m.queue_funding_charge(at,rate='.001',charge_basis='1200')
            m.queue_resume(at+2*MINUTE); m.run(at+2*MINUTE)
            self.assertEqual(m.paused,day<5)
        self.assertEqual(sum(r['event']=='diagnostic_resumed' for r in m.journal),1)

    def test_scheduler_midminute_risk_capacity_is_frozen_or_blocks(self):
        for have_prefix in (False,True):
            with self.subTest(have_prefix=have_prefix):
                m=model(); s=SyntheticCarryScheduler(m,market_sources=SOURCES)
                s.queue_opening(START,spot='1000',future='1000',mark='1000')
                s.advance(START,prefix=prefix(START) if have_prefix else None)
                at=START+timedelta(milliseconds=15)
                s.queue_funding_charge(at,rate='-.3',charge_basis='1000'); s.advance(at)
                binding=s.bindings[m.plan.number]
                s.queue_opening(START+MINUTE,spot='1000',future='1000',mark='1000')
                result=s.advance(START+MINUTE)
                if have_prefix:
                    self.assertIsNone(binding['blocked_reason'])
                    self.assertEqual(binding['prefix_end'],START.isoformat())
                    self.assertTrue(any(r['event']=='leg_filled' for r in m.journal))
                else:
                    self.assertEqual(result['status'],'blocked')
                    self.assertFalse(any(r['event']=='leg_filled' for r in m.journal))


class ChargeLoaderControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=change_basis(synthetic_raw_fixture(days=2),'1200')

    def test_old_strict_loader_still_rejects_same_artificial_body(self):
        with self.assertRaisesRegex(ValueError,'outside_minute_ohlc'): load_raw_month(self.raw)
        data=load_charge_basis_fixture(self.raw)
        self.assertIsInstance(data.funding[0],FundingChargeEvent)
        self.assertEqual(data.funding[0].charge_basis,D(1200))
        self.assertEqual(data.bars['mark'][0].candle.open,D(1000))
        self.assertEqual(data.provenance['funding_mode'],CHARGE_BASIS_FUNDING)

    def test_real_evidence_dates_or_acquisition_cannot_enter_new_synthetic_decoder(self):
        bads=(replace(self.raw,evidence_class='retained_historical_sources'),
              replace(self.raw,start=self.raw.start.replace(year=2025),end=self.raw.end.replace(year=2025)),
              replace(self.raw,actual_market_acquired_at=datetime.now(timezone.utc)))
        for raw in bads:
            with self.subTest(raw=raw.evidence_class),patch('quant_robot.research.crypto_monthly_diagnostic.zipfile.ZipFile') as decoder:
                with self.assertRaises(ValueError): load_charge_basis_fixture(raw)
                decoder.assert_not_called()

    def test_missing_or_invalid_basis_and_bad_source_grid_still_rejected(self):
        for value in ('NaN','0','-1'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                load_charge_basis_fixture(change_basis(self.raw,value))
        rows=_csv(self.raw.archives['mark']); rows.pop()
        archives=dict(self.raw.archives); archives['mark']=_archive('invented_missing_mark',rows)
        with self.assertRaisesRegex(ValueError,'coverage'):
            load_charge_basis_fixture(replace(self.raw,archives=archives))

    def test_legacy_and_new_account_modes_cannot_silently_interchange(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'role_and_explicit'):
                run_account(load_charge_basis_fixture(self.raw),output_dir=Path(temp)/'legacy')
            with self.assertRaisesRegex(ValueError,'role_and_explicit'):
                run_charge_basis_fixture(load_raw_month(synthetic_raw_fixture(days=2)),output_dir=Path(temp)/'new')
            self.assertEqual(list(Path(temp).iterdir()),[])

    def test_complete_artificial_loader_controller_envelope_ledger_path(self):
        evidence=os.environ.get('CRYPTO_BP_EVIDENCE_DIR')
        with tempfile.TemporaryDirectory() as temp:
            output=(Path(evidence)/'new_charge_two_day_account') if evidence else Path(temp)/'new'
            result=run_charge_basis_fixture(load_charge_basis_fixture(self.raw),output_dir=output)
            self.assertTrue(result['account_complete']); self.assertTrue(result['economic_exercise_complete'])
            self.assertTrue(result['ledger']['reconciled']); self.assertEqual(result['fill_count'],4)
            self.assertEqual(len(result['daily_nav']),2)
            self.assertFalse(result['qualified']); self.assertFalse(result['historical_returns_computed'])
            self.assertEqual(result['funding_mode'],CHARGE_BASIS_FUNDING)
            self.assertFalse(result['terminal']['terminal_unsettled'])
            self.assertEqual(result['processed_minutes'],2880)
            self.assertTrue(all(r['valuation']['mark']['value']=='1000' for r in result['funding_events']))
            self.assertTrue(all(r['charge_basis']=='1200' for r in result['funding_events']))
            self.assertTrue(all(r['valuation']['mark']['age_model_ms']==15 for r in result['funding_events']))
            with gzip.open(output/'minute_envelopes.jsonl.gz','rt') as stream:
                envelopes=[json.loads(row) for row in stream]
            self.assertEqual(len(envelopes),2880)
            self.assertFalse(any(point['at'].endswith('.015000+00:00') for row in envelopes for point in row['known_points']))


# Fresh processes load all four prechange files under their original module
# identities. Only gzip container headers are normalized; every decompressed
# journal/state/envelope line and every other summary field is compared.
DEFAULT_PROBE = r'''
import gzip,hashlib,importlib.util,json,sys
from pathlib import Path
from dataclasses import asdict,replace
from datetime import datetime,timezone
backup,output=sys.argv[1:]
if backup!='current':
    for name in ('crypto_carry_model','crypto_carry_scheduler','crypto_carry_driver','crypto_monthly_diagnostic'):
        key='quant_robot.research.'+name
        spec=importlib.util.spec_from_file_location(key,Path(backup)/(name+'.py'))
        module=importlib.util.module_from_spec(spec); sys.modules[key]=module; spec.loader.exec_module(module)
from quant_robot.research.crypto_monthly_diagnostic import load_raw_month,run_account,synthetic_raw_fixture,_json
root=Path(output); root.mkdir()
raw=replace(synthetic_raw_fixture(days=2),fixture_created_at=datetime(2001,1,1,tzinfo=timezone.utc))
data=load_raw_month(raw)
summary=run_account(data,output_dir=root/'account')
traces={path.name:gzip.decompress(path.read_bytes()).decode('utf-8') for path in sorted((root/'account').glob('*.gz'))}
summary['artifacts']={name:{'decompressed_sha256':hashlib.sha256(body.encode()).hexdigest(),'lines':len(body.splitlines())}
                      for name,body in traces.items()}
canonical=_json({'loaded':asdict(data),'summary':summary,'all_decompressed_traces':traces})+'\n'
(root/'canonical_complete_output.json').write_text(canonical,encoding='utf-8')
print(json.dumps({'sha256':hashlib.sha256(canonical.encode()).hexdigest(),'bytes':len(canonical.encode()),
                 'trace_lines':{name:len(body.splitlines()) for name,body in traces.items()}}))
'''


class DefaultCompatibilityTests(unittest.TestCase):
    def test_old_and_new_default_complete_account_outputs_identical(self):
        backup=ROOT/'data/reports/campaign_72h_20261106/manager/BP_prechange_runtime'
        if not (backup/'manifest.json').exists():
            self.skipTest('Local immutable baseline is excluded from Git; evidence is retained in the delivery')
        for name,record in json.loads((backup/'manifest.json').read_text())['files'].items():
            self.assertEqual(hashlib.sha256((backup/name).read_bytes()).hexdigest(),record['sha256'])
        evidence=os.environ.get('CRYPTO_BP_EVIDENCE_DIR')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(evidence) if evidence else Path(temp)
            receipts=[]
            for version in (str(backup),'current'):
                label='legacy_baseline' if version!='current' else 'current_default'
                run=subprocess.run([sys.executable,'-c',DEFAULT_PROBE,version,str(root/label)],
                                   cwd=ROOT,capture_output=True,text=True,timeout=90,check=True)
                receipts.append(json.loads(run.stdout))
            self.assertEqual(receipts[0],receipts[1])
            self.assertEqual((root/'legacy_baseline/canonical_complete_output.json').read_bytes(),
                             (root/'current_default/canonical_complete_output.json').read_bytes())
            if evidence:
                (root/'default_equivalence_receipt.json').write_text(json.dumps({
                    'status':'identical_complete_canonical_outputs','python':sys.version,
                    'receipts':receipts,'normalization':'gzip header metadata only; every decompressed byte retained',
                    'economic_fields_ignored':[]},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': unittest.main()
