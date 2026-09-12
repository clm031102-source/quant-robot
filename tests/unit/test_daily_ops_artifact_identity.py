from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.ops.daily_ops import build_daily_ops_pack


def identity_fixture():
    recipe = {'market': 'CN_ETF', 'factor_source': 'technical', 'factor_name': 'momentum_2',
              'factor_windows': [2], 'top_n': 1, 'rebalance_interval': 1}
    weights = {'max_asset_weight': 0.1, 'max_market_weight': 0.5,
               'max_gross_exposure': 0.5, 'min_cash_weight': 0.5}
    candidate = {'case_id': 'synthetic_case_a', 'promotion_status': 'paper_ready', **recipe}
    signal = {'data_mode': 'fixture', 'as_of_date': '2024-01-08', 'signal_date': '2024-01-08',
              'request': {key: value for key, value in {**recipe, **weights}.items() if key != 'rebalance_interval'},
              'targets': [], 'rebalance_plan': [{'asset_id': 'CN_ETF_XSHG_510300', 'market': 'CN_ETF',
                  'estimated_quantity_delta': 100, 'target_weight': 0.1, 'delta_value': 500}]}
    paper = {'data_mode': 'fixture', 'request': {**recipe, **weights},
             'metrics': {'max_equity_drawdown': -0.01}, 'fills': [], 'execution_events': [], 'guard_events': []}
    return {'promotion_review': {'selected_candidate': candidate}, 'readiness_board': {'blocker_register': []},
            'signal_snapshot': signal, 'paper_simulation': paper, 'run_date': '2024-01-09'}


