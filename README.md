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
python run.py
```

It starts trading on simulated money using **real live prices**. Watch the log and
the trade ledger at `logs/trades.csv`.

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

## Roadmap / not-yet-done

- WebSocket feed for lower-latency fills (current MVP polls REST).
- Maker (limit) entries to pay lower fees — big deal for scalping.
- Backtester over historical candles before paper.
- Position reconciliation against the exchange on restart.
- Telegram/Discord alerts.

## Disclaimer

This is educational software provided as-is, with no warranty. Automated trading
carries substantial risk of loss. Nothing here is financial advice.
