# Round692 PEAD Gap Reversal Source Repair Design

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-pead-gap-reversal-source-repair-round692-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Context

Round691 financial reporting timeliness produced zero research leads after residual IC shape screening. The next step must avoid tuning the failed timeliness formulas.

Older PEAD gap-reversal work is more promising but explicitly constrained:

- Round222 rejected the original post-announcement gap-underreaction sign.
- Round223 inverted the sign and found five residual research leads in the old `fina_indicator` PIT source.
- Round224 removed two highly correlated variants and froze three candidates.
- Round225 rejected all frozen candidates at the walk-forward portfolio layer because of capacity, drawdown, and early-cycle instability.
- The startup gate now blocks gap-reversal grid expansion after Round225.

Round690 is genuinely new information: the local PIT financial statement source cleared a 1,000-symbol source gate. That larger statement source may repair the old source-size and capacity weakness without changing the PEAD gap-reversal mechanism.

## Alternatives

1. Continue Round691 timeliness repair.
   This is low value because all ten Round691 tests failed FDR and neutral gates. The best raw effects looked like style or coverage structure, not clean alpha.

2. Reopen analyst-report or external-feed sources.
   Analyst reports remain quota constrained and weakened after the March extension. External-feed HK-hold quality improved, but Round529 decided it is source-quality evidence only, not a new alpha mechanism.

3. Run a Round692 PEAD gap-reversal source-repair audit on the expanded Round690 statement source.
   This is the selected path. It uses a previously productive mechanism, counts the repaired source as new evidence, and freezes formulas so the work is not parameter tuning.

## Design

Round692 will be a source-repair and candidate-plan round for the PEAD gap-overreaction reversal family. It will not run portfolio grids, walk-forward validation, promotion gates, final holdout reads, or live/paper signal generation.

The candidate plan will preregister only frozen or near-frozen gap-reversal formulas:

- `stmt_pead_gap_overreaction_reversal_1_5`
- `stmt_pead_gap_overreaction_reversal_low_liquidity_penalized_1_5`
- `stmt_pead_gap_overreaction_reversal_volume_confirmed_1_5`
- `stmt_pead_gap_overreaction_reversal_size_neutral_candidate_1_5`
- `stmt_pead_gap_overreaction_reversal_quality_conditioned_1_5`

The `stmt_` prefix is intentional. These candidates are source-repair variants on the expanded statement source, not a re-run of the old `fina_indicator` cache. Formulas remain economically equivalent to the Round223 gap-reversal candidates.

## Data Flow

1. Use local processed statement roots under `data/processed`.
2. Require statement rows to include `ann_date`, `end_date`, `asset_id`, and `market`.
3. Derive `signal_date` as the first tradable date strictly after `ann_date`.
4. Measure event gap on `signal_date` using the CN bar data.
5. Date the factor on the next tradable date after the event-reaction date.
6. Exclude 2026 final holdout from all design, gate, and prescreen work.

If the existing PEAD code cannot read statement roots directly, implementation must add an adapter with tests before any real prescreen.

## Controls

The candidate-plan gate must declare all CN stock control areas:

- A-share tradeability filters.
- PIT financial timing.
- Source-sample integrity and rejected-hypothesis counting.
- Industry, style, size, volatility, and liquidity neutralization.
- ETF rotation boundary.
- Portfolio construction gates, even though portfolio work remains blocked.
- Strict statistics, FDR, and future-function/static leakage audit.
- China market regime coverage.
- Event contamination controls.

Round692 must carry forward CN data manifest warnings:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

These warnings are audit context only and cannot be alpha evidence.

## Success Criteria

Design success is candidate-plan readiness, not alpha discovery.

The round succeeds if:

- startup gates are clear;
- the Round692 candidate plan gate returns `research_ready`;
- all candidates are preregistered with portfolio and promotion disabled;
- the docs explicitly block grid expansion after Round225;
- any required code adaptation is planned with tests before implementation.

The round does not claim a profitable factor unless a later prescreen and validation sequence produces independent evidence.

## Self-Review

- No placeholders remain.
- Scope is one family and one source-repair audit.
- The design does not weaken Round225 walk-forward rejection.
- The design does not continue Round691 timeliness tuning.
- The design keeps final holdout, portfolio grids, promotion, broker/account/order access, and live trading blocked.
