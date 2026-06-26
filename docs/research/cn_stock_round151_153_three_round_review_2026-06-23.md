# CN Stock Round151-153 Three-Round Review

## Round Summary

| Round | Purpose | Result |
|---|---|---|
| Round151 | PIT profitability event/revision preregistration | 10 candidates designed, 7 active, 3 endpoint-dependent frozen, portfolio/promotion blocked |
| Round152 | PIT factor matrix and label-alignment smoke | 28,680 factor values, 57,360 aligned labels, 100% label coverage, 0 alignment violations |
| Round153 | Controlled IC, neutralization, and Round96 de-dup prescreen | 14 tests, 0 FDR significant, 0 neutral-gate pass, 0 research leads |

## What Improved

- The workflow now forces `ann_date` point-in-time alignment before IC. Same-day announcement trading remains blocked.
- Endpoint-dependent candidates are frozen instead of poisoning the active gate.
- The candidate-plan gate distinguishes active candidates from documented inactive candidates.
- The Round153 prescreen adds the missing controls requested in the audit: FDR, industry neutral IC, size neutral IC, liquidity neutral IC, and static profitability reference de-duplication.

## What Failed

- PIT profitability event/revision factors did not produce a robust full-sample edge on the current 100-stock CN sample.
- Raw IC was weak after multiple-testing control.
- Size/liquidity neutral evidence did not clear the gate.
- Some formulas were too close to previously rejected static profitability factors, especially margin improvement and cash earnings confirmation.

## Directional Decision

- Do not run a portfolio grid on this family after Round153.
- Do not tune these formulas in place without a new preregistered repair hypothesis.
- Rotate or repair in Round154. A useful Round154 must either:
  - bring new endpoint data such as forecast/express events,
  - explicitly orthogonalize profitability event signals against size/liquidity/static profitability references before IC,
  - or rotate to another public-reference family with a clearer return engine.

## Current State

- Research leads from Round151-153: 0.
- Promotable candidates from Round151-153: 0.
- Useful process improvement: yes. The process now prevents another blind continuation after a family fails controlled IC and neutralization.

