"""Invented 2004 values and mocked transport; no historical/forward source reads."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from quant_robot.ops import us_allocation_model_capture as T
from quant_robot.ops import us_allocation_source_contract as C
from quant_robot.ops import us_low_unit_model_source as L
from tests.unit.test_us_allocation_model_capture import Response, artificial_body, artificial_calendar


def bundle(root, *, warmup=False, mutation=None):
    schedule, authorities = artificial_calendar()
    target = schedule['sessions'][20]['date']
    dates = [r['date'] for r in schedule['sessions'][:20]] if warmup else [target]
    key = 'warmup' if warmup else target
    now = C._instant(schedule['sessions'][19 if warmup else 20]['close_at']) + timedelta(minutes=16)
    scope = dict(operation_dates=[target], requests={key:dict(urls={})})
    captured = {}
    end = (date.fromisoformat(dates[-1]) + timedelta(days=1)).isoformat()
    for symbol in L.ASSETS:
        url = L.expected_url(symbol, dates[0], end)
        scope['requests'][key]['urls'][symbol] = url
        obj = json.loads(artificial_body(symbol, dates)); row = obj['chart']['result'][0]
        if symbol == 'GLDM': row['events']['dividends'] = {}
        if not warmup:
            row['indicators']['quote'][0].update(high=['11'], low=['9'])
            for action in row['events']['dividends'].values(): action['amount'] = '0.10'
        if symbol == 'GLDM' and mutation is not None: mutation(row)
        with patch.object(T, 'build_opener', return_value=Mock(open=Mock(return_value=Response(json.dumps(obj).encode())))), \
                patch.object(T, '_now', return_value=now):
            captured[symbol] = T.fetch_one(url, Path(root)/symbol, assets=L.ASSETS)
    manifest = dict(schedule=schedule, authorities=authorities)
    batch_ref = T._save(Path(root)/'sources.json', {s:dict(raw=x[1], receipt=x[3]) for s,x in captured.items()})
    prior = dict(prior_session_date=schedule['sessions'][19]['date'], prior_committed_ref=deepcopy(schedule['source_ref']),
        prior_committed_at=(C._instant(schedule['sessions'][20]['open_at'])-timedelta(hours=1)).isoformat())
    packet = T.build_source_packet(scope, manifest, key, captured, batch_ref, assets=L.ASSETS, **prior)
    return {s:x[0] for s,x in captured.items()}, packet, schedule, authorities


def context(packet):
    return C._SourceDecodeContext(packet['purpose'], C._digest(packet),
        C._digest({s:packet['records'][s]['source_ref'] for s in L.ASSETS}), 'b'*64,
        'artificial_source_values', True)


class LowUnitSourceTests(unittest.TestCase):
    def test_shared_four_sources_convert_once_and_keep_identity(self):
        for warmup, count in ((True,160),(False,23)):
            with self.subTest(warmup=warmup), tempfile.TemporaryDirectory() as root:
                raw,p,s,a = bundle(root,warmup=warmup); markers=[]; original=C._number
                def number(token,**kwargs):
                    self.assertEqual(markers,['once'])
                    return original(token,**kwargs)
                with patch.object(C,'_number',side_effect=number) as numeric:
                    result=L.normalize(raw,p,s,authorities=a,context=context(p),before_numeric_decode=lambda:markers.append('once'))
                self.assertEqual(numeric.call_count,count)
                self.assertEqual(markers,['once']);self.assertEqual(len(raw),4)
                self.assertEqual(result['model_accounts_advanced'],0)
                self.assertEqual(result['evidence_kind'],'artificial_source_values')
                self.assertFalse(result['journal_admission_granted']);self.assertEqual(result['real_forward'],0)
                self.assertFalse(result['qualified']);self.assertNotIn('NEVER_CONVERT',json.dumps(result))
                self.assertEqual(result['days'][0]['capacity_volume'],dict.fromkeys(L.ASSETS,'10000'))
                fields={'close','volume'} if warmup else set(L.DAILY_FIELDS)
                self.assertEqual(set(result['days'][0]['prices']['GLDM']),fields)
                self.assertTrue(all(v is None for v in result['source_metadata']['records']['GLDM']['execution'].values()))

    def test_defaults_remain_old_basket_and_cannot_infer_new_assets(self):
        self.assertEqual(C.ASSETS,('SPY','EFA','IEF','GLD'))
        with self.assertRaisesRegex(ValueError,'symbol'):T.expected_url('SPYM','2004-01-01','2004-01-02')
        with self.assertRaisesRegex(ValueError,'registered_asset_scope'):
            T.expected_url('AAPL','2004-01-01','2004-01-02',assets=('AAPL','EFA','IEF','GLDM'))
        with tempfile.TemporaryDirectory() as root:
            raw,p,s,a=bundle(root)
            self.assertFalse(C.assess_source_metadata(p,s,authorities=a)['requirements_met'])
            self.assertTrue(L.assess(p,s,authorities=a)['requirements_met'])
            with self.assertRaises(ValueError):
                C.normalize_yahoo_sources(raw,p,s,authorities=a,context=context(p),before_numeric_decode=lambda:self.fail('marker'))

    def test_split_or_capital_gain_stops_before_numeric_or_journal(self):
        for action in ('splits','capitalGains'):
            with self.subTest(action=action),tempfile.TemporaryDirectory() as root:
                with patch.object(C,'_number',side_effect=AssertionError('numeric conversion')):
                    with self.assertRaisesRegex(ValueError,'split_or_capital_gain_unsupported'):
                        bundle(root,mutation=lambda row:row['events'].update({action:{'unreviewed':{}}}))

    def test_missing_high_and_changed_source_fail_before_marker(self):
        for mutation in (None,lambda row:row['indicators']['quote'][0].pop('high')):
            with tempfile.TemporaryDirectory() as root:
                raw,p,s,a=bundle(root,mutation=mutation)
                if mutation is None:raw['GLDM']+=b' '
                with patch.object(C,'_number',side_effect=AssertionError('numeric conversion')):
                    with self.assertRaises(ValueError):
                        L.normalize(raw,p,s,authorities=a,context=context(p),before_numeric_decode=lambda:self.fail('marker'))

    def test_unmodelled_gold_distribution_is_not_accepted_as_ordinary_dividend(self):
        def distribution(row):
            token = row['timestamp'][0]
            row['events']['dividends'] = {str(token):dict(date=token,amount='0.10')}
        with tempfile.TemporaryDirectory() as root:
            raw,p,s,a=bundle(root,mutation=distribution)
            with patch.object(C,'_number',side_effect=AssertionError('numeric conversion')):
                with self.assertRaisesRegex(ValueError,'source_dividend_asset_unsupported'):
                    L.normalize(raw,p,s,authorities=a,context=context(p),before_numeric_decode=lambda:self.fail('marker'))

    def test_impossible_daily_range_is_not_forwarded(self):
        with tempfile.TemporaryDirectory() as root:
            raw,p,s,a=bundle(root,mutation=lambda row:row['indicators']['quote'][0].update(high=['8']))
            markers=[]
            with self.assertRaisesRegex(ValueError,'daily_OHLC_order'):
                L.normalize(raw,p,s,authorities=a,context=context(p),before_numeric_decode=lambda:markers.append('once'))
            self.assertEqual(markers,['once'])


if __name__=='__main__': unittest.main()
