# CN Stock Round251 Share Unlock / Pledge Supply Event Prescreen

- Date: 2026-06-25
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock factor mining
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Purpose

Round248-250 rejected the event-contextual underreaction family after reference de-duplication and residual audit. Round251 rotated to a different A-share event mechanism: supply pressure and pledge-risk pressure.

This round also tightened the process controls requested by the latest method audit:

- Startup-gate method contracts now validate every required area control and required output, not just area presence.
- Event prescreen outputs now include an event snapshot audit so live Tushare event fetch drift can be reviewed.
- `event_share_unlock_pressure_60` is computed as a daily active pressure signal during the 60-trading-day window before unlock, after the announcement is public.
- Event prescreen now requires multi-year IC coverage before a candidate can be marked as a research lead.

## Implemented Changes

- Added strict required-control/output validation for `method_optimization_contract` and `pre_mining_control_contract`.
- Added `share_float` and `pledge_stat` support to the event PIT/IC prescreen pipeline.
- Added full-window fetch support:
  - `share_float`: yearly `start_date` / `end_date` ranges.
  - `pledge_stat`: weekly `end_date` shards.
- Added event snapshot audit fields: rows, columns, duplicate rows, and date ranges.
- Added yearly IC coverage metrics and blockers:
  - `ic_year_count`
  - `mean_yearly_ic`
  - `yearly_positive_ic_year_rate`
  - `yearly_ic_failure_count`
  - `ic_year_coverage_below_gate`
  - `yearly_ic_stability_below_gate`

## Commands

Startup gate:

```powershell
.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --config configs\factor_mining_startup_cn_stock.json --output-dir data\reports\round251_startup_method_protocol_20260625 --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start
```

Full Round251 prescreen:

```powershell
.venv\Scripts\python.exe scripts\run_event_factor_pit_ic_prescreen.py --output-dir data\reports\round251_share_unlock_pledge_full_20260625 --candidate-names event_share_unlock_pressure_60,event_pledge_ratio_relief_1q --event-start-year 2015 --event-end-year 2025 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 30 --min-ic-observations 8 --min-industries 2 --min-assets-per-industry 2
```

## Full-Sample Results

| Metric | Value |
|---|---:|
| `share_float` rows | 64,885 |
| `pledge_stat` rows | 1,554,101 |
| Factor rows | 1,560,121 |
| Aligned rows | 2,995,607 |
| Tests | 4 |
| FDR-significant tests | 4 |
| Neutral-gate pass tests | 2 |
| Year-coverage pass tests | 0 |
| Research leads | 0 |
| Promotion allowed | 0 |

Top rows after all gates:

| Factor | Horizon | IC Obs | IC Years | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | Lead | Main blocker |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `event_share_unlock_pressure_60` | 20 | 172 | 3 | 0.1443 | 0.666 | 8.73 | 69.8% | 0.0721 | 0.2873 | 0.1743 | no | year coverage below gate |
| `event_share_unlock_pressure_60` | 5 | 172 | 3 | 0.0786 | 0.369 | 4.85 | 62.2% | 0.0183 | 0.2264 | 0.0940 | no | year coverage below gate |
| `event_pledge_ratio_relief_1q` | 20 | 520 | 11 | -0.0104 | -0.350 | -7.97 | 34.0% | -0.0490 | 0.6311 | 0.0018 | no | wrong sign, size-neutral fail, yearly instability |
| `event_pledge_ratio_relief_1q` | 5 | 523 | 11 | -0.0067 | -0.228 | -5.21 | 40.2% | -0.0148 | 0.6320 | 0.0015 | no | wrong sign, size-neutral fail, yearly instability |

## Interpretation

Round251 found a strong-looking unlock-pressure diagnostic, especially at 20 days, but it is not a robust research lead under the optimized process:

- The IC evidence appears only in 3 calendar years: 2015, 2018, and 2024.
- It passes raw, industry-neutral, and size-neutral IC in those years, but fails long-cycle coverage.
- Treating it as promotable would repeat the old mistake of accepting a short-cycle event cluster as a durable alpha.

The pledge-relief factor has broad year coverage but fails direction and tradability interpretation:

- Raw IC is negative across 11 years.
- Quantile spread is negative.
- Size-neutral IC is near zero and below gate.
- The very high industry-neutral IC is not enough because the factor does not translate into the intended positive cross-sectional ranking.

## Decision

Promotable factors from Round251: 0.

Research leads after the new yearly gate: 0.

Useful outcome: the project now has a better event supply/pledge pipeline and a stronger false-positive blocker. The old process would have reported 2 share-unlock leads; the optimized process rejects them because the signal is concentrated in too few years.

## Next Direction

Round252 should not run a portfolio grid on Round251. Allowed next work:

- Audit whether unlock pressure can be converted into a risk-exclusion overlay or industry-level supply-pressure state with broader yearly coverage.
- If year coverage remains sparse, hibernate direct share-unlock stock ranking and rotate to a non-event family.
- Keep pledge-relief positive-direction ranking rejected unless a new preregistered hypothesis explains the observed negative sign and passes size-neutral tests.

