# CN ETF Delayed-NAV Premium Prescreen Decision — 2026-07-29

## Decision

The single-use prescreen was completed exactly once, but the execution is
non-governing and invalidated. Post-execution review found three material
contract defects:

- a late announcement for an older NAV date could replace a newer NAV that was
  already available;
- the implementation did not execute the conditionally preregistered
  neutralization contract;
- the authorization hashes covered NAV evidence but did not bind the mutable
  bar, lifecycle, and trading-calendar authorities used for factors and labels.

The `cn_etf_nav_premium_relative_value` family is therefore closed at zero
research budget without a valid pass-or-reject conclusion. The authorization
was consumed, and the observed labels make a corrected second run a prohibited
post-result retry. No sign flip, lookback change, neutralization redesign,
threshold relaxation, subgroup selection, second execution, portfolio grid,
walk-forward run, final holdout read, or paper promotion is authorized.

## Frozen Evidence

- Candidate: `etf_delayed_nav_premium_innovation_reversal_60`
- Analysis dates: 2020-01-02 through 2024-06-28
- Point-in-time NAV rows/assets: 705,081 / 1,067
- Bar rows/assets/sessions read: 1,121,050 / 1,781 / 1,087
- Eligible asset-date rows: 291,579
- Finite candidate rows/assets/dates: 127,022 / 591 / 907
- Closed-family reference factors/rows: 39 / 4,953,858
- Final 2026 holdout included: false
- Current-name or current-theme input used: false
- Authorization executions allowed/consumed: 1 / 1
- Execution metrics governing: false
- Corrected rerun allowed: false
- Revalidated exact `known_from` violations: 0

Hash identities:

- Preregistration config: `2b2af772c377257531cd9692550790def6c6112862f37d1208abd65f4c8f11f9`
- Preregistration result: `98c15eef32ade8180d74a402e65aadaba6e903a1310838ff5c653cedb73dcaa3`
- Single-use authorization: `2866603a951b63c11f05422d9fa6890ab2f7231a5d3313f118e3c3c8e830c7f4`
- Canonical NAV: `8cbc3a63561dbfcb0a42dcef56b053da484c149f32f1554ff271c1875cb6338a`
- Strictly revalidated source result: `f6ec09a2631eb0972781ee94d5e2f00979d0145c381d517f8bbbbcb56a52b43c`
- Prescreen result: `39d5e4add6e6e4558e3b86e90b29e2ea59436966bcea50f9d3bc9d06b26d7395`
- Candidate-horizon table: `3d63248e27d742785078b72cf0e4d5759ba5677fe36c50b394196db4160a1cf0`
- Hash manifest: `c655701e3f90e97dca85b1925c1e32436e42d18627d93a5ae283849a4748051c`
- Execution ledger: `ab27aafae62acbb893cae84fe9f4eb52708801679e8661e898927c031bef063d`

Generated result data remains ignored under
`data/reports/cn_etf_delayed_nav_premium_prescreen_20260729`; it is not a Git
payload.

## Non-Governing Diagnostic Output

The following values describe the invalid execution only. They must not be
used for promotion, rejection, parameter choice, or a later corrected run.

| Gate metric | H1 primary | H5 diagnostic |
|---|---:|---:|
| Mean rank IC | 0.025348 | 0.013284 |
| ICIR | 0.075484 | 0.040651 |
| FDR-adjusted p-value | 0.046319 | 0.327334 |
| Positive IC rate | 53.37% | 50.17% |
| Gross top-minus-bottom spread | 4.21 bp | 14.45 bp |
| Net spread at 10.5 bp/side base cost | -7.27 bp | 2.98 bp |
| Net spread at 26.6667 bp/side CNY 3,000 fee stress | -24.93 bp | -14.68 bp |
| Net spread at 60 bp/side CNY 1,000 fee stress | -61.35 bp | -51.09 bp |
| Maximum absolute closed-family correlation | 0.4787 | 0.4787 |
| Maximum absolute direct-exposure correlation | 0.9291 | 0.9291 |
| Capacity dates supported | 905 / 905 | 901 / 901 |

Observed H1 blockers under the invalid execution:

- ICIR below 0.30;
- positive IC rate below 55%;
- direct exposure correlation above the strict 0.85 ceiling, driven by
  `raw_nav_premium`;
- net spread at the 10.5 bp/side base cost is not positive.

The invalid execution also observed a maximum one-way participation rate of
0.0144% at CNY 1,000 position size. That diagnostic does not establish
capacity readiness for a corrected signal.

## Small-Capital Reality

The operator inputs remain:

- total capital: CNY 1,000–3,000;
- commission: 0.5 bp per side;
- slippage: 10 bp per side;
- absolute drawdown veto: 40%;
- paper promotion drawdown cap: 8%;
- maximum holding period: 252 sessions;
- maximum single position: CNY 1,000;
- maximum daily loss: CNY 60.

The base round trip without a minimum commission is 21 bp. If the future
broker applies a CNY 5 minimum commission per side, the effective round trip is
53.33 bp at CNY 3,000 and 120 bp at CNY 1,000. The broker's actual minimum
commission and other exchange fees therefore matter more than the advertised
0.5 bp rate at this capital size.

## Paper and Broker Readiness

There is currently no strategy eligible to enter paper observation. The
physical promotion requirements remain entirely uncompleted:

- at least 20 elapsed paper-observation days;
- at least 30 simulated fills;
- at least two market regimes;
- paper maximum drawdown no worse than 8%;
- manual promotion review.

The offline execution-interface contract is schema-ready and repeatably
validated by:

```powershell
python scripts\run_cn_etf_execution_interface_contract_readiness.py
```

It freezes order-intent idempotency, limit-order-only defaults, instrument
metadata, pre-trade risk checks, kill switch, reconciliation, audit logging,
manual confirmation, and the CNY 1,000–3,000 risk envelope. The broker is
unselected and all external boundaries remain disabled.

To implement a concrete broker adapter later, the missing inputs are the
broker/API documentation, sandbox endpoint, authentication/session model,
account type, supported SSE/SZSE ETF scope, minimum commissions and other
fees, supported order types, lot-size/tick/trading-status rules, rate limits,
error/idempotency semantics, and fill/position/cash reconciliation endpoints.

## Next Direction

Do not spend another research execution on this factor family. Future
prescreens must select the maximum NAV date among rows already available,
freeze any neutralization formula explicitly, and bind bar partitions,
lifecycle metadata, trading-calendar data, and the calendar manifest before
authorization. The next candidate must be economically independent of raw NAV
premium and all eight closed CN ETF families, with a new source/readiness
thesis and preregistration before labels are read. Until a frozen candidate
passes, broker integration is an interface-engineering exercise only and must
not be presented as a path to live profit.

No broker connection, account read, order placement, or live-trading action
occurred.
