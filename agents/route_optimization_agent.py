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
from agents.queueing import fluid_queue
from agents.llm_utils import console, invoke_with_retry
from agents.portwatch_client import get_port_utilization
from agents.reference_data import port_by_id, ports
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
NON_CARGO_PORT_TYPES = UNCONGESTED_PORT_TYPES | CANAL_PORT_TYPES

# Candidate ports (28 Nov 2026). The old hand-made 3-port 'alternate_ports' lists left out
# obvious ports (e.g. Ningbo-Zhoushan, 82 nm from Shanghai).
CANDIDATE_RADIUS_NM = 1500  # ASSUMPTION: about 3.75 days of sailing at 400 nm/day; no source.
MIN_CANDIDATES = 3          # ASSUMPTION: if fewer cargo ports are inside the radius, add the nearest ones.
# For a disrupted canal/strait or bypass route the alternative is a different ROUTE, not a nearby
# port, so its hand-made 'alternate_ports' list (bypass routes + ports) is kept. ASSUMPTION: that
# list has no source (build_reference_databases.py).

# A2 (28 Nov 2026): utilisation ceiling for the capacity-constrained equilibrium.
RHO_MAX = 0.95  # ASSUMPTION: keeps the M/G/1 queue stable (rho < 1); no source yet (BUILD_PLAN 5).

USER_EQUILIBRIUM = wardrop.UE                  # uncapped: ablation only
SYSTEM_OPTIMAL = wardrop.SO                    # uncapped: ablation only
CAPPED_USER_EQUILIBRIUM = "capped_user_equilibrium"
CAPPED_SYSTEM_OPTIMAL = "capped_system_optimal"
FREE_CAPACITY_SPLIT = "free_capacity_split"    # ablation only
ALLOCATION_METHODS = (CAPPED_USER_EQUILIBRIUM, CAPPED_SYSTEM_OPTIMAL, USER_EQUILIBRIUM, SYSTEM_OPTIMAL,
                      FREE_CAPACITY_SPLIT)
MAIN_ALLOCATION = CAPPED_USER_EQUILIBRIUM  # SupplyPulse's plan
_SOLVER = {CAPPED_USER_EQUILIBRIUM: (wardrop.UE, True), CAPPED_SYSTEM_OPTIMAL: (wardrop.SO, True),
           USER_EQUILIBRIUM: (wardrop.UE, False), SYSTEM_OPTIMAL: (wardrop.SO, False)}
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


def to_link(alt, capped=False, rho_max=None):
    """agents.wardrop.Link for one alternate (all in days and ships per day).

    capped=True applies the utilisation ceiling (RHO_MAX unless rho_max is given).
    Open-ocean bypass routes are never capped.
    """
    if not alt["congested"]:
        return wardrop.Link(alt["name"], alt["sailing_time_days"], congested=False)
    return wardrop.Link(alt["name"], alt["sailing_time_days"], alt["free_flow_days"],
                        alt["port_capacity"], alt["port_capacity"] * alt["port_utilization"],
                        rho_max=(rho_max if rho_max is not None else RHO_MAX) if capped else None)


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


def allocate(alternates, vessels_affected, duration_hours, method=MAIN_ALLOCATION, rho_max=None):
    """Ships per day and whole ships per alternate for one allocation method.

    With a capped method, ships that do not fit under the ceiling are NOT assigned:
    info["excess_ships"] (whole ships) and info["excess_demand_per_day"] report them.
    """
    if method not in ALLOCATION_METHODS:
        raise ValueError(f"unknown allocation method {method!r}")
    per_day = ships_per_day(vessels_affected, duration_hours)
    info = {"level": None, "iterations": 0, "converged": True, "excess_demand_per_day": 0.0,
            "saturated": False, "rho_max": None}
    if method == FREE_CAPACITY_SPLIT:
        flows = free_capacity_flows(alternates, per_day)
    else:
        solver_method, capped = _SOLVER[method]
        r = wardrop.solve([to_link(a, capped, rho_max) for a in alternates], per_day, solver_method)
        flows = r["flows"]
        info.update({k: r[k] for k in ("level", "iterations", "converged", "saturated")},
                    excess_demand_per_day=r["excess_demand"],
                    rho_max=(rho_max if rho_max is not None else RHO_MAX) if capped else None)
    assigned = (round(vessels_affected * sum(flows) / per_day) if per_day > 0 else 0)
    info["excess_ships"] = vessels_affected - assigned
    info.update(waiting_summary(alternates, flows, vessels_affected, duration_hours))
    return flows, split_vessels(assigned, flows), info


