# Current stock research watchlists (31 October 2026)

This is separate research functionality; no legacy trading rank or ATR settings are modified. All displayed securities are **unvalidated candidates**, not verified investment recommendations.

## Quality + Momentum
Stocks need a recent USD close, dated EUR reference FX, daily ATR, the existing USD 5 price and USD 5m average turnover screen, a 12–2 month momentum value, and SEC annual facts with actual filing date <= snapshot date. Annual facts must be <=610 days old. Profitability: gross profit/assets, operating cashflow/assets, earnings/assets and -debt/assets, at least 2 verified components. Each component is percentile-ranked; quality is the average of available component ranks. Final score: 50% quality and 50% 12-2 momentum. Missing data are excluded rather than imputed.

## Quality + Value + Momentum
Use the existing experimental QVM score (equal thirds) only where SEC annual filing remains documented and matches the as-filed score date. Annual diluted share count is only a rough proxy for present market capitalisation, not a verified current valuation. Academic factor evidence does not prove the specific individual-stock recommendations.

## Supply-bottleneck exposure hypotheses
Only stocks in explicitly hand-curated sector themes are shown; ranked by 12–2 month momentum and not by any fabricated shortage probability. Topic RSS headlines are **sector-wide context**, never company-specific causal evidence. There is not yet a validated company-level economic shortage predictor. The list is called hypotheses, not proven opportunities.

## Overlap
List exactly which Top-10 strategies include each stock and show each rank. As these inputs share momentum, overlaps are not independent statistically confirmed signals.

## Transparency and order estimates
Every card shows dated FX-converted EUR reference closing price, indicative buy=close-ATR and stop=buy-2.5*ATR, source timestamps, SEC filing and source URL where available, and Trade Republic Austria ISIN confirmation. A TR inclusion is not proof of an executable live order or the actual EUR bid/ask. Orders, individual taxes, unmodelled stock dividends and verified future outperformance are not asserted.

Historical academic factor-portfolio performance does not transfer automatically to this current incomplete/survivorship-biased stock universe. The published research tab retains its separate long-run study and the older app tabs unchanged.

Source: scripts/research_candidates.py; UI: docs/research-candidates.js; tests: tests/test_research_candidates.py. GitHub Actions validates these together with legacy tests before deployment.