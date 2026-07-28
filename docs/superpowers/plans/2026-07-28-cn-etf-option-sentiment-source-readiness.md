# CN ETF Option-Sentiment Source Readiness Plan

**Goal:** Produce a deterministic, point-in-time source audit for CN ETF option
sentiment before any factor work.

1. Add a pure readiness operation covering contract identity, analysis-period
   overlap, underlying breadth, daily probe coverage, and positive-close
   quality.
2. Add a strict config and CLI that fetch only contract metadata plus ten
   bounded exchange-date probes, then write normalized evidence and hashes
   under ignored `data/reports/`.
3. Run the real audit and classify the source as ready or structurally blocked.
4. Update the scheduler, research index, and durable report; keep every
   execution and live boundary false.
5. Verify, commit, and push the source-review branch.
