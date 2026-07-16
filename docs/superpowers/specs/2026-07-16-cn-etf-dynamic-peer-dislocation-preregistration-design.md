# CN ETF Dynamic Peer Dislocation Preregistration Design

Date: 2026-07-16

Machine: `office_desktop`

Task: `factor_review`

Branch: `codex/factor-review-cn-etf-dynamic-peer-preregistration-20260716`

## Objective

Freeze exactly one causal CN ETF dynamic-peer dislocation hypothesis before any forward return, factor value, IC, quantile return, or portfolio result is read.

This task produces a machine-verifiable preregistration and a narrowly scoped authorization for one later prescreen. It does not execute the prescreen and cannot make an alpha or profitability claim.

## Alternatives Considered

### Raw five-session peer-relative reversal

Calculate the ETF five-session return minus the median return of its active peers and reverse the sign. This is simple, but it is likely to be a repackaging of the closed `reversal_5` and market-relative-strength paths. It is not selected.

### Rolling pairwise cointegration spread

Estimate a hedge ratio, stationarity test, and half-life for every selected pair. This turns one source-locked hypothesis into thousands of pairwise tests and adds hedge-ratio, test-window, significance, half-life, and pair-aggregation choices. It is not selected.

### Lagged market-residual peer dislocation with robust normalization

Selected. Remove the point-in-time common ETF market return using coefficients estimated only through the prior session, compare the ETF's five-session residual move with the median residual move of its active peers, and normalize the current dislocation using only prior dislocation history. This is closer to temporary relative-value dislocation than standalone reversal and has three economically interpretable windows: 120 sessions for beta, five sessions for dislocation, and 60 sessions for robust normalization.

## Frozen Source Evidence

The preregistration is valid only for the exact audited source below:

- Source config: `configs/cn_etf_dynamic_comovement_peer_readiness_20260716.json`
- Source config SHA-256: `a3eeda49ade9624c1e335d9adfc7a6cdd0803def723feda9ef28a99d1e9c6016`
- Source result: `data/reports/cn_etf_dynamic_comovement_peer_readiness_20260716/cn_etf_dynamic_comovement_peer_readiness.json`
- Source result SHA-256: `4177895b7799c5074ab0b7a0102f9a1f3917d789817e5b2380497c08346fac44`
- Mapping artifact: `data/reports/cn_etf_dynamic_comovement_peer_readiness_20260716/dynamic_peer_mapping.csv`
- Mapping SHA-256: `52d7c0c80b32b164583bea52cc09e0fba7436051d236df6e1ab9343387f5fe63`
- Required source status: `ready_for_peer_source_preregistration`
- Mapping method: `lagged_market_residual_correlation_topk`

The preregistration CLI must hash these files before emitting an authorization. A missing file, hash mismatch, source blocker, changed mapping method, enabled factor generation, or enabled live boundary fails closed.

## Frozen Candidate

- Factor name: `etf_dynamic_peer_residual_dislocation_reversal_5_60`
- Family: `cn_etf_dynamic_comovement_peer_dislocation`
- Direction: `higher_is_better`
- Economic hypothesis: an ETF that has moved unusually below a stable, lagged market-residual peer set is more likely to catch up over the next five sessions than continue diverging.
- Primary horizon: five sessions.
- Diagnostic horizon: 20 sessions.
- Execution lag: one session.
- Candidate count: one.
- Candidate-horizon hypothesis count: two.

The 20-session result is a preregistered decay and sign diagnostic, not an alternate primary horizon. A failed five-session primary row cannot be rescued by a positive 20-session row.

## Exact Signal Formula

For each signal date `t` and ETF `i`:

1. Calculate simple adjusted-close return `r(i,t)` without forward filling.
2. Calculate `m(t)` as the median return across ETFs that are point-in-time eligible on `t`, requiring at least 30 finite returns.
3. Estimate intercept `alpha(i,t-1)` and beta `beta(i,t-1)` from the 120 sessions ending at `t-1`, requiring at least 80 paired observations.
4. Calculate the close-known residual innovation:

   `e(i,t) = r(i,t) - alpha(i,t-1) - beta(i,t-1) * m(t)`

