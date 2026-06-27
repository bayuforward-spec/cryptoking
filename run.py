#!/usr/bin/env python3
"""CryptoKing entry point.

Usage:
    python run.py                 # uses config.yaml + .env
    python run.py --config x.yaml

Paper mode is the default. Set MODE=live in .env (with API keys) only after
you trust the strategy from paper results.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cryptoking.config import load_config  # noqa: E402
from cryptoking.engine import Engine  # noqa: E402
from cryptoking.logger import setup_logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="CryptoKing trading bot")
    parser.add_argument("--config", default="config.yaml", help="path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    log = setup_logging(config.logging.level)

    if config.is_live:
        log.warning("=" * 60)
        log.warning("RUNNING IN LIVE MODE — REAL MONEY IS AT RISK.")
        log.warning("=" * 60)

    engine = Engine(config)
    engine.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
