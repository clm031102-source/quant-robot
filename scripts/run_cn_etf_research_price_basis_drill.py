"""Run fixed synthetic price/action cases; this command has no market-data input."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script invocation
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.normalize import normalize_ohlcv
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.paper.corporate_actions import CorporateActionLedger
from quant_robot.research.labels import make_forward_returns
from quant_robot.research.price_basis import build_cash_action_research_prices
from quant_robot.signals.pipeline import SignalPipelineConfig, generate_signal_snapshot


ASSET_ID = 'CN_ETF_XSHG_510300'
DATES = [date.fromisoformat(value) for value in
         ['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-08', '2024-01-09']]


def run_drill(output_dir: Path) -> dict:
    if (output_dir / 'report.json').exists():
        raise FileExistsError('Use a new output directory to preserve the earlier drill evidence')
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = [
        ('dividend_neutral', [10, 10, 9, 9, 9, 9], 'cash_dividend'),
        ('dividend_reinvestment_gap', [10, 10, 9, 18, 18, 18], 'cash_dividend'),
        ('split_neutral', [10, 10, 5, 5, 5, 5], 'share_split'),
    ]
    results = {}
    for name, prices, kind in cases:
        directory = output_dir / name
        directory.mkdir(exist_ok=True)
        bars = _bars(prices)
        action_path = directory / 'actions.json'
        action_path.write_text(json.dumps(_actions(kind), indent=2), encoding='utf-8')
        transformed = build_cash_action_research_prices(bars, action_path, sessions=DATES)
        positions = {ASSET_ID: 100.0}
        cash = 0.0
        ledger = CorporateActionLedger(action_path, {ASSET_ID}, DATES, positions)
        observations = []
        for session, raw_price, analytical_price in zip(DATES, bars['close'], transformed.bars['adj_close']):
            received, _ = ledger.before_session(session, positions, [])
            cash += received
            pre_close_cash = cash
            cash += ledger.after_session(session, positions)
            observations.append({'date': str(session), 'raw_close': raw_price,
                'quantity': positions[ASSET_ID], 'cash_before_close': pre_close_cash, 'cash_after_close': cash,
                'dividend_receivable': ledger.receivable,
                'account_equity': positions[ASSET_ID] * raw_price + cash + ledger.receivable,
                'theoretical_index_value': 100 * analytical_price})
        table = pd.DataFrame(observations)
        labels = make_forward_returns(transformed.bars, horizons=(1,), execution_lag=1)
        raw_labels = make_forward_returns(bars, horizons=(1,), execution_lag=1)
        factor = compute_basic_factors(transformed.bars, windows=(1,), factor_names=('momentum_1',))
        signal = generate_signal_snapshot(transformed.bars, SignalPipelineConfig(
            market='CN_ETF', factor_name='momentum_1', factor_windows=(1,),
            top_n=1, as_of_date=str(DATES[-1])))
        checks = {
            'research_ex_date_label_zero': abs(float(labels.iloc[0]['forward_return'])) < 1e-12,
            'research_ex_date_momentum_zero': abs(float(factor.iloc[2]['factor_value'])) < 1e-12,
            'ex_date_account_equity_1000': observations[2]['account_equity'] == 1000,
            'raw_prices_preserved': bars['close'].equals(transformed.bars['close']),
            'signal_reference_is_raw_price': signal['targets'][0]['latest_price'] == prices[-1],
            'source_audit_remains_unverified': transformed.evidence['source_audit_verified'] is False,
        }
        if kind == 'cash_dividend':
            checks.update(ex_date_cash_zero=observations[2]['cash_after_close'] == 0,
                ex_date_receivable_100=observations[2]['dividend_receivable'] == 100,
                pay_date_cash_unavailable_before_close=observations[4]['cash_before_close'] == 0,
                pay_date_cash_100_after_close=observations[4]['cash_after_close'] == 100,
                no_second_income_at_payment=observations[3]['account_equity'] == observations[4]['account_equity'])
        if name == 'dividend_reinvestment_gap':
            checks.update(account_before_payment_1900=observations[3]['account_equity'] == 1900,
                theoretical_reinvestment_value_2000=observations[3]['theoretical_index_value'] == 2000)
        if kind == 'share_split':
            checks['post_split_quantity_200'] = observations[2]['quantity'] == 200
        bars.to_csv(directory / 'raw_bars.csv', index=False)
        transformed.bars.to_csv(directory / 'research_bars.csv', index=False)
        transformed.observations.to_csv(directory / 'research_calculation.csv', index=False)
        table.to_csv(directory / 'account_comparison.csv', index=False)
        (directory / 'basis_evidence.json').write_text(json.dumps(transformed.evidence, indent=2), encoding='utf-8')
        results[name] = {'checks': checks, 'passed': all(checks.values()),
            'raw_ex_date_label': float(raw_labels.iloc[0]['forward_return']),
            'research_ex_date_label': float(labels.iloc[0]['forward_return']),
            'account_ending_equity': observations[-1]['account_equity'],
            'theoretical_index_ending_value': observations[-1]['theoretical_index_value'],
            'signal_reference_price': signal['targets'][0]['latest_price'],
            'files': {str(path.relative_to(output_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in sorted(directory.iterdir()) if path.is_file()}}
    report = {'at': datetime.now(timezone.utc).isoformat(), 'data_mode': 'synthetic_fixture',
        'status': 'passed' if all(item['passed'] for item in results.values()) else 'failed',
        'cases': results, 'source_audit_verified': False, 'research_admission_verified': False,
        'new_forward_paper_days': 0, 'market_data_requests': 0, 'executable': False,
        'scope': 'Fixed analytical and ledger arithmetic; no strategy trading, costs, fresh quotes or real sources'}
    (output_dir / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def _bars(prices: list[int]) -> pd.DataFrame:
    asset = Asset(ASSET_ID, '510300.SH', 'CN_ETF', 'XSHG', 'etf', 'CNY', 'Asia/Shanghai', 'XSHG')
    raw = pd.DataFrame({'date': DATES, 'open': prices, 'high': prices, 'low': prices,
                        'close': prices, 'volume': [10000] * len(DATES),
                        'amount': [price * 10000 for price in prices]})
    bars = normalize_ohlcv(raw, asset, 'fixture', '1d')
    bars['ingested_at'] = pd.Timestamp('2024-02-01', tz='UTC')
    return bars


def _actions(kind: str) -> dict:
    event = {'event_id': 'synthetic-event', 'asset_id': ASSET_ID, 'kind': kind,
             'announced_date': '2024-01-02', 'ex_date': '2024-01-04'}
    if kind == 'cash_dividend':
        event.update(record_date='2024-01-03', pay_date='2024-01-08', net_cash_per_share=1.0)
    else:
        event.update(tradable_date='2024-01-04', share_ratio=2.0)
    return {'schema_version': 1, 'source_ref': 'synthetic fixture; not official fund events',
            'coverage_start': str(DATES[0]), 'coverage_end': str(DATES[-1]),
            'asset_ids': [ASSET_ID], 'events': [event]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('data/reports/cn_etf_research_price_basis_drill'))
    args = parser.parse_args()
    report = run_drill(args.output_dir)
    print(json.dumps({'status': report['status'], 'cases': len(report['cases']),
                      'report': str(args.output_dir / 'report.json')}, ensure_ascii=False))
    raise SystemExit(0 if report['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
