# CN Stock Round434-436 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Rounds Reviewed

| Round | Focus | Result | Decision |
|---:|---|---|---|
| 434 | Entry-known calendar overlay | `zero_quarter_end5` improves drawdown and overlap Sharpe across 10/20/30 bps with modest return sacrifice | Add as defensive simulation lane, not independent alpha |
| 435 | Lagged ZZ500 momentum/drawdown regime overlay | No fixed market-state rule improves both annualized return and overlap Sharpe | Reject and block threshold tuning |
| 436 | Delayed-exit trade exposure audit | Industry exposure is clean; active trades are structurally main-board/XSHG/HS-H and same-day-exit dominated | Disclose structural boundary; do not add industry cap |

## What Improved

The sprint now has a better simulation pack, not just a higher-return candidate:

- default return-seeking lane: delayed-exit 10 bps baseline;
- cost-stress lanes: delayed-exit 20 bps and 30 bps;
- defensive lane: quarter-end no-new-entry overlay;
- structural risk disclosure: main-board/XSHG/HS-H exposure and delayed-exit loss monitor.

Most useful new result:

`zero_quarter_end5` at 10 bps reduces max drawdown from -26.21% to -23.20%, improves overlap Sharpe from 0.496 to 0.546, improves beta-hedged overlap Sharpe from 0.792 to 0.869, and lowers best-three-month concentration from 45.72% to 39.61%. It does this while keeping annualized return at 6.40%.

## What Was Rejected

ZZ500 market-state overlays are not useful for the current candidate. Weak benchmark states are not consistently bad for the strategy; some of the signal's return appears to come from stressed or rebound-prone market states. Reducing exposure there cuts the edge.

Industry caps are also not justified. Active industry concentration passes the exposure gate:

- p95 top industry weight share: 16.67%;
- average industry HHI: 0.0483;
- top industry absolute return contribution share: 6.72%.

The actual concentration is structural rather than industry-specific:

- main board: 99.09% active weight;
- XSHG: 83.97% active weight;
- HS-H flag: 73.70% active weight;
- same-day exit: 98.97% active weight.

## Plan Adjustment

Do next:

1. Keep the delayed-exit baseline as the default high-return lane.
2. Carry `zero_quarter_end5` as a defensive paper-simulation lane.
3. Stop tuning ZZ500 momentum/drawdown filters on this candidate.
4. Do not add industry caps unless a future audit shows industry concentration failure.
5. Continue mining only directions that add new evidence or simulation value, preferably:
   - statistical reality checks on the current pack;
   - CPCV/purged walk-forward style robustness;
   - independent event/accounting source only if coverage and PIT gates are already proven.

## Current Best Package

| Lane | Annualized | Total | Overlap Sharpe | Max DD | OOS Strict | Role |
|---|---:|---:|---:|---:|---:|---|
| delayed-exit 10 bps baseline | 6.663% | +218.46% | 0.496 | -26.21% | 90.00% | default return-seeking |
| delayed-exit 10 bps + quarter-end overlay | 6.400% | +204.62% | 0.546 | -23.20% | 90.00% | defensive simulation lane |
| delayed-exit 20 bps baseline | 6.060% | +187.60% | 0.456 | -28.07% | 76.67% | heavier-cost lane |
| delayed-exit 20 bps + quarter-end overlay | 5.886% | +179.27% | 0.506 | -24.06% | 90.00% | defensive heavy-cost lane |
| delayed-exit 30 bps fallback | 5.415% | +157.79% | 0.416 | -29.66% | 76.67% | stress fallback |
| delayed-exit 30 bps + quarter-end overlay | 5.284% | +152.08% | 0.465 | -25.61% | 76.67% | defensive stress fallback |

No new independent alpha factor was promoted in these three rounds. The useful output is a stronger, clearer simulation handoff pack with one defensive risk-control overlay and fewer tempting but weak directions.
