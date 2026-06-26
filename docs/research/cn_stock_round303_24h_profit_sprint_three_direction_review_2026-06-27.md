# CN Stock Round303 24h Profit Sprint Five-Direction Review

Date: 2026-06-27

Machine/task: office_desktop / factor_validation

Scope: CN A-share stock factor mining. This is not ETF rotation, not a paper-trading signal, and not live trading.

## Objective

The 24h sprint goal is to find the most useful profitable factors before the project moves to the paper/simulation phase. The sprint does not relax the project gates: no 2026 final-holdout tuning, no direct TopN grid before residual/dedup/cost-capacity checks, no promotion from raw IC or short-window total return, and no broker/account/order access.

## Directions Reviewed

| Direction | Artifact | Best evidence | Decision |
|---|---|---|---|
| Public Alpha101/Qlib capacity-safe replay | `data/reports/round303_24h_profit_sprint_public_alpha101_prescreen_20260627` and reference dedup output | `qlib_alpha158_return_std_position_blend_20` h5 mean IC 0.0415, ICIR 0.323, t 16.68, IC+ 63.4% | Reject for promotion: highly redundant with references and high market/liquidity exposure |
| Public technical failure-reversal replay | `data/reports/round303_24h_profit_sprint_public_technical_failure_reversal_prescreen_20260627` plus prior Round156 evidence | `inverse_rsrs_slope_failure_liquid_18_60` h5 mean IC 0.0334, ICIR 0.409, IC+ 69.1% | Do not rerun neutral dedup: prior Round156 showed residual IC 0.0066, RSRS redundancy, and residual yearly failures |
| Share-unlock bottom-exclusion overlay | `data/reports/round303_24h_profit_sprint_share_unlock_bottom_exclusion_overlay_20260627` | 20d overlay mean excess 0.00078, positive rate 65.2% | Reject: t-stat 0.18, no bottom-exclusion candidate, not a usable risk overlay |
| Repurchase contextual repair | `data/reports/round303_24h_profit_sprint_repurchase_contextual_repair_pit_ic_prescreen_20260627` | liquidity residual 20d IC 0.0333, ICIR 0.209, t 2.09, IC+ 59.0%; industry-relative 20d IC 0.0299, ICIR 0.206 | Reject: 0 FDR leads, 0 neutral-gate passes, poor quantile shape, size-neutral gate failure |
| Public anomaly style-clean repair | `data/reports/round303_24h_profit_sprint_public_anomaly_style_clean_full2015_2025_20260627` and portfolio diagnostic stress outputs | `public_anomaly_residual_regime_conditioned_20_style_clean_signal` h20 residual IC 0.0359, ICIR 0.455, t 19.49, IC+ 67.6%, exposure-high 0; costed top50/reb5/cost5 total return +2430%, annualized 26.4% before stress | Reject for direct profitability: strict prescreen still has yearly-instability blockers; portfolio returns are dominated by extreme trades. After excluding >50% single-trade gross returns, top50/reb5/cost5 total return falls to -71.7%, annualized -9.1%. Under realistic stress using `close`, excluding `CN_XBEI`, and quarantining assets with >50% daily `close`/`adj_close` jumps, all 12 topN/cost/rebalance cases lose money; best total return is -77.7% |

## What This Means

The sprint did not find a simulation-ready CN-stock profitability factor in these five directions. That is a useful result because it prevents expensive mistakes:

- promoting a Qlib/Alpha101 signal that is mostly a reference/style proxy;
- reopening the RSRS cluster after it already failed residual and redundancy audits;
- treating sparse share-unlock event IC as a tradable exclusion overlay without overlay evidence.
- repairing the repurchase family with industry or liquidity neutralization when the long-cycle result still fails multiple-testing, quantile-shape, and size-neutral gates.
- promoting a high-IC public-anomaly style-clean candidate whose apparent portfolio profits disappear after extreme-trade stress.
- allowing `adj_close` discontinuities, North-exchange tail samples, or extreme adjusted-return artifacts to enter direct profitability claims.

## Stop Rules Now Active

- Do not continue RSRS, SuperTrend, Donchian, MFI/CMF/OBV, or direct public technical parameter sweeps unless a new orthogonal mechanism is preregistered.
- Do not run TopN or paper simulations for share-unlock pressure from Round251/Round303 overlay evidence.
- Do not re-enter repurchase amount, repurchase underreaction, or repurchase quiet-volume formulas by threshold/weight tuning; re-entry requires a new independent data source or execution proof.
- Do not promote `public_anomaly_residual_regime_conditioned_20_style_clean_signal` from raw portfolio return. It may remain a relative-selection diagnostic only; direct profitability failed `close`/clean-universe stress.
- Do not use raw IC, positive FDR, or total return without quantile shape, residual survival, cost/capacity, fold stability, and holdout readiness.
- Any later portfolio diagnostic must include `close` price stress, extreme-trade-excluded return, and a data-quality quarantine before the result is described as profitable.
- Do not spend the 24h sprint on financial reporting timeliness source backfill unless the purpose is source readiness; it cannot produce 1000-symbol financial factors inside the current sprint.

## Next Direction

Continue the sprint with a new mechanism family, not a parameter variation of the rejected directions.

Priority order:

1. Tradeability/true-close repair for any high-return candidate: limit-up/down, ST/new-stock, suspension, delisting, board eligibility, extreme adjusted-return quarantine, and extreme-excluded return must be hard gates.
2. Benchmark-relative or market-regime objective for high-IC relative selection signals: if a factor only beats the cross-section but loses in bear years, it belongs in a relative sleeve or ETF/market-state overlay, not a standalone long-only profitability factor.
3. Event and expectation-revision feeds with broader coverage than the current statement sample: forecast/express variants, holder-number, and top-holder concentration only if PIT and year coverage are sufficient; repurchase is hibernated after Round250 and Round303 repair failure.
4. External/market-state interaction candidates only if they are not already northbound or margin-credit residual failures.

Promotion remains blocked until a candidate clears prescreen, residual/dedup, cost-capacity walk-forward, regime coverage, statistical reality checks, and final-holdout readiness.
