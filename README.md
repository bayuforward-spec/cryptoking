# 👑 CryptoKing

An autonomous **scalping bot** for [crypto.com](https://crypto.com) — trades BTC/ETH
on a tight EMA + RSI strategy, with real risk controls and a **paper-trading mode**
so you can validate everything before risking a cent.

> ⚠️ **Trading crypto with leverage of automation can lose real money fast.**
> Start in `paper` mode. Read the whole README. You are responsible for your funds
> and for complying with local regulations (in Indonesia: Bappebti / OJK).

---

## What it does

```
[crypto.com prices] → [EMA+RSI strategy] → [risk manager] → [broker: paper|live] → [CSV ledger]
```

- **Market data** — pulls live candles + order-book quotes from crypto.com.
- **Strategy** (`ema_rsi_scalper`) — goes long when fast EMA > slow EMA, RSI isn't
  overbought, and the spread is tight. Exits on EMA cross-down or RSI exhaustion.
  It is **fee-aware**: scalping only works if your edge beats round-trip fees.
- **Risk manager** — position sizing from a fixed risk-per-trade, stop-loss /
  take-profit, max open positions, and a **daily-loss kill switch**.
- **Two brokers** — `PaperBroker` (simulated fills against real prices, with fees +
  slippage) and `LiveBroker` (real orders via the authenticated crypto.com API).

## Quick start (paper mode — safe, no keys needed)

```bash
pip install -r requirements.txt
cp .env.example .env          # MODE=paper by default
python run.py                 # headless
# — or, with the web dashboard —
python webapp.py              # open http://localhost:8000
```

It trades on simulated money using **real live prices**. Watch the log, the trade
ledger at `logs/trades.csv`, or the dashboard.

## Web dashboard

```bash
python webapp.py --port 8000            # start/stop from the browser
python webapp.py --autostart            # also start trading on launch
```

Open <http://localhost:8000>. The dashboard shows mode (paper/live), running state,
equity / cash / realized PnL, live prices + current signals, open positions with
unrealized PnL, and recent trades — and has **Start / Stop** buttons. The bot runs
in a background thread inside the same process, so it's a single thing to deploy.

> Bind to `127.0.0.1` (default) or put it behind an authenticated reverse proxy.
> Never expose the dashboard publicly without auth, especially in live mode.

## Going live (real money — only after paper looks good)

1. On crypto.com: **Settings → API Keys**. Create a key with **Trade** permission,
   **disable Withdraw**, and restrict to your server's IP.
2. Put the keys in `.env` and switch the mode:
   ```
   CRYPTOCOM_API_KEY=...
   CRYPTOCOM_API_SECRET=...
   MODE=live
   ```
3. Set `risk.starting_capital` and sizing in `config.yaml` to a **small** amount you
   can afford to lose. Run `python run.py` and watch closely.

## Configuration

All tuning lives in [`config.yaml`](config.yaml) — no code edits needed:

| Section | Key knobs |
|---|---|
| `engine` | instruments, timeframe, poll interval |
| `strategy.params` | EMA periods, RSI thresholds, min edge, max spread |
| `risk` | risk-per-trade, stop-loss/take-profit %, max daily loss, max positions |
| `fees` | your actual taker/maker fee tier + assumed slippage |

Secrets and mode live in `.env` (never committed).

## Running 24/7

The bot is a long-running process. Keep it alive on a small VPS with e.g. `systemd`,
`tmux`, `nohup`, or Docker:

```bash
nohup python run.py > logs/run.out 2>&1 &
```

## Project layout

```
run.py                         entry point
config.yaml                    strategy + risk config
src/cryptoking/
  config.py                    config + .env loading
  indicators.py                EMA / RSI / SMA (pure Python)
  exchange/cryptocom.py        REST client + HMAC signing
  strategy/scalping.py         EMA+RSI scalping strategy
  risk/risk_manager.py         sizing, stops, kill switch
  execution/paper.py           simulated broker
  execution/live.py            real-money broker
  engine.py                    the 24/7 loop
tests/                         pytest suite
```

## Tests

```bash
python -m pytest -q
```

## Fees: the scalper's #1 enemy

Round-trip taker fees on spot are ~0.15%. If your average trade tries to capture
less than that, fees quietly eat you alive. How this project fights back, and what
to do next:

1. **Maker/limit orders instead of market** (biggest win — on the roadmap). Post-only
   limit entries pay the lower maker fee instead of the taker fee.
2. **Stake CRO** for a lower fee tier on crypto.com.
3. **Fewer, higher-quality trades** with a bigger target. `strategy.min_edge` and the
   take-profit/stop ratio in `config.yaml` enforce a net-of-fee edge; raise the
   timeframe to `5m` to capture larger moves per trade.
4. Tune `fees.taker_fee` / `fees.maker_fee` to *your* actual tier so sizing is honest.

## Roadmap / not-yet-done

- **Maker (limit) order execution** — pay maker not taker fees. Top priority for live.
- WebSocket feed for lower-latency fills (current MVP polls REST).
- Backtester over historical candles before paper.
- Position reconciliation against the exchange on restart.
- Dashboard authentication for safe remote access.

## Disclaimer

This is educational software provided as-is, with no warranty. Automated trading
carries substantial risk of loss. Nothing here is financial advice.
