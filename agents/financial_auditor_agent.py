"""Financial Auditor Agent.

Prices the capacity split per receiving port (BUILD_PLAN 4a, Stage 1):
cost and CO2 are summed over ports, the delay is weighted by ships.
The LLM only explains the computed figures.
"""
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from rich import box
from rich.panel import Panel
from rich.table import Table

from agents.carbon import calculate_carbon
from agents.llm_utils import console, invoke_with_retry
from agents.reference_data import port_by_id
from agents.route_optimization_agent import link_times, ships_per_day

# ── Constants (BUILD_PLAN 5.2: each still needs a source) ───────────────────
DAILY_TRADE_VALUE_USD = {  # ASSUMPTION: value of trade delayed per day, by severity; no source yet.
    "critical": 850_000_000, "high": 350_000_000, "medium": 120_000_000, "low": 40_000_000,
}
INVENTORY_RISK_SHARE = 0.15            # ASSUMPTION: share of exposed inventory value at risk; no source yet.
OPERATING_COST_PER_VESSEL_DAY_USD = 25_000  # ASSUMPTION: vessel operating cost per day; no source yet.
ALERT_THRESHOLD_USD = {  # ASSUMPTION: alert thresholds by severity; chosen by hand, not tuned.
    "critical": 100_000_000, "high": 50_000_000, "medium": 10_000_000, "low": 1_000_000,
}
FINANCIAL_MAX_TOKENS = 400  # BUILD_PLAN section 2.


def event_year(state):
    """Year of the event, for the EU ETS phase-in.

    ASSUMPTION: if the event has no date, the current year is used (and flagged).
    """
    raw = state.get("event_date")
    try:
        return int(str(raw)[:4]), False
    except (TypeError, ValueError):
        return datetime.now().year, True


def _origin_country(state):
    port = port_by_id(state.get("nearest_port_id"))
    return port.get("country_code") if port else None


def price_split(state, alternates, year):
    """Cost and carbon for each port that receives ships in the split plan."""
    origin_cc = _origin_country(state)
    rows = []
    for a in alternates:
        n = a.get("vessels_diverted_here", 0)
        if n <= 0:
            continue
        carbon = calculate_carbon(a["distance_nm"], n, origin_cc, a.get("country_code"), year)
        rows.append({
            "port": a["name"], "country": a["country"], "vessels": n,
            "rerouting_cost_usd": a["estimated_cost_usd"] * n,
            "travel_time_days": a["travel_time_days"],   # sailing + BPR port time
            "port_time_days": a["port_time_days"],
            "co2_tonnes": carbon["total_co2_tonnes"],
            "ets_coverage_share": carbon["ets_coverage_share"],
            "carbon_cost_usd": carbon["carbon_cost_usd"],
        })
    return rows


def calculate_financial_impact(state, route_output, inventory_output):
    severity = state["severity"]
    vessels = int(state["vessels_affected"])
    freight_pct = float(state["freight_impact_pct"])
    duration_hours = float(state["duration_hours"])
    year, year_assumed = event_year(state)

    alternates = route_output["alternate_ports_analyzed"]
    per_port = price_split(state, alternates, year)
    shipped = sum(r["vessels"] for r in per_port)

    rerouting_cost = sum(r["rerouting_cost_usd"] for r in per_port)
    # Delay is priced as the ship-weighted TRAVEL TIME (sailing + port), BUILD_PLAN 5 (28 Nov 2026).
    weighted_delay = (sum(r["travel_time_days"] * r["vessels"] for r in per_port) / shipped) if shipped else 0.0
    delay_cost = DAILY_TRADE_VALUE_USD[severity] * weighted_delay
    freight_increase = freight_pct / 100 * rerouting_cost
    inventory_exposure = (inventory_output or {}).get("total_exposure_value_usd", 0)
    inventory_at_risk = inventory_exposure * INVENTORY_RISK_SHARE
    operational = vessels * OPERATING_COST_PER_VESSEL_DAY_USD * (duration_hours / 24)
    carbon_cost = sum(r["carbon_cost_usd"] for r in per_port)
    total_co2 = sum(r["co2_tonnes"] for r in per_port)

    total = rerouting_cost + delay_cost + freight_increase + inventory_at_risk + operational + carbon_cost
    return {
        "rerouting_cost": rerouting_cost,
        "delay_cost": delay_cost,
        "freight_rate_increase": freight_increase,
        "inventory_at_risk": inventory_at_risk,
        "operational_cost": operational,
        "carbon_penalty": carbon_cost,
        "total_impact": total,
        "delay_days": round(weighted_delay, 2),
        "delay_basis": "travel time (sailing + BPR port time), weighted by ships sent to each port",
        "freight_impact_pct": freight_pct,
        "vessels_affected": vessels,
        "duration_hours": duration_hours,
        "per_port": per_port,
        # A2: ships that did not fit under the utilisation ceiling are waiting; they are not
        # rerouted and NOT priced here (their waiting cost has no sourced model yet, BUILD_PLAN 5).
        "excess_ships_waiting": route_output.get("excess_ships", 0),
        "excess_ships_priced": False,
        "carbon_details": {
            "total_co2_tonnes": round(total_co2, 2),
            "carbon_cost_usd": round(carbon_cost, 2),
            "ets_year": year,
            "ets_year_assumed": year_assumed,
            "per_port_coverage": {r["port"]: r["ets_coverage_share"] for r in per_port},
            "berth_emissions_modelled": False,
            "regulation": "EU ETS, Directive (EU) 2023/959",
        },
    }


