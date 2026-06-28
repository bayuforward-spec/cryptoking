"""AI signal analyst — an optional Claude-API confirmation layer on top of the
technical strategy.

When the strategy emits a BUY, the engine asks Claude to review the setup and
return a structured verdict {proceed, confidence, reason}. If Claude vetoes,
the entry is skipped. This consumes Anthropic credits and only runs on actual
entry signals (never every loop), so cost scales with trade frequency.

Uses the official `anthropic` SDK with structured outputs (output_config.format)
so the response is always valid JSON matching our schema. Defaults to
claude-opus-4-8; configurable in config.yaml.

Fails safe per `fail_open`:
  * fail_open=true  -> if the API is unavailable/errors, allow the trade
  * fail_open=false -> if the API is unavailable/errors, skip the trade
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

log = logging.getLogger("cryptoking")

_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "proceed": {
            "type": "boolean",
            "description": "True to allow the trade, false to veto it.",
        },
        "confidence": {
            "type": "number",
            "description": "Confidence in the decision, 0.0 to 1.0.",
        },
        "reason": {
            "type": "string",
            "description": "One concise sentence explaining the decision.",
        },
    },
    "required": ["proceed", "confidence", "reason"],
    "additionalProperties": False,
}

_SYSTEM = (
    "You are a risk-aware crypto trading analyst reviewing a LONG (buy) signal "
    "produced by a technical strategy (market structure + Fibonacci golden "
    "pocket + candlestick confirmation) on a spot exchange. Your job is a final "
    "sanity check: veto setups that look like obvious traps (entering into clear "
    "resistance, against a strong higher-timeframe downtrend, parabolic blow-off, "
    "or a wide/illiquid spread). Approve reasonable continuation/pullback longs. "
    "You are conservative: when the setup is poor, veto. Respond ONLY via the "
    "required JSON schema."
)


@dataclass
class Verdict:
    proceed: bool
    confidence: float
    reason: str


class SignalAnalyst:
    def __init__(
        self,
        enabled: bool = False,
        model: str = "claude-opus-4-8",
        effort: str | None = None,
        fail_open: bool = True,
        max_tokens: int = 1024,
    ):
        self.enabled = enabled
        self.model = model
        self.effort = effort
        self.fail_open = fail_open
        self.max_tokens = max_tokens
        self._client = None
        if enabled:
            self._client = self._make_client()

    def _make_client(self):
        try:
            import anthropic  # imported lazily so the bot runs without it
        except ImportError:
            log.warning("AI filter enabled but `anthropic` not installed; disabling.")
            return None
        try:
            # Resolves ANTHROPIC_API_KEY (or an `ant` profile) from the environment.
            return anthropic.Anthropic()
        except Exception as exc:
            log.warning("Could not init Anthropic client: %s", exc)
            return None

    def review(self, context: dict) -> Verdict:
        """Ask Claude to confirm or veto a BUY setup."""
        if not self.enabled:
            return Verdict(True, 1.0, "AI filter disabled")
        if self._client is None:
            return self._fallback("AI client unavailable")

        prompt = (
            "Review this LONG setup and decide whether to proceed.\n\n"
            + json.dumps(context, indent=2)
        )
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": _SYSTEM,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {"format": {"type": "json_schema", "schema": _VERDICT_SCHEMA}},
        }
        if self.effort:
            kwargs["output_config"]["effort"] = self.effort

        try:
            resp = self._client.messages.create(**kwargs)
            text = next((b.text for b in resp.content if b.type == "text"), "")
            data = json.loads(text)
            return Verdict(
                proceed=bool(data["proceed"]),
                confidence=float(data.get("confidence", 0.0)),
                reason=str(data.get("reason", "")),
            )
        except Exception as exc:  # network, parse, API errors — never crash the loop
            log.warning("AI review failed: %s", exc)
            return self._fallback(f"AI error: {exc}")

    def _fallback(self, reason: str) -> Verdict:
        if self.fail_open:
            return Verdict(True, 0.0, f"{reason} (fail-open: allowed)")
        return Verdict(False, 0.0, f"{reason} (fail-closed: skipped)")
