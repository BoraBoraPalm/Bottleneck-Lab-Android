# Bottleneck Lab – Android

Private research application. Android 8+, offline UI, native HTTPS data retrieval. No brokerage trades or orders.

## APK Build
GitHub → Actions → **Build Android Debug APK**. Every push to `master` starts a build. After success: Actions → workflow run → Artifacts → download `Bottleneck-Lab-Android-APK`, unzip and install `app-debug.apk` on Android.

## Data & limitations
- Stock quotes from Yahoo Finance chart API are **unofficial**, may be delayed, blocked, incomplete, or unavailable.
- News context through publicly available RSS; keyword attention is **not** an economically validated shortage forecast.
- Buy and stop prices are illustrative ATR-based formulas, **not** investment recommendations or statistically validated profitable entries.
- Only use a verified data provider for production decisions. No broker connectivity, no automatic trading.
- No personal API keys are required or bundled in this version.

This repository contains source code for a personal prototype. Compilation and data retrieval must be validated on GitHub Actions and on a real Android phone.

## Mobile website / GitHub Pages
The mobile dashboard is in `docs/index.html`. The data-publishing workflow is `.github/workflows/market-data-pages.yml`.
A GitHub Actions run fetches actual OHLC prices from Yahoo Finance (unofficial) with Stooq as a fallback, computes a price-only score, checks RSS for recent headlines, and publishes a time-stamped `snapshot.json` together with the static site.
The workflow is scheduled every 6 hours and can also be started via **Actions → Refresh data and publish Bottleneck Lab → Run workflow**.
The in-app refresh button only reloads the last **published** snapshot, it does not trigger a broker or data API call directly.

**One-time publishing activation:** Go to repository **Settings → Pages → Build and deployment → Source → GitHub Actions**.
On GitHub Free, Pages requires a **public** repository. Private repository publishing requires an eligible paid plan. The published site itself is public even if its repository is private.
Once a deployment succeeds the expected URL is `https://boraborapalm.github.io/Bottleneck-Lab-Android/`.
A URL must not be considered active until a successful `deploy-pages` run and a browser check confirm it.

**Limits:** The initial 92-stock curated universe is not an exhaustive stock discovery engine. Scores are computed from return momentum and price volatility only. Earnings/fundamental history, economic bottleneck probability forecasts, fair values, expected returns and strategy validation are NOT yet included. News titles indicate coverage, not proof of a bottleneck. No brokerage integration or trading orders.

## Version 4: Exchange-wide discovery (beta)

**How it works**: GitHub Actions imports Nasdaq's official `nasdaqlisted.txt` and `otherlisted.txt` symbol directories, removes test listings, ETFs and obvious non-common-share securities, and adds a curated list of international companies. All eligible known symbols are candidates, but only a rotating slice receives a full price-history request per job. Previously successful data are retained up to 8 days by fetching the last publicly published site snapshot. It is not a complete daily scan of every global stock.

**Ranked coverage**: The dashboard displays (a) discovered universe size, (b) tickers with valid recent quotes, (c) the batch selected for the last run, (d) SEC-fundamentals coverage. Newly discovered USD stocks must have a last price of at least 5 USD and 20-day average dollar turnover of at least 5 million USD before qualifying for the Top 10. This is only a liquidity safeguard; it is not an audited valuation or an expected-return model.

**Fundamentals**: A rotating small subset of US companies is checked against SEC EDGAR companyfacts for annual revenue, year-over-year revenue growth, operating cashflow and net income, with fiscal-period and filing dates. Values are shown separately and **not used to claim a backtested fundamental score**. International companies and many US listings will have no SEC facts.

**Economic bottlenecks**: Keyword RSS links provide context only. This version does **not** yet forecast future shortages or quantify stock-specific causal exposure. Historical fundamental/shortage data and walk-forward validation are needed before a predictive strategy is possible.

**How to use**: Open https://boraborapalm.github.io/Bottleneck-Lab-Android/ on Android, press **Snapshot laden** to reload the published dataset; for a new external data download use the GitHub Actions workflow. The scheduled workflow is approximately every six hours. Ranking data may be several days old (per-ticker `price_date` and `last_checked_at` should be inspected), and quote vendors are unofficial.

**Verification**: CI runs offline Python unit tests and a JavaScript syntax/control check before retrieving prices and publishing. If validation fails, the existing published site remains untouched. Treat data-provider outages and incomplete coverage as normal limitations.
