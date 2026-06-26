# CN Stock Industry-Breadth Bridge Round 69 - 2026-06-21

## Purpose

Round68 rejected standalone `anti_obv_breakout_low_tail_20` regime focus. Round69 stopped single-factor trend-volume mining and tested the translation layer directly:

Can stock-level risk-filter signals aggregate into industry-level breadth strong enough to support a later ETF/theme rotation layer?

This round also added a reusable audit tool:

- `src/quant_robot/ops/industry_breadth_bridge_audit.py`
- `scripts/run_industry_breadth_bridge_audit.py`
- `tests/unit/test_industry_breadth_bridge_audit.py`

The tool is diagnostic only. It does not create paper-ready or live signals.

## Tested Source

- Config: `configs/experiment_grid_cn_stock_composite_risk_filter_bridge_fast_20260621.json`
- Factor source: `daily_basic_public_risk_filter_bridge`
- Factors:
  - `risk_filter_bridge_equal_20`
  - `risk_filter_bridge_agreement_20`
  - `risk_filter_bridge_anti_obv_weighted_20`
- Stock metadata: `data/processed/cn_stock_metadata`
- Period: 2015-01-05 through 2025-12-31
- Horizon: 20
- Execution lag: 1
- Top industries: 5
- Minimum assets per industry: 5
- Minimum industries per date: 20
- Minimum eligible dates: 200

## Rebalance 5 Result

Output:

- `data/reports/industry_breadth_bridge_public_risk_filter_round69_20260621_reb5`

Summary:

- Input rows: 4,996,734
- Date-factor rows: 1,590
- Factors: 3
- Industry-breadth bridge candidates: 0
- Ranking-only signals: 3
- Weak/unproven bridge factors: 0

| Factor | Class | Industry RankIC | RankIC t | Top Excess | Excess t | Positive Excess | Top Compounded | All Compounded | Bottom Compounded |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `risk_filter_bridge_agreement_20` | ranking only | 0.0443 | 4.01 | 0.0036 | 2.37 | 52.85% | 377.71% | -40.93% | -87.55% |
| `risk_filter_bridge_equal_20` | ranking only | 0.0366 | 2.99 | 0.0029 | 1.82 | 52.06% | 241.63% | -40.93% | -90.67% |
| `risk_filter_bridge_anti_obv_weighted_20` | ranking only | 0.0459 | 4.06 | 0.0023 | 1.57 | 52.06% | 143.67% | -40.93% | -93.48% |

## Rebalance 10 Result

Output:

- `data/reports/industry_breadth_bridge_public_risk_filter_round69_20260621_reb10`

Summary:

- Input rows: 2,497,161
- Date-factor rows: 795
- Factors: 3
- Industry-breadth bridge candidates: 0
- Ranking-only signals: 3
- Weak/unproven bridge factors: 0

| Factor | Class | Industry RankIC | RankIC t | Top Excess | Excess t | Positive Excess | Top Compounded | All Compounded | Bottom Compounded |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `risk_filter_bridge_equal_20` | ranking only | 0.0463 | 2.68 | 0.0044 | 1.97 | 53.15% | 169.47% | -23.43% | -71.62% |
| `risk_filter_bridge_agreement_20` | ranking only | 0.0536 | 3.39 | 0.0038 | 1.78 | 52.36% | 122.06% | -23.43% | -79.13% |
| `risk_filter_bridge_anti_obv_weighted_20` | ranking only | 0.0543 | 3.40 | 0.0029 | 1.41 | 52.36% | 83.51% | -23.43% | -80.74% |

## Interpretation

The industry bridge is not useless, but it is not yet a tradable engine.

Useful evidence:

- All three bridge factors have positive industry-level RankIC.
- Top-industry baskets beat the average industry basket in mean return.
- Bottom industries are consistently worse, which matches earlier bottom-exclusion evidence.

Blocking evidence:

- Positive excess rate is only about 52% to 53%, below the 55% bridge-candidate threshold.
- Excess-return t-stat is not robust across rebalance schedules.
- No factor clears the bridge-candidate classification.
- No costed ETF/theme implementation has been tested, so promotion is forbidden.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Research leads:

- Industry-breadth ranking signal from `risk_filter_bridge_agreement_20`.
- Industry-breadth ranking signal from `risk_filter_bridge_equal_20`.
- Industry-breadth ranking signal from `risk_filter_bridge_anti_obv_weighted_20`.

These are ranking-only diagnostics, not standalone alpha.

## Next Direction

The repeated failure pattern is now clear:

- stock signals can identify weak stocks and weak industries;
- buying top stocks or top industries still has unstable absolute risk;
- the project is dominated by market-regime and drawdown problems.

Round70 should not add more raw factor variants. It should be a governance/sync boundary, then the next mining block should test whether a market/cash risk overlay can convert existing ranking signals into lower drawdown and higher risk-adjusted return.

Next research direction after sync:

`market_regime_cash_overlay_for_risk_filter_research_leads_batch`
