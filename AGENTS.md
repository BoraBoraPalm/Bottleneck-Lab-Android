# Project working instructions

## Research continuity

The user requires durable per-test records in this repository. Before answering a question about an earlier test, read `research/README.md`, `research/index.json` and that test's stored report/results. Reuse existing outputs and exact cached bundles; do not rerun an old backtest merely to recover its settings or conclusions.

After each new empirical test, add a dated/versioned folder under `research/tests/` using `research/templates/TEST.md`, save the reproducible protocol/parameters, code identity, data sources/hashes, machine-readable results, interpretation and limitations, and update the index. For large snapshots/model files, retain an exact persistent package reference and SHA-256 plus a complete member manifest. State missing original code/data honestly. Preserve historical original files; corrections go in a new note/version rather than silently altering past results.

Always distinguish signal lookback, forecast horizon, actual and maximum holding duration, exit rule and rebalancing frequency. Record whether a strategy-specific holding-period search was actually performed. A fixed-horizon negative result does not reject all holding durations. Source factor portfolio return frequency is not automatically an individual stock holding duration.

Choose duration/model settings only inside chronological training/validation windows; allow only information and fully matured labels known at each decision time. Compare annualized/risk/cost outcomes with aligned benchmarks, and document multiple testing and previous knowledge of historical test years. Do not select the hindsight best duration on the final test period.

For research-only requests, leave the foreground application unchanged unless the user asks for an app change. Run `python research/tools/check_archive.py` after updating research records. Existing `docs/`, application code and workflows remain outside a documentation-only archive change.