class DailyOpsArtifactIdentityTests(unittest.TestCase):
    def test_recipe_survives_promotion_console_and_review_without_defaults(self):
        from quant_robot.promotion.gate import build_promotion_report, PromotionGateConfig
        from quant_robot.ops.promotion_console import build_promotion_operations_console
        from quant_robot.ops.review_packet import build_promotion_review_packet
        from quant_robot.ops.daily_ops_identity import require_daily_candidate_recipe
        candidate = identity_fixture()['promotion_review']['selected_candidate']
        candidate['factor_windows'] = '(2, 3)'
        # Only metadata propagation is evaluated; this is not a successful market candidate.
        for omit in (None, 'factor_source', 'factor_windows', 'rebalance_interval'):
            with self.subTest(omit=omit), tempfile.TemporaryDirectory() as tmp:
                row = deepcopy(candidate)
                if omit:
                    del row[omit]
                report = build_promotion_report(walk_forward_rows=[row], config=PromotionGateConfig())
                path = Path(tmp) / 'report.json'
                path.write_text(json.dumps(report), encoding='utf-8')
                selected = build_promotion_review_packet(build_promotion_operations_console(path))['selected_candidate']
                if omit:
                    self.assertIsNone(selected.get(omit))
                    with self.assertRaisesRegex(ValueError, 'candidate recipe'):
                        require_daily_candidate_recipe(selected)
                else:
                    recipe = require_daily_candidate_recipe(selected)
                    self.assertEqual(recipe['factor_windows'], [2, 3])
                    self.assertEqual(recipe['factor_source'], 'technical')
                    self.assertEqual(recipe['top_n'], 1)
                    self.assertEqual(recipe['rebalance_interval'], 1)

    def test_daily_cli_generates_the_explicit_recipe_without_parsing_case_labels(self):
        from scripts.run_daily_ops import run_daily_ops
        args = identity_fixture()
        candidate = args['promotion_review']['selected_candidate']
        candidate['case_id'] = 'synthetic_top99_reb99'
        candidate['factor_windows'] = '(2, 3)'
        weights = {key: args['signal_snapshot']['request'][key] for key in (
            'max_asset_weight', 'max_market_weight', 'max_gross_exposure', 'min_cash_weight')}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {'promotion': args['promotion_review'], 'readiness': args['readiness_board'],
                     'profile': {'selected_profile': {'case_id': candidate['case_id'], 'profile_id': 'synthetic', **weights}}}
            for name, payload in files.items():
                (root / f'{name}.json').write_text(json.dumps(payload), encoding='utf-8')
            pack = run_daily_ops(promotion_review=root / 'promotion.json', readiness_board=root / 'readiness.json',
                paper_profile_pack=root / 'profile.json', source='fixture', data_root=root / 'unread',
                run_date='2024-01-10', end_date='2024-01-10', portfolio_value=10000,
                output_dir=root / 'result', max_drawdown_limit=0.08)
            request = json.loads((root / 'result/paper_simulation/manifest.json').read_text(encoding='utf-8'))['request']
            self.assertEqual(request['top_n'], 1)
            self.assertEqual(request['rebalance_interval'], 1)
            self.assertEqual(request['factor_windows'], [2, 3])
            self.assertEqual(pack['decision']['status'], 'paper_ready', pack['decision'])
            self.assertEqual(pack['decision']['artifact_identity']['status'], 'recipe_matched')

    def test_daily_cli_rejects_incomplete_recipe_before_generation(self):
        from scripts import run_daily_ops as daily
        args = identity_fixture()
        del args['promotion_review']['selected_candidate']['factor_windows']
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, payload in (('promotion', args['promotion_review']), ('readiness', {}), ('profile', {})):
                (root / f'{name}.json').write_text(json.dumps(payload), encoding='utf-8')
            with patch.object(daily, 'run_signal_snapshot') as signal, patch.object(daily, 'run_simulation') as paper:
                with self.assertRaisesRegex(ValueError, 'candidate recipe.*factor_windows'):
                    daily.run_daily_ops(promotion_review=root / 'promotion.json', readiness_board=root / 'readiness.json',
                        paper_profile_pack=root / 'profile.json', source='fixture', output_dir=root / 'result')
                signal.assert_not_called()
                paper.assert_not_called()
                self.assertFalse((root / 'result').exists())

    def test_complete_matching_recipe_keeps_source_certification_separate(self):
        pack = build_daily_ops_pack(**identity_fixture())
        identity = pack['decision']['artifact_identity']
        self.assertEqual(pack['decision']['status'], 'paper_ready')
        self.assertEqual(identity['status'], 'recipe_matched')
        self.assertEqual(len(identity['candidate_recipe_sha256']), 64)
        self.assertFalse(identity['source_binding_verified'])
        self.assertFalse(identity['research_admission_verified'])

    def test_different_factor_results_cannot_issue_candidate_tickets(self):
        args = identity_fixture()
        args['signal_snapshot']['request']['factor_name'] = 'reversal_2'
        args['paper_simulation']['request']['factor_name'] = 'volatility_2'
        pack = build_daily_ops_pack(**args)
        self.assertEqual(pack['decision']['status'], 'blocked')
        self.assertEqual(pack['advisory_tickets'], [])
        self.assertIn('daily_artifact_identity_invalid', pack['decision']['blocking_reasons'])

    def test_missing_recipe_fields_are_not_inferred_from_case_name(self):
        for role in ('candidate', 'signal', 'simulation'):
            for field in ('market', 'factor_source', 'factor_name', 'factor_windows', 'top_n'):
                with self.subTest(role=role, field=field):
                    args = identity_fixture()
                    mapping = args['promotion_review']['selected_candidate'] if role == 'candidate' else args[
                        'signal_snapshot' if role == 'signal' else 'paper_simulation']['request']
                    del mapping[field]
                    pack = build_daily_ops_pack(**args)
                    self.assertEqual(pack['advisory_tickets'], [])
                    self.assertEqual(pack['decision']['artifact_identity']['status'], 'blocked')

    def test_same_case_label_cannot_hide_parameter_or_weight_changes(self):
        for role, field, value in (
            ('signal_snapshot', 'top_n', 2), ('signal_snapshot', 'factor_windows', [3]),
            ('signal_snapshot', 'factor_source', 'unverified_precomputed'),
            ('paper_simulation', 'rebalance_interval', 5),
            ('paper_simulation', 'max_asset_weight', 0.3),
            ('signal_snapshot', 'market', 'US'),
            ('paper_simulation', 'case_id', 'other_case'),
        ):
            with self.subTest(role=role, field=field):
                args = identity_fixture()
                args[role]['request'][field] = value
                pack = build_daily_ops_pack(**args)
                self.assertEqual(pack['decision']['status'], 'blocked')
                self.assertEqual(pack['advisory_tickets'], [])

    def test_readiness_and_profile_cannot_select_different_candidates(self):
        for owner in ('readiness', 'profile', 'same_case_different_recipe'):
            with self.subTest(owner=owner):
                args = identity_fixture()
                if owner == 'profile':
                    args['paper_profile'] = {'case_id': 'other_case', 'profile_id': 'synthetic_profile'}
                else:
                    candidate = deepcopy(args['promotion_review']['selected_candidate'])
                    candidate['case_id' if owner == 'readiness' else 'top_n'] = 'other_case' if owner == 'readiness' else 2
                    args['readiness_board']['selected_candidate'] = candidate
                self.assertEqual(build_daily_ops_pack(**args)['advisory_tickets'], [])

    def test_profile_weight_changes_and_missing_case_binding_are_rejected(self):
        for profile in ({'profile_id': 'unbound'}, {'case_id': 'synthetic_case_a', 'max_asset_weight': 0.8}):
            with self.subTest(profile=profile):
                args = identity_fixture()
                args['paper_profile'] = profile
                self.assertEqual(build_daily_ops_pack(**args)['decision']['status'], 'blocked')

    def test_bound_profile_risk_overlay_takes_precedence_over_research_weights(self):
        args = identity_fixture()
        candidate = args['promotion_review']['selected_candidate']
        candidate['max_asset_weight'] = 1.0
        args['paper_profile'] = {'case_id': candidate['case_id'], 'profile_id': 'synthetic_profile',
                                 'max_asset_weight': 0.1}
        self.assertEqual(build_daily_ops_pack(**args)['decision']['artifact_identity']['status'], 'recipe_matched')

    def test_profile_guard_and_profile_id_mismatches_are_blocked(self):
        for field, expected, actual in (('max_drawdown_guard', 0.12, None),
                                        ('guard_cooldown_periods', 3, 0),
                                        ('risk_profile_id', 'profile_a', 'profile_b')):
            with self.subTest(field=field):
                args = identity_fixture()
                profile = {'case_id': 'synthetic_case_a', 'profile_id': 'profile_a'}
                if field != 'risk_profile_id':
                    profile[field] = expected
                args['paper_profile'] = profile
                args['paper_simulation']['request'][field] = actual
                self.assertEqual(build_daily_ops_pack(**args)['advisory_tickets'], [])

    def test_matching_guard_can_explicitly_be_disabled(self):
        args = identity_fixture()
        args['paper_profile'] = {'case_id': 'synthetic_case_a', 'profile_id': 'profile_a',
                                 'max_drawdown_guard': None, 'guard_cooldown_periods': 0}
        args['paper_simulation']['request'].update(max_drawdown_guard=None, guard_cooldown_periods=0,
                                                     risk_profile_id='profile_a')
        self.assertEqual(build_daily_ops_pack(**args)['decision']['artifact_identity']['status'], 'recipe_matched')

    def test_invalid_recipe_values_fail_without_coercing_booleans_or_fractional_counts(self):
        for field, value in (('top_n', True), ('top_n', 1.9), ('factor_windows', [True]),
                             ('top_n', '1.000000000000000001'),
                             ('factor_windows', [2, 2]), ('factor_windows', 'not a tuple'),
                             ('factor_windows', []), ('rebalance_interval', 0),
                             ('factor_name', 123), ('max_asset_weight', 'nan')):
            with self.subTest(field=field, value=value):
                args = identity_fixture()
                args['paper_simulation']['request'][field] = value
                self.assertEqual(build_daily_ops_pack(**args)['decision']['status'], 'blocked')

    def test_csv_tuple_and_json_list_representations_match(self):
        args = identity_fixture()
        args['promotion_review']['selected_candidate']['factor_windows'] = '(2,)'
        args['promotion_review']['selected_candidate']['top_n'] = '1'
        self.assertEqual(build_daily_ops_pack(**args)['decision']['artifact_identity']['status'], 'recipe_matched')

    def test_fresh_builtin_fixture_signal_and_simulation_share_a_recipe(self):
        from scripts.run_signal_snapshot import run_signal_snapshot
        from scripts.run_paper_simulation import run_simulation
        args = identity_fixture()
        weights = {key: args['signal_snapshot']['request'][key] for key in (
            'max_asset_weight', 'max_market_weight', 'max_gross_exposure', 'min_cash_weight')}
        args['signal_snapshot'] = run_signal_snapshot(source='fixture', market='CN_ETF', factor_name='momentum_2',
            factor_windows=(2,), top_n=1, as_of_date='2024-01-10', **weights)
        args['paper_simulation'] = run_simulation(source='fixture', market='CN_ETF', factor_name='momentum_2',
            factor_windows=(2,), top_n=1, end_date='2024-01-10', **weights)
        args['run_date'] = '2024-01-10'
        pack = build_daily_ops_pack(**args)
        self.assertEqual(pack['decision']['artifact_identity']['status'], 'recipe_matched', pack['decision'])

    def test_precomputed_signal_source_is_not_inferred_as_technical(self):
        from quant_robot.data.fixtures import load_demo_market_bars
        from quant_robot.factors.technical import compute_basic_factors
        from quant_robot.signals.pipeline import SignalPipelineConfig, generate_signal_snapshot_from_factors
        bars = load_demo_market_bars()
        bars = bars[bars['market'].eq('CN_ETF')]
        config = SignalPipelineConfig(market='CN_ETF', factor_windows=(2,))
        factors = compute_basic_factors(bars, windows=(2,))
        unbound = generate_signal_snapshot_from_factors(bars, factors, config)
        self.assertIsNone(unbound['request']['factor_source'])
        declared = generate_signal_snapshot_from_factors(bars, factors, config, factor_source='technical')
        self.assertEqual(declared['request']['factor_source'], 'technical')
