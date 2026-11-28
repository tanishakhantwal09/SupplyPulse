"""Route Optimization Agent.

Code allocates the ships; the LLM only explains the code's result (Gap 3).

Gap 1: ships are allocated by a Wardrop (1952) user equilibrium (agents/wardrop.py):
every receiving port gets ships until its travel time (sailing + BPR-congested port
time) equals one common time T, and no unused port is faster.
  BPR: U.S. Bureau of Public Roads (1964), Traffic Assignment Manual (alpha 0.15, beta 4).
  Wardrop, J.G. (1952), Proc. Inst. Civil Engineers 1(3): user equilibrium.
The old free-capacity split is kept only as an ablation strategy ("free-capacity split").
"""
import json
import math

from langchain_core.messages import HumanMessage, SystemMessage
from rich import box
from rich.panel import Panel
from rich.table import Table

from agents import wardrop
from agents.llm_utils import console, invoke_with_retry
from agents.portwatch_client import get_port_utilization
from agents.reference_data import port_by_id
from agents.wardrop import BPR_ALPHA, BPR_BETA  # noqa: F401  (re-exported; sources in agents/wardrop.py)

# ── Constants ────────────────────────────────────────────────────────────────

EARTH_RADIUS_NM = 3440.065  # mean Earth radius 6,371.0 km / 1.852 km per nm.

SAILING_SPEED_NM_PER_DAY = 400  # ASSUMPTION: ~16.7 knots container-ship service speed; no source yet.
COST_PER_NM_USD = 45            # ASSUMPTION: rerouting cost per vessel per nm; no source yet (BUILD_PLAN 5.2).
SEVERITY_COST_MULTIPLIER = {    # ASSUMPTION: urgency premium by severity; no source yet.
    "critical": 1.8, "high": 1.4, "medium": 1.2, "low": 1.0,
}

# Risk of the receiving port, normalised to 0 / 0.5 / 1 (BUILD_PLAN 4a, Stage 1).
# ASSUMPTION: ports of higher strategic importance are better equipped, so lower risk.
RISK_BY_IMPORTANCE = {"critical": 0.0, "high": 0.5}
RISK_DEFAULT = 1.0
RISK_LABEL = {0.0: "Low", 0.5: "Medium", 1.0: "High"}

# ASSUMPTION: scoring weights Risk 40% / Delay 35% / Cost 25%; not tuned on any data.
SCORE_WEIGHTS = {"risk": 0.40, "delay": 0.35, "cost": 0.25}
CONGESTION_WARNING_VC = 0.90  # ASSUMPTION: warn when a port is over 90% of daily capacity.
MIN_EVENT_DAYS = 1.0  # ships arriving within one day are compared with one day of capacity.

# Free-flow time p_i at a receiving link (congested by the BPR term).
PORT_FREE_FLOW_DAYS = 1.0   # ASSUMPTION: time in port for a diverted ship with no congestion; no source yet
                            # (a dated port-call-time statistic is needed). Results are sensitive to it.
CANAL_FREE_FLOW_DAYS = 1.0  # ASSUMPTION: canal / strait transit plus normal queue time; no source yet.
# Link types by ports.json port_type:
#   'chokepoint'      (Suez Canal, Panama Canal, Strait of Malacca) -> congested, p_i = CANAL_FREE_FLOW_DAYS
#   'alternate_route' (Cape of Good Hope, Lombok Strait, Cape Horn) -> open-ocean bypass: uncongested,
#                     no BPR term and no capacity limit, travel time = sailing time only
#   any other type    (cargo ports)                                -> congested, p_i = PORT_FREE_FLOW_DAYS
UNCONGESTED_PORT_TYPES = {"alternate_route"}
CANAL_PORT_TYPES = {"chokepoint"}

USER_EQUILIBRIUM = wardrop.UE
SYSTEM_OPTIMAL = wardrop.SO
FREE_CAPACITY_SPLIT = "free_capacity_split"
ALLOCATION_METHODS = (USER_EQUILIBRIUM, SYSTEM_OPTIMAL, FREE_CAPACITY_SPLIT)
MAIN_ALLOCATION = USER_EQUILIBRIUM  # SupplyPulse's plan
SCORE_NOTE = "comparison only, not used for allocation"


class UnknownPortError(ValueError):
    """The disrupted port is not in ports.json."""


