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
- **Strategy** (`structure_fib`, default) — a faithful encoding of the trading
  guide's method (see below). Two strategies ship:
  - `structure_fib` — top-down structure + Fibonacci golden pocket + candlestick.
  - `ema_rsi_scalper` — simpler EMA-cross + RSI scalper (fee-aware).
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

The bot is a long-running process. The recommended free, hands-off setup is a
**[Oracle Cloud Always Free](DEPLOY.md)** VM with systemd — see **[DEPLOY.md](DEPLOY.md)**
for the full step-by-step (free VM, auto-restart, private dashboard via SSH tunnel,
weekly self-learning timer).

Quick local option:

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
  strategy/structure_fib.py    structure + Fibonacci + candlestick strategy
  strategy/scalping.py         EMA+RSI scalping strategy
  risk/risk_manager.py         sizing, stops, kill switch
  execution/paper.py           simulated broker (market + maker/limit)
  execution/live.py            real-money broker
  ai/analyst.py                optional Claude BUY-signal confirmation
  learn.py                     walk-forward self-learning
  engine.py                    the 24/7 loop
  web/                         Flask dashboard
backtest.py / optimize.py / learn.py   CLI tools
deploy/                        systemd units + setup/retune scripts
DEPLOY.md                      Oracle Cloud (free) deploy guide
tests/                         pytest suite
```

## Backtesting (prove the edge first)

The guide's step 1: never risk money on an unproven strategy. Backtest it.

```bash
# 1) fetch real candles from crypto.com into a CSV (run where network is open)
python backtest.py --fetch data/BTC_USDT.csv --instrument BTC_USDT

# 2) backtest the configured strategy on that data
python backtest.py --csv data/BTC_USDT.csv --instrument BTC_USDT

# or try it offline on deterministic synthetic data
python backtest.py --demo
```

It replays candles through the **same** strategy + risk + paper-broker code the
live engine uses (higher timeframe built by aggregating, exits checked intrabar)
and prints win rate, reward:risk, profit factor, and **expected value per trade**.
A positive expected value over a meaningful sample (30+ trades) is the green light
the guide describes. The shipped defaults are a starting point — expect to tune
`config.yaml` against real data before they show an edge.

> Note: `--fetch` pulls the most recent candles the public API returns. For long
> backtests you'll want a larger history (pagination is on the roadmap), or supply
> your own CSV with columns `t,o,h,l,c,v`.

## Tuning (find a positive-edge config)

Grid-search strategy + risk parameters over historical candles and rank by
expected value:

```bash
python optimize.py --csv data/BTC_USDT.csv     # real data
python optimize.py --demo                        # synthetic
```

It backtests every combination in the grids (edit them at the top of `optimize.py`)
and prints the best by EV, flagging thin samples. Use it to settle `swing_k`,
`rr_ratio`, `stop_buffer`, etc. before going to paper.

## AI signal confirmation (optional)

CryptoKing can use **Claude** as a final sanity check on every BUY signal. When
the technical strategy fires, the setup (instrument, price, proposed stop, trend,
Fibonacci/candle context) is sent to the Claude API, which returns a structured
verdict `{proceed, confidence, reason}`. A veto skips the entry; the reasoning
shows up in the dashboard signals row and the trade reason.

```yaml
# config.yaml
ai:
  enabled: true
  model: claude-opus-4-8     # or claude-sonnet-4-6 / claude-haiku-4-5 (cheaper)
  fail_open: true            # if the API errors: true = allow, false = skip
```

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
pip install anthropic
```

- Runs **only on actual BUY signals**, never every loop — cost scales with trade
  frequency, not poll rate. Haiku is the cheapest model for a high-frequency filter.
- Works anywhere with internet (your VPS/PC) — needs to reach `api.anthropic.com`.
- It's a **filter, not a generator**: it can only veto or approve the technical
  strategy's entries, never invent its own. Toggle it from the Settings panel too.

> Note: this is the legitimate use of Anthropic credits in this project — Claude as
> part of the bot's decision-making. It does **not** host the bot; you still run the
> bot on a VPS/PC (see Running 24/7).

## Self-learning (walk-forward re-tuning)

The bot can adapt its own parameters to recent market behavior — safely. The trap
with self-learning a trading bot is **overfitting** (a config that looks great on
the past and bleeds live), so the guard is strict out-of-sample validation:

```bash
python learn.py --csv data/BTC_USDT.csv            # propose only
python learn.py --csv data/BTC_USDT.csv --apply     # apply if it promotes
python learn.py --csv data/BTC_USDT.csv --ai-review # add a Claude sanity-check note
```

