# CN ETF Dynamic Peer Dislocation Preregistration

Date: 2026-07-16

Branch: `codex/factor-review-cn-etf-dynamic-peer-preregistration-20260716`

Primary market: `CN_ETF`

Decision: `preregistered_single_prescreen`

## Executive Decision

Exactly one CN ETF dynamic-peer residual-dislocation candidate is frozen for one later, authorization-bound prescreen. The preregistration itself passed its source, hash, timing, configuration, and governance checks. It did not calculate a factor value, read a forward return, run an IC test, construct a portfolio, or establish alpha or profitability.

The Quant PM startup gate now has a restricted `single_prescreen_only` mode. It exposes only the frozen candidate and exact evidence hashes, requires the one-time authorization packet and local claim ledger, and keeps research budget at zero. Portfolio grids, walk-forward validation, final-holdout access, promotion, paper signals, broker access, account reads, order placement, and live trading remain prohibited.

## Frozen Candidate

| Field | Frozen value |
| --- | --- |
| Factor | `etf_dynamic_peer_residual_dislocation_reversal_5_60` |
| Family | `cn_etf_dynamic_comovement_peer_dislocation` |
| Direction | higher is better |
| Compact formula | `-robust_z_60(asset_residual_sum_5-peer_median_residual_sum_5)` |
| Primary horizon | 5 sessions |
| Diagnostic horizon | 20 sessions |
| Execution lag | 1 session |
| Candidate count | 1 |
| Counted candidate-horizon hypotheses | 2 |

The economic hypothesis is that an ETF which has moved unusually below a stable, lagged market-residual peer set is more likely to catch up over the next five sessions than continue diverging. The 20-session row is a decay and sign diagnostic. It cannot rescue a failed five-session primary row.

## Exact Signal Timing

1. Calculate simple adjusted-close returns without forward filling.
2. On date `t`, calculate the common ETF market return as the median across at least 30 point-in-time eligible ETFs.
3. Estimate each ETF's OLS intercept and beta over 120 sessions ending at `t-1`, requiring at least 80 paired observations.
4. Calculate date-`t` residual innovation using the lagged intercept and beta.
5. Sum five consecutive residual innovations, requiring all five.
6. Select the audited peer mapping active on `t`; require the ETF and at least three peers to pass daily eligibility.
7. Subtract the ordinary median peer residual sum from the ETF residual sum. Correlation weights are not allowed.
8. Normalize the current dislocation against 60 prior signal dates ending at `t-1`, requiring at least 40 observations.
9. Use prior median as center and `1.4826 * MAD` as scale. Emit no value when scale is non-finite or at most `1e-12`.
10. Reverse the normalized dislocation sign. Historical normalization always uses the mapping active on each historical date; a new mapping is never projected backward.

Date-`t` close information is allowed only because execution is lagged one session. Every coefficient, historical center, and scale is lagged.

## Data Boundary

| Rule | Frozen value |
| --- | --- |
| Analysis start | 2020-01-02 |
| Analysis end | 2024-06-28 |
| Final holdout start | 2026-01-01 |
| Minimum prior observations | 120 |
| Liquidity | median ADV20 at least CNY 5 million |
| Maximum stale-price rate | 5% |
| Maximum absolute daily adjusted return | 20% |
| Lifecycle | official list/delist interval required |
| Minimum active daily peers | 3 |

Post-analysis partitions must be skipped before reading. Current names, current themes, current official peer assignments, future returns, 2026 rows, and forward-filled returns cannot influence the factor.

## Frozen Source Evidence

| Artifact | SHA-256 |
| --- | --- |
| Dynamic peer source config | `a3eeda49ade9624c1e335d9adfc7a6cdd0803def723feda9ef28a99d1e9c6016` |
| Dynamic peer readiness result | `4177895b7799c5074ab0b7a0102f9a1f3917d789817e5b2380497c08346fac44` |
| Dynamic peer mapping CSV | `52d7c0c80b32b164583bea52cc09e0fba7436051d236df6e1ab9343387f5fe63` |

Required source status is `ready_for_peer_source_preregistration`. The mapping CSV must contain only `lagged_market_residual_correlation_topk` in its `mapping_method` column. The CLI hashes all three source files and validates the mapping method before writing the authorization.

## Statistical Gate

| Gate | Frozen threshold |
| --- | ---: |
| Minimum daily cross-section | 30 |
| Minimum IC observations | 20 |
| Minimum yearly IC observations | 20 |
| Minimum usable years | 3 |
| Newey-West and FDR alpha | 0.05 |
| Minimum mean Rank IC | 0.02 |
| Minimum ICIR | 0.30 |
| Minimum positive IC rate | 0.55 |
| Minimum quintile monotonicity | 0.70 |
| Maximum top-quintile turnover | 0.90 |
| Minimum positive-year rate | 0.60 |
| Maximum absolute reference correlation | strictly below 0.85 |

Benjamini-Hochberg correction covers both frozen horizon rows. The primary five-session row must pass every gate. The 20-session row must have non-negative mean Rank IC and non-negative top-minus-bottom spread, but still cannot substitute for the primary row.

## Reference And Exposure Challenge

The prescreen must use the complete candidate and reference unions from these closed-family configs:

| Reference config | SHA-256 |
| --- | --- |
| `configs/cn_etf_skip_momentum_prescreen_20260716.json` | `75dd8529d21762804029741928287fb07ba5251bcfd85bcfe7445a029ac93611` |
| `configs/cn_etf_liquidity_capacity_prescreen_20260716.json` | `b0eed9567ddd0172c0a02cc7cb3b1fb494db95b5053cc5acb8a2cf68412e5b76` |
| `configs/cn_etf_market_residual_volatility_prescreen_20260716.json` | `303b0a66961baa65fbbf72f55f0ad030675908b061954017ae84a890dea62ad0` |

