import json
from datetime import date
from pathlib import Path
import tempfile
import unittest
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