def calculate_pareto_options(state, alternates, year):
    """Single-port options (all ships to one port), for the cost / carbon / time trade-off.

    The BPR delay is recomputed with ALL ships going to that one port.
    """
    vessels = int(state["vessels_affected"])
    per_day = ships_per_day(vessels, state["duration_hours"])
    origin_cc = _origin_country(state)
    options = []
    for a in alternates:
        t = link_times(a, per_day)
        delay, vc = round(t["travel_time_days"], 3), t["volume_ratio"]
        carbon = calculate_carbon(a["distance_nm"], vessels, origin_cc, a.get("country_code"), year)
        cost = a["estimated_cost_usd"] * vessels
        options.append({
            "port": a["name"], "country": a["country"], "cost_usd": cost,
            "delay_days": delay, "volume_ratio": vc, "sailing_time_days": a["sailing_time_days"],
            "distance_nm": a["distance_nm"], "carbon_usd": carbon["carbon_cost_usd"],
            "co2_tonnes": carbon["total_co2_tonnes"], "risk": a["risk_level"],
            "total_cost_usd": cost + carbon["carbon_cost_usd"],
        })
    if not options:
        return []
    winners = [
        ("Min Cost", "Cost-priority operators", min(options, key=lambda x: (x["cost_usd"], x["co2_tonnes"], x["delay_days"]))),
        ("Min Carbon", "Lowest CO2", min(options, key=lambda x: (x["co2_tonnes"], x["cost_usd"], x["delay_days"]))),
        ("Min Time", "Time-priority (travel time, all ships to one port)",
         min(options, key=lambda x: (x["delay_days"], x["cost_usd"], x["co2_tonnes"]))),
    ]
    # Each port appears ONCE, with every tag it wins (e.g. "Min Cost + Min Carbon").
    grouped = {}
    for tag, best_for, o in winners:
        g = grouped.setdefault(o["port"], {**o, "tags": [], "best_for": [], "kind": "single-port option"})
        g["tags"].append(tag)
        g["best_for"].append(best_for)
    for g in grouped.values():
        g["option"] = " + ".join(g["tags"])
    return list(grouped.values())


SYSTEM_PROMPT = """You are the Financial Auditor Agent in SupplyPulse.
All figures were calculated by deterministic code. Explain them in plain language.
Use only the numbers given. Do not invent numbers, savings, probabilities or insurance decisions.
Keep the split plan (the recommendation) and the single-port what-if options clearly apart."""


# Section headings used in the prompt. The number-and-wording check
# (experiments/llm_number_check.py) uses them to know what each number is.
SPLIT_HEADING = "SPLIT PLAN"
SINGLE_HEADING = "SINGLE-PORT OPTIONS"


