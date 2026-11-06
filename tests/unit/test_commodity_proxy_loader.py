"""Synthetic retained originals exercise units, identity and exact source rows."""
from datetime import date, timedelta
import io
import json
import unittest
from unittest.mock import patch

import pandas as pd

from scripts.run_commodity_proxy_accounts import lifecycle_records, load_inputs
from quant_robot.research.commodity_proxy_accounts import calculate
from quant_robot.research.commodity_proxy_admission import canonical, digest


class CommodityLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        days = []
        day = date(2020, 1, 2)
        while day <= date(2024, 6, 28):
            if day.weekday() < 5 and day != date(2022, 1, 3):
                days.append(day)
            day += timedelta(days=1)
        # This is an invented calendar, not a copy or assertion about CN holidays.
        del days[21:21+len(days)-1087]
        sessions = [date(2019, 12, 30), date(2019, 12, 31), *days]
        snapshots = {'calendar': ('market,date,is_open\n'+'\n'.join(
            f'CN,{day.isoformat()},1' for day in sessions)).encode()}
        partitions = []
        for year in range(2020, 2025):
            selected = [day for day in days if day.year == year]
            rows = [dict(asset_id='CN_ETF_XSHE_159985', symbol='159985.SZ', date=day,
                open=5., high=5., low=5., close=5., adj_close=5., volume=123400.,
                currency='CNY', source='tushare', adjusted=False, exchange='XSHE', asset_type='etf')
                for day in selected]
            # A different asset must never become part of the account input.
            rows.append({**rows[0], 'asset_id': 'OTHER', 'open': -100.})
            output = io.BytesIO(); pd.DataFrame(rows).to_parquet(output, index=False)
            raw = output.getvalue(); snapshots['bars_'+str(year)] = raw
            partitions.append(dict(year=year, target_rows=len(selected), sha256=digest(raw)))
        authority = dict(asset_id='CN_ETF_XSHE_159985', target_metadata={'adjusted': False},
            units=dict(stored_volume='fund units/shares', stored_amount='CNY',
                       do_not_apply_multipliers_again=True), partitions=partitions)
        snapshots['etf_authority'] = canonical(authority)
        requests, receipts = [], []
        for index in range(38):
            size = 58 if index < 8 else 57  # Exactly2174 rows across38 originals.
            code, identity = f'M{2000+index:04d}.DCE', f'synthetic_{index+1:02d}'
            wanted = [day.isoformat() for day in sessions[:size]]
            body = dict(code=0, data=dict(fields=['ts_code', 'trade_date', 'settle'],
                items=[[code, day.replace('-', ''), 3001.25 if index == 0 else 3000.25]
                       for day in wanted]))
            raw = canonical(body); snapshots[f'settlement_{index+1:02d}'] = raw
            requests.append(dict(request_id=identity, params={'ts_code': code}, required_selected_dates=wanted))
            receipts.append(dict(request_id=identity, ts_code=code, raw_sha256=digest(raw),
                status='format_complete_for_selected_dates', missing_selected_dates=[],
                additional_in_range_dates=[], row_count=size))
        snapshots['settlement_scope'] = canonical({'requests': requests})
        snapshots['settlement_structure'] = canonical(dict(POST_started_count=38, retries=0,
            receipts=receipts, scope_sha256=digest(snapshots['settlement_scope'])))
        snapshots['actions'] = canonical(dict(asset_id='CN_ETF_XSHE_159985',
            coverage_start='2020-01-02', coverage_end='2024-06-28',
            share_conversions_supported=False, actions=[]))
        snapshots['actions_review'] = canonical(dict(status='accepted_for_conditional_account',
            actions_sha256=digest(snapshots['actions']), qualified=False))
        # Preserve the real metadata document's four-key shape, with invented rows.
        records = []
        for index in range(38):
            expiry = date(2025, 1, 1)+timedelta(days=7*index)
            records.append(dict(ts_code=f'M{2000+index:04d}.DCE', fut_code='M', exchange='DCE',
                list_date='20190101', delist_date=expiry.strftime('%Y%m%d'),
                last_ddate=(expiry+timedelta(days=1)).strftime('%Y%m%d'),
                per_unit=10, trade_unit='吨', quote_unit='人民币元/吨'))
        snapshots['lifecycle'] = canonical(dict(
            source_sha256='f6d5c671061d18a1c131716122f3e6444f2d7f7ec546940224d91252a4e5745c',
            records=records, delist_date_semantics='provider_documented_last_trade_date',
            historical_vintage_verified=False))
        cls.snapshots = snapshots

    def test_filters_one_ETF_preserves_normalized_units_and_unknown_execution(self):
        result = load_inputs(self.snapshots)
        self.assertEqual(len(result['bars']), 1087)
        self.assertEqual(len(result['settlements']), 2174)
        self.assertTrue(all(row['volume'] == 123400 for row in result['bars']))
        self.assertTrue(all(row['suspended'] is None and row['limit_up'] is None
                            and row['limit_down'] is None for row in result['bars']))
        self.assertEqual(result['actions'], [])
        self.assertEqual(result['lifecycle'], json.loads(self.snapshots['lifecycle'])['records'])

    def test_retained_wrapper_integrates_loader_selector_and_all_accounts(self):
        result = calculate(**load_inputs(self.snapshots))
        self.assertEqual(result['account_count'], 36)
        self.assertEqual(result['cash_benchmark_count'], 2)
        self.assertEqual(len(result['signal_evidence']['signals']), 1089)
        primary = result['account_summaries']['development/curve/min5_slip10']
        self.assertGreater(primary['actual_buy_fills'], 0)
        self.assertGreater(primary['roundtrips']['count'], 0)
        self.assertFalse(result['qualified'])

    def test_wrapper_failure_happens_before_any_price_reader(self):
        original = json.loads(self.snapshots['lifecycle'])
        malformed = [original['records'], {**original, 'source_sha256': '0'*64},
                     {**original, 'delist_date_semantics': 'delivery_date'},
                     {**original, 'historical_vintage_verified': True},
                     {**original, 'extra': True}, {**original, 'records': []}]
        for document in malformed:
            with self.subTest(document_type=type(document).__name__):
                snapshots = {**self.snapshots, 'lifecycle': canonical(document)}
                with patch('scripts.run_commodity_proxy_accounts.pd.read_parquet') as read:
                    with self.assertRaises(ValueError):
                        load_inputs(snapshots)
                    read.assert_not_called()

    def test_invalid_contract_rows_rejected_by_original_selector(self):
        document = json.loads(self.snapshots['lifecycle'])
        document['records'][0]['per_unit'] = 100
        with self.assertRaisesRegex(ValueError, 'contract units'):
            lifecycle_records(canonical(document), ['2019-12-30', '2019-12-31'])

    def test_adjusted_authority_and_changed_original_rejected(self):
        snapshots = dict(self.snapshots)
        authority = json.loads(snapshots['etf_authority']); authority['target_metadata']['adjusted'] = True
        snapshots['etf_authority'] = canonical(authority)
        with self.assertRaisesRegex(ValueError, 'unadjusted ETF'):
            load_inputs(snapshots)
        snapshots = dict(self.snapshots); snapshots['settlement_01'] += b' '
        with self.assertRaisesRegex(ValueError, 'settlement originals'):
            load_inputs(snapshots)

    def test_extra_source_day_cannot_be_accepted_by_updating_only_raw_hash(self):
        snapshots = dict(self.snapshots)
        body = json.loads(snapshots['settlement_01']); body['data']['items'][0][1] = '20260101'
        snapshots['settlement_01'] = canonical(body)
        structure = json.loads(snapshots['settlement_structure'])
        structure['receipts'][0]['raw_sha256'] = digest(snapshots['settlement_01'])
        snapshots['settlement_structure'] = canonical(structure)
        with self.assertRaisesRegex(ValueError, 'settlement rows changed'):
            load_inputs(snapshots)

    def test_unbound_action_list_does_not_become_empty_verified_events(self):
        snapshots = dict(self.snapshots)
        review = json.loads(snapshots['actions_review']); review['actions_sha256'] = '0'*64
        snapshots['actions_review'] = canonical(review)
        with self.assertRaisesRegex(ValueError, 'corporate-action input'):
            load_inputs(snapshots)


if __name__ == '__main__':
    unittest.main()
