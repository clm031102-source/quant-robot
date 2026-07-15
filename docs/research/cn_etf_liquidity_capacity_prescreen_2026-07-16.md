# CN ETF Liquidity-Capacity Prescreen Closeout

Date: 2026-07-16

Machine: `office_desktop`

Branch: `codex/factor-batch-cn-etf-liquidity-capacity-20260716`

Status: rejected; family stop-lossed

## Decision

The frozen liquidity-change, participation-breadth, and amount-distribution batch produced zero research leads. All six factor-horizon rows had negative mean Rank IC, failed Benjamini-Hochberg FDR, failed directional cross-sectional shape, and exceeded the frozen 1% one-way participation limit at the tenth-percentile top-quintile ADV20.

`cn_etf_liquidity_capacity` is therefore stop-lossed with zero research budget. No sign flip, window tuning, threshold relaxation, parameter rescue, portfolio grid, or walk-forward run is allowed for this structure.

The closed 0.35 budget is reallocated exactly as preregistered:

| Family | New budget |
| --- | ---: |
| `cn_etf_volatility_regime` | 0.35 |
| `cn_etf_flow_breadth_aggregation` | 0.35 |
| `cn_etf_fund_structure` | 0.30 |

## Frozen Contract

- Config: `configs/cn_etf_liquidity_capacity_prescreen_20260716.json`
- Config SHA-256: `b0eed9567ddd0172c0a02cc7cb3b1fb494db95b5053cc5acb8a2cf68412e5b76`
- Candidates: 3
- Forward horizons: 5 and 20 sessions
- Execution lag: 1 session
- Frozen tests: 6
- Historical references: 13
- FDR alpha: 0.05 across all six tests
- Research-lead minimums: Rank IC 0.02, ICIR 0.30, positive IC rate 55%, positive Q5-Q1, monotonicity 0.70, at least three usable years, at least 60% positive years, and historical-reference correlation below 0.85
- Capacity assumption: CNY 1 million portfolio, 10 equal positions, CNY 100,000 per position, maximum 1% one-way participation
- Capacity requirement: tenth-percentile top-quintile ADV20 at least CNY 10 million with 100% evidence coverage

## Point-In-Time Data

| Item | Value |
| --- | ---: |
| Source rows | 1,119,490 |
| Source assets | 1,781 |
| Source sessions | 1,085 |
| Source window | 2020-01-02 through 2024-06-28 |
| Official metadata assets | 1,766 |
| Eligible asset-date keys | 227,010 |
| Eligible assets | 679 |
| Eligible sessions | 833 |
| Factor rows | 681,030 |
| Reference rows | 2,951,130 |
| Label rows | 2,191,185 |
| Daily IC observations | 4,917 |
| Yearly IC rows | 24 |

Eligibility used official ETF lifecycle/status, at least 252 prior observations, trailing 20-session median amount of at least CNY 5 million, stale-price rate no greater than 5%, positive current price and amount, and absolute current return no greater than 20%. The endpoint-selected Round25 universe was not reused.

The 2026 final holdout was sealed and not accessed. Any future walk-forward for another family still requires a separately audited 2024-H2 through 2025 history backfill.

## Results

| Factor | H | Mean IC | ICIR | FDR q | IC>0 | Q5-Q1 | Mono | Turnover | Positive years | Max reference corr | ADV20 P10 CNY | Participation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `etf_amount_distribution_quality_20` | 5 | -0.0143 | -0.120 | 0.1446 | 44.0% | -0.00141 | -0.90 | 10.3% | 0% | 0.8384 vs `amount_stability_20` | 9,733,114 | 1.027% |
| `etf_amihud_improvement_5_60` | 5 | -0.0169 | -0.094 | 0.1446 | 45.0% | -0.00046 | -0.70 | 27.1% | 25% | 0.4157 vs `quiet_accumulation_60` | 7,705,649 | 1.298% |
| `etf_amount_participation_breadth_20_60` | 5 | -0.0174 | -0.100 | 0.1446 | 46.9% | -0.00089 | -0.20 | 9.0% | 25% | 0.8064 vs `quiet_accumulation_60` | 8,338,793 | 1.199% |
| `etf_amihud_improvement_5_60` | 20 | -0.0237 | -0.132 | 0.1591 | 47.4% | -0.00153 | -0.70 | 27.0% | 25% | 0.4157 vs `quiet_accumulation_60` | 7,705,649 | 1.298% |
| `etf_amount_distribution_quality_20` | 20 | -0.0307 | -0.270 | 0.1424 | 38.3% | -0.00500 | -1.00 | 10.2% | 0% | 0.8384 vs `amount_stability_20` | 9,833,618 | 1.017% |
| `etf_amount_participation_breadth_20_60` | 20 | -0.0325 | -0.187 | 0.1446 | 44.3% | -0.00381 | -0.20 | 9.0% | 25% | 0.8064 vs `quiet_accumulation_60` | 8,324,093 | 1.201% |

All six capacity rows had 100% ADV20 evidence coverage, so the capacity rejection is not caused by missing values. None crossed the 0.85 duplicate threshold, although amount distribution quality and participation breadth were close enough to prior amount-stability/quiet-accumulation exposures to reinforce the stop-loss decision.

The consistently negative direction does not authorize multiplying the factors by minus one. A sign reversal after observing results is a new hypothesis and an outcome-driven rescue explicitly prohibited by the preregistration.

## Legacy Candidate Quarantine

The canonical current promotion report at `data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json` was rebuilt under the present strict gate:

- Candidates: 270
- Blocked: 270
- Paper-ready: 0
- Report SHA-256: `0f1e3c0020d455a6262a9b4d9bd617a4107ddb481345df35ee513efcaf12ea81`

The old `CN_ETF_liquidity_10_top1_cost5_reb5` label came from an obsolete one-split process without current fold, adjusted-IC, positive-IC-rate, date, provider, and data-quality requirements. It remains quarantined and cannot be reused or promoted.

## Next Direction

The next scheduler-governed action is a duplicate/stop-loss audit of `cn_etf_volatility_regime`, tied at the maximum 0.35 budget with flow breadth but already marked active. The audit must first enumerate prior low-volatility, downside-risk, drawdown, defensive, and regime-gated ETF failures. Only a genuinely untested subspace may receive a compact preregistered prescreen; otherwise rotate directly to ETF-level flow breadth aggregation.

## Safety

Research-to-paper only. No portfolio grid, walk-forward, paper signal, broker connection, account read, order placement, automatic live trading, or profitability claim was produced.
