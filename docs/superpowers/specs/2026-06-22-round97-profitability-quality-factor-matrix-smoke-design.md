# Round97 Profitability Quality Factor Matrix Smoke Design

## Objective

Build factor values from the 14 Round96 pre-registered profitability-quality candidates, align each financial event by `ann_date` to the next available trading day, and verify that forward-return labels start after the signal date.

This is a factor-matrix and label-alignment smoke. It is not an IC, Sharpe, profit-rate, win-rate, or portfolio backtest round.

## Guardrails

- Consume only Round96 pre-registered candidates.
- Use `ann_date` as the information availability date.
- Map each event to the first bar date on or after `ann_date`.
- Use execution lag of at least 1 trading day.
- Reject any aligned row where `signal_date < ann_date`.
- Reject any aligned row where `entry_date <= signal_date`.
- Reject any aligned row where `exit_date <= entry_date`.
- Do not promote or paper-ready any candidate from this smoke.

## Acceptance Criteria

- A reusable factor-matrix smoke ops module exists.
- A CLI writes JSON, Markdown, and candidate summary CSV.
- Unit tests cover passing label alignment and blocking missing labels.
- Real Round95/96 data aligns to local CN stock bars with no leakage violations.
- Startup gate advances only to controlled IC screening.

## Non-Goals

- No IC or RankIC claim.
- No Sharpe/profit/win-rate claim.
- No portfolio construction.
- No full-universe factor backtest.
- No GitHub push.
- No broker, account, order, or live-trading action.
