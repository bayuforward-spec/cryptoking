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

from flask import Flask, jsonify, render_template

from ..analytics import compute_stats
from ..config import Config
from ..engine import Engine

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

    def snapshot(self) -> dict:
        return self.engine.snapshot()


def create_app(config: Config, autostart: bool = False) -> Flask:
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
