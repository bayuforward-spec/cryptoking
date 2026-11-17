"""Market scanner — rank a watchlist of instruments by the SAME structure_fib
logic the engine trades on, using crypto.com candle data.

For each instrument it computes, on live crypto.com candles:
  * higher-timeframe market structure (trend),
  * the last up-impulse and its Fibonacci golden pocket,
  * whether price is pulling back into that pocket,
  * a bullish reversal candle,
  * a structural stop (below the swing low) and R:R-based TP1/TP2,
  * a 0-100 confluence score.

This runs where the bot runs (open network to crypto.com), so the numbers match
what the engine would act on — unlike a third-party indicator feed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import RiskConfig
from .exchange.cryptocom import CryptoComClient
from .patterns import bullish_reversal
from .structure import fib_retracement, last_up_impulse, market_structure

# Default watchlist — top large-caps available as USDT spot pairs on crypto.com.
DEFAULT_WATCHLIST = [
    "BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "ADA_USDT",
    "DOGE_USDT", "AVAX_USDT", "LINK_USDT", "DOT_USDT", "LTC_USDT",
    "BCH_USDT", "TRX_USDT", "ATOM_USDT", "NEAR_USDT", "UNI_USDT",
    "APT_USDT", "ETC_USDT", "XLM_USDT", "FIL_USDT", "ICP_USDT",
]

STOP_BUFFER = 0.0015
RR_TARGET = 2.0
SWING_K = 3
MAX_RISK_PCT = 8.0


@dataclass
class ScanRow:
    instrument: str
    price: float | None = None
    trend: str = "unknown"
    in_pocket: bool = False
    candle: str = ""
    entry: float | None = None
    stop: float | None = None
    tp1: float | None = None
    tp2: float | None = None
    rr: float | None = None
    risk_pct: float | None = None
    score: int = 0
    actionable: bool = False
    error: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def scan_instrument(
    client: CryptoComClient,
    instrument: str,
    exec_timeframe: str,
    trend_timeframe: str,
    swing_k: int = SWING_K,
) -> ScanRow:
    try:
        quote = client.get_quote(instrument)
        ex = client.get_candles(instrument, exec_timeframe)
        tr = client.get_candles(instrument, trend_timeframe)
    except Exception as exc:  # per-instrument failure shouldn't abort the scan
        return ScanRow(instrument=instrument, error=str(exc))

    if len(ex) < 4 * swing_k + 5 or len(tr) < 4 * swing_k + 5:
        return ScanRow(instrument=instrument, error="insufficient candles")

    price = quote.mid
    trend = market_structure(tr, swing_k).trend

    in_pocket = False
    stop = None
    imp = last_up_impulse(ex, swing_k)
    if imp is not None:
        low, high = imp
        fib = fib_retracement(low, high)
        in_pocket = fib.in_golden_pocket(price)
        stop = low * (1 - STOP_BUFFER)

    hit, name = bullish_reversal(ex)
    candle = name if hit else ""

    valid_sl = stop is not None and stop < price
    risk = price - stop if valid_sl else None
    tp1 = price + risk if valid_sl else None
    tp2 = price + RR_TARGET * risk if valid_sl else None
    risk_pct = (risk / price * 100) if valid_sl else None

    score = 0
    if trend == "uptrend":
        score += 40
    elif trend == "range":
        score += 15
    if in_pocket:
        score += 25
    if candle:
        score += 20
    if valid_sl and risk_pct is not None and risk_pct <= MAX_RISK_PCT:
        score += 15
    if trend == "downtrend":
        score = min(score, 20)

    actionable = trend != "downtrend" and valid_sl and in_pocket and bool(candle)

    return ScanRow(
        instrument=instrument,
        price=price,
        trend=trend,
        in_pocket=in_pocket,
        candle=candle,
        entry=price if valid_sl else None,
        stop=stop if valid_sl else None,
        tp1=tp1,
        tp2=tp2,
        rr=RR_TARGET if valid_sl else None,
        risk_pct=risk_pct,
        score=score,
        actionable=actionable,
    )


def scan_market(
    client: CryptoComClient,
    instruments: list[str],
    exec_timeframe: str,
    trend_timeframe: str,
    swing_k: int = SWING_K,
) -> list[ScanRow]:
    rows = [
        scan_instrument(client, inst, exec_timeframe, trend_timeframe, swing_k)
        for inst in instruments
    ]
    # Rank: successful rows by score desc; errored rows last.
    rows.sort(key=lambda r: (r.error == "", r.score), reverse=True)
    return rows
