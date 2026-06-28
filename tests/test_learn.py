import math

from cryptoking.config import load_config
from cryptoking.learn import apply_proposal, walk_forward_retune
from cryptoking.optimize import grid
from cryptoking.exchange.cryptocom import Candle


def _candles(n=1600):
    out = []
    price = 100.0
    for i in range(n):
        close = 100 + i * 0.03 + math.sin(i / 18) * 6 + math.sin(i / 4) * 1.0
        o = price
        out.append(Candle(t=i, o=o, h=max(o, close) + 0.6, l=min(o, close) - 0.6, c=close, v=1.0))
        price = close
    return out


def test_walk_forward_returns_proposal_with_holdout_metrics():
    cfg = load_config("config.yaml")
    cfg.strategy.params["swing_k"] = 2
    proposal = walk_forward_retune(
        _candles(), cfg,
        strategy_grid=grid(swing_k=[2, 3], require_candle_pattern=[True, False]),
        risk_grid=grid(rr_ratio=[1.5, 2.0]),
        now_iso="2026-01-01T00:00:00Z",
        train_frac=0.6, trend_ratio=8, min_trades=5,
    )
    # Whatever the verdict, both holdout metrics must be populated and it must
    # never promote a config that loses out-of-sample.
    assert proposal.current_holdout is not None
    assert proposal.proposed_holdout is not None
    if proposal.promote:
        assert proposal.proposed_holdout.expectancy > 0
        assert proposal.proposed_holdout.expectancy > proposal.current_holdout.expectancy
        assert proposal.proposed_holdout.closed_trades >= 5


def test_apply_proposal_mutates_and_persists(tmp_path):
    import shutil
    cfg_dst = tmp_path / "config.yaml"
    shutil.copy("config.yaml", cfg_dst)
    cfg = load_config(cfg_dst)

    from cryptoking.learn import Metrics, Proposal
    m = Metrics(0.0, 0.0, 0.0, 0, 0.0)
    proposal = Proposal(
        created_at="t", promote=True, reason="test",
        strategy_params={"swing_k": 4}, risk_overrides={"rr_ratio": 3.0},
        current_holdout=m, proposed_holdout=m, min_trades=5,
    )
    apply_proposal(proposal, cfg, str(cfg_dst))
    assert cfg.strategy.params["swing_k"] == 4
    assert cfg.risk.rr_ratio == 3.0
    assert proposal.applied is True
    # persisted
    reloaded = load_config(cfg_dst)
    assert reloaded.strategy.params["swing_k"] == 4
    assert reloaded.risk.rr_ratio == 3.0
