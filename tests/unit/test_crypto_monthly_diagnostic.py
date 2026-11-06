from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

from quant_robot.research.crypto_monthly_diagnostic import (
    HEADER, MINUTE, PRIMARY, SCENARIOS, START, _archive, _csv,
    load_raw_month, run_account, run_matrix, synthetic_raw_fixture,
)


def alter_csv(raw, market, transform):
    rows=_csv(raw.archives[market]); transform(rows)
    archives=dict(raw.archives)
    archives[market]=_archive('changed_synthetic_'+market,rows)
    return replace(raw,archives=archives)


def alter_tool(raw, transform, mirror=True):
    tool=json.loads(raw.funding_tool_return); transform(tool)
    if mirror:
        tool['content'][0]['text']=json.dumps(tool['structuredContent'])
    return replace(raw,funding_tool_return=json.dumps(tool).encode())


class RawLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.raw=synthetic_raw_fixture(days=2)

    def test_exact_original_shapes_units_and_subsecond_events(self):
        data=load_raw_month(self.raw)
        self.assertEqual(data.coverage['minutes_per_market'],2880)
        self.assertEqual(data.funding[0].at,START+timedelta(milliseconds=15))
        self.assertIsNone(data.funding[0].synchronous_spot)
        self.assertIsNone(data.bars['mark'][0].volume_btc)
        self.assertEqual(data.bars['spot'][0].candle.end,START+MINUTE)
        self.assertIsNone(data.provenance['actual_market_acquired_at'])
        self.assertNotEqual(data.provenance['fixture_created_at'],START.isoformat())

    def test_real_evidence_rejected_before_zip_decode(self):
        with patch('quant_robot.research.crypto_monthly_diagnostic.zipfile.ZipFile') as decode:
            with self.assertRaisesRegex(ValueError,'separate_admission_guard'):
                load_raw_month(replace(self.raw,evidence_class='real_source'))
            decode.assert_not_called()

    def test_real_date_cannot_be_unlocked_with_synthetic_label(self):
        with patch('quant_robot.research.crypto_monthly_diagnostic.zipfile.ZipFile') as decode:
            with self.assertRaisesRegex(ValueError,'fabricated_january'):
                load_raw_month(replace(self.raw,start=START.replace(year=2025),end=self.raw.end.replace(year=2025)))
            decode.assert_not_called()

    def test_source_acquisition_clock_cannot_be_faked_as_model_clock(self):
        with self.assertRaisesRegex(ValueError,'separate_admission_guard'):
            load_raw_month(replace(self.raw,actual_market_acquired_at=START))

    def test_checksum_mismatch_is_fatal(self):
        archives=dict(self.raw.archives)
        archives['spot']=replace(archives['spot'],checksum=b'bad')
        with self.assertRaisesRegex(ValueError,'checksum'):
            load_raw_month(replace(self.raw,archives=archives))

    def test_missing_or_duplicate_minute_rejected(self):
        for transform in (lambda rows:rows.pop(), lambda rows:rows.__setitem__(7,rows[6])):
            with self.subTest(transform=transform):
                with self.assertRaisesRegex(ValueError,'coverage|grid'):
                    load_raw_month(alter_csv(self.raw,'spot',transform))

    def test_exact_header_required_no_old_um_alias(self):
        with self.assertRaisesRegex(ValueError,'exact_202501_header'):
            load_raw_month(alter_csv(self.raw,'um',lambda rows:rows[0].__setitem__(0,'open_timestamp')))

    def test_spot_us_not_inferred_from_synthetic_year(self):
        with self.assertRaisesRegex(ValueError,'time_unit'):
            load_raw_month(alter_csv(self.raw,'spot',lambda rows:rows[0].__setitem__(0,str(int(rows[0][0])//1000))))

    def test_bad_close_clock_rejected(self):
        with self.assertRaisesRegex(ValueError,'close_mismatch'):
            load_raw_month(alter_csv(self.raw,'mark',lambda rows:rows[1].__setitem__(6,rows[1][0])))

    def test_bad_price_volume_and_column_count_rejected(self):
        for transform in (lambda rows:rows[0].__setitem__(2,'NaN'),
                          lambda rows:rows[0].__setitem__(5,'-1'),
                          lambda rows:rows[0].pop(),
                          lambda rows:rows[0].__setitem__(3,'1001')):
            with self.subTest(transform=transform),self.assertRaises(ValueError):
                load_raw_month(alter_csv(self.raw,'spot',transform))

    def test_mcp_wrapper_shape_cannot_be_reused(self):
        with self.assertRaisesRegex(ValueError,'mcp_schema'):
            load_raw_month(replace(self.raw,funding_tool_return=json.dumps({'response':json.loads(self.raw.funding_tool_return)}).encode()))

    def test_mirror_and_rate_disagreement_rejected(self):
        for mirror in (False,True):
            raw=alter_tool(self.raw,lambda tool:tool['structuredContent']['result'][0].__setitem__('fundingRate','.0002'),mirror)
            with self.subTest(mirror=mirror),self.assertRaisesRegex(ValueError,'mirror|rate_or_mark'):
                load_raw_month(raw)

    def test_milliseconds_must_not_be_rounded_to_seconds(self):
        raw=alter_tool(self.raw,lambda tool:tool['structuredContent']['result'][0].__setitem__('fundingTime',int(self.raw.expected_funding_times_ms[0]/1000)*1000))
        with self.assertRaisesRegex(ValueError,'time_rate'):
            load_raw_month(raw)

    def test_missing_mark_rate_type_or_rate_is_fatal(self):
        for field in ('markPrice','rateType','fundingRate'):
            with self.subTest(field=field),self.assertRaises(ValueError):
                load_raw_month(alter_tool(self.raw,lambda tool:tool['structuredContent']['result'][0].pop(field)))

    def test_funding_gap_cannot_be_filled_with_zero(self):
        with self.assertRaisesRegex(ValueError,'event_coverage'):
            load_raw_month(alter_csv(self.raw,'funding',lambda rows:rows.pop()))

    def test_funding_event_outside_ohlc_rejected(self):
        with self.assertRaisesRegex(ValueError,'outside_minute_ohlc'):
            load_raw_month(alter_tool(self.raw,lambda tool:tool['structuredContent']['result'][0].__setitem__('markPrice','1001')))


class ControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        cls.data=load_raw_month(synthetic_raw_fixture(days=2))
        cls.result=run_account(cls.data,output_dir=cls.root/'primary')

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def rows(self,name):
        with gzip.open(self.root/'primary'/(name+'.jsonl.gz'),'rt',encoding='utf-8') as stream:
            return [json.loads(line) for line in stream]

    def test_raw_loader_to_real_controller_fill_and_ledger(self):
        result=self.result
        self.assertTrue(result['account_complete'])
        self.assertTrue(result['economic_exercise_complete'])
        self.assertTrue(result['ledger']['reconciled'])
        self.assertEqual(result['fill_count'],4)
        self.assertEqual(len(result['daily_nav']),2)
        self.assertEqual(result['spot_rule']['quantity_step'],D('.00001'))
        self.assertEqual(result['futures_rule']['min_notional'],D('100'))
        self.assertGreater(D(result['ledger']['base_fee_btc_informational_not_double_subtracted']),0)

    def test_warmup_only_then_day_two_fixed_entry(self):
        self.assertEqual(self.result['orders'][0]['time'],'2001-01-02T00:03:00+00:00')
        first=self.rows('event_states')[0]
        self.assertEqual(first['spot_cash'],'500')
        self.assertEqual(first['futures_cash'],'500')
        self.assertEqual(D(self.result['daily_nav'][0]['reference_nav']),D('1000'))

    def test_funding_exact_clock_unknown_spot_and_no_fake_receipts(self):
        self.assertTrue(self.result['funding_event_coverage_complete'])
        self.assertTrue(self.result['funding_events'][0]['time'].endswith('00.015000+00:00'))
        self.assertFalse(self.result['synchronous_funding_spot_observed'])
        for row in self.rows('transfer_assumptions'):
            self.assertEqual(row['event'],'model_assumed_transfer_confirmation')
            from datetime import datetime
            self.assertEqual(datetime.fromisoformat(row['due_at'])-datetime.fromisoformat(row['requested_at']),5*MINUTE)
            self.assertEqual(row['requested_at'],row['scheduled_at'])
            self.assertFalse(row['historical_api_receipt'])

    def test_terminal_and_last_close_without_next_month_open(self):
        result=self.result
        self.assertEqual(result['final_processing_at'],'2001-01-03T00:00:00+00:00')
        self.assertFalse(result['terminal']['terminal_unsettled'])
        self.assertFalse(result['next_month_opening_or_funding_consumed'])
        rows=self.rows('event_states')
        last=[row for row in rows if row['at']==result['final_processing_at']]
        self.assertTrue(last)
        self.assertFalse(any(row['event'] in ('quote','funding') for row in last))

    def test_envelopes_streamed_all_minutes_not_global_path_claim(self):
        self.assertEqual(sum(self.result['per_minute_conditional_envelope'].values()),2880)
        self.assertEqual(len(self.rows('minute_envelopes')),2880)
        self.assertNotIn('event_states',self.result)
        self.assertFalse(self.result['qualified'])
        self.assertFalse(self.result['historical_returns_computed'])

    def test_matrix_keeps_all_nine_and_cash_when_no_capacity(self):
        data=load_raw_month(synthetic_raw_fixture(days=2,volume='0'))
        matrix=run_matrix(data,output_dir=self.root/'zero_capacity_matrix')
        self.assertEqual(matrix['scenario_ids'],list(SCENARIOS)+['CASH'])
        self.assertEqual(matrix['cash']['nav'],'1000')
        self.assertEqual(matrix['primary'],PRIMARY)
        for name,row in matrix['accounts'].items():
            self.assertTrue(row['account_complete'],name)
            self.assertFalse(row['economic_exercise_complete'],name)
            self.assertEqual(row['fill_count'],0)
            self.assertTrue(row['ledger']['reconciled'])
            self.assertEqual(row['fee_scenario']['spot'],SCENARIOS[name].spot)
            self.assertEqual(row['fee_scenario']['slippage'],SCENARIOS[name].slippage)
            self.assertFalse(row['qualified'])

    def test_output_cannot_overwrite_prior_account(self):
        with self.assertRaises(FileExistsError):
            run_account(self.data,output_dir=self.root/'primary')

    def test_missing_loaded_minute_blocks_before_creating_account(self):
        bars=dict(self.data.bars); bars['spot']=bars['spot'][:-1]
        target=self.root/'missing_minute'
        with self.assertRaisesRegex(ValueError,'loaded_coverage'):
            run_account(replace(self.data,bars=bars),output_dir=target)
        self.assertFalse(target.exists())

    def test_nonpositive_nav_preserves_failure_and_stops_account(self):
        data=load_raw_month(synthetic_raw_fixture(days=2,funding_rate='-10'))
        result=run_account(data,output_dir=self.root/'nonpositive')
        self.assertEqual(result['status'],'blocked_execution')
        self.assertEqual(result['reason'],'nonpositive_model_nav_stop_preserve_exposure')
        self.assertFalse(result['account_complete'])
        self.assertLess(D(result['ledger']['actual_nav']),0)
        self.assertGreater(D(result['kernel_component']['short_btc']),0)
        self.assertTrue(result['ledger']['reconciled'])
        self.assertFalse(result['qualified'])

    def test_shock_exercises_fixed_transfer_assumption_and_retains_risk(self):
        data=load_raw_month(synthetic_raw_fixture(days=3,shock=True))
        result=run_account(data,output_dir=self.root/'shock')
        self.assertTrue(result['account_complete'])
        self.assertGreater(result['model_assumed_transfer_count'],0)
        self.assertGreater(result['per_minute_conditional_envelope'].get('unresolved_path',0),0)
        self.assertGreater(result['risk_observation_counts'].get('daily_loss_2_percent',0),0)
        with gzip.open(self.root/'shock/transfer_assumptions.jsonl.gz','rt') as stream:
            rows=[json.loads(line) for line in stream]
        from datetime import datetime
        for row in rows:
            self.assertEqual(datetime.fromisoformat(row['due_at'])-datetime.fromisoformat(row['requested_at']),5*MINUTE)
            self.assertEqual(row['scheduled_at'],row['requested_at'])
            self.assertFalse(row['historical_api_receipt'])

    def test_missing_assumed_confirmation_blocks(self):
        data=load_raw_month(synthetic_raw_fixture(days=3,shock=True))
        with patch('quant_robot.research.crypto_monthly_diagnostic.TransferConfirmation',return_value=None):
            result=run_account(data,output_dir=self.root/'missing_confirmation')
        self.assertEqual(result['reason'],'missing_model_assumed_transfer_confirmation')
        self.assertFalse(result['account_complete'])
        self.assertGreater(D(result['kernel_component']['in_transit']),0)


if __name__=='__main__': unittest.main()
