"""LangGraph orchestration of the four SupplyPulse agents.

Flow: signal gate -> Supervisor -> Route -> Inventory -> Financial -> final decision.
If the gate does not say PROCEED, no agent runs and the result says why.

Gap 3 (Turpin et al., NeurIPS 2023): every number in the result is computed by
code and recorded in the attribution file; LLM text is explanation only.
"""
import json
import time
from datetime import datetime, timezone
from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph
from rich import box
from rich.panel import Panel
from rich.table import Table

from agents import llm_utils
from agents.confidence import PROCEED, gate_event, outcome_reason
from agents.financial_auditor_agent import financial_auditor_agent
from agents.inventory_agent import inventory_agent
from agents.llm_utils import console
from agents.reference_data import DATA_DIR, ROOT
from agents.route_optimization_agent import BPR_ALPHA, BPR_BETA, route_optimization_agent
from agents.supervisor_agent import supervisor_agent

RESULT_FILE = ROOT / "agents" / "pipeline_result.json"
ATTRIBUTION_FILE = ROOT / "agents" / "pipeline_attribution.json"
RESPONSE_TARGET_SECONDS = 30  # BUILD_PLAN section 1: plan within 30 seconds.


class SupplyPulseState(TypedDict):
    event: dict
    enforce_gate: Optional[bool]
    gate: Optional[dict]
    supervisor_assessment: Optional[str]
    route_output: Optional[dict]
    inventory_output: Optional[dict]
    financial_output: Optional[dict]
    final_decision: Optional[dict]
    start_time: float
    agents_activated: list
    timings: dict


def _timed(name, fn):
    def node(state):
        t0 = time.time()
        out = fn(state)
        state["timings"][name] = round(time.time() - t0, 3)
        return out
    return node


def gate_node(state):
    g = gate_event(state["event"])
    # Policy: enforced for live GDELT events only, unless the caller overrides it.
    if state["enforce_gate"] is not None:
        g["enforced"] = bool(state["enforce_gate"])
        g["policy_override"] = True
        g["reason"] = outcome_reason(g)
    state["gate"] = g
    console.print(f"  Signal gate: {g['action']} (score {g['score']}), "
                  f"{'enforced' if g['enforced'] else 'not enforced'}: {g['label']}")
    return state


def route_after_gate(state):
    g = state["gate"]
    if not g["enforced"] or g["action"] == PROCEED:
        return "supervisor"
    return "gated"


def supervisor_node(state):
    state["supervisor_assessment"] = supervisor_agent(state["event"])
    state["agents_activated"].append("supervisor")
    return state


def route_node(state):
    state["route_output"] = route_optimization_agent(state["event"])
    state["agents_activated"].append("route_optimization")
    return state


def inventory_node(state):
    state["inventory_output"] = inventory_agent(state["event"], state["route_output"])
    state["agents_activated"].append("inventory")
    return state


def financial_node(state):
    state["financial_output"] = financial_auditor_agent(state["event"], state["route_output"],
                                                        state["inventory_output"])
    state["agents_activated"].append("financial_auditor")
    return state


def _base_result(state, status):
    event = state["event"]
    return {
        "status": status,
        "event_id": str(event.get("event_id", "N/A")),
        "data_source": event.get("data_source", "N/A"),
        "disrupted_port": event["nearest_port_name"],
        "event_date": str(event.get("event_date", "N/A")),
        "analysis_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "severity": event["severity"].upper(),
        "signal_gate": state["gate"],
        "agents_activated": list(state["agents_activated"]),
        "agent_timings_seconds": dict(state["timings"]),
        "llm_usage": llm_utils.usage_totals(),
        "llm_model": llm_utils.MODEL_NAME,
        "llm_enabled": not llm_utils.no_llm(),
    }


def gated_node(state):
    result = _base_result(state, "gated")
    result["decision"] = state["gate"]["action"]
    result["decision_basis"] = "Live event: the signal gate did not reach PROCEED, so no agent was run."
    result["total_response_time_seconds"] = round(time.time() - state["start_time"], 2)
    state["final_decision"] = result
    _save(result, {"metadata": result, "note": "Gated event: no plan was computed."})
    return state


