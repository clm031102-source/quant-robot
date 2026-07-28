# CN ETF Fund-Structure Crowding Prescreen Closeout

Date: 2026-07-28

Branch: `codex/factor-batch-cn-etf-fund-structure-20260728`
Market: `CN_ETF`

## Decision

The frozen candidate
`etf_residual_share_creation_crowding_reversal_20` failed its five-session
primary gate and the family is closed at zero budget. The twenty-session row
was diagnostic only and cannot rescue the primary. No sign flip, window
change, control removal, threshold relaxation, subgroup rescue, portfolio
grid, walk-forward, or holdout read is allowed.

This is not a paper-ready or profit-validated strategy.

## Frozen execution

- One candidate and two counted hypotheses: H5 primary, H20 diagnostic.
- The hash-bound authorization was atomically claimed once and is consumed.
- Analysis window: 2020-01-02 through 2024-06-28.
- 2026 final holdout remained sealed.
- 645,645 fund-structure rows and 1,119,490 price rows were read.
- 283,787 finite candidate rows covered 771 ETFs and 965 signal dates.
- The source, five canonical yearly partitions, preregistration, authorization,
  config, execution artifacts, and claim ledger are fingerprinted under
  ignored `data/reports/` paths.

## Results

| Role | Horizon | Mean Rank IC | ICIR | FDR q | Positive IC rate | Monotonicity | Gross spread | Net spread at 10 bps | Capacity dates | Passed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Primary | 5 | 0.006219 | 0.058750 | 0.576070 | 0.527633 | 0.60 | 0.001368 | 0.001078 | 378 / 959 | No |
| Diagnostic | 20 | 0.001172 | 0.011994 | 0.904735 | 0.523305 | 0.70 | 0.003057 | 0.002766 | 377 / 944 | Diagnostic only |

The H5 row retained a positive average spread after the frozen 10 bps one-way
cost stress, but it failed FDR, minimum mean IC, ICIR, positive-IC frequency,
monotonicity, and every-date capacity. Minimum daily top-quintile P10 ADV20 was
CNY 6.05 million and maximum one-way participation reached 1.652690%, above
the one-percent limit.

Maximum absolute closed-family correlation was 0.229150. Maximum direct
exposure correlation was 0.849910, just below the strict 0.85 ceiling. The
candidate was therefore not rejected as a duplicate; it was rejected because
the predictive evidence was weak and unstable.

## Evidence identities

- Preregistration config:
  `a6a7a7f3d694e0a8484d907302f4f35c423a8432e1fb24b687c9896e7bc8ce8e`
- Preregistration result:
  `6d76024f892e82a849bbe3de8d2d1c8c13635924993fa9f6f4eb2bd232f82e13`
- Authorization:
  `383a87953a5263faacb46ab6fc893ad58cc1300b364dc463869a72e8776e0b3d`
- Prescreen result:
  `a75c8cab26244e6f74b0053deb4381460d8163574d90bf38d5a2f1ccbf8171d0`
- Candidate-horizon table:
  `9255caf9cc63f246866fad31ad3d06dc28190001fef6121201bcb58d956aff8f`
- Hash manifest:
  `c5f35b4b6f68db9f7c5b1dde5715d2e8b49f3fd0277f79e4d40a807965b975ca`
- Execution ledger:
  `63374c5ff36440349dcace1ce3ddfb6e82d55e22ae635728db430fa3c0d02f23`

## Next direction

Rotate to a genuinely orthogonal CN ETF source family. The next review must
start from source availability and point-in-time integrity; it must not reuse
the closed price, liquidity, volatility, dynamic-peer, or fund-share crowding
spaces. The project remains research-to-paper only, with no broker, account,
order, or live-trading access.