class NoAlternatesError(ValueError):
    """No usable alternate port exists for the disrupted port."""


# ── Maths ────────────────────────────────────────────────────────────────────
def haversine_nm(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(2 * EARTH_RADIUS_NM * math.asin(math.sqrt(a)), 1)


def ships_per_day(vessels_affected, duration_hours):
    """Spread the diverted ships evenly over the event.

    ASSUMPTION: arrivals are spread evenly over the disruption window.
    max(duration_days, 1) keeps events shorter than a day from producing a
    ships-per-day figure larger than the total number of ships.
    """
    days = max(float(duration_hours or 0) / 24.0, MIN_EVENT_DAYS)
    return vessels_affected / days


def link_type(port):
    if port.get("port_type") in UNCONGESTED_PORT_TYPES:
        return "open_ocean_bypass"
    if port.get("port_type") in CANAL_PORT_TYPES:
        return "canal_or_strait"
    return "port"


def to_link(alt):
    """agents.wardrop.Link for one alternate (all in days and ships per day)."""
    if not alt["congested"]:
        return wardrop.Link(alt["name"], alt["sailing_time_days"], congested=False)
    return wardrop.Link(alt["name"], alt["sailing_time_days"], alt["free_flow_days"],
                        alt["port_capacity"], alt["port_capacity"] * alt["port_utilization"])


def link_times(alt, per_day):
    """Port time, travel time and V/C for `per_day` diverted ships at one alternate."""
    link = to_link(alt)
    return {"port_time_days": wardrop.port_time(link, per_day),
            "travel_time_days": wardrop.travel_time(link, per_day),
            "volume_ratio": wardrop.volume_ratio(link, per_day)}


def split_vessels(total_vessels, weights):
    """Whole ships per port in proportion to `weights` (largest-remainder rounding, exact total)."""
    weights = [max(w, 0.0) for w in weights]
    total_w = sum(weights)
    if total_vessels <= 0 or total_w <= 0:
        return [0] * len(weights)
    exact = [total_vessels * w / total_w for w in weights]
    shares = [int(math.floor(x)) for x in exact]
    leftover = total_vessels - sum(shares)
    order = sorted(range(len(exact)), key=lambda i: exact[i] - shares[i], reverse=True)
    for i in order[:leftover]:
        shares[i] += 1
    return shares


def free_capacity_flows(alternates, per_day):
    """ABLATION ONLY ("free-capacity split"): ships per day in proportion to free daily slots,
    ignoring distance. If no port has free slots, in proportion to capacity."""
    slots = [max(a["port_capacity"] * (1 - a["port_utilization"]), 0.0) for a in alternates]
    if sum(slots) <= 0:
        slots = [a["port_capacity"] for a in alternates]
    total = sum(slots)
    return [per_day * w / total for w in slots] if total > 0 else [0.0] * len(alternates)


def allocate(alternates, vessels_affected, duration_hours, method=MAIN_ALLOCATION):
    """Ships per day and whole ships per alternate for one allocation method."""
    if method not in ALLOCATION_METHODS:
        raise ValueError(f"unknown allocation method {method!r}")
    per_day = ships_per_day(vessels_affected, duration_hours)
    if method == FREE_CAPACITY_SPLIT:
        flows, info = free_capacity_flows(alternates, per_day), {"level": None, "iterations": 0, "converged": True}
    else:
        r = wardrop.solve([to_link(a) for a in alternates], per_day, method)
        flows, info = r["flows"], {k: r[k] for k in ("level", "iterations", "converged")}
    return flows, split_vessels(vessels_affected, flows), info


def apply_allocation(alternates, flows, ships):
    """Write ships, V/C, port time and travel time onto each alternate."""
    for alt, x, n in zip(alternates, flows, ships):
        t = link_times(alt, x)
        vc = t["volume_ratio"]
        alt.update({
            "vessels_diverted_here": n,
            "vessels_per_day_here": round(x, 2),
            "current_load": round(alt["port_capacity"] * alt["port_utilization"], 1) if alt["congested"] else None,
            "volume_ratio": round(vc, 3) if vc is not None else None,
            "port_time_days": round(t["port_time_days"], 3),
            "travel_time_days": round(t["travel_time_days"], 3),
            "congestion_warning": vc is not None and vc > CONGESTION_WARNING_VC,
            "receives_ships": n > 0,
        })


def plan_routes(disrupted_port_id, severity, vessels_affected=0, duration_hours=24, method=MAIN_ALLOCATION):
    """Allocate the diverted ships over the usable alternates.

    Returns {"alternates": [...], "method", "level", "iterations", "converged", "ships_per_day"}.
    Raises UnknownPortError / NoAlternatesError.
    """
    disrupted = port_by_id(disrupted_port_id)
    if not disrupted:
        raise UnknownPortError(f"Unknown port id: {disrupted_port_id!r}")

    alternates = []
    for alt_id in disrupted.get("alternate_ports", []):
        alt = port_by_id(alt_id)
        if not alt:
            continue
        kind = link_type(alt)
        congested = kind != "open_ocean_bypass"
        capacity = alt.get("vessel_capacity", 0) or 0
        if congested and capacity <= 0:
            continue  # cannot receive ships
        distance = haversine_nm(disrupted["lat"], disrupted["lon"], alt["lat"], alt["lon"])
        utilization, util_source = get_port_utilization(alt["name"], alt.get("current_utilization", 0.70))
        risk_score = RISK_BY_IMPORTANCE.get(alt["strategic_importance"], RISK_DEFAULT)
        alternates.append({
            "port_id": alt["port_id"],
            "name": alt["name"],
            "country": alt["country"],
            "country_code": alt.get("country_code"),
            "link_type": kind,
            "congested": congested,
            "distance_nm": distance,
            # s_i: Haversine great-circle distance (ASSUMPTION: real sea routes are longer) / speed.
            "sailing_time_days": distance / SAILING_SPEED_NM_PER_DAY,
            "free_flow_days": (CANAL_FREE_FLOW_DAYS if kind == "canal_or_strait" else PORT_FREE_FLOW_DAYS)
            if congested else 0.0,
            "estimated_cost_usd": round(distance * COST_PER_NM_USD * SEVERITY_COST_MULTIPLIER.get(severity, 1.2)),
            "risk_score": risk_score,
            "risk_level": RISK_LABEL[risk_score],
            "strategic_importance": alt["strategic_importance"],
            "commodities": alt.get("commodities", []),
            "port_capacity": capacity,
            "port_utilization": utilization,
            "utilization_source": util_source,
        })
    if not alternates:
        raise NoAlternatesError(f"No usable alternate port for {disrupted['name']}")

    flows, ships, info = allocate(alternates, vessels_affected, duration_hours, method)
    apply_allocation(alternates, flows, ships)
    for a in alternates:
        a["sailing_time_days"] = round(a["sailing_time_days"], 3)

    # Score: shown for comparison only, NOT used for allocation (BUILD_PLAN 5).
    max_time = max(a["travel_time_days"] for a in alternates) or 1
    max_cost = max(a["estimated_cost_usd"] for a in alternates) or 1
    for a in alternates:
        a["score"] = round(
            SCORE_WEIGHTS["risk"] * a["risk_score"]
            + SCORE_WEIGHTS["delay"] * a["travel_time_days"] / max_time
            + SCORE_WEIGHTS["cost"] * a["estimated_cost_usd"] / max_cost, 4)
        a["score_note"] = SCORE_NOTE
    # Recommended port = the port with the most ships (then the shortest travel time).
    alternates.sort(key=lambda a: (-a["vessels_diverted_here"], a["travel_time_days"]))
    return {"alternates": alternates, "method": method,
            "ships_per_day": ships_per_day(vessels_affected, duration_hours), **info}


def get_alternate_ports(disrupted_port_id, severity, vessels_affected=0, duration_hours=24, method=MAIN_ALLOCATION):
    return plan_routes(disrupted_port_id, severity, vessels_affected, duration_hours, method)["alternates"]


# ── Agent ────────────────────────────────────────────────────────────────────
ROUTE_MAX_TOKENS = 400  # BUILD_PLAN section 2.

SYSTEM_PROMPT = """You are the Route Optimization Agent in SupplyPulse.
The ships have ALREADY been allocated by deterministic code (a Wardrop user equilibrium):
each port that receives ships has the same travel time (sailing + port time), and no
unused port would be faster. Do not change the allocation or choose another port.
Explain it in plain language. Use only the numbers given. Do not invent numbers.
Do not give a confidence percentage. The risk/delay/cost score is for comparison only;
it was NOT used to allocate ships."""


def build_user_prompt(disrupted_port_name, severity, affected_routes, alternates, plan):
    table = [{
        "name": a["name"], "country": a["country"], "link_type": a["link_type"],
        "distance_from_disrupted_port_nm": a["distance_nm"],
        "sailing_time_days": a["sailing_time_days"], "port_time_days": a["port_time_days"],
        "travel_time_days": a["travel_time_days"], "ships_sent": a["vessels_diverted_here"],
        "load_vs_capacity": a["volume_ratio"], "risk": a["risk_level"],
        "score_comparison_only": a["score"],
    } for a in alternates]
    level = plan.get("level")
    return f"""Port disruption: {disrupted_port_name} (severity {severity.upper()})
Affected routes: {', '.join(affected_routes) or 'none'}
Allocation method: Wardrop user equilibrium. Common travel time of the ports used: {round(level, 3) if level is not None else 'n/a'} days.
Port receiving the most ships: {alternates[0]['name']}

Alternates (computed by code):
{json.dumps(table, indent=2)}

Write:
1. WHY THIS ALLOCATION: 2 sentences on why ships go to the ports they go to, using the travel times above.
2. ROUTE ADJUSTMENT: 1 sentence naming the receiving ports (distance is from the disrupted port, not added distance).
3. RISK FACTORS: 2 bullet points, based only on the figures above."""


def _print_table(alternates):
    table = Table(title="Alternate Port Allocation (Wardrop user equilibrium)", box=box.ROUNDED,
                  border_style="cyan", header_style="bold cyan")
    for col in ["Port", "Ships", "Ships/day", "Load/Cap", "Sailing", "Port time", "Travel time", "Score*"]:
        table.add_column(col)
    for a in alternates:
        vc = f"{a['volume_ratio'] * 100:.0f}%" if a["volume_ratio"] is not None else "uncongested"
        table.add_row(a["name"], str(a["vessels_diverted_here"]), str(a["vessels_per_day_here"]), vc,
                      f"{a['sailing_time_days']} d", f"{a['port_time_days']} d", f"{a['travel_time_days']} d",
                      str(a["score"]))
    console.print(table)
    console.print(f"  [dim]*Score 0.40 risk + 0.35 time + 0.25 cost: {SCORE_NOTE}. "
                  "BPR alpha=0.15, beta=4 (U.S. Bureau of Public Roads 1964); Wardrop (1952).[/dim]")


def _parse_list(value):
    return json.loads(value) if isinstance(value, str) else list(value or [])


def route_optimization_agent(state):
    console.print(Panel("[bold cyan]ROUTE OPTIMIZATION AGENT[/bold cyan]\nAnalysing alternate ports...",
                        border_style="cyan"))
    severity = state["severity"]
    affected_routes = _parse_list(state.get("affected_routes"))
    vessels_affected = int(state["vessels_affected"])
    duration_hours = float(state["duration_hours"])

    plan = plan_routes(state["nearest_port_id"], severity, vessels_affected, duration_hours)
    alternates = plan["alternates"]
    _print_table(alternates)

    messages = [SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=build_user_prompt(state["nearest_port_name"], severity,
                                                       affected_routes, alternates, plan))]
    explanation = invoke_with_retry(messages, ROUTE_MAX_TOKENS, agent="route_optimization")
    console.print(Panel(explanation, border_style="green", title="Route Optimization Agent: explanation"))

    return {
        "alternate_ports_analyzed": alternates,
        "recommended_port": alternates[0],
        "llm_reasoning": explanation,
        "agent": "route_optimization",
        "bpr_congestion_applied": True,
        "bpr_alpha": BPR_ALPHA,
        "bpr_beta": BPR_BETA,
        "allocation_method": plan["method"],
        "equilibrium_time_days": round(plan["level"], 4) if plan["level"] is not None else None,
        "solver_iterations": plan["iterations"],
        "solver_converged": plan["converged"],
        "port_free_flow_days": PORT_FREE_FLOW_DAYS,
        "canal_free_flow_days": CANAL_FREE_FLOW_DAYS,
        "vessels_affected": vessels_affected,
        "ships_per_day": round(ships_per_day(vessels_affected, duration_hours), 2),
        "duration_hours": duration_hours,
    }
