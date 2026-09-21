"""Fixed synthetic cash-account comparison; no market-data input or factor."""
from __future__ import annotations

import argparse
import copy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd

from scripts.run_cn_etf_research_price_basis_drill import ASSET_ID, DATES, _actions, _bars
from quant_robot.paper.account_comparison import compare_cash_accounts
from quant_robot.paper.fixed_hold import FixedHoldConfig, FixedHoldEntry, run_fixed_hold_benchmark


def run_drill(output_dir: Path) -> dict:
    if output_dir.exists():
        raise FileExistsError('Use a new output directory to preserve previous evidence')
    output_dir.mkdir(parents=True)
    other = 'CN_ETF_XSHE_159915'
    changing = _bars([10, 10, 9, 9.5, 9.5, 9.5])
    flat = _bars([10] * 6).assign(asset_id=other, symbol='159915.SZ', exchange='XSHE', calendar='XSHE')
    bars = pd.concat([changing, flat], ignore_index=True)
    dataset = _actions('cash_dividend')
    dataset['asset_ids'] = [ASSET_ID, other]
    path = output_dir / 'actions.json'
    path.write_text(json.dumps(dataset, indent=2), encoding='utf-8')
    config = FixedHoldConfig(entries=(FixedHoldEntry(ASSET_ID, 100, 10),), initial_cash=10000,
        commission_bps=5, minimum_commission=5, slippage_bps=0, market_impact_bps=0,
        max_participation_rate=.01, corporate_actions_path=path)
    accounts = {
        'cash_distribution_account': run_fixed_hold_benchmark(bars, config, sessions=DATES),
        'flat_price_account': run_fixed_hold_benchmark(bars,
            replace(config, entries=(FixedHoldEntry(other, 100, 10),)), sessions=DATES),
    }
    for name, account in accounts.items():
        (output_dir / f'{name}.json').write_text(json.dumps(account, indent=2), encoding='utf-8')
        pd.DataFrame(account['equity_curve']).to_csv(output_dir / f'{name}.csv', index=False)
    # The comparison consumes the persisted result, not only the in-memory objects.
    left = json.loads((output_dir / 'cash_distribution_account.json').read_text())
    right = json.loads((output_dir / 'flat_price_account.json').read_text())
    comparison = compare_cash_accounts(left, right)
    checks = {
        'same_initial_10000': left['equity_curve'][0]['equity'] == right['equity_curve'][0]['equity'] == 10000,
        'same_economics': left['request']['execution_economics'] == right['request']['execution_economics'],
        'one_buy_each': len(left['fills']) == len(right['fills']) == 1,
        'distribution_account_10045': left['metrics']['ending_equity'] == 10045,
        'flat_account_9995': right['metrics']['ending_equity'] == 9995,
        'relative_account_return_005': abs(comparison['relative_return'] - .005) < 1e-12,
        'no_extra_pay_date_income': left['equity_curve'][3]['equity'] == left['equity_curve'][4]['equity'],
        'net_cash_unavailable_before_pay_close': left['equity_curve'][4]['cash_before_close'] == 8995,
        'source_and_alpha_unverified': not comparison['source_quality_verified'] and not comparison['risk_adjusted_alpha_verified'],
    }
    failures = {}
    for name in ('different_fee', 'different_dates', 'free_initial_asset'):
        invalid = copy.deepcopy(right)
        if name == 'different_fee':
            invalid['request']['execution_economics']['minimum_commission'] = 0
        elif name == 'different_dates':
            invalid['equity_curve'].pop()
        else:
            invalid['equity_curve'][0]['equity'] += 1000
        try:
            compare_cash_accounts(left, invalid)
        except ValueError as exc:
            failures[name] = str(exc)
        checks[name + '_rejected'] = name in failures
    bars.to_csv(output_dir / 'synthetic_bars.csv', index=False)
    report = {'at': datetime.now(timezone.utc).isoformat(),
        'status': 'passed' if all(checks.values()) else 'failed', 'data_mode': 'synthetic_fixture',
        'checks': checks, 'comparison': comparison, 'rejection_reasons': failures,
        'market_data_requests': 0, 'real_factor_generation': 0, 'new_forward_paper_days': 0,
        'executable': False, 'source_audit_verified': False, 'net_positive_ev_verified': False,
        'scope': 'Declared hypothetical paths and accounting only; different assets are not certified to have equal risk',
        'files': {item.name: hashlib.sha256(item.read_bytes()).hexdigest()
                  for item in output_dir.iterdir() if item.is_file()}}
    (output_dir / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('data/reports/cn_etf_fixed_hold_drill'))
    args = parser.parse_args()
    report = run_drill(args.output_dir)
    print(json.dumps({'status': report['status'], 'report': str(args.output_dir / 'report.json')}))
    raise SystemExit(0 if report['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
