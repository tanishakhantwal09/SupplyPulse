"""Whole pipeline, offline (no LLM): deterministic numbers, honest failures."""
import pytest

from agents.confidence import MANUAL_LABEL
from agents.langgraph_orchestrator import run_supplypulse
from agents.route_optimization_agent import UnknownPortError
from tests.sample_events import (LIVE_STRONG, LIVE_WEAK, ROTTERDAM_HIGH, SHANGHAI_CRITICAL, SUEZ_CRITICAL,
                                 UNKNOWN_PORT, USER_SIMULATED, WEAK_SIGNAL)

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


def test_shanghai_travel_time_is_plausible_and_at_equilibrium():
    r = run_supplypulse(SHANGHAI_CRITICAL)
    assert r["allocation_method"] == "user_equilibrium"
    assert r["travel_time_days"] < 4                 # was 74 days with alpha=1.5 and no spreading
    used = [a for a in r["ship_allocation"] if a["vessels"] > 0]
    assert max(a["travel_time_days"] for a in used) - min(a["travel_time_days"] for a in used) < 1e-3
    assert r["plan_weighted_delay_days"] == pytest.approx(r["equilibrium_time_days"], abs=0.01)


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


def test_live_weak_signal_is_gated_and_no_agent_runs():
    r = run_supplypulse(LIVE_WEAK)
    assert r["status"] == "gated"
    assert r["signal_gate"]["enforced"] is True
    assert r["agents_activated"] == []
    assert "recommended_alternate_port" not in r


def test_live_strong_signal_runs():
    r = run_supplypulse(LIVE_STRONG)
    assert r["status"] == "completed"
    assert r["signal_gate"]["action"] == "PROCEED" and r["signal_gate"]["enforced"] is True


@pytest.mark.parametrize("event", [WEAK_SIGNAL, USER_SIMULATED], ids=["dataset-event", "user-simulation"])
def test_manual_scenario_always_runs_but_shows_the_gate(event):
    r = run_supplypulse(event)
    assert r["status"] == "completed"                     # weak signal, but the user confirmed it
    g = r["signal_gate"]
    assert g["enforced"] is False
    assert g["label"] == MANUAL_LABEL
    assert g["action"] == "REJECTED" and g["score"] == pytest.approx(0.1215, abs=1e-3)


def test_gate_can_be_forced_for_experiments():
    assert run_supplypulse(WEAK_SIGNAL, enforce_gate=True)["status"] == "gated"
    assert run_supplypulse(LIVE_WEAK, enforce_gate=False)["status"] == "completed"


def test_unknown_port_fails_loudly():
    with pytest.raises(UnknownPortError):
        run_supplypulse(UNKNOWN_PORT)


def test_usage_and_timings_are_recorded():
    r = run_supplypulse(SHANGHAI_CRITICAL)
    assert set(r["agent_timings_seconds"]) >= {"supervisor", "route_optimization", "inventory", "financial_auditor"}
    assert r["llm_usage"]["calls"] == 4
    assert r["llm_model"] == "openai/gpt-oss-20b"


def test_manual_run_reason_says_agents_ran():
    r = run_supplypulse(WEAK_SIGNAL)
    assert r["status"] == "completed" and "agents ran anyway" in r["signal_gate"]["reason"]
    forced = run_supplypulse(WEAK_SIGNAL, enforce_gate=True)
    assert forced["status"] == "gated" and "agents not activated" in forced["signal_gate"]["reason"]


@pytest.mark.parametrize("event", [SHANGHAI_CRITICAL, SUEZ_CRITICAL, ROTTERDAM_HIGH], ids=["shanghai", "suez", "rotterdam"])
def test_single_port_options_list_each_port_once(event):
    opts = run_supplypulse(event)["single_port_options"]
    ports = [o["port"] for o in opts]
    assert len(ports) == len(set(ports))                                   # no port listed twice
    assert sorted(t for o in opts for t in o["tags"]) == ["Min Carbon", "Min Cost", "Min Time"]
    for o in opts:
        assert o["option"] == " + ".join(o["tags"]) and o["kind"] == "single-port option"


def test_timing_condition_is_recorded():
    r = run_supplypulse(SHANGHAI_CRITICAL)            # tests run with static utilisation and no LLM
    assert r["timing_condition"]["portwatch"] == "static"
    assert r["timing_condition"]["llm_client"] == "disabled"


def test_timing_condition_cold_and_warm():
    from agents.langgraph_orchestrator import timing_condition
    live = {"alternate_ports_analyzed": [{"utilization_source": "portwatch_live"},
                                         {"utilization_source": "portwatch_cache"}]}
    cached = {"alternate_ports_analyzed": [{"utilization_source": "portwatch_cache"},
                                           {"utilization_source": "static"}]}
    assert timing_condition(live)["portwatch"] == "cold"
    assert timing_condition(cached)["portwatch"] == "warm"
    assert timing_condition(None)["portwatch"] == "static"
