"""Synthetic-only integration exercise of the fiscal schedule and cash contract."""
import argparse
from dataclasses import replace
from datetime import date, timedelta
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

import pandas as pd
from scripts.run_cn_etf_research_price_basis_drill import ASSET_ID, _bars
from quant_robot.paper.event_hold import EventHoldConfig, ScheduledEntry, run_event_hold_account
from quant_robot.research.fiscal_execution_decision import compare_fiscal_accounts


def run_drill(output_dir):
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=False)
    sessions = [date(2022, 6, 1) + timedelta(days=i) for i in range(66)]
    frame = pd.concat([_bars([4] * 6).iloc[[0]]] * len(sessions), ignore_index=True)
    frame['date'], frame['timestamp'] = sessions, pd.to_datetime(sessions)
    frame['volume'], frame['amount'] = 1_000_000, 4_000_000
    actions_path = directory / 'synthetic_actions.json'
    actions_path.write_text(json.dumps({'schema_version': 3, 'source_ref': 'synthetic only no real prices',
        'coverage_start': str(sessions[0]), 'coverage_end': str(sessions[-1]),
        'asset_ids': [ASSET_ID], 'events': []}), encoding='utf-8')
    entries = [ScheduledEntry(f'fixture-{i}', sessions[i-1], sessions[i]) for i in (1, 23, 45)]
    config = EventHoldConfig(asset_id=ASSET_ID, corporate_actions_path=actions_path,
        cash_amount_policy='gross_announcement_assumption', slippage_bps=0, market_impact_bps=0)
    results = {}
    for minimum in (0, 5, 10):
        settings = replace(config, minimum_commission=minimum)
        selected = run_event_hold_account(frame, settings, entries=[entries[0], entries[2]], sessions=sessions)
        unconditional = run_event_hold_account(frame, settings, entries=entries, sessions=sessions)
        results[str(minimum)] = {'selected': selected, 'unconditional': unconditional,
            'comparison': compare_fiscal_accounts(selected, unconditional)}
    report = {'stage': 'synthetic_event_hold_drill', 'source_origin': 'synthetic_fixture',
        'real_prices_read': False, 'real_fiscal_factors_computed': False, 'research_admission_granted': False,
        'new_forward_paper_days': 0, 'scenarios': results}
    (directory / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    result = run_drill(args.output_dir)
    print(json.dumps({'stage': result['stage'], 'source_origin': result['source_origin'],
        'scenarios': {key: value['comparison'] for key, value in result['scenarios'].items()}}, indent=2))


if __name__ == '__main__':
    main()
