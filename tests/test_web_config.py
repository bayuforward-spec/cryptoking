import shutil
from pathlib import Path

from cryptoking.config import load_config
from cryptoking.web.app import create_app


def _app(tmp_path):
    cfg_src = Path("config.yaml")
    cfg_dst = tmp_path / "config.yaml"
    shutil.copy(cfg_src, cfg_dst)
    config = load_config(cfg_dst)
    config.logging.trades_csv = str(tmp_path / "trades.csv")
    return create_app(config, config_path=str(cfg_dst)), config, cfg_dst


def test_get_config(tmp_path):
    app, _, _ = _app(tmp_path)
    c = app.test_client()
    r = c.get("/api/config").get_json()
    assert "risk" in r and "execution" in r and "strategy" in r


def test_update_config_persists(tmp_path):
    app, config, cfg_dst = _app(tmp_path)
    c = app.test_client()
    r = c.post("/api/config", json={
        "risk": {"rr_ratio": 3.0, "risk_per_trade": 0.02},
        "execution": {"order_type": "market"},
        "strategy": {"params": {"swing_k": 4, "require_candle_pattern": False}},
    })
    assert r.get_json()["ok"] is True
    # in-memory applied + coerced
    assert config.risk.rr_ratio == 3.0
    assert config.risk.risk_per_trade == 0.02
    assert config.execution.order_type == "market"
    assert config.strategy.params["swing_k"] == 4
    assert config.strategy.params["require_candle_pattern"] is False
    # persisted to YAML
    reloaded = load_config(cfg_dst)
    assert reloaded.risk.rr_ratio == 3.0
    assert reloaded.execution.order_type == "market"


def test_invalid_order_type_rejected(tmp_path):
    app, _, _ = _app(tmp_path)
    c = app.test_client()
    r = c.post("/api/config", json={"execution": {"order_type": "banana"}})
    assert r.status_code == 400
    assert r.get_json()["ok"] is False
