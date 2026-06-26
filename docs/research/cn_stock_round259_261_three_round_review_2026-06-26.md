# CN Stock Round259-261 Three-Round Review

Date: 2026-06-26

Machine: office_desktop

Scope: CN stock factor mining, research-to-review only

## Summary

Rounds 259-261 tested three orthogonal families after the daily-basic and forecast lines were hibernated:

| Round | Family | Candidates | Tests | Residual Leads | Portfolio Candidates | Decision |
|---:|---|---:|---:|---:|---:|---|
| 259 | listing age and board structural constraints | 7 | 14 | 0 | 0 | hibernate |
| 260 | official A-share tradeability event state | 7 | 14 | 0 | 0 | hibernate |
| 261 | industry breadth and dispersion regime translation | 6 | 12 | 0 | 0 | hibernate |

Total for this review block: 20 unique candidates, 40 horizon tests, 0 residual research leads, 0 portfolio preflight candidates, 0 promotable candidates.

## What Improved

The workflow improved materially compared with the earlier blind-search phase:

- Every family was pre-registered before screening.
- All three rounds used 2015-2025 long-cycle replay rather than relying on 2023-2024 short windows.
- Short-window smoke results were treated as pipeline checks only.
- Industry/style neutralization and size/liquidity/volatility residualization were hard gates.
- Portfolio grids and promotion were blocked before residual leads existed.
- Failed families were written into startup constraints so the next run cannot quietly tune the same line.

This is the right process, even though the results were poor.

## Why Results Were Poor

The common failure pattern is not random noise alone. The main issue is IC-to-residual collapse:

- Round259 listing-age/board factors had some short-window provisional leads, but all disappeared across 2015-2025.
- Round260 official tradeability events contained useful risk-state information, but as alpha they failed raw/neutral/residual consistency. The best residual diagnostic, `official_st_name_risk_avoidance_20`, had residual IC 0.0279 but weak ICIR and negative raw/neutral layers.
- Round261 industry breadth-regime factors had strong raw/neutral IC in places, but residual IC peaked at only 0.0127 with weak ICIR and many yearly failures.

The pattern says many candidate families are describing market structure, liquidity, style, or tradeability risk, not independent stock-selection alpha.

## Direction Audit

The three directions were not a repeat of the earlier moneyflow-only mistake. They covered structural listing state, official trading constraints, and industry breadth/regime translation. That is a better rotation cadence.

The weakness is that all three still relied mainly on transformed price/bar/state information. They did not yet introduce a truly new information source with strong point-in-time economic content. The next useful direction should be more orthogonal than another price/industry-state transformation.

## Stop-Loss Decisions

Do not continue these families without a new orthogonal hypothesis:

- `listing_age_board_structural_constraints_after_round259_zero_residual_leads`
- `official_tradeability_event_state_after_round260_zero_residual_leads`
- `industry_breadth_regime_translation_after_round261_zero_residual_leads`

Do not run TopN portfolio grids, sign flips, window sweeps, or reference-dedup walk-forward from these families. There are no core residual survivors to justify that cost.

## Next Direction

Round262 must rotate again. The preferred next direction is a true event or information-updating family with better point-in-time semantics, not another raw price-volume or industry-state variant.

Highest-priority candidates for Round262:

- event revision or expectation update with verified available dates, if a non-forecast data source exists locally;
- industry relative information surprise only if coverage can be made broad and PIT-safe;
- regime-conditional translation only as an overlay after a standalone residual lead exists;
- cached feature-matrix infrastructure for heavy industry/regime states before re-entering any industry-state family.

Final holdout remains blocked. Promotion remains impossible without residual lead, reference dedup, cost/capacity walk-forward, and regime coverage.

