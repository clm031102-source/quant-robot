# Audit Remediation Suite Design

## Goal

Convert the strict audit findings into enforceable research, data-quality, cost, readiness, and execution-boundary controls without pretending that code can prove live profitability.

## Scope

This work addresses three classes of audit findings:

- Code-verifiable gaps: single-split validation, weak statistical evidence, thin cost modeling, shallow data-quality checks, and permissive promotion evidence.
- Evidence-gated gaps: short paper history, provider data gaps, stale provider readiness, and missing live-readiness provenance.
- Non-code gaps: real broker execution, real account reads, live fills, and sustained profit evidence. These remain blocked until external evidence exists.

## Architecture

The remediation keeps the existing pipeline shape:

```text
data -> factors -> labels -> research -> validation -> promotion -> paper ops -> execution boundary
```

The implementation adds stricter evidence artifacts rather than bypassing existing stages. Existing commands remain backward compatible, but new fields allow stronger gates and reports.

## Components

### Rolling Validation

`quant_robot.validation.walk_forward` gains optional rolling folds. Existing `split_date` behavior remains valid. Rolling mode aggregates train/test metrics by case across folds and reports fold counts, accepted-fold counts, mean test metrics, worst drawdown, and fold rejection reasons.

### Statistical Evidence

`quant_robot.research.ic` and `quant_robot.research.pipeline` add IC t-statistics, approximate p-values, positive IC rate, observation counts, and significance status. These are summary fields for gates and reports; they do not replace out-of-sample returns.

### Cost And Capacity Evidence

`quant_robot.backtest.costs` adds a structured transaction cost model with commission, spread, slippage, and market-impact components. Backtests and paper reports can emit estimated cost bps and participation warnings when volume or amount data is available.

### Data Quality Evidence

`quant_robot.data.quality_report` adds extreme-return, stale-price, and adjusted-close jump counts. These fields become promotion warnings or blockers depending on severity.

### Promotion And Readiness Gates

`quant_robot.promotion.gate` consumes the new evidence fields. Missing statistical evidence, severe data-quality failures, short rolling validation, and stale provider-readiness provenance prevent promotion beyond `research_only`.

### Execution Boundary

A read-only execution boundary module records what a future broker adapter is allowed to do: account snapshot read models, manual approval packets, kill-switch state, and explicit refusal to place orders. This is scaffolding for safe review, not live trading.

## Error Handling

All new gates fail closed:

- Missing evidence becomes a blocker or warning, never an implicit pass.
- Unknown data-quality fields remain backward compatible but are marked as missing evidence in new strict modes.
- Live-order fields must remain false unless a future explicit live phase changes the boundary.

## Testing

Every behavior change is test-first:

- Rolling validation tests verify multiple folds and fold aggregation.
- Statistical tests verify t-stat and p-value behavior.
- Cost tests verify cost decomposition and cost-adjusted returns.
- Data quality tests verify extreme, stale, and adjusted-jump counts.
- Promotion tests verify weak evidence cannot become `paper_ready`.
- Execution-boundary tests verify read-only behavior and kill-switch defaults.

## Non-Code Evidence Still Required

The following audit findings cannot be fixed by code alone and stay as explicit gates:

- At least 20 real paper-observation ready runs.
- Provider-level missing date rows resolved or accepted with reviewed evidence.
- Real broker account and order-routing approval by the user.
- Small-capital live trial evidence before any automated trading.