Missing or all-null reference evidence fails closed. Candidate values must also be challenged directly against `market_beta_120`, `residual_volatility_60`, `momentum_60`, `short_return_5`, and `log_adv20`, each with the same strict 0.85 correlation ceiling. Passing source-topology de-duplication alone is not factor-value independence evidence.

## Capacity And Cost Gate

- Diagnostic capital is CNY 1 million across 10 positions, or CNY 100,000 per position.
- Maximum one-way participation is 1% of ADV20.
- Top-quintile ADV20 P10 must support the position on every evaluated date.
- Both top- and bottom-quintile turnover must be reported.
- One-way costs are 5 bps baseline and 10 bps stress.
- The five-session cost-adjusted top-minus-bottom spread must remain positive at 10 bps.

These are prescreen diagnostics, not portfolio authorization. Position, holding-period, rebalance, leverage, and capital grids are prohibited.

## One-Time Authorization

| Item | Value |
| --- | --- |
| Authorization ID | `6460f4cafced4f39cc963c5e0bbc31fe4ae56d7f976804ae8beebfdd0d262a62` |
| Allowed task | `factor_batch` |
| Allowed stage | `cn_etf_dynamic_peer_dislocation_prescreen` |
| Maximum executions | 1 |
| Current execution count | 0 |
| Authorization packet | `data/reports/cn_etf_dynamic_peer_dislocation_preregistration_20260716/single_prescreen_authorization.json` |
| Claim ledger | `data/reports/cn_etf_dynamic_peer_dislocation_prescreen_execution_ledger.json` |

The future prescreen must validate the packet hash and atomically claim the authorization before reading labels. The ledger does not currently exist, confirming that the authorization has not been consumed. A second claim, an existing lock, a packet mutation, a candidate/config mismatch, or an enabled downstream boundary fails closed.

## Deterministic Artifacts

The real preregistration ran repeatedly with identical hashes:

| Artifact | SHA-256 |
| --- | --- |
| Frozen config | `4811e1497bbfe9688e006dcb7764381c7ea977ddfde79790248f0223996233c6` |
| Result JSON | `2038a32fa9b250a33a76bdca08c204a349a1cdec959fc3c10dbe4b6a4f6440f5` |
| Markdown artifact | `5482ac1d275433e36815bce6a5a094deac599f5ad322f5c1b4929f1c3044bbd5` |
| Candidate CSV | `db7263fc74b4fb8a862dcba78002ca104ecc0198bf35d447c50afce5734c49fd` |
| Authorization packet | `c645de436c462365c443dd0574b750feb68b3955263b39a316b184862e99f5c9` |

Generated artifacts remain under ignored `data/reports/` paths and are not eligible for Git.

## Verification

- All 25 focused preregistration, authorization, CLI, Quant PM, and scheduler tests passed.
- The complete repository suite passed: 2,295 tests in 698.189 seconds.
- Python compilation passed for `src`, `scripts`, and `tests`.
- The project audit scanned 2,804 files and passed factor-config, mock-boundary, real-data, syntax, and safety checks.
- The maintainability audit reported no baseline regression. Known debt remains 13 oversized modules, 572 unit-test files, two integration-test files, and no end-to-end test layer.
- The real Quant PM gate returned `ready` in `single_prescreen_only` mode with the exact candidate, config hash, authorization hash, one maximum execution, zero executions, and all downstream boundaries false.

## Stop And Rotation Policy

There is one authorized prescreen and two counted horizon tests. Sign inversion, window changes, mean-for-median substitution, mapping changes, eligibility relaxation, threshold relaxation, horizon substitution, parameter grids, regime rescue, portfolio rescue, and walk-forward rescue are all prohibited.

If the five-session row fails any statistical, reference, direct-exposure, capacity, or stressed-cost gate, close this family with zero budget. If it passes, first backfill and audit 2024-H2 through 2025, then preregister walk-forward and cost/capacity validation. Do not open the 2026 final holdout.

## What Was Not Read Or Claimed

The preregistration operation read the frozen config and source-readiness artifacts only. It read no bar partitions, factor matrices, forward-return labels, IC rows, quantile returns, portfolio returns, walk-forward folds, paper signals, account data, or final-holdout rows. No authorization claim was recorded.

Therefore:

- no alpha has been demonstrated;
- no profitability has been demonstrated;
- no strategy is paper-ready or live-ready;
- source readiness and preregistration are not promotion evidence.

## Residual Risks

- The source is price-derived and may still collapse into short reversal, beta, volatility, momentum, or liquidity once factor values are compared.
- The 83.32% source coverage margin over the 80% gate is adequate but modest.
- The current analysis stops at 2024-06-28; 2024-H2 through 2025 remains missing for later walk-forward work.
- A single frozen prescreen can reject this idea, but cannot establish durable profitability by itself.
- Project-wide maintainability debt remains in oversized legacy modules and sparse workflow-level tests; this focused governance work does not remove that broader debt.

## Next Task

Create a new branch such as `codex/factor-batch-cn-etf-dynamic-peer-dislocation-20260716`, run the Quant PM startup gate with task `factor_batch`, validate and atomically claim the exact authorization, then execute the single frozen prescreen. Stop immediately after writing the prescreen decision. Do not tune or start a second run.

## Completion Boundary

This work closes the preregistration and authorization stage only. The project remains research-to-paper: no broker connection, account read, order placement, automatic trading, or unsupported profitability claim.
