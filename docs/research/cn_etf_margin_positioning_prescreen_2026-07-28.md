# CN ETF Margin-Positioning Prescreen Closeout

Date: 2026-07-28

## Decision

The preregistered
`etf_residual_margin_financing_growth_reversal_20` candidate is rejected.
`cn_etf_margin_positioning` is stop-lossed at zero budget.

The primary five-session row produced a small positive spread after the frozen
10 bps cost model, but failed statistical materiality, independence, and
every-date capacity gates. The 20-session diagnostic was stronger but cannot
replace or rescue the primary.

No rerun, sign flip, lookback change, control removal, threshold relaxation,
subgroup rescue, portfolio grid, walk-forward, or final-holdout access is
allowed.

## Execution integrity

- Frozen authorization ID:
  `e1a1bd00518ff83a360a30bdb4ba8373087519f340d5ba60d2184ff27e758baa`
- Authorization was claimed and consumed exactly once
- Factor and reference preparation completed before the authorization claim
  without reading forward returns
- Forward labels were read only after the atomic claim
- 2026 final holdout included: false
- Gap-crossing factor and label windows for 2020-05-28 and 2020-06-03 were
  excluded
- Candidate rows: 147,000
- Finite candidate rows: 139,592
- Candidate assets: 357
- Candidate dates: 927
- Closed-family reference rows: 5,444,088

## Frozen primary result

| Metric | H5 primary |
| --- | ---: |
| Daily IC observations | 921 |
| Mean Rank IC | 0.011358 |
| ICIR | 0.110679 |
| Newey-West p-value | 0.043922 |
| FDR q-value | 0.087843 |
| Positive IC rate | 55.483170% |
| Quintile monotonicity | 0.70 |
| Positive-year rate | 80% |
| Gross Q5-Q1 spread | 0.000540 |
| Net Q5-Q1 at 5 bps | 0.000289 |
| Net Q5-Q1 at 10 bps | 0.000037 |
| Average top-quintile turnover | 0.266148 |
| Maximum closed-family correlation | 0.154660 |
| Maximum direct-exposure correlation | 0.888064 |
| Capacity-qualified dates | 866 / 921 |

The strict failures were:

- not FDR-significant at 5%;
- mean Rank IC below 0.02;
- ICIR below 0.30;
- direct raw margin-growth exposure correlation not strictly below 0.85;
- capacity not supported on every primary date.

The positive IC rate, monotonicity, yearly sign consistency, turnover,
closed-family correlation, and 10 bps net-spread sign passed their individual
checks. They are insufficient because every primary gate was preregistered as
mandatory.

The worst capacity date was 2021-09-08. Minimum daily top-quintile P10 ADV20 was
CNY 7.10 million and maximum one-way participation was 1.407612%, above the
1% ceiling.

## Diagnostic result

The H20 diagnostic had mean Rank IC 0.012208, monotonicity 1.0, gross spread
0.001772, and net 10 bps spread 0.001268. It passed the deliberately minimal
diagnostic role criteria, but its FDR q-value was 0.217634 and it cannot rescue
the rejected H5 primary.

## Provenance

- Preregistration config SHA-256:
  `c6d11639c7e1f5c454f7ad4434e682139c074d031bd391d89034aafc76b26855`
- Preregistration result SHA-256:
  `bcc8f5030d24530f9f9afa81f2c411375fba9009ce82f70589ff6a4b7973e45d`
- Authorization SHA-256:
  `2dbc3f08f1c16a9a174b2bae3ddf1ba94188ae1fcf764c775fe6691709053fc2`
- Canonical margin dataset SHA-256:
  `f1152513e73bc69576d04a61585f3971cad007dc04482dbdc0e38d049d3565ec`
- Prescreen JSON SHA-256:
  `c509a728dd770c0250e7c856ba95b964c7f299aef7d394b914e2c5e29ec4e5ef`
- Result table SHA-256:
  `67e1ac32072c00276e56a68d40b33cd4651d78b8bca0ea78d1c2f8f314ec424b`
- Hash manifest SHA-256:
  `515d76ef758bbb39446e5c05f803a714e39898864438914186895f2c041c50ff`
- Execution ledger SHA-256:
  `b8a79342d4646091b739d1896ad71c910bf99787b399ac90faca4a945345d034`

Detailed execution evidence remains under ignored
`data/reports/cn_etf_margin_positioning_prescreen_20260728/`.

## Next direction

Do not continue margin-credit rescue work. The next primary review must use a
genuinely different point-in-time source. The highest-value external unlock is
historical official ETF PCF/constituent data, followed by audited historical
ETF benchmark membership or high-quality ETF IOPV/premium microstructure.
Without one of those sources, further mining of the same daily price, liquidity,
volatility, fund-share, option, or margin mechanisms has a high false-discovery
risk.
