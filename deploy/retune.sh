#!/usr/bin/env bash
# Fetch recent candles and run the self-learning re-tune.
# Called by cryptoking-learn.service (systemd timer). Edit instruments here.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=.venv/bin/python
INSTRUMENT="${INSTRUMENT:-BTC_USDT}"
DATA="data/${INSTRUMENT}.csv"

mkdir -p data
# Pull the most recent candles from crypto.com into a CSV.
$PY backtest.py --fetch "$DATA" --instrument "$INSTRUMENT"

# Propose a re-tune. Remove "--apply" to require manual approval in the dashboard.
# Add "--ai-review" to attach a Claude sanity-check note (uses Anthropic credits).
$PY learn.py --csv "$DATA" --instrument "$INSTRUMENT"
