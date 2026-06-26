# CN Stock Round230 Liquidity Shock Recovery Residual Prescreen - 2026-06-24

## Purpose

Round230 deliberately rotated away from the failed moneyflow/public-anomaly path and tested a new OHLCV liquidity-shock-recovery family. The hypothesis was that short-term price impact, range shock, and volume shock absorption might contain a capacity-aware reversal/recovery signal after removing industry, size, liquidity, and volatility exposures.

This remains research-only:

- portfolio grid allowed: false;
- promotion allowed: false;
- final holdout: not touched;
- broker/account/order/live trading: not allowed.

## Run

Command:

```powershell
python scripts\run_liquidity_shock_recovery_residual_prescreen.py --sharded --output-dir data\reports\liquidity_shock_recovery_residual_prescreen_round230_20260624
```

The sharded full-cycle run completed successfully. Runtime was roughly 20 minutes on the office desktop. This is acceptable for one controlled family screen, but future full-cycle research runners should add shard-level progress logging and reuse more intermediate matrices when possible, because a silent 20 minute run is too opaque for continuous mining.

## Data Window

- Signal window: 2015-01-01 to 2025-12-31.
- Bar date range: 2015-01-05 to 2025-12-31.
- Bar rows: 10,785,537.
- Asset count: 5,707.
- Factor rows: 34,416,770.
- Industry-neutral rows: 33,215,373.
- Residual rows: 33,089,155.
- Label rows: 10,777,095.
- Shards: 11 yearly shards.

## Results

| Factor | H | Raw IC | Neutral IC | Residual IC | Residual ICIR | Positive Residual IC | Lead | Main Blockers |
|---|---:|---:|---:|---:|---:|---:|---|---|
| `range_shock_liquidity_recovery_20_10` | 5 | 0.0512 | 0.0457 | 0.0161 | 0.237 | 58.5% | no | residual IC below threshold; residual yearly instability |
| `liquidity_recovery_quality_composite_20` | 5 | 0.0441 | 0.0401 | 0.0130 | 0.213 | 57.8% | no | residual IC below threshold; high exposure; residual yearly instability |
| `amihud_shock_reversal_recovery_20_5` | 5 | 0.0342 | 0.0316 | 0.0126 | 0.238 | 59.4% | no | residual IC below threshold; high exposure; residual yearly instability |
| `volume_shock_absorption_reversal_20_5` | 5 | 0.0151 | 0.0140 | 0.0037 | 0.067 | 51.9% | no | neutral/residual IC and ICIR below threshold; positive-rate failure; residual yearly instability |
| `downside_liquidity_resilience_20` | 5 | 0.0362 | 0.0327 | 0.0035 | 0.057 | 53.5% | no | residual IC/ICIR/positive-rate failure; high exposure; raw, neutral, and residual yearly instability |

## Decision

Promotable factors from Round230: 0.

Paper-ready factors from Round230: 0.

Residual research leads from Round230: 0.

The family should rotate instead of tuning windows. The strongest diagnostic result was `range_shock_liquidity_recovery_20_10`: raw and industry-neutral IC were positive, but residual IC fell to 0.0161 and failed yearly stability. That means the apparent edge is not yet independent enough after style and implementation exposure controls.

## Method Lessons

- Long-cycle full-sample residual prescreen worked as intended: it prevented raw IC from being promoted into a portfolio grid.
- The family is not worth additional parameter sweeps unless a genuinely new orthogonal repair is introduced.
- The next family should not be another OHLCV liquidity/reversal variant. It should come from a different economic mechanism, preferably one with point-in-time event timing, supply/demand constraint changes, or a clearer regime interaction.
- Progress logging and intermediate cache reuse should be improved before more long silent full-cycle runs.

## Next Direction

`round231_rotate_after_liquidity_shock_recovery_failure`

Rules for the next round:

- do not tune windows inside `liquidity_shock_recovery`;
- do not run a portfolio grid from these five factors;
- do not promote raw or industry-neutral IC when residual IC fails;
- rotate to a new family or a new orthogonal exposure-repair hypothesis.
