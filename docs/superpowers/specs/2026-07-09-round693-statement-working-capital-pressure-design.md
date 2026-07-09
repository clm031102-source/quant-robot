# Round693 Statement Working Capital Pressure Design

## Context

Round691 financial reporting timeliness and Round692 PEAD gap-reversal source repair both produced zero promotable candidates. Round693 rotates to a different statement substructure: operating working-capital pressure and cash-buffer deterioration after financial statements become observable.

This is not a continuation of old realized profitability revision, cash-conversion event drift, financial reporting timeliness, or PEAD gap-reversal work. It uses PIT financial statement rows only because the Round690/Round692 local statement source is available and aligned through `ann_date`; it tests new fields that were not part of the old accounting-quality formulas: `c_cash_equ_end_period`, `inventories`, `accounts_receiv`, `accounts_pay`, `free_cashflow`, and liability coverage fields.

## Hypothesis

Firms with improving cash coverage, falling operating working-capital lockup, and better free-cashflow liability buffers may have lower near-term financing pressure after the statement is released. The signal is economically different from profitability acceleration: it asks whether the balance sheet is consuming cash or releasing cash after the report is public.

## Candidate Family

Family id: `statement_working_capital_pressure`.

Pre-registered candidates:

- `swcp_cash_current_liability_improvement`
- `swcp_operating_working_capital_release`
- `swcp_inventory_receivable_efficiency_improvement`
- `swcp_free_cashflow_liability_buffer`
- `swcp_balanced_cash_working_capital_pressure`

The first four are fixed single-formula candidates. The balanced candidate is a frozen equal-weight cross-sectional rank composite of cash-buffer improvement, operating working-capital release, and free-cashflow liability buffer. No sign, lag, horizon, or window tuning is allowed inside Round693.

## Data And PIT Rules

Use local `data/processed` financial statement inputs only. Do not download or extend statement data in this factor-batch round.

Signal date rule: each factor row is dated on the first trading date strictly after `ann_date`. Period-end-only signals and same-day announcement trading are forbidden. The 2026 final holdout remains sealed for tuning.

Initial column coverage check on the local statement cache found about 40,665 statement rows and 959 assets. Required new fields had broad coverage: cash, revenue, free cashflow, liabilities, inventory, receivables, and payables were all above roughly 95% row coverage except for no blocker.

## Screening Policy

Round693 may run only matrix/label smoke and residual IC shape prescreen on the five pre-registered candidates. Portfolio grids, promotion gates, sign flips, parameter grids, mixed-window harvesting, and final-holdout reads are blocked.

Residual screening must carry forward the CN stock data-manifest warnings: `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`. Any lead must pass industry, size, liquidity, quantile shape, FDR/multiple-testing, and PIT-alignment checks before a later walk-forward preflight can be considered.

## Success And Stop Conditions

Success for this round means the candidate-plan gate clears and the prescreen produces at least one research lead after neutral gates and multiple-testing accounting.

Stop immediately if source fields are missing, PIT alignment fails, candidate-plan gate blocks, factor rows collapse below usable coverage, or residual screening produces zero research leads. A zero-lead result hibernates this exact family unless a future round introduces a genuinely new source or orthogonal hypothesis.
