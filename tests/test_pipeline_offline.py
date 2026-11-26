"""Whole pipeline, offline (no LLM): deterministic numbers, honest failures."""
import pytest

from agents.confidence import NOT_APPLICABLE
from agents.langgraph_orchestrator import run_supplypulse
from agents.route_optimization_agent import UnknownPortError
from tests.sample_events import (ROTTERDAM_HIGH, SHANGHAI_CRITICAL, SUEZ_CRITICAL, UNKNOWN_PORT,
                                 USER_SIMULATED, WEAK_SIGNAL)

COMPONENTS = ("rerouting_cost", "delay_cost", "freight_rate_increase",
              "inventory_at_risk", "operational_cost", "carbon_penalty")


def test_shanghai_completes_with_a_code_selected_port():
    r = run_supplypulse(SHANGHAI_CRITICAL)
    assert r["status"] == "completed"
    assert r["recommended_alternate_port"] == "Port of Busan"
    assert r["decision"] == "REROUTE"
    assert "confidence" not in r                       # no fixed 91/82/71%
    assert r["signal_gate"]["action"] == "PROCEED"
    assert sum(a["vessels"] for a in r["ship_allocation"]) == 350


def test_total_is_the_sum_of_the_six_parts():
    r = run_supplypulse(SHANGHAI_CRITICAL)
    assert r["total_financial_impact_usd"] == pytest.approx(sum(r["cost_breakdown_usd"][k] for k in COMPONENTS))


def test_shanghai_delay_is_plausible_now():
    r = run_supplypulse(SHANGHAI_CRITICAL)
    assert r["additional_transit_days"] < 2          # was 74 days with alpha=1.5 and no spreading
    assert r["plan_weighted_delay_days"] < 6


def test_no_eu_ets_cost_for_asia_only_voyages():
    r = run_supplypulse(SHANGHAI_CRITICAL)
    assert r["cost_breakdown_usd"]["carbon_penalty"] == 0


def test_rotterdam_pays_ets_with_2025_phase_in():
    r = run_supplypulse(ROTTERDAM_HIGH)
    assert r["status"] == "completed"
    assert r["carbon_details"]["ets_year"] == 2025
    assert r["cost_breakdown_usd"]["carbon_penalty"] > 0
    coverage = r["carbon_details"]["per_port_coverage"]
    assert coverage.get("Port of Felixstowe", 0.5) == 0.5   # UK is outside the EU ETS
    assert all(v in (0.5, 1.0) for v in coverage.values())


def test_runs_are_deterministic():
    a, b = run_supplypulse(SUEZ_CRITICAL), run_supplypulse(SUEZ_CRITICAL)
    assert a["total_financial_impact_usd"] == b["total_financial_impact_usd"]
    assert a["ship_allocation"] == b["ship_allocation"]


def test_weak_signal_is_gated_and_no_agent_runs():
    r = run_supplypulse(WEAK_SIGNAL)
    assert r["status"] == "gated"
    assert r["agents_activated"] == []
    assert "recommended_alternate_port" not in r


def test_gate_can_be_bypassed_for_experiments():
    assert run_supplypulse(WEAK_SIGNAL, enforce_gate=False)["status"] == "completed"


def test_user_simulation_skips_the_gate():
    r = run_supplypulse(USER_SIMULATED)
    assert r["signal_gate"]["action"] == NOT_APPLICABLE
    assert r["status"] == "completed"


def test_unknown_port_fails_loudly():
    with pytest.raises(UnknownPortError):
        run_supplypulse(UNKNOWN_PORT)


def test_usage_and_timings_are_recorded():
    r = run_supplypulse(SHANGHAI_CRITICAL)
    assert set(r["agent_timings_seconds"]) >= {"supervisor", "route_optimization", "inventory", "financial_auditor"}
    assert r["llm_usage"]["calls"] == 4
    assert r["llm_model"] == "openai/gpt-oss-20b"