def final_decision_node(state):
    event = state["event"]
    route, inv, fin_out = state["route_output"], state["inventory_output"], state["financial_output"]
    fin = fin_out["financial_breakdown"]
    rec = route["recommended_port"]
    top = inv["inventory_analysis"][0] if inv["inventory_analysis"] else {}
    elapsed = round(time.time() - state["start_time"], 2)

    # ASSUMPTION: severity-based rule (critical/high -> REROUTE). It is the same rule
    # that produced the dataset's decision_reroute column, so it must NOT be scored
    # against that column (BUILD_PLAN section 2: old F1 0.974 is retired).
    decision = "REROUTE" if event["severity"] in ("critical", "high") else "MONITOR"

    result = _base_result(state, "completed")
    result.update({
        "decision": decision,
        "decision_basis": "Severity rule: REROUTE if critical or high, else MONITOR (ASSUMPTION)",
        "recommended_alternate_port": rec["name"],
        "alternate_port_country": rec["country"],
        "distance_nm": rec["distance_nm"],
        "additional_transit_days": rec["travel_time_days"],   # travel time (sailing + port) at that port
        "allocation_method": route["allocation_method"],
        "equilibrium_time_days": route["equilibrium_time_days"],
        "plan_weighted_delay_days": fin["delay_days"],
        "ship_allocation": [{"port": a["name"], "vessels": a["vessels_diverted_here"],
                             "vessels_per_day": a["vessels_per_day_here"], "volume_ratio": a["volume_ratio"],
                             "sailing_time_days": a["sailing_time_days"],
                             "port_time_days": a["port_time_days"],
                             "travel_time_days": a["travel_time_days"],
                             "link_type": a["link_type"]} for a in route["alternate_ports_analyzed"]],
        "rerouting_cost_usd": fin["rerouting_cost"],
        "cost_breakdown_usd": {k: fin[k] for k in ("rerouting_cost", "delay_cost", "freight_rate_increase",
                                                    "inventory_at_risk", "operational_cost", "carbon_penalty")},
        "cost_per_port": fin["per_port"],
        "carbon_details": fin_out["carbon_details"],
        "single_port_options": fin_out["pareto_options"],
        "inventory_analysis": inv["inventory_analysis"],
        "unmatched_commodities": inv["unmatched_commodities"],
        "total_financial_impact_usd": fin["total_impact"],
        "financial_alert": fin_out["financial_alert_triggered"],
        "alert_threshold_usd": fin_out["alert_threshold_usd"],
        "top_priority_commodity": top.get("commodity", "N/A"),
        "inventory_exposure_usd": inv["total_exposure_value_usd"],
        "total_response_time_seconds": elapsed,
        "response_target_met": elapsed < RESPONSE_TARGET_SECONDS,
        "agent_timings_seconds": dict(state["timings"]),
        "llm_usage": llm_utils.usage_totals(),
        "agent_assessments": {
            "supervisor": state["supervisor_assessment"],
            "route": route["llm_reasoning"],
            "inventory": inv["llm_reasoning"],
            "financial": fin_out["llm_reasoning"],
        },
    })
    result["agents_activated"] = list(state["agents_activated"]) + ["supervisor_final"]
    state["final_decision"] = result

    attribution = {
        "metadata": {
            "generated_at": result["analysis_date"], "event_id": result["event_id"],
            "event_date": result["event_date"], "disrupted_port": result["disrupted_port"],
            "severity": result["severity"],
            "note": ("All numbers below are computed by code and are reproducible. LLM text is "
                     "explanation only. Reference: Turpin et al. (NeurIPS 2023)."),
        },
        "signal_gate": state["gate"],
        "route_decision": {
            "allocation": "Wardrop (1952) user equilibrium: equal travel time t_i = s_i + p_i*(1 + 0.15*((L_i + x_i)/C_i)^4) at every port used",
            "scoring_formula": "0.40*risk + 0.35*time/max + 0.25*cost/max: comparison only, not used for allocation",
            "bpr_formula": (f"port time = p_i * (1 + {BPR_ALPHA} * (V/C)^{BPR_BETA}); "
                            "U.S. Bureau of Public Roads (1964), Traffic Assignment Manual"),
            "equilibrium_time_days": route["equilibrium_time_days"],
            "ships_per_day": route["ships_per_day"],
            "ports_evaluated": route["alternate_ports_analyzed"],
            "winning_port": rec["name"],
        },
        "inventory_decision": {
            "commodities_assessed": inv["inventory_analysis"],
            "unmatched_commodities": inv["unmatched_commodities"],
            "total_exposure_usd": inv["total_exposure_value_usd"],
        },
        "financial_decision": {
            "formula": "C_reroute + C_delay + C_freight + C_inventory + C_operational + C_carbon(EU ETS)",
            "components": {k: fin[k] for k in ("rerouting_cost", "delay_cost", "freight_rate_increase",
                                                "inventory_at_risk", "operational_cost", "carbon_penalty")},
            "total_usd": fin["total_impact"],
            "per_port": fin["per_port"],
            "alert_triggered": fin_out["financial_alert_triggered"],
            "alert_threshold_usd": fin_out["alert_threshold_usd"],
            "note": "Several cost constants are ASSUMPTIONS (see agents/financial_auditor_agent.py).",
        },
        "eu_ets_carbon_data": {"carbon_details": fin_out["carbon_details"],
                               "pareto_options": fin_out["pareto_options"]},
        "decision_summary": {"final_decision": decision, "decision_basis": result["decision_basis"],
                             "response_time_seconds": elapsed},
        "llm_usage": result["llm_usage"],
        "llm_prompts": dict(llm_utils.PROMPTS),  # what each LLM was given (Gap 3 lineage)
    }
    _print(result)
    _save(result, attribution)
    return state


