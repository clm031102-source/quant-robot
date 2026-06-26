# Round102 Capacity-Safe Price-Volume Prescreen Design

## Objective

Evaluate the 10 Round101 pre-registered CN stock price-volume, low-volatility, and public technical candidates before any portfolio grid is allowed.

## Required Gates

- Use 2015-2025 long-cycle data.
- Keep 2026 as final holdout.
- Use execution lag 1.
- Run 5-day and 20-day forward-return labels.
- Report IC, ICIR, t-stat, IC positive rate, quintile spread, monotonicity, top-quantile turnover, and multiple-testing flags.
- Do not allow direct promotion from this stage.

## Engineering Requirements

- Load local `processed/bars` parquet or csv shards.
- Compute all 10 pre-registered candidate names.
- Apply minimum signal-date and ADV20 amount filters.
- Avoid all-factor merged tables during summarization.
- Write JSON, Markdown, result CSV, and IC observation CSV to `data/reports`.

## Research Lead Definition

A candidate-horizon pair can become a research lead only if:

- FDR significant after multiple testing.
- Mean IC >= 0.02.
- ICIR >= 0.30.
- IC positive rate >= 0.55.
- Q5-Q1 spread is positive.
- Quintile monotonicity >= 0.70.
- Top-quantile turnover <= 0.90.

Research lead does not mean paper-ready or live-usable.