def build_user_prompt(state, fin, alert, threshold, pareto):
    vessels = int(state["vessels_affected"])
    split = "\n".join(f"- {r['port']}: {r['vessels']} ships, travel time {r['travel_time_days']} d, "
                      f"rerouting ${r['rerouting_cost_usd']:,.0f}" for r in fin["per_port"])
    # Compare like with like: single-port REROUTING cost vs split-plan REROUTING cost.
    # "lower"/"higher" is decided by code, so the LLM does not have to compare numbers.
    def cmp(a, b):
        return "lower than" if a < b else "higher than" if a > b else "equal to"
    split_co2 = fin["carbon_details"]["total_co2_tonnes"]
    opts = "\n".join(
        f"- {o['option']}: {o['port']}: rerouting cost ${o['cost_usd']:,.0f} "
        f"({cmp(o['cost_usd'], fin['rerouting_cost'])} the split plan rerouting cost ${fin['rerouting_cost']:,.0f}); "
        f"delay {o['delay_days']} d ({cmp(o['delay_days'], fin['delay_days'])} the split plan {fin['delay_days']} d); "
        f"CO2 {o['co2_tonnes']:,.0f} t ({cmp(o['co2_tonnes'], split_co2)} the split plan {split_co2:,.0f} t)"
        for o in pareto)
    return f"""Port disruption: {state['nearest_port_name']} (severity {state['severity'].upper()}), {vessels} ships affected

{SPLIT_HEADING} (this is the recommendation: ships shared across ports by a capacity-constrained Wardrop user equilibrium):
{split}
- Ship-weighted travel time (sailing + port) of the split plan: {fin['delay_days']} days
- Ships waiting because no port has room under the utilisation ceiling (excess demand, not rerouted, not priced): {fin['excess_ships_waiting']}

{SPLIT_HEADING} COST, six parts (USD):
- Rerouting: {fin['rerouting_cost']:,.0f}
- Trade delay ({fin['delay_days']} days): {fin['delay_cost']:,.0f}
- Freight increase: {fin['freight_rate_increase']:,.0f}
- Inventory at risk: {fin['inventory_at_risk']:,.0f}
- Operational: {fin['operational_cost']:,.0f}
- EU ETS carbon: {fin['carbon_penalty']:,.0f} ({fin['carbon_details']['total_co2_tonnes']:,.0f} t CO2)
- TOTAL: {fin['total_impact']:,.0f}
Alert: {'TRIGGERED' if alert else 'not triggered'} (threshold {threshold:,.0f})

{SINGLE_HEADING} (what-if only, NOT the plan: ALL {vessels} ships sent to ONE port):
{opts}

Rules: every time you give a number, say whether it belongs to the "split plan" or to a
"single-port option". Never describe a single-port option figure as the plan.

Write:
1. COST ASSESSMENT: which parts of the split plan cost dominate the total (2 sentences).
2. TRADE-OFF: what the single-port options show about rerouting cost, delay and CO2 compared with the split plan,
   using the "lower than / higher than" words given above (2 sentences). Compare rerouting cost with rerouting cost,
   never with the split plan TOTAL.
3. CAVEAT: one sentence noting that several cost constants are assumptions."""


def _print(fin, alert, threshold, pareto):
    t = Table(title="Financial Impact Breakdown", box=box.ROUNDED, border_style="yellow", header_style="bold yellow")
    t.add_column("Component", min_width=30)
    t.add_column("USD", justify="right", min_width=18)
    for label, key in [("Rerouting", "rerouting_cost"), ("Trade delay", "delay_cost"),
                       ("Freight increase", "freight_rate_increase"), ("Inventory at risk", "inventory_at_risk"),
                       ("Operational", "operational_cost"), ("EU ETS carbon", "carbon_penalty"),
                       ("TOTAL", "total_impact")]:
        t.add_row(label, f"${fin[key]:,.0f}")
    console.print(t)
    console.print(f"  Alert: {'TRIGGERED' if alert else 'within threshold'} (threshold ${threshold:,.0f})")
    if pareto:
        p = Table(title="Single-port options (what-if: ALL ships to one port; not the plan)",
                  box=box.ROUNDED, border_style="cyan")
        for c in ["Option", "Port", "Cost", "Delay", "CO2 (t)", "Carbon cost"]:
            p.add_column(c)
        for o in pareto:
            p.add_row(o["option"], o["port"], f"${o['cost_usd']:,.0f}", f"{o['delay_days']} d",
                      f"{o['co2_tonnes']:,.0f}", f"${o['carbon_usd']:,.0f}")
        console.print(p)


def financial_auditor_agent(state, route_output, inventory_output=None):
    console.print(Panel("[bold yellow]FINANCIAL AUDITOR AGENT[/bold yellow]\n"
                        "Pricing each receiving port, including EU ETS carbon...", border_style="yellow"))
    severity = state["severity"]
    fin = calculate_financial_impact(state, route_output, inventory_output)
    pareto = calculate_pareto_options(state, route_output["alternate_ports_analyzed"],
                                      fin["carbon_details"]["ets_year"])
    threshold = ALERT_THRESHOLD_USD[severity]
    alert = fin["total_impact"] > threshold
    _print(fin, alert, threshold, pareto)

    messages = [SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=build_user_prompt(state, fin, alert, threshold, pareto))]
    explanation = invoke_with_retry(messages, FINANCIAL_MAX_TOKENS, agent="financial_auditor")
    console.print(Panel(explanation, border_style="green", title="Financial Auditor Agent: explanation"))

    return {
        "financial_breakdown": fin,
        "financial_alert_triggered": alert,
        "alert_threshold_usd": threshold,
        "carbon_details": fin["carbon_details"],
        "pareto_options": pareto,
        "llm_reasoning": explanation,
        "agent": "financial_auditor",
    }