5. Sum five consecutive residual innovations, requiring all five:

   `E5(i,t) = sum(e(i,s), s=t-4..t)`

6. Use the audited quarterly mapping active on `t`. Keep peers that are point-in-time eligible on `t` and have finite `E5`. Require at least three peers.
7. Calculate the peer consensus as the ordinary median of peer `E5` values. Correlation values select peers but do not create another weighting parameter.
8. Calculate the raw dislocation:

   `D(i,t) = E5(i,t) - median(E5(j,t), j in active peers)`

9. From the 60 prior signal dates ending at `t-1`, require at least 40 finite historical `D(i,s)` observations. Calculate the prior median and median absolute deviation:

   `center(i,t-1) = median(D(i,s))`

   `scale(i,t-1) = 1.4826 * median(abs(D(i,s) - center(i,t-1)))`

10. If scale is not finite or is at most `1e-12`, emit no factor value. Otherwise:

    `factor(i,t) = -(D(i,t) - center(i,t-1)) / scale(i,t-1)`

Every rolling coefficient, center, and scale is lagged one session. The signal may use date-`t` close information only because the execution lag is one session. Historical dislocations use the mapping that was active on each historical date; a newly selected peer set is never projected backward.

## Data And Eligibility Boundary

- Primary market: `CN_ETF`.
- Data root: `data/processed/tushare_etf_wide_history_2023_2026`.
- Analysis start: 2020-01-02.
- Analysis end: 2024-06-28.
- Final holdout start: 2026-01-01.
- Later partitions must be skipped before reading.
- Official ETF lifecycle membership is required.
- Minimum prior observations: 120.
- Median amount over 20 sessions: at least CNY 5 million.
- Stale-price rate: at most 5%.
- Absolute one-session adjusted return: at most 20%.
- A factor row requires the ETF and at least three active peers to pass daily eligibility.

No current name, current theme, current official peer assignment, future return, 2026 holdout row, or post-analysis partition may influence factor construction.

## Frozen Statistical Gate

The shared cross-sectional prescreen thresholds remain unchanged:

- Minimum daily cross-section: 30.
- Minimum IC observations: 20.
- Minimum yearly IC observations: 20.
- Minimum usable years: three.
- Newey-West and FDR alpha: 0.05.
- Minimum mean Rank IC: 0.02.
- Minimum ICIR: 0.30.
- Minimum positive IC rate: 0.55.
- Minimum quintile monotonicity: 0.70.
- Maximum top-quintile turnover: 0.90.
- Minimum positive-year rate: 0.60.
- Maximum absolute mean daily reference correlation: strictly below 0.85.

Benjamini-Hochberg correction covers both frozen candidate-horizon rows. The five-session primary row must pass every standard gate. The 20-session diagnostic row must have non-negative mean Rank IC and non-negative top-minus-bottom quintile spread. If the primary row fails, there is no research lead.

## Reference And Exposure Challenge

Candidate values must be compared with the complete candidate and reference sets frozen in these closed-family configs:

- `configs/cn_etf_skip_momentum_prescreen_20260716.json`, SHA-256 `75dd8529d21762804029741928287fb07ba5251bcfd85bcfe7445a029ac93611`
- `configs/cn_etf_liquidity_capacity_prescreen_20260716.json`, SHA-256 `b0eed9567ddd0172c0a02cc7cb3b1fb494db95b5053cc5acb8a2cf68412e5b76`
- `configs/cn_etf_market_residual_volatility_prescreen_20260716.json`, SHA-256 `303b0a66961baa65fbbf72f55f0ad030675908b061954017ae84a890dea62ad0`

The frozen union includes price rotation, skip momentum, raw reversal, market-relative strength, liquidity, low-volatility, drawdown/recovery, range-compression, downside-beta, idiosyncratic-volatility, and residual-skew evidence. Missing or all-null reference evidence fails closed.