def waiting_summary(alternates, flows, vessels_affected, duration_hours):
    """Times over ALL diverted ships, including those that wait (Newell 1982 fluid queue).

    Placed ships: travel time t_i at their port. Waiting ships (E): wait W at anchorage, then
    sail to the same ports in proportion to the placed flow, so their total time is
    W + flow-weighted travel time of those ports (ASSUMPTION, agents/queueing.py).
    """
    days = max(float(duration_hours or 0) / 24.0, MIN_EVENT_DAYS)
    lam = ships_per_day(vessels_affected, duration_hours)
    mu = sum(flows)
    q = fluid_queue(lam, mu, days)
    placed_time = sum(link_times(a, x)["travel_time_days"] * x for a, x in zip(alternates, flows) if x > 0)
    mean_t = placed_time / mu if mu > 0 else 0.0
    out = {"waiting_ships_exact": q["waiting_ships"], "avg_wait_of_waiting_days": q["avg_wait_of_waiting_days"],
           "total_waiting_ship_days": q["total_waiting_ship_days"], "waiting_placeable": q["placeable"],
           "placed_avg_travel_time_days": mean_t}
    if lam <= 0:
        out["all_ships_avg_travel_time_days"] = 0.0
    elif not q["placeable"]:
        out["all_ships_avg_travel_time_days"] = math.inf
    else:
        total = placed_time * days + q["waiting_ships"] * (q["avg_wait_of_waiting_days"] + mean_t)
        out["all_ships_avg_travel_time_days"] = total / (lam * days)
    return out


def apply_allocation(alternates, flows, ships, waiting_ships=0):
    """Write ships, V/C, port time and travel time onto each alternate.

    vessels_diverted_here = ships placed immediately; vessels_waiting_for_here = ships that wait at
    anchorage and are served later by this port (in proportion to its placed flow).
    """
    later = split_vessels(int(waiting_ships), flows) if waiting_ships > 0 else [0] * len(flows)
    for alt, x, n, w in zip(alternates, flows, ships, later):
        alt["vessels_waiting_for_here"] = w
        t = link_times(alt, x)
        vc = t["volume_ratio"]
        alt.update({
            "utilisation": round(vc, 3) if vc is not None else None,
            "vessels_diverted_here": n,
            "vessels_per_day_here": round(x, 2),
            "current_load": round(alt["port_capacity"] * alt["port_utilization"], 1) if alt["congested"] else None,
            "volume_ratio": round(vc, 3) if vc is not None else None,
            "port_time_days": round(t["port_time_days"], 3),
            "travel_time_days": round(t["travel_time_days"], 3),
            "congestion_warning": vc is not None and vc > CONGESTION_WARNING_VC,
            "receives_ships": n > 0,
        })


def candidate_ports(disrupted, radius_nm=None):
    """[(port record, basis)] of candidate receiving links for a disrupted port or link."""
    if disrupted.get("port_type") in NON_CARGO_PORT_TYPES:
        return [(port_by_id(a), "listed alternative for a canal/strait/bypass (hand-made list, ASSUMPTION)")
                for a in disrupted.get("alternate_ports", []) if port_by_id(a)]
    radius = CANDIDATE_RADIUS_NM if radius_nm is None else radius_nm
    cargo = [p for p in ports() if p["port_id"] != disrupted["port_id"]
             and p.get("port_type") not in NON_CARGO_PORT_TYPES]
    cargo.sort(key=lambda p: haversine_nm(disrupted["lat"], disrupted["lon"], p["lat"], p["lon"]))
    inside = [p for p in cargo if haversine_nm(disrupted["lat"], disrupted["lon"], p["lat"], p["lon"]) <= radius]
    chosen = [(p, f"cargo port within {radius:,} nm") for p in inside]
    for p in cargo[len(inside):]:
        if len(chosen) >= MIN_CANDIDATES:
            break
        chosen.append((p, f"nearest cargo port (fewer than {MIN_CANDIDATES} within {radius:,} nm)"))
    return chosen


