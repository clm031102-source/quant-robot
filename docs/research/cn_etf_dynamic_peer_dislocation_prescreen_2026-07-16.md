# CN ETF Dynamic Peer Dislocation Prescreen Closeout

Date: 2026-07-16

Machine: `office_desktop`

Task: `factor_batch`

Branch: `codex/factor-batch-cn-etf-dynamic-peer-dislocation-20260716`

Status: rejected; `cn_etf_dynamic_comovement_peer_dislocation` stop-lossed at zero budget

## Executive Decision

The single authorization-bound prescreen for
`etf_dynamic_peer_residual_dislocation_reversal_5_60` completed exactly once.
The frozen five-session primary row failed the statistical, cross-sectional
shape, every-date capacity, and 10 bps stressed-cost gates. The 20-session
diagnostic row was negative and, by preregistration, cannot rescue the primary
result.

The family is closed with zero research budget. No rerun, sign inversion,
window or mapping change, threshold relaxation, regime rescue, portfolio grid,
walk-forward validation, final-holdout access, paper signal, or promotion is
authorized.

The next allowed work is `factor_review` for one genuinely orthogonal CN ETF
family, prioritizing point-in-time historical fund-share, scale, NAV, and
premium/discount source readiness. A new factor batch remains blocked.

## Frozen Contract And Authorization

- Preregistration config:
  `configs/cn_etf_dynamic_peer_dislocation_preregistration_20260716.json`
- Preregistration config SHA-256:
  `4811e1497bbfe9688e006dcb7764381c7ea977ddfde79790248f0223996233c6`
- Preregistration result SHA-256:
  `2038a32fa9b250a33a76bdca08c204a349a1cdec959fc3c10dbe4b6a4f6440f5`
- Authorization SHA-256:
  `c645de436c462365c443dd0574b750feb68b3955263b39a316b184862e99f5c9`
- Authorization ID:
  `6460f4cafced4f39cc963c5e0bbc31fe4ae56d7f976804ae8beebfdd0d262a62`
- Execution limit: one
- Recorded executions: one
- Authorization consumed: yes
- Primary horizon: 5 sessions
- Diagnostic-only horizon: 20 sessions
- Multiple testing: Benjamini-Hochberg across the two frozen hypotheses
- Execution lag: one market session
- Final holdout: 2026 and later, sealed

The operation built point-in-time inputs before atomically claiming the
authorization. Forward labels were constructed only after the claim. The
execution ledger and terminal outcome preserve the consumed authorization, so
the command must not be rerun.

## Data Accounting

| Item | Count or range |
| --- | ---: |
| Analysis window | 2020-01-02 through 2024-06-28 |
| Historical bar rows | 1,119,490 |
| Historical assets | 1,781 |
| Historical sessions | 1,085 |
| Point-in-time eligible rows | 291,292 |
| Eligible assets | 792 |
| Dynamic peer mapping rows | 20,301 |
| Candidate rows | 207,954 |
| Finite candidate rows | 136,612 |
| Candidate assets | 581 |
| Candidate dates | 841 |
| Raw forward-label rows | 2,191,185 |
| Market-calendar-aligned label rows | 1,952,597 |
| Historical reference factors | 39 |
| Historical reference rows | 5,327,868 |
| Daily IC observations | 1,655 |
| Yearly IC rows | 8 |
| Frozen tests | 2 |
| Research leads | 0 |

Market-calendar alignment removed 238,588 compressed next-row labels that did
not represent the frozen market-session horizons. Later partitions were
excluded before read, and the 2026 final holdout was not accessed.

## Results

| Role | H | Mean Rank IC | ICIR | FDR q | IC positive | Q5-Q1 gross | Net 5bps | Net 10bps | Monotonicity | Capacity dates | Passed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Primary | 5 | 0.004539 | 0.058640 | 0.253717 | 53.41% | 0.000369 | -0.000158 | -0.000684 | 0.30 | 466 / 835 | no |
| Diagnostic only | 20 | -0.006343 | -0.083154 | 0.253717 | 47.93% | -0.000362 | -0.000888 | -0.001414 | -0.70 | 465 / 820 | no |

Primary blockers:

