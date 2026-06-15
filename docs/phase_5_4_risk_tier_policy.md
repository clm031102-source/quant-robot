# Phase 5.4 Risk Tier Policy

This phase changes the promotion target from one fixed 20% drawdown ceiling to a staged risk policy.

The goal is to support the user's stated capital path:

- start with small capital and accept higher drawdown for higher return potential;
- keep live-order boundaries disabled;
- graduate later into lower-drawdown, steadier profiles after capital grows.

## Risk Tiers

Default tiers:

- `capital_preservation`: max paper drawdown `20%`, min paper Sharpe `0.5`, min paper Calmar `1.0`, min trades `20`.
- `balanced_growth`: max paper drawdown `25%`, min paper Sharpe `0.5`, min paper Calmar `1.0`, min trades `20`.
- `aggressive_growth`: max paper drawdown `30%`, min paper Sharpe `0.5`, min paper Calmar `1.0`, min trades `20`.

Candidate selection remains conservative at the execution boundary:

- `live_order_allowed` is always `false`.
- `live_boundary_allowed` is always `false`.
- a tier match only permits further paper observation and manual review.

## Commands

Refresh the constrained risk candidate pack:

```powershell
python scripts\run_risk_candidate_selector.py --promotion-report data\reports\promotion_gate_cn_etf_risk_constrained\promotion_report.json --daily-ops-pack data\reports\daily_ops\daily_ops_pack.json --output-dir data\reports\risk_candidate_selector_risk_constrained --max-drawdown-limit 0.2 --min-walk-forward-sharpe 0.3 --min-relative-return 0 --min-paper-sharpe 0.5 --min-trades 20 --risk-tiers configs\constrained_candidate_search_cn_etf.json --primary-risk-tier capital_preservation
```

Refresh constrained search:

```powershell
python scripts\run_constrained_candidate_search.py --config configs\constrained_candidate_search_cn_etf.json
```

Refresh paper profile optimization:

```powershell
python scripts\run_paper_profile_optimizer.py --config configs\paper_profile_optimizer_cn_etf.json
```

## Current Result

The promotion-level risk candidate selector still found no tier-eligible candidate:

- candidates: `48`
- paper-matched candidates: `5`
- tier-eligible candidates: `0`

The constrained search still keeps one useful frontier candidate:

- `CN_ETF_liquidity_10_top1_cost5_reb5`

The paper profile optimizer tested `16` profile attempts and selected one aggressive-growth profile:

- profile: `cap60_guard12_cd3`
- case: `CN_ETF_liquidity_10_top1_cost5_reb5`
- max asset weight: `0.60`
- max drawdown guard: `0.12`
- guard cooldown periods: `3`
- paper total return: `0.939358`
- paper max drawdown: `-0.252031`
- paper Sharpe: `0.527171`
- paper Calmar: `3.727153`
- fills: `171`
- eligible tier: `aggressive_growth`

Interpretation: the project has moved from a strict 20% drawdown research gate to a staged capital-growth policy. The current best profile fits the early aggressive-growth target, but it does not fit balanced or capital-preservation tiers. It must remain under paper observation before any production discussion.

## Next Push

The next useful work is to turn this selected aggressive-growth profile into an operational paper candidate:

- freeze the selected profile into the daily ops pack;
- add paper-trading run state, drift checks, and stop conditions;
- use Tushare-adjusted data for broader validation and recent-market refresh;
- rerun walk-forward windows with stricter leakage and survivorship checks;
- add a manual approval checklist before any broker or live-order integration is considered.

