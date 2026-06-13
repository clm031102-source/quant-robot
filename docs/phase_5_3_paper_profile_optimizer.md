# Phase 5.3 Paper Profile Optimizer

This phase adds a local optimizer for paper-risk profiles around constrained-search frontier candidates.

## Command

```powershell
python scripts\run_paper_profile_optimizer.py --config configs\paper_profile_optimizer_cn_etf.json
```

The command reads `data/reports/constrained_candidate_search/constrained_candidate_search_pack.json`, takes the top frontier candidate, runs configured paper profile attempts, and writes:

- `data/reports/paper_profile_optimizer/paper_profile_optimizer_pack.json`
- `data/reports/paper_profile_optimizer/paper_profile_optimizer_pack.md`
- `data/reports/paper_profile_optimizer/paper_profile_attempts.csv`
- `data/reports/paper_profile_optimizer/paper_profile_summary.csv`

The command is local-only and does not connect to brokers, read accounts, place orders, or allow live trading.

## Current Result

The optimizer tested 12 profile attempts for `CN_ETF_liquidity_10_top1_cost5_reb5`.

No profile passed both strict paper gates:

- `min_paper_sharpe >= 0.5`
- `max_equity_drawdown >= -0.2`

Best trade-off observed:

- `cap46_guard10_cd3`: drawdown passed at `-0.198059`, but Sharpe was only `0.408513`.
- `cap471_guard10_cd3`: Sharpe passed at `0.525191`, but drawdown was `-0.202364`.
- `cap475_guard10_cd3`: Sharpe passed at `0.52443`, but drawdown was `-0.204355`.
- stronger drawdown guards around `0.471` reduced drawdown but broke return quality, producing negative Sharpe.

Interpretation: the current frontier candidate cannot be made policy-eligible by minor exposure/guard tuning alone. The next useful step is to broaden the candidate search itself: additional factor families, ensemble filters, or volatility-aware position sizing rather than only static max-weight tweaks.

