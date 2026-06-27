# CN Stock Round418 - Entry-Timed Public Factor Grid

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round418 batch-rebuilt the Round405 public-indicator candidates with entry-timed volatility target and self-risk controls.

The goal was to stop hand-picking one public factor and instead force the whole public-indicator pool through the same paper-simulation causality gate.

## Reusable Code Added

- `src/quant_robot/ops/simulation_shortlist_entry_timed_grid.py`
- `scripts/run_simulation_shortlist_entry_timed_grid.py`
- `tests/unit/test_simulation_shortlist_entry_timed_grid.py`
- `tests/unit/test_simulation_shortlist_entry_timed_grid_cli.py`

## Command

```powershell
python scripts\run_simulation_shortlist_entry_timed_grid.py --source-dir data\reports\round405_24h_profit_sprint_all_public_factor_tilt_on_dragon_hot_20260627 --output-dir data\reports\round418_24h_profit_sprint_entry_timed_public_factor_grid_20260627 --candidate-prefix round418_entry_timed --top 15
```

## Result

- candidates scanned: 64
- paper-ready candidates: 64
- blocked candidates: 0
- best candidate: `round418_entry_timed_tilt_public_alpha101_open_close_pressure_fade_10_bottom10_m150`

Top candidates:

| Rank | Candidate | Total Return | Ann. Return | Sharpe | Overlap Sharpe | Max DD | LOY Min Ann. | Best Month Share |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `alpha101_open_close_pressure_fade_10_bottom10_m150` | +143.58% | 5.53% | 0.933 | 0.487 | -21.54% | 2.62% | 49.84% |
| 2 | `alpha101_vwap_proxy_reversion_liquid_20_bottom10_m150` | +142.81% | 5.51% | 0.930 | 0.485 | -21.54% | 2.59% | 50.02% |
| 3 | `alpha101_intraday_close_position_reversal_bottom10_m150` | +139.94% | 5.43% | 0.921 | 0.480 | -21.55% | 2.53% | 50.41% |
| 4 | `alpha101_range_compression_liquid_20_bottom10_m150` | +134.17% | 5.28% | 0.911 | 0.479 | -20.79% | 2.49% | 50.83% |
| 5 | `rsrs_right_skew_18_60_top10_m150` | +133.57% | 5.26% | 0.899 | 0.473 | -20.78% | 2.47% | 51.57% |

## OOS And Beta Check

The top three candidates were audited together.

| Candidate | Mean OOS Ann. | Mean OOS Overlap Sharpe | Strict Pass | Beta | Beta-Hedged Ann. | Beta-Hedged Max DD |
|---|---:|---:|---:|---:|---:|---:|
| `openclose` | 5.32% | 0.702 | 76.67% | 0.0340 | 5.49% | -11.10% |
| `vwap` | 5.27% | 0.694 | 76.67% | 0.0340 | 5.47% | -11.10% |
| `intraday` | 5.17% | 0.688 | 76.67% | 0.0339 | 5.40% | -11.10% |

Pairwise event-return correlations:

| Pair | Correlation |
|---|---:|
| openclose vs vwap | 0.999925 |
| openclose vs intraday | 0.999778 |
| vwap vs intraday | 0.999821 |

## Decision

Do not add the vwap or intraday variants as independent factors. They are near-identical to the open-close candidate.

Round419 should tune the risk budget of the open-close entry-timed candidate under the user's stated -30% drawdown tolerance.
