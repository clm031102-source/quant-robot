# Round103 Bollinger Lead Dedup Review Design

## Context

Round101 pre-registered 10 capacity-safe public price-volume candidates for CN stock cross-sectional alpha research. Round102 replayed them on the long 2015-01-01 to 2025-12-31 sample and found one research lead: `bollinger_reversal_lowvol_liquid_20` on the 20-day horizon. The lead is not promotable yet because the prescreen stage only proves statistical signal shape, not portfolio tradability.

This Round103 design implements the next required gate: correlation de-duplication plus the three-round review for Rounds101-103. The goal is to avoid repeatedly repackaging the same low-volatility reversal signal as different candidate names before spending a heavier walk-forward portfolio budget.

## Scope

Build a local, repeatable Round103 audit for office desktop CN stock factor validation:

- Compute cross-sectional daily Spearman correlations between the Round102 lead and every other Round101 price-volume candidate.
- Classify whether the lead is unique enough to deserve a cost/capacity portfolio bridge.
- Produce machine-readable JSON, CSV, and Markdown output under `data/reports`.
- Write lightweight research docs under `docs/research`.
- Update `configs/factor_mining_startup_cn_stock.json` so future mining starts from the audited next direction.

The stage remains research-only. It must not promote any factor to paper-ready, must not include 2026 final holdout data, and must not connect to brokers, account data, or live trading.

## Design Choices

### A. Correlation Dedup Method

Use sampled signal dates from the same capacity-safe factor frame created by Round102 factor formulas. For each non-lead candidate, compute a Spearman correlation with the lead on each shared date, requiring a minimum cross-section. Summarize:

- `correlation_observations`
- `mean_correlation`
- `mean_abs_correlation`
- `median_abs_correlation`
- `max_abs_correlation`
- `positive_correlation_rate`
- `median_cross_section`

Classification:

- `unique`: `max_abs_correlation < 0.70` and `mean_abs_correlation < 0.50`
- `moderately_redundant`: not unique, but below high redundancy
- `highly_redundant`: `max_abs_correlation >= 0.85` or `mean_abs_correlation >= 0.70`

This follows the project gate already registered in the startup config: candidate correlation de-duplication before portfolio grid expansion.

### B. Prescreen Lead Guard

The operation must consume the Round102 prescreen report. It should confirm that the selected lead exists and was marked `research_lead = true` for the requested horizon. If the prescreen does not support the lead, Round103 must block any next portfolio bridge.

### C. Next-Direction Rule

Round103 cannot make a promotion claim. It can only choose the next research direction:

- If the lead is not highly redundant: continue to `round104_bollinger_lead_cost_capacity_bridge_preregistration`.
- If the lead is highly redundant: rotate away to `round104_family_rotation_after_bollinger_redundancy`.

### D. Three-Round Review

The Round101-103 review will record:

- Round101 candidates: 10 pre-registered, no promotion.
- Round102 candidates tested: 10 unique factors, 20 factor-horizon tests, 1 research lead, 0 promotable.
- Round103 dedup verdict and next-direction decision.
- Main blocker histogram: portfolio promotion not yet allowed, monotonicity failures, top-minus-bottom failures, negative-direction failures, and possible redundancy.

User risk preference is included explicitly: drawdown up to roughly 30% is a soft tolerance when return quality is strong, but capacity, extreme-trade, cost, and execution gates remain hard blockers.

## Files

- Create `src/quant_robot/ops/capacity_safe_price_volume_lead_dedup.py`
- Create `scripts/run_capacity_safe_price_volume_lead_dedup.py`
- Create `tests/unit/test_capacity_safe_price_volume_lead_dedup.py`
- Create `tests/unit/test_capacity_safe_price_volume_lead_dedup_cli.py`
- Create `docs/research/cn_stock_capacity_safe_price_volume_lead_dedup_round103_2026-06-22.md`
- Create `docs/research/cn_stock_round101_103_three_round_review_2026-06-22.md`
- Modify `configs/factor_mining_startup_cn_stock.json`
- Modify `tests/unit/test_factor_mining_startup_gate_cli.py`

## Verification

Run unit tests for the new operation and CLI, then rerun the existing price-volume preregistration and prescreen tests. Run the startup gate, JSON validation, py_compile, project audit, and git diff check before reporting results.

Expected proof points:

- New tests fail before the operation exists.
- New tests pass after implementation.
- Real Round103 output uses 2015-2025 data only.
- Startup gate points to the Round103 audit as the source audit and a Round104 next direction.
- No generated `data/reports` files are committed.
