# CN Stock Public Formula Gap Audit Round59

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Goal

Audit why the Round58 public formula price-volume factors had strong RankIC but no promotable portfolio result.

## Source

- Leaderboard: `data/reports/industry_neutral_portfolio_public_formula_price_volume_round58_20260621/leaderboard.csv`
- Audit output: `data/reports/ic_portfolio_gap_audit_public_formula_price_volume_round58_20260621`
- Audit tool: `scripts/run_ic_portfolio_gap_audit.py`

## Result

- Cases audited: 16
- Strong RankIC cases: 16
- IC-to-portfolio gap cases: 16
- Capacity-limited cases: 10
- Promotable long-only cases: 0
- Extreme trade cases: 0

Decision reason counts:

- `relative_return_below_threshold`: 16
- `capacity_limited_trades_present`: 10

Translation status counts:

- `translation_gap`: 6
- `capacity_blocked`: 10

## Factor-Level Read

Cleanest research lead:

- `formula_pv_corr_reversal_20`
- Cases: 2
- Strong RankIC cases: 2
- IC-to-portfolio gaps: 2
- Capacity-limited cases: 0
- Best RankIC: 0.0782
- Best overlap-adjusted Sharpe: 0.1771
- Best total return: 35.48%

Rejected or hibernated directions:

- `formula_volume_contraction_reversal_20`: strong IC but capacity blocked.
- `formula_pv_corr_momentum_confirmed_20_60`: strong IC but negative portfolio outcome and capacity blocked.
- `formula_volume_contraction_momentum_confirmed_20_60`: strong IC but negative portfolio outcome and capacity blocked.
- range-contraction variants: strong IC but weak or negative portfolio outcome; many capacity blocked.

## Diagnosis

This is not a discovery-count problem. The project has enough factor names. The problem is that cross-sectional ranking evidence is not yet becoming a costed, capacity-safe portfolio edge.

Likely causes:

- the all-market equal-weight benchmark is extremely strong over 2015-2025, so weak absolute portfolios fail relative-return gates;
- industry-neutral top-N long-only construction may dilute the spread captured by IC;
- the best lead has positive absolute return but weak overlap-adjusted Sharpe and sub-50% win rate;
- broader public formula sweeps create multiple-testing waste without solving the conversion issue;
- capacity issues are widespread outside the `pv_corr_reversal_20` lead.

## Required Next Action

Run a single-lead bottom-exclusion overlay diagnostic on `formula_pv_corr_reversal_20`.

Do not:

- expand all public formula names again;
- tune new factor windows from this evidence;
- claim profitability from IC or overlay diagnostics alone;
- promote anything before costed walk-forward portfolio validation.

Next round label: Round60 `pv_corr_reversal_bottom_exclusion_overlay`.
