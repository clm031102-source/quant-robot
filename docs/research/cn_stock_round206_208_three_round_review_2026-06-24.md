# CN Stock Round206-208 Three-Round Review

- Date: 2026-06-24
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock cross-sectional alpha research only
- Safety: research-to-review only; no broker, no account reads, no orders, no live trading

## Why This Review Exists

The standing protocol says every three work rounds must trigger review, audit, and direction adjustment. This block covers:

- Round206: event-factor control closeout.
- Round207: 52-week high / anchor momentum quality prescreen.
- Round208: inverse 52-week high overextension avoidance prescreen.

The question is whether the project should keep working the 52-week family, promote anything, or rotate.

## Round206 Summary

Round206 closed the event-factor control gap without turning event data into alpha claims.

Key outcomes:

- Event controls closed: 3 / 3
- Event direct alpha allowed: false
- Event portfolio grid allowed: false
- Non-event CN stock factor generation allowed: true
- Direct CN stock blockers after control closeout: 0

This was infrastructure progress, not profitability evidence.

## Round207 Summary

Round207 pre-registered four 52-week high / anchor quality candidates and ran a full 2015-2025 IC, FDR, quantile, and turnover prescreen.

Data:

- Bar rows: 10,785,537
- Assets: 5,707
- Factor rows: 38,085,208
- Aligned rows: 75,581,788
- Tests: 8

Result:

- FDR-significant tests: 8 / 8
- Research leads: 0
- Promotion candidates: 0

Best evidence was strongly negative, not buyable:

| Factor | Horizon | IC | ICIR | t-stat | Q5-Q1 | Decision |
|---|---:|---:|---:|---:|---:|---|
| `high_52w_breakout_amount_confirmation_252_20` | 20 | -0.0615 | -0.395 | -19.88 | -0.0720 | wrong-way |
| `high_52w_proximity_liquid_quality_252_20` | 20 | -0.0519 | -0.306 | -15.38 | -0.0736 | wrong-way |

Interpretation:

Buying high-anchor names did not work. It looked like an overextension/crowding clue, so a reverse hypothesis was allowed only as a new preregistered test.

## Round208 Summary

Round208 treated the Round207 negative evidence as a new hypothesis, not as automatic proof. Four inverse/avoidance candidates were pre-registered, passed candidate-plan gate, and were tested on the same 2015-2025 long cycle without reading final holdout.

Data:

- Bar rows: 10,785,537
- Assets: 5,707
- Factor rows: 38,085,208
- Aligned rows: 75,581,788
- Tests: 8

Result:

- FDR-significant tests: 6 / 8
- Research leads: 0
- Promotion candidates: 0

Top Round208 rows:

| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Turnover | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `avoid_high_52w_breakout_amount_exhaustion_252_20` | 5 | 0.0178 | 0.135 | 6.80 | 54.1% | 0.0144 | 0.500 | 7.8% | below lead gate |
| `avoid_high_52w_breakout_amount_exhaustion_252_20` | 20 | 0.0164 | 0.119 | 6.00 | 51.7% | 0.0669 | 0.800 | 7.8% | below lead gate |
| `avoid_high_52w_proximity_overextension_252_20` | 20 | -0.0322 | -0.255 | -12.83 | 34.0% | 0.0629 | 0.900 | 8.9% | sign conflict |

The only positive rows were too weak: IC below 0.02, ICIR far below 0.30, positive-IC rate below 55%, and quantile monotonicity not stable enough at 5d.

The proximity inverse also had a sign conflict: negative mean IC but positive Q5-Q1 and monotonicity. That is a diagnostic smell, not a promotion path; it needs residual/style decomposition if ever revisited, but not immediate portfolio conversion.

## Failure Pattern

The 52-week family produced information, but not a clean tradable factor:

- Direct high-anchor buying was significantly wrong-way.
- Simple inverse/avoidance improved some rows but did not reach the research-lead threshold.
- No candidate passed the current IC/ICIR/positive-rate/monotonicity gate.
- No portfolio grid is allowed.
- No promotion claim is allowed.

This is exactly the case the three-round review rule is designed for: stop before turning a clue into another parameter spiral.

## Decision

- Promotable factors: 0
- Paper-ready factors: 0
- Research leads to continue immediately: 0
- Useful clue retained: high-anchor / breakout crowding may be a negative-risk feature, but not a standalone alpha family
- Family status: hibernate 52-week anchor as standalone factor mining

Next direction:

```text
round209_rotate_away_from_52week_anchor_to_new_non_price_volume_or_universe_structure_family
```

Round209 must not:

- tune more 52-week windows;
- flip signs again without a new source of information;
- run a portfolio grid from Round207 or Round208;
- claim the positive Q5-Q1 row as a usable factor.

Round209 should prefer a new information axis, not another price-anchor variant. Suitable directions are:

- universe-structure / listing-age / delisting-risk residual signals under existing tradeability controls;
- financial PIT data coverage expansion before new accounting factors;
- sector-neutral breadth or dispersion features only if they are not reusing the failed regime-temperature family;
- ETF-specific work only in a separate CN_ETF branch, not this CN stock mining branch.

## Process Improvements Completed

The project now enforces:

- event controls as controls, not alpha claims;
- candidate-plan family rotation policy;
- hibernated-family re-entry blockers;
- three-round review blockers;
- 52-week family hibernation after two failed prescreens and this review.

Startup confirmations added:

- `round208_52week_overextension_prescreen_confirmed`
- `round208_zero_52week_research_leads_confirmed`
- `round206_208_three_round_review_confirmed`
- `round209_rotate_away_from_52week_anchor_confirmed`
