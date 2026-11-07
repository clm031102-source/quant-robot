import json
from datetime import date
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
from unittest.mock import patch

from quant_robot.gui.project_state import current_project_status, current_daily_ops
from quant_robot.gui.research_service import build_project_status_snapshot, build_daily_ops_snapshot


class CurrentProjectStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'configs').mkdir()
        (self.root/'current.md').write_text('Current reviewed project record',encoding='utf-8')
        self.state = dict(schema_version=1,display_only=True,market='CN_ETF',
            updated_at='2026-11-04',state='research_in_progress',state_label='研究推进中',
            authority_document='current.md',capital_cny=10000,actual_fees_verified=False,
            paper_observation_allowed=False,selected_candidate=None,
            counts=dict(return_studies=12,source_screens=3,qualified_strategies=0,
                        forward_observation_days=0,prepared_candidates=4),
            blockers=[dict(blocker_id='no_qualified_strategy',severity='block',track_id='strategy',evidence='No eligible strategy')],
            next_actions=[dict(priority=1,track_id='research',title='Validate the new finite study',reason='Finite check required')])
        self.path = self.root/'configs/project_state_cn_etf.json'
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.state,ensure_ascii=False),encoding='utf-8')

    def get(self):
        return current_project_status(self.root,today=date(2026,11,4))

    def test_current_status_does_not_inherit_old_ready_candidate(self):
        old = self.root/'data/reports/pre_api_readiness_board'
        old.mkdir(parents=True)
        (old/'pre_api_readiness_board.json').write_text(json.dumps(
            {'overall_status':'clear','selected_candidate':{'case_id':'old','promotion_status':'paper_ready'}}))
        result=self.get()
        self.assertEqual(result['selected_candidate'],{})
        self.assertEqual(result['evidence_counts']['qualified_strategies'],0)
        self.assertEqual(result['evidence_counts']['forward_observation_days'],0)
        self.assertFalse(result['paper_observation_allowed'])
        self.assertEqual(result['generated_at'],'2026-11-04')

    def test_etf_user_confirmation_is_partial_and_preserves_utc_source_label(self):
        costs = dict(ETF_minimum_commission_CNY_per_transaction=5,
                     source='user_reported_2026-11-07UTC', broker_and_rate_unconfirmed=True)
        self.state['user_confirmed_costs'] = dict(costs, BTC_minimum_commission=5)
        for local_date in ('2026-11-06', '2026-11-07'):
            with self.subTest(local_date=local_date):
                self.state['updated_at'] = local_date
                self.write()
                result = current_project_status(self.root, today=date(2026,11,7))
                self.assertEqual(result['user_confirmed_costs'], costs)
                self.assertFalse(result['actual_fees_verified'])
                self.assertFalse(result['paper_observation_allowed'])

    def test_missing_or_malformed_fee_confirmation_is_not_inferred(self):
        valid = dict(ETF_minimum_commission_CNY_per_transaction=5,
                     source='user_reported_2026-11-07UTC', broker_and_rate_unconfirmed=True)
        self.assertEqual(self.get()['user_confirmed_costs'], {})
        bad = [None, [], {}, False]
        bad += [dict(valid, ETF_minimum_commission_CNY_per_transaction=value)
                for value in (True, False, 0, -5, '5', None, float('nan'), float('inf'), 10)]
        bad += [dict(valid, source=value) for value in
                (None, '', 'broker_verified', 'user_reported_invalidUTC',
                 'user_reported_2026-02-30UTC', 'user_reported_20261107UTC')]
        bad += [dict(valid, broker_and_rate_unconfirmed=value) for value in (False, 1, 'true')]
        for costs in bad:
            with self.subTest(costs=costs):
                self.state['user_confirmed_costs'] = costs
                self.write()
                result = self.get()
                self.assertEqual(result['user_confirmed_costs'], {})
                self.assertFalse(result['actual_fees_verified'])

    def test_broker_and_rate_confirmation_does_not_authorize_other_product_costs(self):
        costs = dict(ETF_minimum_commission_CNY_per_transaction=5,
                     source='user_reported_2026-11-07UTC', broker_and_rate_unconfirmed=False,
                     broker='华宝证券', ETF_commission_rate=0.0001)
        self.state['user_confirmed_costs'] = dict(costs, repo_commission_rate=0.0001)
        self.write()
        result = self.get()
        self.assertEqual(result['user_confirmed_costs'], costs)
        self.assertFalse(result['actual_fees_verified'])
        self.assertFalse(result['paper_observation_allowed'])
        for bad in (dict(costs, ETF_commission_rate=True),
                    dict(costs, ETF_commission_rate='0.0001'),
                    dict(costs, broker='')):
            self.state['user_confirmed_costs'] = bad
            self.write()
            self.assertEqual(self.get()['user_confirmed_costs'], {})

    def test_status_read_reflects_new_record_without_execution_permissions(self):
        self.assertEqual(self.get()['evidence_counts']['return_studies'], 12)
        self.state['counts']['return_studies'] = 23
        self.state['state_label'] = '新的工作记录'
        self.write()
        result = self.get()
        self.assertEqual(result['evidence_counts']['return_studies'], 23)
        self.assertEqual(result['state_label'], '新的工作记录')
        self.assertFalse(result['paper_observation_allowed'])
        self.assertFalse(result['live_boundary_allowed'])

    @unittest.skipUnless(shutil.which('node'), 'Node.js needed for status refresh regression')
    def test_browser_status_refresh(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run([shutil.which('node'), '--test', 'tests/gui_project_status.test.cjs'],
                                cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_malformed_stale_or_future_state_never_falls_back(self):
        for content in ('{', '{}', json.dumps(dict(self.state,updated_at='2026-06-13')),
                        json.dumps(dict(self.state,updated_at='2026-11-05'))):
            with self.subTest(content=content):
                self.path.write_text(content)
                self.assertEqual(self.get()['overall_status'],'evidence_blocked')
                self.assertEqual(self.get()['selected_candidate'],{})
        self.path.unlink()
        self.assertEqual(self.get()['overall_status'],'evidence_blocked')

    def test_state_document_cannot_grant_promotion_or_live_permissions(self):
        for key,value in [('paper_observation_allowed',True),('selected_candidate',{'case_id':'fake'}),
                          ('counts',dict(self.state['counts'],qualified_strategies=1))]:
            with self.subTest(key=key):
                original=self.state[key]
                self.state[key]=value;self.write()
                result=self.get()
                self.assertEqual(result['overall_status'],'evidence_blocked')
                self.assertFalse(result['live_boundary_allowed'])
                self.state[key]=original

    def test_missing_authority_document_blocks_status(self):
        (self.root/'current.md').unlink()
        self.assertEqual(self.get()['overall_status'],'evidence_blocked')

    def test_invalid_nested_state_fails_closed_without_daily_exception(self):
        for key in ('blockers', 'next_actions'):
            original=self.state[key]
            for rows in ([{}], [dict(original[0], priority='bad')] if key=='next_actions' else [dict(original[0],blocker_id=None)]):
                self.state[key]=rows; self.write()
                self.assertEqual(self.get()['overall_status'],'evidence_blocked')
                self.assertFalse(current_daily_ops(self.root,'unused')['decision']['paper_trading_allowed'])
            self.state[key]=original

    def test_explicit_history_cannot_reactivate_old_paper_permission(self):
        old=self.root/'history.json'
        old.write_text(json.dumps(dict(decision=dict(status='paper_ready',paper_trading_allowed=True),
                                      advisory_tickets=[dict(asset='old')])) )
        result=build_daily_ops_snapshot(old)
        self.assertTrue(result['historical_decision']['paper_trading_allowed'])
        self.assertFalse(result['decision']['paper_trading_allowed'])
        self.assertEqual(result['advisory_tickets'],[])
        self.assertEqual(result['decision']['status'],'historical_only')

    def test_blank_daily_path_uses_current_status(self):
        with patch('quant_robot.gui.research_service.current_daily_ops',return_value={'current':True}):
            self.assertEqual(build_daily_ops_snapshot(''),{'current':True})

    def test_default_gui_routes_use_current_authority(self):
        with patch('quant_robot.gui.research_service.current_project_status',return_value={'current':True}) as state:
            self.assertEqual(build_project_status_snapshot(),{'current':True})
            state.assert_called_once()
        with patch('quant_robot.gui.research_service.current_daily_ops',return_value={'current':True}) as ops:
            self.assertEqual(build_daily_ops_snapshot(),{'current':True})
            ops.assert_called_once()

    def test_old_daily_ops_cannot_supply_tickets_or_paper_permission(self):
        old=self.root/'old_ops.json'
        old.write_text(json.dumps({'decision':{'paper_trading_allowed':True},
                                   'advisory_tickets':[{'asset':'old'}]}))
        result=current_daily_ops(self.root,old)
        self.assertFalse(result['decision']['paper_trading_allowed'])
        self.assertEqual(result['ticket_count'],0)
        self.assertEqual(result['candidate'],{})
        self.assertFalse(result['legacy_artifact_is_current_authority'])

    def test_risk_and_campaign_are_display_only_without_paper_permission(self):
        self.state['max_single_position_fraction_NAV'] = 1
        self.state['current_risk_policy'] = dict(drawdown=.4,
            daily_loss_fraction_previous_NAV=.02, complete_flat_cooldown_sessions=5)
        self.state['campaign'] = dict(id='campaign', deadline='2026-11-09T16:21:39Z',
                                     checkpoint='checkpoint.json')
        (self.root/'checkpoint.json').write_text(json.dumps(dict(campaign_id='campaign',
            deadline='2026-11-09T16:21:39Z', at='2026-11-04T10:00:00Z',
            phase='synthetic_validation', active_tasks=[dict(id='paper_bridge',
            stage='in_progress', next='Verify recovery')], paper_observation_allowed=True)), encoding='utf-8')
        self.write()
        result = self.get()
        self.assertEqual(result['current_risk_policy']['drawdown'], .4)
        self.assertEqual(result['campaign']['tasks'][0]['task_id'], 'paper_bridge')
        self.assertTrue(result['campaign']['checkpoint_available'])
        self.assertFalse(result['paper_observation_allowed'])
        self.assertEqual(result['selected_candidate'], {})

    def test_missing_or_mismatched_campaign_record_does_not_hide_current_blockers(self):
        self.state['campaign'] = dict(id='campaign', deadline='2026-11-09T16:21:39Z',
                                     checkpoint='checkpoint.json')
        self.write()
        for content in (None, '{', json.dumps(dict(campaign_id='old'))):
            if content is not None:
                (self.root/'checkpoint.json').write_text(content, encoding='utf-8')
            result = self.get()
            self.assertEqual(result['overall_status'], 'research_in_progress')
            self.assertFalse(result['campaign']['checkpoint_available'])
            self.assertFalse(result['paper_observation_allowed'])

    def test_campaign_path_cannot_escape_project(self):
        self.state['campaign'] = dict(id='campaign', deadline='2026-11-09T16:21:39Z',
                                     checkpoint='../checkpoint.json')
        self.write()
        self.assertFalse(self.get()['campaign']['checkpoint_available'])

    def test_incomplete_risk_fields_do_not_inherit_old_profile(self):
        self.state['max_single_position_fraction_NAV'] = 1
        for risk in (None, [], {}, dict(drawdown=.4),
                     dict(drawdown='0.4', daily_loss_fraction_previous_NAV=.02,
                          complete_flat_cooldown_sessions=5),
                     dict(drawdown=.4, daily_loss_fraction_previous_NAV=.02,
                          complete_flat_cooldown_sessions=True)):
            self.state['current_risk_policy'] = risk
            self.write()
            result = self.get()
            self.assertEqual(result['current_risk_policy'], {})
            self.assertIsNone(result['max_single_position_fraction_NAV'])
            self.assertFalse(result['paper_observation_allowed'])
