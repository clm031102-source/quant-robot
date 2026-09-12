import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.paper.simulator import PaperSimulationConfig, run_paper_simulation, write_paper_simulation_artifacts
from quant_robot.signals.pipeline import (
    SignalPipelineConfig, generate_signal_snapshot, generate_signal_snapshot_from_factors, write_signal_snapshot,
)


class DailyInputProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.bars = load_demo_market_bars()
        self.config = SignalPipelineConfig(market='CN_ETF', factor_name='momentum_2', factor_windows=(2,),
            top_n=1, as_of_date='2024-01-08')

    def test_same_recipe_with_changed_input_has_different_bar_identity(self):
        original = generate_signal_snapshot(self.bars, self.config)
        changed = self.bars.copy()
        mask = changed['market'].eq('CN_ETF') & (pd.to_datetime(changed['date']).dt.date <= pd.Timestamp('2024-01-08').date())
        changed.loc[mask, 'volume'] += 1
        result = generate_signal_snapshot(changed, self.config)
        self.assertEqual(original['request'], result['request'])
        self.assertNotEqual(original['input_provenance']['bars']['content_sha256'],
                            result['input_provenance']['bars']['content_sha256'])

    def test_excluded_future_and_other_market_rows_do_not_change_identity(self):
        original = generate_signal_snapshot(self.bars, self.config)['input_provenance']
        changed = self.bars.copy()
        excluded = changed['market'].ne('CN_ETF') | (pd.to_datetime(changed['date']).dt.date > pd.Timestamp('2024-01-08').date())
        changed.loc[excluded, 'volume'] += 1
        result = generate_signal_snapshot(changed, self.config)['input_provenance']
        self.assertEqual(original, result)
        self.assertEqual(result['bars']['last_date'], '2024-01-08')
        self.assertEqual(result['bars']['markets'], ['CN_ETF'])

    def test_precomputed_ranking_values_have_separate_identity(self):
        bars = self.bars[self.bars['market'].eq('CN_ETF')].copy()
        factors = compute_basic_factors(bars, windows=(2,))
        original = generate_signal_snapshot_from_factors(bars, factors, self.config)
        changed = factors.copy()
        changed['factor_value'] += 0.001
        result = generate_signal_snapshot_from_factors(bars, changed, self.config)
        left, right = original['input_provenance'], result['input_provenance']
        self.assertEqual(left['bars'], right['bars'])
        self.assertNotEqual(left['factors']['content_sha256'], right['factors']['content_sha256'])
        self.assertIsNone(result['request']['factor_source'])
        self.assertFalse(right['source_quality_verified'])
        self.assertFalse(right['research_admission_verified'])

    def test_history_records_warmup_and_does_not_require_current_signal_hash(self):
        config = PaperSimulationConfig(market='CN_ETF', factor_name='momentum_2', factor_windows=(2,),
            top_n=1, start_date='2024-01-05', end_date='2024-01-09')
        simulation = run_paper_simulation(self.bars, config)
        historical = simulation['input_provenance']
        current = generate_signal_snapshot(self.bars, self.config)['input_provenance']
        self.assertEqual(historical['artifact_role'], 'historical_simulation')
        self.assertEqual(current['artifact_role'], 'signal_snapshot')
        self.assertLess(historical['bars']['first_date'], config.start_date)
        self.assertEqual(historical['bars']['last_date'], config.end_date)
        self.assertNotEqual(historical['bars']['content_sha256'], current['bars']['content_sha256'])
        self.assertFalse(historical['source_quality_verified'])

    def test_serialized_and_reloaded_fixture_artifacts_preserve_record(self):
        from scripts.run_daily_ops import _read_signal_artifact, _read_simulation_artifact
        signal = generate_signal_snapshot(self.bars, self.config)
        paper = run_paper_simulation(self.bars, PaperSimulationConfig(market='CN_ETF', end_date='2024-01-08'))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_signal_snapshot(signal, root/'signal')
            write_paper_simulation_artifacts(paper, root/'paper')
            self.assertEqual(_read_signal_artifact(root/'signal')['input_provenance'], signal['input_provenance'])
            self.assertEqual(_read_simulation_artifact(root/'paper')['input_provenance'], paper['input_provenance'])

    def test_writer_does_not_invent_provenance_for_legacy_result(self):
        paper = run_paper_simulation(self.bars, PaperSimulationConfig(market='CN_ETF', end_date='2024-01-08'))
        paper.pop('input_provenance', None)
        with tempfile.TemporaryDirectory() as tmp:
            write_paper_simulation_artifacts(paper, Path(tmp))
            manifest = json.loads((Path(tmp)/'manifest.json').read_text())
            self.assertNotIn('input_provenance', manifest)

    def test_empty_targets_and_fills_remain_readable_without_relaxing_csv_errors(self):
        from scripts.run_daily_ops import _read_signal_artifact, _read_simulation_artifact, _read_csv_records
        signal = generate_signal_snapshot(self.bars, self.config)
        signal['targets'] = []
        paper = run_paper_simulation(self.bars, PaperSimulationConfig(market='CN_ETF', end_date='2024-01-08'))
        paper['fills'] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_signal_snapshot(signal, root/'signal')
            write_paper_simulation_artifacts(paper, root/'paper')
            self.assertEqual(_read_signal_artifact(root/'signal')['targets'], [])
            self.assertEqual(_read_simulation_artifact(root/'paper')['fills'], [])
            (root/'broken.csv').write_text('')
            with self.assertRaises(pd.errors.EmptyDataError):
                _read_csv_records(root/'broken.csv')

    def test_empty_frame_and_index_independence_are_explicit(self):
        from quant_robot.storage.input_provenance import describe_input_frame
        frame = pd.DataFrame({'asset_id': ['a'], 'date': ['2024-01-02'], 'market': ['CN_ETF'], 'value': [1.0]})
        first = describe_input_frame(frame, role='fixture_values')
        frame.index = [99]
        self.assertEqual(first, describe_input_frame(frame, role='fixture_values'))
        empty = describe_input_frame(frame.iloc[:0], role='fixture_values')
        self.assertEqual(empty['row_count'], 0)
        self.assertEqual(empty['asset_count'], 0)
        self.assertIsNone(empty['first_date'])
        self.assertIsNone(empty['last_date'])
        self.assertEqual(first['pandas_version'], pd.__version__)
