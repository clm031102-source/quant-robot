# Phase 5.1 Risk Candidate Selector

Phase 5.1 adds a fail-closed selector between promotion reports and daily operations. Its purpose is to prevent a candidate from reaching paper operations unless the candidate passes walk-forward evidence, paper-simulation evidence, duplicate suppression, and the active Daily Ops risk context.

## Inputs

- `data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json`
- `data/reports/daily_ops/daily_ops_pack.json`

## Default Policy

- Maximum walk-forward drawdown: `-20%`
- Maximum paper drawdown: `-20%`
- Minimum walk-forward Sharpe: `0.3`
- Minimum paper Sharpe: `0.5`
- Minimum walk-forward trades: `20`
- Live orders: always disabled

## Current Result

The current report has 270 promotion candidates, 5 paper-matched candidates, and 0 risk-eligible candidates under the default policy. The top candidate is rejected because:

- walk-forward drawdown breaches the limit
- paper drawdown breaches the limit
- current Daily Ops is blocked by `risk_max_drawdown_breach`

This is expected behavior. The selector is designed to stop risky candidates before they are translated into advisory tickets.

## Run

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\run_risk_candidate_selector.py
```

Outputs:

- `data/reports/risk_candidate_selector/risk_candidate_pack.json`
- `data/reports/risk_candidate_selector/risk_candidate_pack.md`
- `data/reports/risk_candidate_selector/risk_candidate_candidates.csv`
- `data/reports/risk_candidate_selector/risk_candidate_summary.csv`

## Next Work

The next useful step is a constrained candidate search that lowers exposure, raises cash buffers, expands slower rebalance intervals, and requires fresh paper simulation before any candidate can re-enter Daily Ops.

## Later Backlog

- Add a pre-live signal monitor after the paper-simulation loop is stable and before broker API integration. The monitor should run in the Windows background, refresh signal snapshots and rebalance plans, deduplicate repeated alerts, and notify with both Windows system notifications and a stronger confirmation popup for buy/sell/risk changes. It must not connect to broker APIs, read live accounts, or place orders.
