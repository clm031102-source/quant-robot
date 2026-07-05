# Round566 Next Steps Checklist

Use this after Round565 is merged or after pulling latest `main`.

## Current State

- Round565 HK-hold low-frequency sponsorship is rejected as a research lead source family.
- The rejection is based on preregistered source checks, construction smoke, reference-dedup prep, and residual IC prescreen.
- No portfolio grid, promotion gate, provider download, or 2026 final-holdout read was run.
- Round566 local aggregate financial reporting timeliness source audit is blocked:
  - unique symbols: 394;
  - required unique symbols: 1,000;
  - candidate plan allowed: false.

## Recommended Next Work

1. Do not preregister or test financial reporting timeliness factors from the 394-symbol cache.
2. If continuing this source, use a dedicated data-pipeline branch and resume Round303-style backfill with overlap preview, stock-basic pre-listing filtering, and no candidate generation until 1,000 symbols.
3. If not backfilling, rotate to another accessible PIT-safe source and run a candidate-plan gate before any IC screen.
4. Keep promotion gates and 2026 final-holdout reads blocked.

## Explicitly Do Not Do

- Do not tune Round565 HK-hold windows.
- Do not flip HK-hold directions.
- Do not widen HK-hold parameters.
- Do not run a portfolio grid for Round565 candidates.
- Do not read 2026 final holdout for Round565.
- Do not revive old northbound accumulation, northbound crowding/reversal, margin-credit, LPR, or daily-basic valuation repair without a genuinely new preregistered mechanism.
