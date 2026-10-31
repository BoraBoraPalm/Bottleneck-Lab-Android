# Worldwide market scope — Bottleneck Lab

## What works now

- Every six hours, the existing GitHub Pages pipeline discovers stocks from the open-source global Adanos primary-listing database (MIT), using listing_key / ISIN, alongside official US Nasdaq Trader symbol directories.
- Foreign tickers are converted only with an explicit supported exchange suffix. Ambiguous and unsupported venues are **skipped**, not guessed. Source metadata includes home-country/issuer region, exchange, sector when known, and ISIN.
- This is a **stock directory**, not full market-data coverage. On 31 October 2026, the verified CI run found 46,203 raw stocks, 39,671 safely mapped ticker/venue combinations, a total combined universe of 40,543 symbols, 1,102 with actual recent quotes, and only 313 meeting the new global EUR turnover/price screen. All those numbers can change every run.
- The 205 rotating additional symbol probes per six-hour run are balanced between regions; a small manually curated list ensures representative international reference names remain checked at every run. Quote fetches from Yahoo/Stooq are independently fallible. This is **not** an exhaustive live worldwide screening.
- GBP stock quotes in GBp or GBX are divided by 100 before EUR conversion. All other numeric conversions use dated Frankfurter reference rates, never a Trade Republic executable bid/ask.
- Separate 'Weltweit' tab displays discoverable vs actually priced companies per region, EUR-equivalent price/volume and the independent 12–2-month momentum screen, with TR-AT ISIN toggle. The independent 'Strategien & Forschung' tab adds a region-capped worldwide momentum list (maximum four names per region).
- A research ticker becomes eligible for the global liquidity screen only with latest indicative EUR share price at least 2 EUR and average 20-session EUR volume×price at least 2 million EUR/day. Missing price, FX, volume or momentum fails closed.
- TR-Austria verification uses the exact reference ISIN against the official Austria instrument list (inclusion != current execution availability).

## What is *not* global yet

- SEC 10-K fundamentals are almost entirely US-based, so the existing Quality, Value and Q/V/M factor lists are explicitly labelled SEC/USA. **Do not** compare a US company's Q/V score to a foreign company missing IFRS figures.
- The Kenneth French historical strategy research remains a US-market academic study. It is **not** a global alpha demonstration, and untradeable factor index returns are not Trade Republic trade profits.
- News are sector-wide and supply-bottleneck forecasts are not independently validated. A globally ranked momentum screen cannot claim to predict international bottleneck winners.
- Not every country/exchange is represented in the metadata or supported by Yahoo symbol mappings; some countries, stock categories and FX units may be omitted. Delisted equities and internationally consistent point-in-time fundamental history are not presently covered.

## Source and reproducibility

Global directory: https://github.com/adanos-software/free-ticker-database
Yahoo exchange suffixes: https://help.yahoo.com/kb/finance/SLN2310.html
Production logic: scripts/global_universe.py, scripts/v4_pipeline.py, scripts/research_candidates.py
Global UI: docs/global.html; independent research UI: docs/strategies.html
Integrity tests: tests/test_global_universe.py and tests/test_research_candidates.py

Future globally fair Q/V/M needs licensing and collection of standardized international financial statements (IFRS and other GAAP), release dates, currency, current shares outstanding, corporate actions and all historical delistings; do not impute or claim those currently exist.