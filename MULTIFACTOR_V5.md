# Bottleneck Lab v5 — Quality / Value / Momentum (research preview)

## What is implemented
The former 60-trading-day momentum/ATR score remains available as **Legacy Top 10**. It has **not** been replaced by an unvalidated strategy.

A separate **Multifaktor (Beta)** tab combines the following factors with *fixed equal weights*:

| Factor | Implementation | Interpretation |
|---|---|---|
| Momentum | Daily close 42 sessions ago divided by close 252 sessions ago, minus 1 | Long-term 12–2 month price momentum, avoiding most recent ~2 trading months |
| Quality | Percentile ranks of gross profit/assets, operating cashflow/assets, net income/assets, and negative long-term debt/assets, as available | Annual US GAAP profitability / leverage |
| Value | Percentile ranks of earnings yield, operating cashflow yield, and book-to-market, as available | Annual reported USD fundamentals / **approximate** market capitalization |

Within each factor, use the average of *available* component ranks (not zeros for missing metrics). The final composite is the mean of the three factor ranks. Require **all three factors**, at least two quality metrics and one value metric, as well as a sufficiently recent SEC annual 10-K.

Do **not** use the resulting scores as estimated probabilities of positive returns. Their 0–100 display is a **within-covered-cohort percentile composite**, NOT a world-market rank. Cohort counts are visible.

## Source integrity and weaknesses
- Original quote data: unofficial Yahoo Finance and occasional Stooq fallback, now up to 2 years of OHLC to calculate 12–2 momentum.
- Financial data: SEC EDGAR companyfacts (annual 10-K/10-K/A), with reporting and filing dates. Data are refreshed incrementally.
- Shares: diluted shares from the annual filing approximate current outstanding shares. Share-count changes, splits, buybacks and multiple classes can seriously distort yield ratios. Therefore value is only an exploratory approximation.
- Currency: EUR prices are reference conversions, **not** live Trade Republic orderable bid/ask. Underlying Q/V measures are USD, to match the USD shares, SEC facts and exchange quote.
- Companies without complete documents **receive no QVM score**. No inferred sector, analyst revision or bottleneck impact score is secretly substituted.
- Coverage: mainly US-listed companies with complete SEC GAAP facts; international companies, financials, ADRs, recent IPOs and smaller firms are undercovered. Not sector-neutral; no validated historical universe.
- Liquidity: existing minimum USD price and traded turnover screen. The pilot does not implement a validated sector covariance portfolio optimizer, because current sector classification is not reliably available.
- Earnings momentum, economic-bottleneck forecasting and scientifically tested sector diversification remain **future work**; do not claim them as implemented.

## Research verification
Automated tests in `tests/test_multifactor.py` check that 10-K facts are **not eligible before their actual filing date**, future SEC restatements cannot contaminate earlier signals, that 12–2 momentum excludes the latest 42 days, and that missing fundamental fields do not receive a default score. The HTML CI also rejects duplicate or trailing JavaScript.

The separate `research/evaluate_qvm_pit.py` script attempts an exploratory as-of-date historical comparison using actual SEC filing timestamps; its current-stock sampling is subject to **survivorship and coverage selection**, and cannot be called a fully point-in-time investable-market backtest. A successful CI run and a concrete results report are required before interpreting any performance.

## Academic background
- Jegadeesh & Titman (1993), *Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency*.
- Novy-Marx (2013), *The Other Side of Value: The Gross Profitability Premium*.
- Fama & French (2015), *A Five-Factor Asset Pricing Model*.
- Asness, Moskowitz & Pedersen (2013), *Value and Momentum Everywhere*.
- Hou, Xue & Zhang (2020), *Replicating Anomalies*.

Academic support for factors **does not imply** this specific prototype is profitable after execution costs or for an Austrian investor.
