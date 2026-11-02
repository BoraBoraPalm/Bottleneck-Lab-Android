# Research archive rules

Follow the root research-continuity instructions. Each completed study needs its own folder, README, `test.json`, immutable original result/report files and complete original-bundle member/hash manifest. Keep cached results readable independently of an evaluation run. Use `research/tools/restore_bundle.py` to restore existing cached artifacts rather than re-fetch or re-evaluate them.

Do not edit files under a historical study's `files/` merely to improve an old result or make an old script match today's app. Add a dated correction/version and explain its relation to the frozen source. Mark source-only, result-only and fully reproducible studies distinctly. Keep missing values/missing original code visible.

The completed holding-duration study, its scope and remaining open questions are documented in `research/HOLDING_PERIODS.md`. A planned duration search must not be marked completed. Lookback, forecast horizon, holding cap, realized holding duration, exit policy, turnover and rebalancing are separate required fields.
