"""Crypto.com Exchange API v1 client.

Public market-data endpoints need no authentication. Private endpoints
(account, orders) are signed with HMAC-SHA256 per the v1 spec:

    sig = HMAC_SHA256(secret, method + id + api_key + params_string + nonce)

Docs: https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any

import requests

MAX_PARAM_LEVEL = 3


@dataclass
class Candle:
    t: int      # open time (ms)
    o: float
    h: float
    l: float
    c: float
    v: float


@dataclass
class Quote:
    instrument: str
    bid: float
    ask: float
    last: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread_frac(self) -> float:
        if self.mid <= 0:
            return float("inf")
        return (self.ask - self.bid) / self.mid


def _params_to_str(obj: Any, level: int = 0) -> str:
    """Serialize request params for signing (crypto.com v1 algorithm)."""
    if level >= MAX_PARAM_LEVEL:
        return str(obj)
    if not isinstance(obj, dict):
        return str(obj)
    out = ""
    for key in sorted(obj.keys()):
        out += key
        val = obj[key]
        if val is None:
            out += "null"
        elif isinstance(val, bool):
            out += "true" if val else "false"
        elif isinstance(val, list):
            for sub in val:
                out += _params_to_str(sub, level + 1)
        else:
            out += str(val)
    return out


class CryptoComClient:
    def __init__(
        self,
        api_base: str,
        api_key: str = "",
        api_secret: str = "",
        timeout: int = 10,
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self.session = requests.Session()
        self._id = 0

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    # ----------------------- public market data -----------------------

    def get_candles(self, instrument: str, timeframe: str) -> list[Candle]:
        data = self._public(
            "public/get-candlestick",
            {"instrument_name": instrument, "timeframe": timeframe},
        )
        rows = data.get("data", []) or []
        candles: list[Candle] = []
        for r in rows:
            candles.append(
                Candle(
                    t=int(r["t"]),
                    o=float(r["o"]),
                    h=float(r["h"]),
                    l=float(r["l"]),
                    c=float(r["c"]),
                    v=float(r["v"]),
                )
            )
        candles.sort(key=lambda c: c.t)
        return candles

    def get_quote(self, instrument: str) -> Quote:
        data = self._public("public/get-tickers", {"instrument_name": instrument})
        rows = data.get("data", []) or []
        if not rows:
            raise RuntimeError(f"No ticker data for {instrument}")
        t = rows[0]
        return Quote(
            instrument=instrument,
            bid=float(t["b"]),
            ask=float(t["k"]),
            last=float(t["a"]),
        )

    # ----------------------- private (signed) -----------------------

    def get_account_summary(self, currency: str | None = None) -> dict:
        params = {"currency": currency} if currency else {}
        return self._private("private/user-balance", params)

    def create_order(
        self,
        instrument: str,
        side: str,          # BUY / SELL
        order_type: str,    # MARKET / LIMIT
        quantity: float,
        price: float | None = None,
    ) -> dict:
        params: dict[str, Any] = {
            "instrument_name": instrument,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
        }
        if order_type.upper() == "LIMIT":
            if price is None:
                raise ValueError("LIMIT order requires a price")
            params["price"] = str(price)
        return self._private("private/create-order", params)

    def cancel_order(self, order_id: str) -> dict:
        return self._private("private/cancel-order", {"order_id": order_id})

    def get_open_orders(self, instrument: str | None = None) -> dict:
        params = {"instrument_name": instrument} if instrument else {}
        return self._private("private/get-open-orders", params)

    # ----------------------- transport -----------------------

    def _public(self, method: str, params: dict) -> dict:
        url = f"{self.api_base}/{method}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") not in (0, "0", None):
            raise RuntimeError(f"API error {body.get('code')}: {body.get('message')}")
        return body.get("result", {})

    def _private(self, method: str, params: dict) -> dict:
        if not self.api_key or not self.api_secret:
            raise RuntimeError(
                f"{method} requires API credentials (running in paper mode?)"
            )
        req_id = self._next_id()
        nonce = int(time.time() * 1000)
        param_str = _params_to_str(params)
        sig_payload = f"{method}{req_id}{self.api_key}{param_str}{nonce}"
        signature = hmac.new(
            self.api_secret.encode(),
            sig_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        payload = {
            "id": req_id,
            "method": method,
            "api_key": self.api_key,
            "params": params,
            "nonce": nonce,
            "sig": signature,
        }
        url = f"{self.api_base}/{method}"
        resp = self.session.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") not in (0, "0", None):
            raise RuntimeError(f"API error {body.get('code')}: {body.get('message')}")
        return body.get("result", {})
