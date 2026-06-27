# CN Stock Round376 - Event Calendar Rule Diagnosis

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: simulation-readiness audit for the 24h CN stock profit-factor sprint. Research-to-review only; no broker, account, order, or live-trading access.

## Why This Round

Round373 showed that the new raw-generation helper did not reproduce the official low-turnover replacement event stream. Round376 narrows the problem down before any generated event stream can be used for simulation handoff.

## Output

`data/reports/round376_24h_profit_sprint_event_calendar_rule_diagnosis_20260627`

Compared sources:

- reference: `data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627/replace_drop_turnover_f_low10_entry_cash_period_returns.csv`
- official wrapper base: `data/reports/round339_24h_profit_sprint_replacement_filters_voltarget_wrappers_20260627/replace_drop_turnover_f_low10_base_period_returns.csv`
- generated: `data/reports/round367_24h_profit_sprint_turnover_low_mainboard_prerank_replacement_20260627/replace_drop_turnover_f_low10_entry_cash_after_period_returns.csv`

## Findings

The Round338 reference and Round339 official wrapper base are exact event-stream matches:

- common dates: 834;
- left-only dates: 0;
- right-only dates: 0;
- max absolute return difference: 0;
- signal-date mismatches: 0;
- entry-date mismatches: 0.

The Round367 generated stream is close in return shape but not event-calendar compatible:

- common dates versus reference: 736;
- reference dates missing in generated: 98;
- extra generated dates: 132;
- common-date return differences above 1 bp: 218;
- max absolute common-date return difference: 0.5741%;
- common-date return correlation: 0.9994;
- signal-date mismatches on common dates: 130;
- entry-date mismatches on common dates: 126.

The drift is not a simple fixed calendar-day shift. The best shifted overlap is the unshifted stream:

- unshifted generated/reference Jaccard: 0.7619;
- plus 7 calendar days Jaccard: 0.5643;
- minus 7 calendar days Jaccard: 0.5629.

The reference-only dates cluster mainly in 2015-2018. The generated-only dates also cluster in 2015-2018, with smaller tails through 2025.

## Important Implementation Detail

Metrics must always sort by `date` before computing drawdown and path-dependent statistics. The Round339 base file is not monotonically sorted by date, even though its dated returns exactly match Round338 after grouping/sorting. Existing shortlist loaders already sort by date; future audit scripts must keep doing this explicitly.

## Diagnosis

The current office-desktop workspace no longer has the old official trade-level parquet referenced by earlier docs, so the exact official 834-date normalization rule cannot be reconstructed from trade-level evidence on this machine.

The available evidence is enough to block raw-generated replacement:

1. the frozen Round338/Round339 event stream is internally consistent and exact;
2. the Round367 raw-generated event stream does not reproduce its event calendar;
3. the difference is not explained by a simple date shift;
4. therefore, generated replacement files cannot be promoted to simulation sources until the event-calendar parity gate passes.

## Decision

Keep the current simulation shortlist on frozen, replay-validated event sources.

Do not use `replace_drop_turnover_f_low10_entry_cash_after_period_returns.csv` from Round367, or any successor raw-generated stream, as a simulation event source unless it passes the event-calendar parity gate against the frozen reference.
