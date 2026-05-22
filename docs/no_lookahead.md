# No-Lookahead Rules

The framework follows these rules:

- A factor row at date `t` can only use market data with date `<= t`.
- Forward-return labels are stored separately from factors.
- A signal generated at date `t` is executed no earlier than the next available bar.
- Rolling factors are computed per asset with pandas `shift` and `rolling`.
- Cross-sectional ranking is computed within the current date only.
- Tests include a future price spike to prove earlier factor rows do not change.

Violating these rules makes research results unusable, even when backtest metrics look attractive.
