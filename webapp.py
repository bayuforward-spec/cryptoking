#!/usr/bin/env python3
"""CryptoKing web dashboard entry point.

Usage:
    python webapp.py                  # serves dashboard on http://localhost:8000
    python webapp.py --port 8080
    python webapp.py --autostart      # start the trading loop immediately

The bot runs in a background thread inside this process; use the dashboard's
Start/Stop buttons (or --autostart) to control it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cryptoking.config import load_config  # noqa: E402
from cryptoking.logger import setup_logging  # noqa: E402
from cryptoking.web.app import create_app  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="CryptoKing web dashboard")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--autostart", action="store_true", help="start trading on launch")
    args = parser.parse_args()

    config = load_config(args.config)
    log = setup_logging(config.logging.level)
    log.info("Dashboard on http://%s:%d  (mode=%s)", args.host, args.port, config.mode)

    app = create_app(config, autostart=args.autostart)
    # threaded=True so API calls don't block while the engine thread runs.
    app.run(host=args.host, port=args.port, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
