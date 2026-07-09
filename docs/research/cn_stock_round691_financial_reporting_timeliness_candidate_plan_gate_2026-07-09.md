# CN Stock Round691 Financial Reporting Timeliness Candidate Plan Gate

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-financial-reporting-timeliness-round691-20260709`

Scope: preregister the first financial reporting timeliness candidate set after Round690 cleared the source gate. This round only created the candidate plan and ran the candidate plan gate. It did not run IC screens, residual prescreens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Machine / task | `office_desktop` / `factor_batch` |
| Branch prefix | corrected to accepted CN stock prefix `codex/factor-batch-cn-stock-` |
| Quant PM startup gate | `ready`, blockers `[]` |
| Factor mining startup gate | `cleared`, blockers `[]` |
| CN stock data manifest | `review_required`, blockers `[]` |
| Manifest warnings | `extreme_return_rows_present`, `moneyflow_symbol_coverage_below_bars` |
| Live boundary | no broker connection, account reads, orders, or automatic trading |

The manifest warnings are carried forward as prescreen audit inputs. They are not alpha evidence and do not authorize result interpretation without later data-quality notes.

## Candidate Plan

Config:

```text
configs/factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json
```

The plan declares all nine default CN stock control areas:

- `cn_stock_tradeability`
- `financial_pit_timing`
- `source_sample_integrity`
- `industry_style_neutralization`
- `etf_rotation_scope_boundary`
- `portfolio_construction`
- `strict_statistics`
- `china_market_regime`
- `event_factors`

Promotion policy keeps:

```text
promotion_allowed=false
portfolio_backtest_allowed_before_prescreen=false
final_holdout_available_for_tuning=false
```

## Preregistered Candidates

| Candidate | Intent |
| --- | --- |
| `frt_reporting_lag_short` | Faster PIT report availability as lower-opacity / stronger-control proxy |
| `frt_reporting_lag_improvement_4q` | Same-quarter year-over-year reporting lag improvement |
| `frt_reporting_lag_stability_8q` | Stable trailing eight-quarter reporting cadence |
| `frt_early_report_quality_combo` | Frozen timeliness plus PIT-safe realized quality or cash-conversion composite |
| `frt_late_reporter_risk_avoidance` | Extreme late reporting as opacity or operating-friction risk proxy |

All candidates are `market=CN`, `asset_type=stock`, `registration_status=pre_registered`, `portfolio_backtest_allowed=false`, and `promotion_allowed=false`.

## Candidate Plan Gate Result

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json --output-dir data\reports\round691_financial_reporting_timeliness_candidate_plan_gate_20260709
```

Result:

| Metric | Value |
| --- | ---: |
| Status | `research_ready` |
| Candidate plan gate cleared | true |
| Research screen allowed | true |
| Candidate count | 5 |
| Active candidate count | 5 |
| Complete control areas | 9 / 9 |
| Blocked control areas | 0 |
| Portfolio grid allowed | false |
| Promotion allowed | false |
| Blockers | `[]` |

Independent assertion check printed:

```text
round691_candidate_plan_gate_validated
```

## Decision

Round691 clears the preregistered candidate plan gate for `financial_reporting_timeliness`. The next allowed action is a specialized PIT financial reporting timeliness prescreen with fixed 5D and 20D horizons, strict `signal_date > ann_date` proof, industry/style residual controls, multiple-testing accounting, and manifest-warning carry-forward.

Portfolio grids, promotion, sign/window tuning, mixed-window harvesting, live trading work, and 2026 final-holdout reads remain blocked.
