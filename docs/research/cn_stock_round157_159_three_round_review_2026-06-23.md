# CN Stock Round157-159 Three-Round Review

- Date: 2026-06-23
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Review cadence: required after every 3 factor-mining rounds

## Round Summary

| Round | Direction | Result | Decision |
| --- | --- | --- | --- |
| 157 | Price-volume shock reversal preregistration | 8 candidates, 7 families, 0 RSRS, 0 portfolio/promotion | Proceeded only to neutral prescreen |
| 158 | Price-volume shock neutral/residual prescreen | 8 tested, 0 residual research leads, 0 portfolio candidates, 0 promotion | Hibernate this family; no parameter tuning |
| 159 | A-share tradeability/limit-event preregistration | 8 candidates, 7 families, all require true-limit and tradeability audit, 0 portfolio/promotion | Rotate to Round160 proxy prescreen |

## Round158 Failure Diagnosis

The best raw signals did not survive the gates that matter for a tradable CN stock factor:

- `downside_volume_absorption_reversal_10_60`: raw IC 0.0348, neutral IC 0.0343, residual IC 0.0150, residual ICIR 0.219. Blocked because residual mean was below threshold and exposure/yearly stability remained weak.
- `amihud_shock_reversal_liquid_20_60`: raw IC 0.0224, neutral IC 0.0193, residual IC 0.0174, residual ICIR 0.247. Blocked by subthreshold neutral/residual quality, high reference redundancy, and style exposure.
- The remaining six candidates were weaker or unstable after neutral/residual checks.

This means the family had interesting raw/industry-neutral fragments but no robust residual alpha and no justified portfolio conversion path.

## Optimization Added Before Continuing

The startup protocol now requires explicit per-run confirmation for:

- A-share real tradeability controls.
- Financial PIT timing and revision/lag handling.
- Industry/style neutralization.
- CN stock vs CN ETF scope boundary.
- Portfolio construction controls beyond raw TopN.
- Strict statistical checks.
- China market regime controls.
- Event-factor PIT and contamination controls.

These controls are now in `configs/factor_mining_startup_cn_stock.json` and are checked by the default startup-gate tests.

## Direction Decision

Do not continue moneyflow-only, RSRS, or price-volume shock tuning. Round160 should run `round160_cn_tradeability_limit_event_proxy_prescreen` on the Round159 candidate set with long-cycle sample, lagged labels, tradeability-blocked signal counts, industry/style residual checks, and FDR accounting.

No factor from Round157-159 is promotable yet. Round159 only improves the search direction and process discipline.
