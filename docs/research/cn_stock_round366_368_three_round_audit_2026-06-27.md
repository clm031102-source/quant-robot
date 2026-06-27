# CN Stock Round366-368 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: mandatory three-round review inside the 24h profit-factor sprint.

## Rounds Reviewed

| Round | Work | Main Result | Decision |
|---:|---|---|---|
| 366 | Industry/board exposure audit for `replace_drop_turnover_f_low10` | Industry concentration is acceptable; board-permission cashing is the real defect | Test board-permission pre-ranking |
| 367 | Mainboard pre-rank replacement | Entry allowed improves to 95.75% and annualized return rises to 6.86%, but max drawdown worsens to -48.95% | Keep as high-risk research only |
| 368 | Block/OOS/vol-target robustness | Mainboard pre-rank has higher mean OOS return but worse left tail; vol target cannot reduce DD below 30% | Do not promote |

## What Improved

The project now has two reusable controls:

- `scripts/run_shortlist_exposure_audit.py` checks industry/board concentration, missing classification weight, HHI, and return contribution dominance.
- `scripts/run_turnover_low_prerank_replacement.py` tests static pre-rank replacement variants without using next-day limit status as a ranking input.

These controls address a real process gap: previous candidate evidence could hide whether returns were alpha, board access, or unintentional cash exposure.

## Best New Finding

The best new finding is not a new promoted factor. It is an implementation insight:

The current low-turnover line benefits from cashing board-permission-blocked names. Replacing them with more mainboard low-turnover names increases return but also increases crash exposure.

That means the cash proxy is partly acting as a risk reducer. Treating all untradeable positions as merely "wasted alpha" would be wrong.

## Candidate Status

| Candidate | Status | Reason |
|---|---|---|
| `replace_drop_turnover_f_low10_mainboard_prerank` | rejected for simulation shortlist | full-sample DD -48.95%; vol-target DD still -36.71% to -41.73% |
| `mainboard_prerank + vol_target_4_lb84` | high-risk research reference | annualized 6.63%, Sharpe 0.927, but DD -36.71% |
| `drop_low10 + vol_target_4_lb84` | conservative reference | annualized 5.33%, Sharpe 0.884, DD -29.27% |
| existing `drop_low10 + vol_target_6_lb84` | remains primary research lane | annualized 5.84% in this replay, overlap 0.481, DD -30.48%; stronger shortlist variants still use ZZ500 overlays |

No new simulation candidate is added from Rounds366-368.

## Direction Change

Stop pursuing broad board-permission pre-rank tuning as an alpha family.

Use board permission as a required implementation/control audit:

- quantify blocked board weight;
- verify that any pre-rank replacement does not silently increase crash exposure;
- keep next-day limit/suspension as cash/retry handling, not as pre-ranking alpha.

The next mining work should rotate to a more independent source of edge:

1. raw-data-to-event generation replay for current shortlist candidates;
2. industry/breadth or macro-regime translation that is independent of low-turnover;
3. PIT financial/event timing if coverage and announcement lags pass startup gates.

The goal remains a profitable simulation-ready project, not endless parameter sweeps.

## Verification

Commands passed after the changes:

- `.venv\Scripts\python.exe -m json.tool configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json`
- `.venv\Scripts\python.exe -m unittest tests.unit.test_shortlist_exposure_audit tests.unit.test_turnover_low_prerank_replacement tests.unit.test_simulation_shortlist_replay tests.unit.test_shortlist_return_block_audit`
- `.venv\Scripts\python.exe scripts\check_simulation_shortlist_config.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json`
- `.venv\Scripts\python.exe scripts\run_simulation_shortlist_replay.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json --output-dir data\reports\round368_24h_profit_sprint_simulation_shortlist_replay_after_exposure_controls_20260627 --metric-tolerance 0.005`

Replay status: passed, 5 candidates replayed, 0 blockers.
