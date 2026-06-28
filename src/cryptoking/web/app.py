"""Flask web dashboard + JSON API for CryptoKing.

Runs the trading engine in a background thread so the whole bot is a single
process you can deploy on a small VPS. The browser polls the JSON API.

Endpoints:
  GET  /                 dashboard (HTML)
  GET  /api/status       full engine snapshot
  GET  /api/trades       recent rows from the trade ledger
  POST /api/start        start the trading loop
  POST /api/stop         stop the trading loop
"""

from __future__ import annotations

import csv
import logging
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from ..analytics import compute_stats
from ..config import Config, save_config
from ..engine import Engine
from ..learn import Metrics, Proposal, apply_proposal, read_proposal

log = logging.getLogger("cryptoking")


class BotRunner:
    """Owns the Engine and the background thread running its loop."""

    def __init__(self, config: Config):
        self.config = config
        self.engine = Engine(config)
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return False
        self._thread = threading.Thread(target=self.engine.run, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> bool:
        if not (self._thread and self._thread.is_alive()):
            return False
        self.engine.stop()
        return True

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def rebuild(self) -> None:
        """Recreate the Engine from the (mutated) config — used after a settings
        change. Only valid while stopped."""
        self.engine = Engine(self.config)

    def snapshot(self) -> dict:
        return self.engine.snapshot()


def _coerce_like(current, value):
    """Coerce an incoming JSON value to the type of the current value."""
    if isinstance(current, bool):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    if isinstance(current, int) and not isinstance(current, bool):
        return int(value)
    if isinstance(current, float):
        return float(value)
    return value


def _apply_config_updates(config: Config, body: dict) -> None:
    """Apply a settings payload onto the live Config dataclasses, with coercion.

    Only a safe allowlist of fields is editable from the dashboard.
    """
    eng = body.get("engine", {})
    if "timeframe" in eng:
        config.engine.timeframe = str(eng["timeframe"])
    if "trend_timeframe" in eng:
        tt = eng["trend_timeframe"]
        config.engine.trend_timeframe = str(tt) if tt else None
    if "poll_interval_seconds" in eng:
        config.engine.poll_interval_seconds = int(eng["poll_interval_seconds"])

    for key, val in (body.get("strategy", {}).get("params", {}) or {}).items():
        if key in config.strategy.params:
            config.strategy.params[key] = _coerce_like(config.strategy.params[key], val)

    for key, val in (body.get("risk", {}) or {}).items():
        if hasattr(config.risk, key):
            setattr(config.risk, key, _coerce_like(getattr(config.risk, key), val))

    ex = body.get("execution", {}) or {}
    if "order_type" in ex:
        ot = str(ex["order_type"]).lower()
        if ot not in ("market", "limit"):
            raise ValueError("order_type must be 'market' or 'limit'")
        config.execution.order_type = ot
    if "limit_offset" in ex:
        config.execution.limit_offset = float(ex["limit_offset"])

    ai = body.get("ai", {}) or {}
    if "enabled" in ai:
        config.ai.enabled = _coerce_like(config.ai.enabled, ai["enabled"])
    if "model" in ai:
        config.ai.model = str(ai["model"])
    if "fail_open" in ai:
        config.ai.fail_open = _coerce_like(config.ai.fail_open, ai["fail_open"])


def create_app(config: Config, autostart: bool = False, config_path: str = "config.yaml") -> Flask:
    app = Flask(__name__)
    runner = BotRunner(config)
    if autostart:
        runner.start()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/status")
    def status():
        return jsonify(runner.snapshot())

    @app.get("/api/trades")
    def trades():
        path = Path(config.logging.trades_csv)
        rows: list[dict] = []
        if path.exists():
            with path.open("r", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
        # newest first, cap to last 100
        rows.reverse()
        return jsonify(rows[:100])

    @app.get("/api/stats")
    def stats():
        return jsonify(compute_stats(config.logging.trades_csv).as_dict())

    @app.get("/api/config")
    def get_config():
        return jsonify(
            {
                "running": runner.is_running,
                "engine": {
                    "timeframe": config.engine.timeframe,
                    "trend_timeframe": config.engine.trend_timeframe,
                    "poll_interval_seconds": config.engine.poll_interval_seconds,
                },
                "strategy": {"name": config.strategy.name, "params": config.strategy.params},
                "risk": {
                    "risk_per_trade": config.risk.risk_per_trade,
                    "rr_ratio": config.risk.rr_ratio,
                    "stop_loss_pct": config.risk.stop_loss_pct,
                    "max_open_positions": config.risk.max_open_positions,
                    "max_daily_loss_pct": config.risk.max_daily_loss_pct,
                },
                "execution": {
                    "order_type": config.execution.order_type,
                    "limit_offset": config.execution.limit_offset,
                },
                "ai": {
                    "enabled": config.ai.enabled,
                    "model": config.ai.model,
                    "fail_open": config.ai.fail_open,
                },
            }
        )

    @app.post("/api/config")
    def update_config():
        if runner.is_running:
            return jsonify({"ok": False, "error": "stop the bot before changing settings"}), 409
        body = request.get_json(silent=True) or {}
        try:
            _apply_config_updates(config, body)
        except (ValueError, TypeError) as exc:
            return jsonify({"ok": False, "error": f"invalid value: {exc}"}), 400
        save_config(config, config_path)
        runner.rebuild()  # pick up new settings on next start
        return jsonify({"ok": True})

    @app.get("/api/learn/proposal")
    def learn_proposal():
        return jsonify(read_proposal() or {})

    @app.post("/api/learn/apply")
    def learn_apply():
        if runner.is_running:
            return jsonify({"ok": False, "error": "stop the bot before applying"}), 409
        data = read_proposal()
        if not data:
            return jsonify({"ok": False, "error": "no proposal found"}), 404
        if not data.get("promote") or data.get("applied"):
            return jsonify({"ok": False, "error": "proposal is not promotable or already applied"}), 400
        proposal = Proposal(
            created_at=data["created_at"], promote=data["promote"], reason=data["reason"],
            strategy_params=data["strategy_params"], risk_overrides=data["risk_overrides"],
            current_holdout=Metrics(**data["current_holdout"]),
            proposed_holdout=Metrics(**data["proposed_holdout"]),
            min_trades=data["min_trades"],
        )
        apply_proposal(proposal, config, config_path)
        runner.rebuild()
        return jsonify({"ok": True})

    @app.post("/api/start")
    def start():
        started = runner.start()
        return jsonify({"ok": started, "running": runner.engine.is_running})

    @app.post("/api/stop")
    def stop():
        stopped = runner.stop()
        return jsonify({"ok": stopped, "running": runner.engine.is_running})

    app.runner = runner  # type: ignore[attr-defined]
    return app
