"""Shared LLM helper (retries, usage counting) and PortWatch normalisation. No real calls."""
import pytest

from agents import llm_utils
from agents import portwatch_client as pw


class FakeResponse:
    def __init__(self, text, tin=10, tout=5, finish="stop", reasoning=0):
        self.content = text
        self.usage_metadata = {"input_tokens": tin, "output_tokens": tout,
                               "output_token_details": {"reasoning": reasoning}}
        self.response_metadata = {"finish_reason": finish}


class FakeLLM:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


@pytest.fixture
def llm_on(monkeypatch):
    monkeypatch.setenv("SUPPLYPULSE_NO_LLM", "0")
    llm_utils.reset_usage()

    def install(fake):
        monkeypatch.setattr(llm_utils, "get_llm", lambda max_tokens: fake)
        return fake
    return install


def test_no_llm_mode_needs_no_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert llm_utils.invoke_with_retry([], 100, agent="x") == llm_utils.NO_LLM_TEXT


def test_429_waits_60s_then_succeeds(llm_on):
    fake = llm_on(FakeLLM([Exception("Error code: 429 rate limit"), FakeResponse("ok")]))
    waits = []
    assert llm_utils.invoke_with_retry([], 100, agent="route", sleep=waits.append) == "ok"
    assert waits == [60] and fake.calls == 2
    assert llm_utils.USAGE["route"]["input_tokens"] == 10


def test_gives_up_after_max_attempts(llm_on):
    llm_on(FakeLLM([Exception("429")] * 3))
    with pytest.raises(llm_utils.LLMError):
        llm_utils.invoke_with_retry([], 100, agent="x", sleep=lambda s: None)


def test_bad_request_is_not_retried(llm_on):
    fake = llm_on(FakeLLM([Exception("401 invalid api key"), FakeResponse("never")]))
    with pytest.raises(llm_utils.LLMError):
        llm_utils.invoke_with_retry([], 100, agent="x", sleep=lambda s: None)
    assert fake.calls == 1


def test_empty_output_is_a_failure(llm_on):
    llm_on(FakeLLM([FakeResponse(""), FakeResponse("  "), FakeResponse("")]))
    with pytest.raises(llm_utils.LLMError):
        llm_utils.invoke_with_retry([], 100, agent="x", sleep=lambda s: None)


def test_truncated_answer_is_flagged_and_not_retried(llm_on):
    fake = llm_on(FakeLLM([FakeResponse("half an answer", tout=400, finish="length", reasoning=300),
                           FakeResponse("never used")]))
    text = llm_utils.invoke_with_retry([], 400, agent="route", sleep=lambda s: None)
    assert text == "half an answer" and fake.calls == 1
    u = llm_utils.USAGE["route"]
    assert u["truncated"] is True and u["wasted_output_tokens"] == 400 and u["reasoning_tokens"] == 300
    assert llm_utils.usage_totals()["truncated_agents"] == ["route"]


def test_truncated_with_no_text_is_flagged_not_retried(llm_on):
    fake = llm_on(FakeLLM([FakeResponse("", tout=700, finish="length"), FakeResponse("never used")]))
    assert llm_utils.invoke_with_retry([], 700, agent="sup", sleep=lambda s: None) == llm_utils.TRUNCATED_EMPTY_TEXT
    assert fake.calls == 1


def test_empty_answer_that_is_retried_counts_as_wasted(llm_on):
    llm_on(FakeLLM([FakeResponse("", tout=50), FakeResponse("ok", tout=20)]))
    assert llm_utils.invoke_with_retry([], 700, agent="sup", sleep=lambda s: None) == "ok"
    assert llm_utils.USAGE["sup"]["wasted_output_tokens"] == 50
    assert llm_utils.USAGE["sup"]["truncated"] is False


def test_client_uses_low_reasoning_effort(monkeypatch):
    import langchain_groq
    seen = {}

    class StubGroq:
        def __init__(self, **kw):
            seen.update(kw)
    monkeypatch.setattr(langchain_groq, "ChatGroq", StubGroq)
    monkeypatch.setattr(llm_utils, "_CLIENTS", {})
    monkeypatch.setenv("GROQ_API_KEY", "test-not-a-real-key")
    llm_utils.get_llm(400)
    assert seen["reasoning_effort"] == "low" and seen["max_tokens"] == 400
    assert seen["model_name"] == "openai/gpt-oss-20b"


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.setenv("SUPPLYPULSE_NO_LLM", "0")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(llm_utils, "_CLIENTS", {})
    with pytest.raises(llm_utils.LLMError, match="GROQ_API_KEY"):
        llm_utils.get_llm(123)


def test_los_angeles_and_long_beach_share_one_combined_capacity():
    assert pw.PORT_NAME_MAP["Port of Los Angeles"] == pw.PORT_NAME_MAP["Port of Long Beach"] == "port664"
    assert pw._capacity_for("Port of Los Angeles") == pw._capacity_for("Port of Long Beach") == 27 + 23


def test_static_switch_skips_portwatch(monkeypatch):
    monkeypatch.setattr(pw, "fetch_portwatch_utilization",
                        lambda name: (_ for _ in ()).throw(AssertionError("must not be called")))
    assert pw.get_port_utilization("Port of Busan", 0.67) == (0.67, "static")


def test_portwatch_down_falls_back_to_static(monkeypatch):
    monkeypatch.setenv("SUPPLYPULSE_STATIC_UTIL", "0")
    monkeypatch.setattr(pw, "load_cache", lambda: {})

    def boom(*a, **k):
        raise ConnectionError("down")
    monkeypatch.setattr(pw.requests, "get", boom)
    assert pw.get_port_utilization("Port of Busan", 0.67) == (0.67, "static")
