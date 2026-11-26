"""Every test runs offline: no LLM call, no PortWatch call, no result files written."""
import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("SUPPLYPULSE_NO_LLM", "1")
    monkeypatch.setenv("SUPPLYPULSE_STATIC_UTIL", "1")
    monkeypatch.setenv("SUPPLYPULSE_NO_SAVE", "1")
    monkeypatch.setenv("SUPPLYPULSE_QUIET", "1")
    monkeypatch.delenv("SUPPLYPULSE_FAKE_LLM_SECONDS", raising=False)