def _print(r):
    t = Table(box=box.DOUBLE_EDGE, border_style="green", show_header=False)
    t.add_column("Field", style="bold cyan", min_width=28)
    t.add_column("Value", min_width=40)
    for k, v in [("Decision", r["decision"]), ("Disrupted port", r["disrupted_port"]),
                 ("Severity", r["severity"]),
                 ("Signal gate", f"{r['signal_gate']['action']} (score {r['signal_gate']['score']})"),
                 ("Recommended port", r["recommended_alternate_port"]),
                 ("BPR delay at that port", f"{r['additional_transit_days']} days"),
                 ("Total impact (estimate)", f"${r['total_financial_impact_usd']:,.0f}"),
                 ("Response time", f"{r['total_response_time_seconds']} s"),
                 ("LLM tokens (in / out)", f"{r['llm_usage']['input_tokens']} / {r['llm_usage']['output_tokens']}")]:
        t.add_row(k, str(v))
    console.print(Panel(t, title="SUPPLYPULSE: FINAL DECISION", border_style="green"))


def _save(result, attribution):
    if llm_utils.no_save():
        return
    with open(RESULT_FILE, "w") as f:
        json.dump(result, f, indent=2, default=str)
    with open(ATTRIBUTION_FILE, "w") as f:
        json.dump(attribution, f, indent=2, default=str)


def build_graph():
    g = StateGraph(SupplyPulseState)
    g.add_node("gate", gate_node)
    g.add_node("supervisor", _timed("supervisor", supervisor_node))
    g.add_node("route_optimization", _timed("route_optimization", route_node))
    g.add_node("inventory", _timed("inventory", inventory_node))
    g.add_node("financial_auditor", _timed("financial_auditor", financial_node))
    g.add_node("final_decision", _timed("final_decision", final_decision_node))
    g.add_node("gated", gated_node)
    g.set_entry_point("gate")
    g.add_conditional_edges("gate", route_after_gate, {"supervisor": "supervisor", "gated": "gated"})
    g.add_edge("supervisor", "route_optimization")
    g.add_edge("route_optimization", "inventory")
    g.add_edge("inventory", "financial_auditor")
    g.add_edge("financial_auditor", "final_decision")
    g.add_edge("final_decision", END)
    g.add_edge("gated", END)
    return g.compile()


def run_supplypulse(event, enforce_gate=None):
    """Run the pipeline on one event and return the final result dict.

    enforce_gate=None follows the gate policy (enforced for live GDELT events only;
    manual scenarios always run). True/False overrides it (experiments only).
    Errors (unknown port, no alternates, LLM failure) are raised, never hidden.
    """
    llm_utils.reset_usage()
    state = SupplyPulseState(event=event, enforce_gate=enforce_gate, gate=None,
                             supervisor_assessment=None, route_output=None, inventory_output=None,
                             financial_output=None, final_decision=None, start_time=time.time(),
                             agents_activated=[], timings={})
    return build_graph().invoke(state)["final_decision"]


if __name__ == "__main__":
    # Uses the DEVELOPMENT set. The held-out set is only for final evaluation.
    import pandas as pd

    df = pd.read_parquet(DATA_DIR / "training_set.parquet")
    event = df[df["severity"] == "critical"].iloc[0].to_dict()
    result = run_supplypulse(event)
    console.print(f"Status: {result['status']}; response time {result['total_response_time_seconds']} s")