- `not_fdr_significant_after_multiple_testing`
- `mean_rank_ic_below_threshold`
- `icir_below_threshold`
- `positive_ic_rate_below_threshold`
- `quantile_monotonicity_below_threshold`
- `primary_capacity_not_supported_every_date`
- `primary_10bps_net_spread_not_positive`

The 20-session diagnostic additionally had negative mean Rank IC, negative
gross spread, and negative monotonicity. It supplied no independent reason to
reopen the primary decision.

## Duplication And Exposure

- Maximum absolute historical-reference correlation: `0.201903` against
  `reversal_5`
- Maximum absolute direct-exposure correlation: `0.201903` against
  `short_return_5`
- Frozen correlation ceiling: `0.85`
- Reference evidence complete: yes
- Direct-exposure evidence complete: yes

The candidate was sufficiently distinct from the frozen historical references
and direct exposures. The rejection is caused by weak efficacy, failed shape,
cost, and capacity rather than duplication.

## Cost And Capacity

For the primary row, average top- and bottom-quintile transition turnover were
`0.526484` and `0.526008`. The small positive gross spread became negative at
both 5 bps and 10 bps one-way cost assumptions.

The all-date capacity gate also failed:

- Minimum daily top-quintile P10 ADV20: CNY `6,310,561.10`
- Maximum one-way participation: `1.584645%`
- Frozen maximum participation: `1%`
- Worst date: `2022-01-28`
- Every-date support: false

Pooled or average liquidity cannot override an unsupported date. Capacity and
cost thresholds were frozen before the run and are not eligible for relaxation.

## Provenance

- Prescreen result JSON SHA-256:
  `3cadcd4755947e1837894c25c87f7455a17bc603f416a551b9b12aed55b4c813`
- Candidate-horizon results SHA-256:
  `963c821adec8f29f5fd0f293fb13c5aa2fbf325df86cfe7126ebaddc1ef9e500`
- Generated Markdown SHA-256:
  `ddb1b9cf435644d2ff7a10a5bb713f83de8296b021bbf1af8c64b27ec0523fcb`
- Mapping SHA-256:
  `52d7c0c80b32b164583bea52cc09e0fba7436051d236df6e1ab9343387f5fe63`
- Source config SHA-256:
  `a3eeda49ade9624c1e335d9adfc7a6cdd0803def723feda9ef28a99d1e9c6016`
- Source-readiness result SHA-256:
  `4177895b7799c5074ab0b7a0102f9a1f3917d789817e5b2380497c08346fac44`

Generated CSV and JSON evidence remains under
`data/reports/cn_etf_dynamic_peer_dislocation_prescreen_20260716/` and is
intentionally excluded from Git.

## Scheduler Decision

The scheduler records:

- family status: `stop_lossed`
- family budget: `0.0`
- unallocated primary budget: `1.0`
- factor batch allowed: false
- family rotation review allowed: true
- portfolio grid allowed: false
- walk-forward allowed: false
- final holdout allowed: false
- promotion and paper signal allowed: false

Price rotation, liquidity-capacity, volatility-regime, and dynamic-peer
dislocation are now closed. Peer relative value, ETF-level flow breadth, and
fund structure remain source-blocked or unallocated; none is authorized for
factor generation.

## Next Research Direction

Open a separate `factor_review` task and audit one orthogonal CN ETF source
family, prioritizing fund structure:

1. Inventory local and provider-backed historical ETF share, scale, NAV, close,
   and premium/discount fields.
2. Establish point-in-time publication timing, revision behavior, lifecycle
   handling, and date coverage before calculating a factor.
3. Require audited coverage through 2025 before any walk-forward proposal while
   keeping 2026 sealed.
4. Search existing formulas and rejection evidence for duplication.
5. Only if source readiness passes, preregister one compact hypothesis and one
   bounded prescreen. Do not implement a parameter grid first.

If the source cannot be made point-in-time safe or historically complete,
record an external source blocker and rotate again. Do not recycle the closed
price, volatility, liquidity, or peer-dislocation families under new names.

## Safety Boundary

This is research-to-paper evidence only. It is not evidence of profitability,
paper readiness, or live readiness. Broker connection, account reads, order
placement, automatic trading, and all live boundaries remain disabled.
