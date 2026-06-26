# CN Stock Round222 Family Rotation: Financial PIT Post-Announcement Drift

Date: 2026-06-24

Scope: CN A-share stock cross-sectional alpha research. This is a family-rotation and preregistration handoff. It is not ETF rotation, not a portfolio backtest, not a promotion memo, and not live trading.

## Rotation Decision

Selected family:

`financial_pit_post_announcement_drift`

Next direction:

`round222_financial_pit_post_announcement_drift_preregistration`

Rotation tool result:

- Status: cleared.
- Families reviewed: 6.
- Hibernated families: 4.
- Selected families: 1.
- Research preregistration allowed: true.
- Portfolio grid allowed: false.
- Promotion allowed: false.
- Blockers: none.

Local tool output:

`data/reports/cn_stock_family_rotation_decision_round222_financial_pit_post_announcement_drift_20260624/`

## Why This Direction

Rounds 219-221 show that another price-shape family is low-value right now:

- Round219 public trend-strength-state: 0 residual leads.
- Round220 industry leader-lag diffusion: 0 promotable residual candidates.
- Round221 information discreteness / FIP: 0 residual leads, 0 portfolio preflight candidates, and 0 promotions.

The next family needs a different information channel. Financial PIT post-announcement drift is public, interpretable, and directly tied to the earlier control work on `ann_date`, `available_date`, and `signal_date`. It tests whether the market underreacts to financial announcements after the information is actually tradable.

This is not a return to direct profitability-quality formula tuning. The event timing and reaction layer is the mechanism; direct profitability metrics without event-timing controls remain hibernated.

## Candidate Seed

Preregister these ideas before IC or portfolio work:

- `pead_event_reaction_continuation_1_20`
- `pead_event_gap_underreaction_1_20`
- `pead_volume_disagreement_drift_1_20`
- `pead_late_announcer_risk_reversal_5_20`
- `pead_positive_fundamental_change_low_reaction_20`
- `pead_negative_surprise_reaction_avoidance_20`
- `pead_reaction_quality_residual_composite_20`

## Mandatory Controls

Round222 must include these controls before any profitability claim:

- `financial_pit_signal_date_filter_required`
- `ann_date_available_date_signal_date_preserved`
- `no_same_day_announcement_reaction_trading`
- `event_day_reaction_available_next_trade_date_only`
- `financial_coverage_audit_before_ic`
- `tradeability_mask_required`
- `industry_style_residual_evaluation`
- `profitability_valuation_reference_dedup_required`
- `event_family_reference_dedup_required`
- `multiple_testing_accounting`
- `no_portfolio_grid_before_residual_ic_shape_prescreen`
- `china_regime_coverage_required`

## Blocked Continuations

The following are explicitly rejected:

- FIP/information-discreteness parameter tuning after Round221 zero residual leads.
- FIP TopN, cost/capacity, or portfolio grids after Round221 failure.
- Using the Round221 Q2 smoke as promotion evidence.
- Industry leader-lag parameter tuning after Round220 full-sample failure.
- Public trend-state window tuning after Round219 residual failure.
- Direct profitability-quality formula tuning under a post-announcement name.

## First Round222 Work Item

Start with preregistration and coverage, not IC:

1. Confirm the financial root is `data/processed/round202_financial_pit_signal_filtered_20260623` or a newer filtered PIT root.
2. Audit whether coverage is sufficient for a full-cycle cross-sectional claim.
3. Define event-day reaction availability so event-day close/open/volume observations are only used on a later tradable date.
4. Generate factor rows with PIT columns preserved.
5. Only then run residual IC, reference de-duplication, and exposure checks.

## Safety

Research-to-review only. No broker connection, no live account reads, no order placement, and no automatic live trading.
