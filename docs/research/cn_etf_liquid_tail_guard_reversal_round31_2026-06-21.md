# CN ETF Liquid Tail-Guard Reversal Round31

Date: 2026-06-21
Machine: office_desktop
Task: factor_validation
Branch: codex/factor-validation-cn-stock-long-cycle-20260618

## Objective

Run a long-cycle walk-forward validation on public tail-guard reversal factors for the liquid CN ETF universe. This round intentionally rotates away from prior trend-volume and basic momentum families.

## Setup

- Config: `configs/walk_forward_cn_etf_liquid_tail_guard_reversal_round31_20260621.json`
- Data root: `data/processed/tushare_etf_wide_history_2023_2026`
- Universe: `data/reports/etf_liquid_universe_tushare_wide_2020_2024_round25/etf_liquid_universe.json`
- Market: `CN_ETF`
- Liquid universe size: 264 ETFs
- Date count: 1085 trading dates
- Benchmark: `CN_ETF_XSHG_510300`
- Walk-forward: 756 train days, 126 test days, 63 step days, 4 folds
- Portfolio: Top5, 80% gross exposure, 5 bps cost, 2 bps impact, 10% max participation
- Multiple-testing alpha: 0.05

## Preflight

ETF validation preflight cleared.

- Fold count: 4
- Median allowed rebalance dates: 26
- Minimum allowed rebalance dates: 26
- Zero-allowed fold count: 0
- Blockers: none

## Factors Tested

| Factor | Source | Rebalance |
|---|---|---:|
| `rsi_reversal_liquid_low_tail_14_20` | `public_technical_tail_guard` | 5, 10 |
| `bollinger_reversal_liquid_low_tail_20` | `public_technical_tail_guard` | 5, 10 |

## Results

| Rank | Case | Accepted folds | Mean test Sharpe | Mean ann. return | Mean relative return | Mean win rate | Test max DD | Adjusted IC p |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `CN_ETF_rsi_reversal_liquid_low_tail_14_20_top5_cost5_reb10` | 2/4 | -0.2142 | -1.92% | 4.24% | 52.08% | -9.89% | 1.0000 |
| 2 | `CN_ETF_bollinger_reversal_liquid_low_tail_20_top5_cost5_reb5` | 1/4 | -0.5822 | -7.94% | 1.40% | 47.92% | -17.74% | 1.0000 |
| 3 | `CN_ETF_rsi_reversal_liquid_low_tail_14_20_top5_cost5_reb5` | 0/4 | -0.6555 | -7.55% | 1.65% | 45.83% | -14.05% | 1.0000 |
| 4 | `CN_ETF_bollinger_reversal_liquid_low_tail_20_top5_cost5_reb10` | 2/4 | -0.2344 | -2.03% | 4.13% | 52.08% | -11.37% | 1.0000 |

Summary:

- Total cases: 4
- Accepted aggregate cases: 0
- Rejected cases: 4
- Strict split: passed on all cases
- Main rejection reasons: OOS Sharpe below threshold, relative return below threshold, adjusted IC significance not passed

## Audit Decision

This factor family is not currently useful for CN ETF rotation.

The best two rebalance-10 variants show small positive relative return versus the benchmark, but both have negative absolute annualized returns, negative Sharpe, no adjusted IC significance, and overlapping-sample risk flags. This is not a paper-ready or live-usable signal.

Direction decision:

- Do not expand this tail-guard reversal family with more parameters now.
- Keep the result as negative evidence.
- Rotate Round32 to a different public-method family: low-volatility/defensive allocation or ETF theme breadth/risk-on overlay.

## Running Ledger

- Round26 trend-volume full sample: 0 promotable, weak research leads only.
- Round27 trend-volume regime WF: 0 promotable; regime config underpowered.
- Round28 trend-volume no-regime WF: 0 promotable; best weak research lead.
- Round29 basic momentum WF: 0 promotable.
- Round31 tail-guard reversal WF: 0 promotable; stop expanding this family.
