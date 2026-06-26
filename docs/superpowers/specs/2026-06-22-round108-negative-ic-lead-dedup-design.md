# Round108 Negative-IC Lead Dedup Design

## Context

Round107 found one research lead from the pre-registered negative-IC trend/amount family:

- `overheat_avoidance_relative_strength_60`
- Horizon: 20 days
- Mean IC: 0.0417
- ICIR: 0.309
- Q5-Q1: 0.0519
- Top-quantile turnover: 18.1%

This is not promotion evidence. It must pass a correlation de-duplication and capacity/extreme-trade audit before any portfolio conversion.

## Goal

Build Round108 as a narrow audit of the single Round107 lead. The audit decides whether the lead is unique enough and clean enough to move to a cost/capacity portfolio bridge, or whether the family should rotate.

## Design Choice

Three approaches were considered:

1. Reuse Round103 unchanged.
   - Pro: fastest.
   - Con: it only compares one factor family and cannot distinguish active-reference redundancy from expected inverse lineage.

2. Build a generic all-family dedup framework.
   - Pro: reusable.
   - Con: too broad for this round and likely to delay useful progress.

3. Build a focused Round108 audit.
   - Pro: narrow, testable, and directly tied to the only Round107 lead.
   - Con: some helper logic overlaps with Round103.

Chosen approach: focused Round108 audit.

## Reference Families

The audit compares the lead against:

- `capacity_safe_price_volume`: Round101-103 low-vol/reversal/public price-volume factors. High redundancy here is a hard blocker because this cluster was already audited and hibernated.
- `positive_trend_accumulation_source`: Round104-105 positive trend/amount factors. High inverse correlation here is expected lineage, not by itself a hard blocker.
- `negative_ic_trend_accumulation_same_family`: Round106-107 sibling candidates. High correlation here is not a promotion blocker by itself, but it prevents broad same-family expansion.

## Capacity And Extreme-Trade Audit

The audit samples signal dates after factor computation and reviews the lead's top quintile:

- top-quantile row count
- top-quantile date count
- median signal-date amount
- median ADV20 amount
- amount or ADV20 breaches
- signal-date absolute return >= 9.5% rate
- signal-date absolute return >= 20% count

The 9.5% threshold is a practical A-share limit-move proxy. It is not a full tradeability simulation, but it catches obvious cases where the selected names are dominated by hard-to-trade limit moves.

## Gates

Round108 blocks portfolio conversion if:

- the Round107 prescreen report does not confirm the lead;
- the lead factor is missing from the computed matrix;
- the lead is highly redundant with the hard-blocking `capacity_safe_price_volume` reference family;
- the top quintile has no observations;
- amount or ADV20 breaches occur after the capacity filter;
- the top-quintile signal-date abs-return >= 9.5% rate exceeds 5%.

If no hard blocker appears, the next direction is `round109_overheat_relative_strength_cost_capacity_bridge`.

If a hard blocker appears, the next direction is `round109_family_rotation_after_round108_dedup_failure`.

## Non-Goals

- No parameter tuning.
- No portfolio grid.
- No 2026 final holdout read.
- No promotion.
- No treating 30% drawdown tolerance as a capacity or tradeability waiver.
