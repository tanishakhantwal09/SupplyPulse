"""Shared LLM helper for all four agents.

- get_llm(max_tokens): one Groq client per max_tokens value (created lazily,
  so tests and SUPPLYPULSE_NO_LLM runs need no API key).
- invoke_with_retry(...): one place for retries, timeouts and token counting.
- USAGE: measured token counts and time per agent for the current run.
  This is what "cost per analysis" must be computed from (BUILD_PLAN 5.3).

Switches (read at call time, so tests can set them):
  SUPPLYPULSE_NO_LLM=1           skip LLM calls (numbers are unchanged)
  SUPPLYPULSE_QUIET=1            hide console output
  SUPPLYPULSE_STATIC_UTIL=1      use static utilisation instead of PortWatch
  SUPPLYPULSE_NO_SAVE=1          do not write pipeline result files
  SUPPLYPULSE_FAKE_LLM_SECONDS=n with NO_LLM, sleep n s per call (timing tests)
"""
import os
import time

from dotenv import load_dotenv
from rich.console import Console

from agents.reference_data import ROOT

load_dotenv(ROOT / ".env")

# BUILD_PLAN section 2 (decided): model and Groq free tier.
MODEL_NAME = "openai/gpt-oss-20b"
TEMPERATURE = 0.1  # ASSUMPTION: low temperature for stable wording; not tuned.

# BUILD_PLAN section 2: "Retry wait of 60 s on HTTP 429".
RATE_LIMIT_WAIT_SECONDS = 60
MAX_ATTEMPTS = 3  # ASSUMPTION: 3 attempts, then the run is reported as failed.
REQUEST_TIMEOUT_SECONDS = 60  # ASSUMPTION: generous limit for a 700-token answer.
TIMEOUT_RETRY_WAIT_SECONDS = 5  # ASSUMPTION: short pause before retrying a timeout.

NO_LLM_TEXT = "[LLM disabled (SUPPLYPULSE_NO_LLM=1): no explanation generated]"


def flag(name):
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes")


def no_llm():
    return flag("SUPPLYPULSE_NO_LLM")


def quiet():
    return flag("SUPPLYPULSE_QUIET")


def static_util():
    return flag("SUPPLYPULSE_STATIC_UTIL")


def no_save():
    return flag("SUPPLYPULSE_NO_SAVE")


class _QuietAwareConsole:
    """Rich console that respects SUPPLYPULSE_QUIET at print time."""

    def __init__(self):
        self._console = Console()

    def print(self, *args, **kwargs):
        if not quiet():
            self._console.print(*args, **kwargs)


console = _QuietAwareConsole()


class LLMError(RuntimeError):
    """Raised when the LLM call fails after all retries."""


# ── Usage counter ────────────────────────────────────────────────────────────
USAGE = {}


def reset_usage():
    USAGE.clear()


def _record(agent, input_tokens, output_tokens, seconds):
    u = USAGE.setdefault(agent, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0})
    u["calls"] += 1
    u["input_tokens"] += int(input_tokens or 0)
    u["output_tokens"] += int(output_tokens or 0)
    u["seconds"] = round(u["seconds"] + seconds, 3)


def usage_totals():
    return {
        "calls": sum(u["calls"] for u in USAGE.values()),
        "input_tokens": sum(u["input_tokens"] for u in USAGE.values()),
        "output_tokens": sum(u["output_tokens"] for u in USAGE.values()),
        "per_agent": {k: dict(v) for k, v in USAGE.items()},
    }


# ── Client ───────────────────────────────────────────────────────────────────
_CLIENTS = {}


def get_llm(max_tokens):
    if max_tokens not in _CLIENTS:
        from langchain_groq import ChatGroq  # imported lazily: not needed offline

        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise LLMError("GROQ_API_KEY is not set (add it to .env, or set SUPPLYPULSE_NO_LLM=1)")
        _CLIENTS[max_tokens] = ChatGroq(
            api_key=key,
            model_name=MODEL_NAME,
            temperature=TEMPERATURE,
            max_tokens=max_tokens,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=0,  # retries are handled below, in one place
        )
    return _CLIENTS[max_tokens]


def _is_rate_limit(err):
    text = str(err)
    return "429" in text or "rate limit" in text.lower() or type(err).__name__ == "RateLimitError"


def _is_timeout(err):
    return "timeout" in type(err).__name__.lower() or "timed out" in str(err).lower()


def invoke_with_retry(messages, max_tokens, agent, sleep=time.sleep):
    """Call the LLM and return its text. Raises LLMError after MAX_ATTEMPTS.

    Empty or missing text is treated as a failure, never passed on silently.
    """
    if no_llm():
        fake = float(os.getenv("SUPPLYPULSE_FAKE_LLM_SECONDS", "0") or 0)
        if fake > 0:
            sleep(fake)
        _record(agent, 0, 0, fake)
        return NO_LLM_TEXT

    llm = get_llm(max_tokens)
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        start = time.time()
        try:
            response = llm.invoke(messages)
            text = (getattr(response, "content", "") or "").strip()
            meta = getattr(response, "usage_metadata", None) or {}
            _record(agent, meta.get("input_tokens"), meta.get("output_tokens"), time.time() - start)
            if not text:
                raise LLMError("LLM returned empty text")
            return text
        except Exception as err:  # noqa: BLE001 - every failure is retried or reported
            last_err = err
            if attempt == MAX_ATTEMPTS:
                break
            if _is_rate_limit(err):
                console.print(f"  [yellow]Rate limit (429): waiting {RATE_LIMIT_WAIT_SECONDS}s, "
                              f"retry {attempt + 1}/{MAX_ATTEMPTS}[/yellow]")
                sleep(RATE_LIMIT_WAIT_SECONDS)
            elif _is_timeout(err) or isinstance(err, LLMError):
                sleep(TIMEOUT_RETRY_WAIT_SECONDS)
            else:
                break  # other errors (bad key, bad request) are not retried
    raise LLMError(f"{agent}: LLM call failed after {attempt} attempt(s): {last_err}") from last_err
