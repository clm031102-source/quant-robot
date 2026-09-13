"""Attach a declared fixed hold to an already computed paper cash account."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from quant_robot.paper.account_comparison import calendar_date, compare_cash_accounts
from quant_robot.paper.fixed_hold import FixedHoldConfig, FixedHoldEntry, run_fixed_hold_benchmark


def load_fixed_hold_entries(path: str | Path) -> tuple[tuple[FixedHoldEntry, ...], str]:
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    if (not isinstance(data, dict) or set(data) != {'schema_version', 'entries'}
            or type(data.get('schema_version')) is not int or data['schema_version'] != 1
            or not isinstance(data['entries'], list) or not data['entries']):
        raise ValueError('Unsupported fixed-hold entry declaration')
    entries = []
    for entry in data['entries']:
        if not isinstance(entry, dict) or set(entry) != {'asset_id', 'quantity', 'limit_price'}:
            raise ValueError('Fixed-hold entries require exactly asset_id, quantity and limit_price')
        entries.append(FixedHoldEntry(**entry))
    return tuple(entries), hashlib.sha256(raw).hexdigest()


def attach_fixed_hold_comparison(bars: pd.DataFrame, result: dict, *,
                                  entries: tuple[FixedHoldEntry, ...], source_path: str | Path,
                                  source_sha256: str) -> dict:
    """Inherit financial terms; the entry file cannot override cash or fees."""
    # Validate the existing account before building a comparison. This also
    # rejects preloaded holdings disguised as a purchase from the same capital.
    compare_cash_accounts(result, result)
    request = result['request']
    sessions = [calendar_date(row['date']) for row in result['equity_curve']]
    config = FixedHoldConfig(entries=entries,
        initial_cash=request['initial_cash'], commission_bps=request['commission_bps'],
        minimum_commission=request['minimum_commission'], slippage_bps=request['slippage_bps'],
        market_impact_bps=request['market_impact_bps'], max_participation_rate=request['max_participation_rate'],
        corporate_actions_path=request['corporate_actions_path'])
    frame = bars[bars['date'].map(calendar_date).isin(sessions)]
    benchmark = run_fixed_hold_benchmark(frame, config, sessions=sessions)
    comparison = compare_cash_accounts(result, benchmark)
    return {**result, 'request': {**request, 'fixed_hold_benchmark_path': str(source_path),
                                 'fixed_hold_benchmark_sha256': source_sha256},
            'fixed_hold_benchmark': benchmark, 'account_comparison': comparison}
