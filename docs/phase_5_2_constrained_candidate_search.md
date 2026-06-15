# Phase 5.2 Constrained Candidate Search

This phase adds a resumable local pipeline for searching candidates under the stricter Phase 5 risk policy.

## Command

```powershell
python scripts\run_constrained_candidate_search.py --config configs\constrained_candidate_search_cn_etf.json
```

The command orchestrates:

- strict walk-forward validation with a 20% max drawdown gate;
- conservative paper-batch simulations with lower exposure and cash guards;
- promotion gate refresh from the constrained artifacts;
- risk candidate selector refresh;
- a summary pack with frontier near-miss candidates.

The command is local-only. It does not use broker APIs, account reads, order placement, or live trading.

## Outputs

- `data/reports/walk_forward_cn_etf_risk_constrained/`
- `data/reports/paper_batch_cn_etf_risk_constrained/`
- `data/reports/promotion_gate_cn_etf_risk_constrained/promotion_report.json`
- `data/reports/risk_candidate_selector_risk_constrained/risk_candidate_pack.json`
- `data/reports/constrained_candidate_search/constrained_candidate_search_pack.json`

## Current Result

The current constrained run found 5 walk-forward accepted candidates from 48 searched cases and completed 5 paper simulations.

No candidate is risk-eligible yet. The best frontier candidate is:

- `CN_ETF_liquidity_10_top1_cost5_reb5`
- walk-forward Sharpe: `0.784624`
- walk-forward relative return: `0.023006`
- walk-forward max drawdown: `-0.19765`
- paper Sharpe: `0.451505`
- paper max drawdown: `-0.153336`
- paper Sharpe gap to policy: `0.048495`

Interpretation: lowering exposure fixed the drawdown breach, but the paper-quality gate still rejects the candidate because paper Sharpe is below `0.5`. The next useful research work is to improve paper Sharpe without letting paper drawdown cross `-20%`.

## GUI

The GUI exposes this pack on the Daily Ops page as `Constrained Search` and `Frontier Candidates`. The API endpoint is:

```text
/api/risk/constrained-search
```

