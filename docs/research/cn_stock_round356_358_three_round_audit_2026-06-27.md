# CN Stock Round356-358 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Rounds Reviewed

| Round | Work | Status |
|---:|---|---|
| 356 | Shortlist block-dependence audit | Completed |
| 357 | Strict block-gate sensitivity | Completed |
| 358 | Simulation lane decision audit | Completed |

## Main Finding

The current shortlist is stronger than a one-year fluke, but weaker than a fully smooth all-regime alpha.

Round356 is constructive:

- all five candidates remain positive after removing their most important year;
- all five stay below the 70% top-three-month concentration blocker;
- 2015 is the dominant removed year, but not the only source of return.

Round357 is cautionary:

- 0 of 5 pass the deliberately strict gate of +3% leave-one-year annualized return, 0.40 leave-one-year overlap Sharpe, and no more than 45% top-three-month log contribution;
- this means the family still carries meaningful early-period contribution and should not be marketed as regime-independent.

## Lane Decision

Keep four simulation lanes and one reference lane.

| Lane | Decision | Reason |
|---|---|---|
| `primary_high_return` | Keep as return-seeking lane | Best total return and acceptable user drawdown profile, but highest strict-gate fragility |
| `primary_balanced_zz500_75` | Keep as middle lane | Best compromise after strict block sensitivity; only concentration blocker |
| `primary_defensive_zz500` | Keep as default robustness lane | Strong cost/pass profile and robust leave-one-year overlap |
| `primary_ps_filtered_defensive_zz500` | Keep as defensive diagnostic lane | Best overlap/concentration profile, lower return floor |
| `safer_defensive_zz500` | De-emphasize as ultra-defensive reference | Lowest drawdown, but weaker corrected leave-one-year return and no independent information beyond `primary_defensive_zz500` |

## What This Says About Direction

The work is not drifting back into blind factor fishing.

The current productive path is:

1. extract one real long-cycle lead from low-turnover repair;
2. fix its tradeability/capacity failure with entry-cash and stale-turnover filters;
3. control drawdown with volatility targeting and CSI500 trend state;
4. audit beta, costs, capacity, return concentration, and overlap;
5. reduce candidate count before simulation.

The limitation is equally clear:

- these are highly related variants of one signal family;
- they are not five independent profitable factors;
- the family still depends materially on 2015 and struggles in 2018;
- strict block gates show that simulation should begin cautiously.

## Updated Next Work

Round359 should package and push:

- reusable block audit module and CLI;
- Round356/357/358 docs;
- shortlist config/runbook updates;
- unit tests and config validation.

After Round359, the next mining direction should be one of:

1. implement a repeatable simulation entrypoint for the four retained lanes;
2. run holding/rebalance/TopN sensitivity if the entrypoint can reproduce the official event streams;
3. search for genuinely orthogonal data sources only if they pass the startup gate and are not in the blocked-family list.

Do not add more same-family variants until the simulation mapping is repeatable.