def plan_routes(disrupted_port_id, severity, vessels_affected=0, duration_hours=24, method=MAIN_ALLOCATION,
                rho_max=None, radius_nm=None):
    """Allocate the diverted ships over the usable alternates.

    Returns {"alternates": [...], "method", "level", "iterations", "converged", "ships_per_day"}.
    Raises UnknownPortError / NoAlternatesError.
    """
    disrupted = port_by_id(disrupted_port_id)
    if not disrupted:
        raise UnknownPortError(f"Unknown port id: {disrupted_port_id!r}")

    alternates = []
    for alt, basis in candidate_ports(disrupted, radius_nm):
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
            "candidate_basis": basis,
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

    flows, ships, info = allocate(alternates, vessels_affected, duration_hours, method, rho_max)
    apply_allocation(alternates, flows, ships, info["excess_ships"])
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


def get_alternate_ports(disrupted_port_id, severity, vessels_affected=0, duration_hours=24, method=MAIN_ALLOCATION,
                        rho_max=None, radius_nm=None):
    return plan_routes(disrupted_port_id, severity, vessels_affected, duration_hours, method, rho_max,
                       radius_nm)["alternates"]


# ── Agent ────────────────────────────────────────────────────────────────────
ROUTE_MAX_TOKENS = 400  # BUILD_PLAN section 2.

SYSTEM_PROMPT = """You are the Route Optimization Agent in SupplyPulse.
The ships have ALREADY been allocated by deterministic code (a capacity-constrained Wardrop
user equilibrium): no port is filled above its utilisation ceiling; ports below the ceiling
share the same travel time (sailing + port time); a port at its ceiling may be faster; and no
unused port would be faster. Ships that do not fit are reported as waiting (excess demand).
Do not change the allocation or choose another port.
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
    ceiling = plan.get("rho_max")
    if plan.get("saturated"):
        # Every capped port is full: there is no common travel time (bug found in the 28 Nov 2026 Groq run).
        time_line = ("Every receiving port is filled to the utilisation ceiling, so there is NO common travel "
                     "time; each port keeps its own travel time (see the table).")
    else:
        time_line = (f"Common travel time of the ports below the ceiling: "
                     f"{round(level, 3) if level is not None else 'n/a'} days.")
    return f"""Port disruption: {disrupted_port_name} (severity {severity.upper()})
Affected routes (routes that call at this port): {', '.join(affected_routes) or 'none'}
Allocation method: capacity-constrained Wardrop user equilibrium, utilisation ceiling {ceiling if ceiling else 'none'}.
{time_line}
Port receiving the most ships: {alternates[0]['name']}
Ships that do not fit under the ceiling (waiting, not assigned): {plan.get('excess_ships', 0)}

Alternates (computed by code):
{json.dumps(table, indent=2)}

Write:
1. WHY THIS ALLOCATION: 2 sentences on why ships go to the ports they go to, using the travel times above,
   and say how many ships wait because they do not fit.
2. ROUTE ADJUSTMENT: 1 sentence naming the receiving ports (distance is from the disrupted port, not added distance).
3. RISK FACTORS: 2 bullet points, based only on the figures above.
Use only numbers given above. Do not calculate new numbers (no sums, differences or percentages)."""


def _print_table(alternates):
    table = Table(title="Alternate Port Allocation (capacity-constrained Wardrop user equilibrium)", box=box.ROUNDED,
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
        "rho_max": plan["rho_max"],
        "excess_ships": plan["excess_ships"],
        "excess_demand_ships_per_day": round(plan["excess_demand_per_day"], 3),
        "saturated": plan["saturated"],
        "candidate_radius_nm": CANDIDATE_RADIUS_NM,
        "waiting_ships": plan["excess_ships"],
        "avg_wait_of_waiting_days": plan["avg_wait_of_waiting_days"],
        "total_waiting_ship_days": plan["total_waiting_ship_days"],
        "all_ships_avg_travel_time_days": plan["all_ships_avg_travel_time_days"],
        "port_free_flow_days": PORT_FREE_FLOW_DAYS,
        "canal_free_flow_days": CANAL_FREE_FLOW_DAYS,
        "vessels_affected": vessels_affected,
        "ships_per_day": round(ships_per_day(vessels_affected, duration_hours), 2),
        "duration_hours": duration_hours,
    }
