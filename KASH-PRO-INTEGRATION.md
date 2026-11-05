# KashTrader Pro Intelligence

This branch adds a **Pro Intelligence** view to Kash v3.7.0 while preserving the existing Live Chart, Screenshot Analyzer, and Day Trader views.

## Features
- Multi-exchange spot market scanner using CCXT public endpoints (Binance, Bybit, OKX, KuCoin, Gate.io, Kraken).
- Exchange candle chart and order-book bid/ask snapshots using TradingView Lightweight Charts 5.2.1.
- EMA crossover and RSI mean-reversion example backtests with next-candle-open execution, fees, slippage, exposure and basic performance metrics.
- Return-series analytics and deterministic bootstrap Monte Carlo scenarios.
- No private exchange keys, wallets, or live-order endpoints. This is research-only.

## Frontend deploy
Keep `kash-v3.html`, `kash-pro.css`, and `kash-pro.js` together in the Vercel project root. The original entry file is patched to expose the new tab, and the other three tabs remain unchanged. The chart library loads from the pinned 5.2.1 unpkg distribution. Lightweight Charts requires TradingView attribution and a link; the chart is configured with `attributionLogo: true` and a visible TradingView link.

## Backend deploy
Deploy `backend/` as a separate Docker web service (the `render.yaml` is a starter blueprint). Set `KASH_ALLOWED_ORIGINS` to the exact deployed Kash origin. Once deployed, open the site with the Pro tab and set `window.KASH_PRO_CONFIG = { apiBase: 'https://your-api.example.com' }` before `kash-pro.js`, or set `KASH_PRO_API_BASE` in the deployment wrapper; alternatively use `KashPro.setApiBase(url)` in the browser console. The first-run default is `http://127.0.0.1:8000` for local development.

## Local backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Health: `/health`; API docs: `/docs`.

## Limitations and production hardening
- CCXT uses public market endpoints and built-in exchange rate limiting. Exchange availability, pair symbols, timeframes and regional access differ.
- CORS is not authentication. Before exposing the API to the public, add API-level throttling, server-side caching, request budgets, monitoring and an authentication strategy appropriate to the product.
- Backtest is long-only and does not model stop/target intrabar path, partial fills, order queue, liquidation, funding accrual, borrow, precision or minimum order constraints.
- Historical backtest and bootstrap results are not forecasts or advice. Use out-of-sample evaluation and a benchmark.
- `Freqtrade` and `OpenBB` are not bundled as they are separate services with independent security/provider requirements. Freqtrade should begin in dry-run mode; never expose its control API publicly. OpenBB needs explicitly selected data providers.

## Licenses
TradingView Lightweight Charts is Apache-2.0 and requires the TradingView creator attribution notice plus a link to tradingview.com; the chart's built-in attribution logo is enabled and the UI includes a TradingView link. CCXT is MIT. QuantStats is Apache-2.0. Review dependency notices for commercial distribution.
