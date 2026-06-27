# CN Stock Round460 Independent Long-Cycle Prescreen

Date: 2026-06-27

Scope: CN A-share stock cross-sectional factor research on `office_desktop`.
This is research-to-review only: no broker connection, no account reads, no order placement, and no automatic live trading.
The 2026 final holdout remains sealed.

## Objective

Round459 required the next work to rotate away from the same range / Alpha101 / Dragon-Hot projection cluster and run an independent long-cycle prescreen before any more same-family work.

Round460 tried three independent-looking directions:

- overnight / intraday gap public technical candidates;
- information-discreteness / FIP path-quality candidates;
- 52-week-high quality / anchor candidates.

## Commands And Outcomes

52-week-high quality completed:

```powershell
python scripts\run_high_52week_quality_prescreen.py --output-dir data\reports\round460_24h_profit_sprint_high_52week_quality_prescreen_20260627 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,10,20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

Overnight / intraday gap timed out before writing a result:

```powershell
python scripts\run_overnight_intraday_gap_prescreen.py --output-dir data\reports\round460_24h_profit_sprint_overnight_intraday_gap_prescreen_20260627 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,10,20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

Information discreteness hit a memory error in the non-sharded path before writing a result. The failure happened while sorting a large Arrow-backed frame inside the factor computation path.

## 52-Week-High Result

Data footprint:

| Metric | Value |
|---|---:|
| Bar assets | 5,707 |
| Bar rows | 10,785,537 |
| Date range | 2015-01-05 to 2025-12-31 |
| Candidate count | 4 |
| Horizon tests | 12 |
| Factor rows | 38,085,208 |
| Label rows | 32,140,060 |
| Aligned rows | 113,427,632 |
| FDR-significant tests | 12 |
| Research leads | 0 |
| Promotion allowed | 0 |

Top negative rows:

| Factor | Horizon | IC | ICIR | t-stat | IC+ | Q5-Q1 | Mono | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `high_52w_breakout_amount_confirmation_252_20` | 20 | -0.0615 | -0.395 | -19.88 | 34.3% | -0.0720 | -0.700 | reject |
| `high_52w_breakout_amount_confirmation_252_20` | 10 | -0.0588 | -0.388 | -19.55 | 34.1% | -0.0235 | -0.200 | reject |
| `high_52w_proximity_liquid_quality_252_20` | 20 | -0.0519 | -0.306 | -15.39 | 36.5% | -0.0736 | -0.800 | reject |
| `high_52w_breakout_amount_confirmation_252_20` | 5 | -0.0516 | -0.343 | -17.27 | 36.3% | -0.0079 | -0.100 | reject |

Interpretation:

- The signal is not absent; the direct high-anchor buying direction is significantly wrong-way in this 2015-2025 CN-stock sample.
- Wrong-way evidence is not automatically a tradable inverse factor. It only creates a new hypothesis if freshly pre-registered and tested.
- The project already tested the inverse / overextension-avoidance 52-week family in Round208. That run produced 0 research leads and 0 promotion candidates.

## Historical Re-Entry Audit

Round460 also checked historical evidence before spending more runtime:

- Round109 already tested an overnight / intraday gap public family and found 0 research leads.
- Round208 already tested inverse 52-week overextension avoidance and found 0 research leads.
- Round221 already ran a full 2015-2025 sharded information-discreteness residual audit: 6 candidates, 0 residual research leads, 0 portfolio preflight candidates, 0 promotion candidates.

This means the Round460 resource failures are not the only blocker. The stronger blocker is that these families are already in the rejection memory unless a genuinely new orthogonal mechanism or data source is introduced.

## Decision

Round460 produced:

- New independent alpha: 0.
- New paper-ready signal: 0.
- New promotion candidate: 0.
- Useful process output: 1 fresh long-cycle rejection of direct 52-week-high quality anchors, plus a stricter re-entry block against old rejected families.

Do not continue:

- 52-week anchor or inverse-overextension window tuning.
- Non-sharded information-discreteness reruns.
- Overnight / intraday gap parameter expansion without a new source of orthogonal information.

Round461 must prefer a genuinely new information axis or simulation-readiness hardening, not another retry of the three Round460 prescreen families. Valid next work:

- an accessible point-in-time event / expectation source with confirmed coverage;
- an entry-known structural risk-control factor that improves the existing paper lanes without reading 2026 holdout;
- a source-efficiency audit before any endpoint-heavy family;
- or a formal paper-readiness validation missing from the current high-return lane.

## Process Lesson

The optimized workflow is working: long-cycle evidence plus historical rejection memory prevented a tempting wrong-way 52-week signal from becoming another parameter-mining branch. The next efficiency gain is to route candidate families through rejection memory before launching heavy full-sample jobs.
