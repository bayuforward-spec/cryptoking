from cryptoking.ai.analyst import SignalAnalyst, Verdict


def test_disabled_always_proceeds():
    a = SignalAnalyst(enabled=False)
    v = a.review({"instrument": "BTC_USDT"})
    assert v.proceed is True


def test_fail_open_when_client_unavailable():
    a = SignalAnalyst(enabled=True, fail_open=True)
    a._client = None  # simulate missing client/SDK
    v = a.review({"instrument": "BTC_USDT"})
    assert v.proceed is True
    assert "fail-open" in v.reason


def test_fail_closed_when_client_unavailable():
    a = SignalAnalyst(enabled=True, fail_open=False)
    a._client = None
    v = a.review({"instrument": "BTC_USDT"})
    assert v.proceed is False
    assert "fail-closed" in v.reason


class _FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeResp:
    def __init__(self, text):
        self.content = [_FakeBlock(text)]


class _FakeMessages:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResp(self._text)


class _FakeClient:
    def __init__(self, text):
        self.messages = _FakeMessages(text)


def test_parses_veto_verdict():
    a = SignalAnalyst(enabled=True)
    a._client = _FakeClient('{"proceed": false, "confidence": 0.8, "reason": "into resistance"}')
    v = a.review({"instrument": "BTC_USDT", "price": 100})
    assert v.proceed is False
    assert v.confidence == 0.8
    assert "resistance" in v.reason
    # schema was requested
    assert a._client.messages.calls[0]["output_config"]["format"]["type"] == "json_schema"


def test_parses_approve_verdict():
    a = SignalAnalyst(enabled=True)
    a._client = _FakeClient('{"proceed": true, "confidence": 0.6, "reason": "clean pullback"}')
    v = a.review({"instrument": "ETH_USDT"})
    assert v.proceed is True


def test_bad_json_falls_back():
    a = SignalAnalyst(enabled=True, fail_open=True)
    a._client = _FakeClient("not json")
    v = a.review({"instrument": "BTC_USDT"})
    assert v.proceed is True  # fail-open on parse error


def test_effort_passed_only_when_set():
    a = SignalAnalyst(enabled=True, effort="low")
    a._client = _FakeClient('{"proceed": true, "confidence": 0.5, "reason": "ok"}')
    a.review({"x": 1})
    assert a._client.messages.calls[0]["output_config"]["effort"] == "low"
