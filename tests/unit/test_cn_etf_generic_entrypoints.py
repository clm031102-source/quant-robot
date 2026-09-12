import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quant_robot.data.fixtures import load_demo_market_bars
from scripts import run_experiment_grid as grid
from scripts import run_paper_simulation as paper
from scripts import run_research_pipeline as research
from scripts import run_signal_snapshot as signal
from scripts import run_walk_forward as walk_forward


class CnEtfGenericEntrypointTests(unittest.TestCase):
    def test_grid_and_walk_forward_cli_preflight_without_results(self):
        root = Path(__file__).resolve().parents[2]
        for script, source in (
            ('run_experiment_grid.py', 'processed-bars'),
            ('run_walk_forward.py', 'processed-bars'),
            ('run_walk_forward.py', 'authority-bars'),
        ):
            with self.subTest(script=script, source=source), tempfile.TemporaryDirectory() as tmp:
                config = Path(tmp)/'config.json'
                grid_config = {'markets': ['US', 'CN_ETF'], 'factor_names': ['momentum_2']}
                payload = grid_config if script == 'run_experiment_grid.py' else {
                    'split_date': '2024-01-08', 'experiment_grid': grid_config,
                }
                config.write_text(json.dumps(payload), encoding='utf-8')
                output = Path(tmp)/'no-results'
                result = subprocess.run(
                    [sys.executable, str(root/'scripts'/script), '--source', source,
                     '--config', str(config), '--data-root', str(Path(tmp)/'unread-data'),
                     '--output-dir', str(output)],
                    cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=30,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('CN_ETF processed data requires a registered', result.stderr)
                self.assertFalse(output.exists())

    def test_grid_and_walk_forward_reject_before_membership_and_stock_gates(self):
        for module, function, gate_name in (
            (grid, grid.run_grid, '_enforce_cn_stock_startup_gate'),
            (walk_forward, walk_forward.run_walk_forward, '_enforce_cn_stock_walk_forward_inputs'),
        ):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                config = Path(tmp)/'config.json'
                grid_config = {'markets': ['CN', 'CN_ETF']}
                payload = grid_config if module is grid else {
                    'split_date': '2024-01-08', 'experiment_grid': grid_config,
                }
                config.write_text(json.dumps(payload), encoding='utf-8')
                with patch.object(module, gate_name) as gate, \
                        patch.object(module, '_attach_processed_cn_etf_rotation_membership') as membership, \
                        patch.object(module, '_load_bars') as load:
                    with self.assertRaisesRegex(ValueError, 'CN_ETF.*registered'):
                        function(config_path=config, source='processed-bars', data_root='unread-data')
                    gate.assert_not_called()
                    membership.assert_not_called()
                    load.assert_not_called()

    def test_multi_market_loaders_check_all_markets_before_any_read(self):
        for module in (grid, walk_forward):
            for market in ('CN_ETF', 'ALL', ' cn_etf '):
                with self.subTest(module=module.__name__, market=market), \
                        patch.object(module, 'load_processed_bars', return_value=load_demo_market_bars()) as load:
                    with self.assertRaisesRegex(ValueError, 'CN_ETF.*registered'):
                        module._load_bars('processed-bars', Path('unread-data'), ('US', market))
                    load.assert_not_called()

    def test_authority_loader_rejects_etf_before_reading_source_config(self):
        with patch.object(walk_forward, 'load_authority_processed_bars_from_config') as load:
            with self.assertRaisesRegex(ValueError, 'CN_ETF.*registered'):
                walk_forward._load_bars('authority-bars', Path('unread-config.json'), ('CN_ETF',))
            load.assert_not_called()

    def test_real_cli_processes_deny_without_writing_results(self):
        root = Path(__file__).resolve().parents[2]
        for script in ('run_research_pipeline.py', 'run_signal_snapshot.py', 'run_paper_simulation.py'):
            with self.subTest(script=script), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp)/'no-results'
                result = subprocess.run(
                    [sys.executable, str(root/'scripts'/script), '--source', 'processed-bars',
                     '--market', 'CN_ETF', '--data-root', str(Path(tmp)/'unread-data'),
                     '--output-dir', str(output)],
                    cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=30,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('CN_ETF processed data requires a registered', result.stderr)
                self.assertFalse(output.exists())

    def test_research_loader_rejects_before_reading_etf_bars(self):
        with patch.object(research, 'load_processed_bars', return_value=load_demo_market_bars()) as load:
            with self.assertRaisesRegex(ValueError, 'CN_ETF.*registered'):
                research.load_research_bars('processed-bars', Path('fixture-not-opened'), 'CN_ETF')
            load.assert_not_called()

    def test_signal_and_paper_reject_before_positions_and_outputs(self):
        for module, function in ((signal, signal.run_signal_snapshot), (paper, paper.run_simulation)):
            with self.subTest(function=function.__name__), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp)/'must-not-exist'
                with patch.object(module, 'load_processed_bars') as load:
                    with self.assertRaisesRegex(ValueError, 'CN_ETF.*registered'):
                        function(source='processed-bars', market='CN_ETF', data_root='fixture-not-opened',
                                 positions_csv='fixture-positions-not-opened.csv', output_dir=output)
                    load.assert_not_called()
                    self.assertFalse(output.exists())

    def test_all_market_and_case_aliases_cannot_enter_without_etf_authorization(self):
        for module, function in ((signal, signal.run_signal_snapshot), (paper, paper.run_simulation)):
            for market in ('ALL', 'all', 'cn_etf', ' CN_ETF '):
                with self.subTest(module=module.__name__, market=market):
                    with patch.object(module, '_enforce_cn_stock_' + ('signal_snapshot_inputs' if module is signal else 'paper_simulation_inputs')) as stock_gate, \
                            patch.object(module, 'load_processed_bars') as load:
                        with self.assertRaisesRegex(ValueError, 'CN_ETF.*registered'):
                            function(source='processed-bars', market=market, data_root='fixture-not-opened')
                        load.assert_not_called()
                        stock_gate.assert_not_called()

    def test_private_loaders_also_refuse_protected_data(self):
        for module in (signal, paper):
            with self.subTest(module=module.__name__), patch.object(module, 'load_processed_bars') as load:
                with self.assertRaisesRegex(ValueError, 'CN_ETF.*registered'):
                    module._load_bars('processed-bars', Path('fixture-not-opened'), 'ALL')
                load.assert_not_called()

    def test_fixture_market_data_still_loads_without_research_authorization(self):
        for function in (research.load_research_bars, signal._load_bars, paper._load_bars):
            with self.subTest(function=function.__module__):
                bars = function('fixture', Path('fixture-not-opened'), 'ALL')
                self.assertIn('CN_ETF', set(bars['market']))
        for module in (grid, walk_forward):
            with self.subTest(module=module.__name__):
                bars = module._load_bars('fixture', Path('fixture-not-opened'), ('CN_ETF',))
                self.assertIn('CN_ETF', set(bars['market']))

    def test_non_etf_research_loader_behavior_is_preserved(self):
        with patch.object(research, 'load_processed_bars', return_value='fixture-us-result') as load:
            result = research.load_research_bars('processed-bars', Path('fixture-root'), 'US')
            self.assertEqual(result, 'fixture-us-result')
            self.assertEqual(load.call_args.args[1], 'US')
