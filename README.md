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