How it works (`learn.py` + `src/cryptoking/learn.py`):
1. Split recent candles into **train** (older) and **holdout** (newer).
2. Grid-search parameters on **train only**.
3. Measure the train-winner on the **holdout** (data it never saw).
4. Measure the **current** config on the same holdout.
5. **Promote only if** the new config beats current on the holdout, has a positive
   expected value, and traded enough to be meaningful — otherwise reject.

A promotion is written to `logs/proposal.json`; nothing changes live until you
**Approve** it from the dashboard's *Self-learning* panel (stop the bot first), or
pass `--apply` for autonomous adaptation. Run it weekly via the systemd timer in
[DEPLOY.md](DEPLOY.md). Optionally `--ai-review` attaches a Claude note flagging
overfitting/sizing concerns (uses Anthropic credits).

> The bot never silently rewrites its own live trading rules — promotions must
> clear the holdout bar, and applying is gated behind approval or an explicit flag.

## Settings panel

The dashboard has a **Settings** section to change order type (market/limit),
timeframes, risk-per-trade, reward:risk, stop buffer, and strategy params — no file
editing. Stop the bot, edit, Save; changes are written to `config.yaml` and applied
on the next Start. (Settings are locked while the bot is running.)

## Tests

```bash
python -m pytest -q
```

## The strategy: the trading guide, in code

The default `structure_fib` strategy implements the guide's method end-to-end:

**Top-down framework** — the higher timeframe (`trend_timeframe`, e.g. 4h) sets
*direction* via market structure; the execution timeframe (`timeframe`, e.g. 15m)
finds the *entry*.

**Market structure** — higher-highs + higher-lows = uptrend; the reverse = downtrend;
otherwise a range. The bot only takes longs *with* an uptrend (spot is long-only;
shorting needs futures/margin, intentionally out of scope here).

**Fibonacci golden pocket** — it draws the retracement of the last up-impulse and
only enters when price has pulled back into the 0.618–0.786 "golden pocket" (support).

**Candlestick confirmation** — entry requires a bullish reversal candle (hammer,
bullish engulfing, tweezer bottom, or marubozu) in that pocket.

**Risk = the guide's math** (in `risk/`):
- Risk **1%** of equity per trade (`risk_per_trade`), never more.
- Position size = `equity × risk% ÷ stop-distance` — sized from the *actual* stop,
  which is placed just below the swing low (structure invalidation).
- Take-profit = **R:R × stop-distance** (`rr_ratio`, default 2:1).
- Daily-loss kill switch halts new entries after `max_daily_loss_pct`.

**The math, tracked for you** — the dashboard's "Your Edge" panel computes win rate,
**expected value per trade**, profit factor, and reward:risk from your closed trades
(`analytics.py`). As the guide stresses: a positive expected value is the whole game —
you don't need to win most trades, just make more when right than you lose when wrong.

**The process** — backtest → demo/paper (25–50+ trades) → live only once expected
value is positive. Paper mode + the ledger + the edge panel are built for exactly this.
Don't skip steps.

## Fees: the scalper's #1 enemy

Round-trip taker fees on spot are ~0.15%. If your average trade tries to capture
less than that, fees quietly eat you alive. How this project fights back, and what
to do next:

1. **Maker/limit orders instead of market** (biggest win — now built in, default
   `order_type: limit`). Post-only limit entries pay the lower maker fee instead of
   the taker fee and avoid crossing the spread. Switch in `config.yaml` → `execution`
   or from the dashboard Settings panel.
2. **Stake CRO** for a lower fee tier on crypto.com.
3. **Fewer, higher-quality trades** with a bigger target. `strategy.min_edge` and the
   take-profit/stop ratio in `config.yaml` enforce a net-of-fee edge; raise the
   timeframe to `5m` to capture larger moves per trade.
4. Tune `fees.taker_fee` / `fees.maker_fee` to *your* actual tier so sizing is honest.

## Roadmap / not-yet-done

- Longer backtest history via paginated candle fetching.
- WebSocket feed for lower-latency fills (current MVP polls REST).
- Maker-order fill modeling: real limit orders may not fill; the paper broker
  currently assumes they do. Add unfilled/partial handling for live realism.
- Position reconciliation against the exchange on restart.
- Dashboard authentication for safe remote access.
- Additional exchange clients (Bybit futures for shorting, or a Bappebti-registered
  Indonesian exchange) behind the existing Broker interface.

## Disclaimer

This is educational software provided as-is, with no warranty. Automated trading
carries substantial risk of loss. Nothing here is financial advice.