The prescreen must also report correlations to these direct source exposures: `market_beta_120`, `residual_volatility_60`, `momentum_60`, `short_return_5`, and `log_adv20`. The same strict 0.85 ceiling applies. This factor cannot proceed by claiming that source-topology de-duplication alone proves factor-value independence.

## Cost And Capacity Gate

- Amount unit: CNY.
- ADV window: 20 sessions.
- Diagnostic portfolio value: CNY 1 million.
- Position count: 10.
- Maximum one-way participation: 1% of ADV20.
- Top-quintile ADV20 10th percentile must support the diagnostic position on every evaluated date.
- One-way cost challenges: 5 bps baseline and 10 bps stress.
- Both top- and bottom-quintile turnover must be reported.
- The five-session cost-adjusted top-minus-bottom spread must remain positive at 10 bps.

These are prescreen diagnostics, not a portfolio authorization. No position grid, holding-period grid, rebalance grid, leverage choice, or capital optimization is allowed.

## Stop And Rotation Policy

There is one authorized prescreen execution for this frozen candidate and two counted candidate-horizon hypotheses.

If the five-session primary row fails any statistical, reference, exposure, capacity, or stressed-cost gate, the family closes with zero budget. The following are prohibited:

- sign inversion;
- beta, dislocation, or scale window changes;
- mean-for-median substitution;
- mapping threshold or peer-count changes;
- eligibility relaxation;
- horizon substitution;
- threshold relaxation;
- parameter grids;
- regime rescue;
- portfolio or walk-forward rescue.

If the primary row passes, the next step is still not a portfolio grid. The project must first backfill and audit 2024-H2 through 2025, then preregister a walk-forward and cost/capacity validation. The 2026 final holdout remains sealed.

## Preregistration Packet

The preregistration operation reads only the frozen config and the source/readiness artifacts. It must not load bars or labels. It writes deterministic JSON, Markdown, candidate CSV, and a single-prescreen authorization packet under ignored `data/reports/`.

The authorization packet binds:

- preregistration config SHA-256;
- preregistration result SHA-256;
- source config, source result, and mapping SHA-256 values;
- factor name;
- primary and diagnostic horizons;
- allowed prescreen stage;
- task type `factor_batch`;
- maximum executions equal to one;
- a required local execution ledger;
- all portfolio, promotion, holdout, paper, broker, account, order, and live boundaries set to false.

The future prescreen CLI must validate the packet hash and atomically claim the authorization in the local execution ledger before reading forward labels. A second claim with the same authorization identity fails closed.

## Quant PM Single-Prescreen Mode

After the deterministic preregistration artifacts are written and hashed, the scheduler may record `prescreen_preregistered_single_batch_only`. Budget remains zero.

The Quant PM gate may then return `single_prescreen_only` only when:

- task is `factor_batch`;
- the scheduler has zero active primary families and only the expected insufficient-family blocker;
- the last decision binds the exact candidate, config, preregistration, and authorization hashes;
- `single_prescreen_run_limit` equals one;
- portfolio, walk-forward, promotion, holdout, paper, and live boundaries remain false.

The gate exposes the exact factor and config hash as scope. It must not turn this exception into general factor-batch permission.

## Required Artifacts

- Frozen preregistration JSON config.
- Pure preregistration operation and deterministic artifact writer.
- Strict config-validating CLI.
- Source-hash and boundary regression tests.
- Single-prescreen authorization validator and claim-ledger tests.
- Quant PM `single_prescreen_only` tests.
- Scheduler decision and research-index update.
- Durable preregistration report.
- Full verification under the repository Python 3.12 environment.

## Safety

Research-to-paper only. This stage reads no forward labels and performs no factor generation. Portfolio grids, walk-forward runs, final-holdout access, paper signals, broker connections, account reads, order placement, automatic trading, and profitability claims are prohibited.
