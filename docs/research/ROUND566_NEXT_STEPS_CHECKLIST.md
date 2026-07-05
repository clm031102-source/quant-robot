# Round566 Next Steps Checklist

Use this after Round565 is merged or after pulling latest `main`.

## Current State

- Round565 HK-hold low-frequency sponsorship is rejected as a research lead source family.
- The rejection is based on preregistered source checks, construction smoke, reference-dedup prep, and residual IC prescreen.
- No portfolio grid, promotion gate, provider download, or 2026 final-holdout read was run.

## Recommended Next Work

1. Start from latest `main` on a new task branch.
2. Run startup context and Quant PM startup gate for `office_desktop` / `factor_batch`.
3. Select a genuinely new PIT-safe source mechanism rather than tuning HK-hold sponsorship.
4. Preregister the new family in a candidate-plan config and run the candidate-plan gate before any IC screen.

## Explicitly Do Not Do

- Do not tune Round565 HK-hold windows.
- Do not flip HK-hold directions.
- Do not widen HK-hold parameters.
- Do not run a portfolio grid for Round565 candidates.
- Do not read 2026 final holdout for Round565.
- Do not revive old northbound accumulation, northbound crowding/reversal, margin-credit, LPR, or daily-basic valuation repair without a genuinely new preregistered mechanism.
