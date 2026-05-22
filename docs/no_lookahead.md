# No-Lookahead Rules

The framework follows these rules:

- A factor row at date `t` can only use market data with date `<= t`.
- Forward-return labels are stored separately from factors.
- A signal generated at date `t` is executed no earlier than the next available bar.
- The configured forward horizon is used consistently for labels and the research backtest holding period.
- Signal snapshots filter bars to `as_of_date` before computing factors and prices.
- Rolling factors are computed per asset with pandas `shift` and `rolling`.
- Cross-sectional ranking is computed within the current date only.
- Walk-forward test runs may include pre-split warmup bars for rolling calculations, but test signals and trades must start after the split.
- Multi-market `ALL` backtests use a single global portfolio scope by default, so combining markets does not multiply exposure by market count.
- Tests include a future price spike to prove earlier factor rows do not change.

Violating these rules makes research results unusable, even when backtest metrics look attractive.
