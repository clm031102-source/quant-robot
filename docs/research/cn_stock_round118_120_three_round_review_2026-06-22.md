# CN Stock Round118-120 Three-Round Review

## Scope

This review covers the three most recent CN stock factor-mining rounds:

- Round118: soft-capacity low-turnover walk-forward early-stop audit.
- Round119: low-vol/reversal/liquidity incremental-residual preregistration.
- Round120: fixed full-sample incremental-residual IC/quantile/turnover/reference/exposure prescreen.

## Results

| Round | Direction | Candidates or rows | Useful result | Promotion |
|---|---|---:|---|---:|
| 118 | Soft-capacity low-turnover continuation audit | 108 completed OOS rows | 0 accepted rows, 0 positive-relative rows, early stop triggered | 0 |
| 119 | Incremental-residual preregistration | 8 candidates | Clean preregistration and no portfolio permission | 0 |
| 120 | Incremental-residual full-sample prescreen | 8 candidates, 24 tests | 1 raw statistical lead, 0 true incremental leads after gates | 0 |

Round120 fixed artifact:

`data/reports/lowvol_reversal_liquidity_incremental_residual_prescreen_round120_fixed_20260622`

## Bright Data

Round120 did produce one strong raw statistical result:

| Factor | Horizon | IC | ICIR | t-stat | IC positive | Q5-Q1 | Monotonicity | Top turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `range_contraction_incremental_residual_20` | 20 | 0.0548 | 0.530 | 27.10 | 68.6% | 0.06349 | 0.900 | 21.7% |

This is the strongest raw data point in this three-round block. It is also the most important rejection: after fixing the reference-correlation audit, it was highly redundant with `range_contraction_lowvol_reversal_20` with max abs correlation 0.9001.

## Why The Block Produced No Usable Factor

1. The low-turnover line did not survive relative OOS validation.

Round118 showed that the soft-capacity version removed the worst capacity issue, but also removed the attractive relative performance. Continuing that sweep would likely waste compute.

2. The incremental-residual line stayed too close to its parent cluster.

Round120 had 22 FDR-significant tests out of 24, but FDR significance alone is not enough. The only strict raw lead was blocked by reference redundancy.

3. The public technical family is becoming a cluster, not a source of fresh alpha.

Many of these indicators are public, intuitive, and statistically active, but they overlap strongly with low-vol/reversal/liquidity exposures already observed in earlier rounds.

4. A process bug almost produced an overly optimistic conclusion.

The initial reference audit used independently sampled candidate and reference dates, creating false zero-overlap rows. This was fixed and covered by a regression test. The corrected conclusion is stricter: 0 true incremental leads.

## Decisions

- Hibernate the exact soft-capacity low-turnover continuation line.
- Hibernate the exact low-vol/reversal/liquidity incremental-residual continuation line.
- Do not promote `range_contraction_incremental_residual_20` from raw IC strength.
- Do not flip negative-IC residual candidates without new preregistration.
- Rotate away from the current technical low-vol/reversal/liquidity cluster.

## Next Direction

Advance to:

`round122_financial_profitability_quality_data_coverage_preflight`

Rationale:

- The recent technical families are repeatedly redundant.
- Tushare financial/profitability data exists in the project and should be audited for point-in-time lag, coverage, and survivorship risk before factor mining.
- Profitability-quality factors have a stronger economic story than another same-cluster technical residual.

Round122 should not mine a portfolio immediately. It should first answer:

- Which Tushare financial fields are available by date and asset?
- What reporting lag should be enforced?
- How much coverage exists from 2015-2025?
- Are there enough observations for CN stock cross-sectional IC?
- Which profitability-quality templates can be preregistered without future leakage?

## Engineering Actions

Before more full-sample sweeps, add or prioritize:

- Cached/reusable full-sample label matrices.
- Cached reference-factor matrices for common clusters.
- Chunked candidate/reference correlation diagnostics.
- A report field that distinguishes raw statistical leads from true incremental leads.

The current full-sample prescreen is correct but expensive. The next framework improvement should make correctness cheaper, not loosen the gates.
