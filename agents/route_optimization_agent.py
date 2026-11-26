"""Route Optimization Agent.

Code chooses the port; the LLM only explains the code's choice (Gap 3).

Gap 1: BPR congestion plus a capacity split across receiving ports.
  BPR link-performance function: t = t0 * (1 + alpha * (V/C)^beta),
  U.S. Bureau of Public Roads (1964), Traffic Assignment Manual,
  U.S. Department of Commerce, Washington DC. Standard alpha = 0.15, beta = 4.
  Capacity split: motivated by Wardrop (1952), "Some theoretical aspects of road
  traffic research", Proc. Inst. Civil Engineers 1(3): user equilibrium, where no
  ship could lower its own delay by switching port. NOTE: the current split
  (in proportion to free capacity) is a simple heuristic and does NOT compute that
  equilibrium; it ignores distance (see docs/EXPERIMENTS.md, gap ablation).
"""
import json
import math

from langchain_core.messages import HumanMessage, SystemMessage
from rich import box
from rich.panel import Panel
from rich.table import Table

from agents.llm_utils import console, invoke_with_retry
from agents.portwatch_client import get_port_utilization
from agents.reference_data import port_by_id

# ── Constants ────────────────────────────────────────────────────────────────
BPR_ALPHA = 0.15  # U.S. Bureau of Public Roads (1964), Traffic Assignment Manual.
BPR_BETA = 4.0    # U.S. Bureau of Public Roads (1964), Traffic Assignment Manual.

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


def bpr_multiplier(volume_ratio, alpha=BPR_ALPHA, beta=BPR_BETA):
    return 1.0 + alpha * (volume_ratio ** beta)


def bpr_congestion_penalty(base_delay, arrivals_per_day, capacity_per_day, utilization,
                           alpha=BPR_ALPHA, beta=BPR_BETA):
    """BPR-adjusted delay at a receiving port.

    V/C = (current daily load + diverted ships per day) / daily capacity.
    Returns (adjusted_delay, current_load, volume_ratio, multiplier).
    A port with no capacity cannot receive ships, so it raises instead of
    pretending there is no congestion.
    """
    if capacity_per_day <= 0:
        raise ValueError("capacity_per_day must be positive")
    current_load = capacity_per_day * utilization
    volume_ratio = (current_load + arrivals_per_day) / capacity_per_day
    mult = bpr_multiplier(volume_ratio, alpha, beta)
    return round(base_delay * mult, 2), round(current_load, 1), round(volume_ratio, 3), round(mult, 3)


def split_vessels(total_vessels, free_slots):
    """Share total_vessels across ports in proportion to free daily slots.

    Heuristic motivated by Wardrop (1952) user equilibrium; it is not the equilibrium itself.

    Uses largest-remainder rounding so the integers add up exactly to total_vessels.
    Ports with no free slots get 0. If no port has free slots, the ships are
    shared in proportion to capacity instead (caller passes capacities) and every
    port will show V/C > 1.
    """
    weights = [max(s, 0.0) for s in free_slots]
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


def get_alternate_ports(disrupted_port_id, severity, vessels_affected=0, duration_hours=24):
    """Score every usable alternate port. Raises UnknownPortError / NoAlternatesError."""
    disrupted = port_by_id(disrupted_port_id)
    if not disrupted:
        raise UnknownPortError(f"Unknown port id: {disrupted_port_id!r}")

    alternates = []
    for alt_id in disrupted.get("alternate_ports", []):
        alt = port_by_id(alt_id)
        if not alt:
            continue
        capacity = alt.get("vessel_capacity", 0) or 0
        if capacity <= 0:
            continue  # cannot receive ships
        distance = haversine_nm(disrupted["lat"], disrupted["lon"], alt["lat"], alt["lon"])
        utilization, util_source = get_port_utilization(alt["name"], alt.get("current_utilization", 0.70))
        risk_score = RISK_BY_IMPORTANCE.get(alt["strategic_importance"], RISK_DEFAULT)
        alternates.append({
            "port_id": alt["port_id"],
            "name": alt["name"],
            "country": alt["country"],
            "country_code": alt.get("country_code"),
            "distance_nm": distance,
            "estimated_delay_days": round(distance / SAILING_SPEED_NM_PER_DAY, 1),
            "estimated_cost_usd": round(distance * COST_PER_NM_USD * SEVERITY_COST_MULTIPLIER.get(severity, 1.2)),
            "risk_score": risk_score,
            "risk_level": RISK_LABEL[risk_score],
            "strategic_importance": alt["strategic_importance"],
            "commodities": alt.get("commodities", []),
            "port_capacity": capacity,
            "port_utilization": utilization,
            "utilization_source": util_source,
            "available_slots": round(max(capacity * (1 - utilization), 0.0), 1),
        })

    if not alternates:
        raise NoAlternatesError(f"No usable alternate port for {disrupted['name']}")

    # ── Capacity split (Gap 1) ───────────────────────────────────────────────
    per_day = ships_per_day(vessels_affected, duration_hours)
    slots = [a["available_slots"] for a in alternates]
    if sum(slots) <= 0:  # every alternate already full: share by capacity, flag below
        slots = [a["port_capacity"] for a in alternates]
    shares = split_vessels(vessels_affected, slots)
    total_slots = sum(slots)
    for alt, n, w in zip(alternates, shares, slots):
        per_day_here = per_day * max(w, 0) / total_slots
        delay, load, vc, mult = bpr_congestion_penalty(
            alt["estimated_delay_days"], per_day_here, alt["port_capacity"], alt["port_utilization"])
        alt.update({
            "vessels_diverted_here": n,
            "vessels_per_day_here": round(per_day_here, 1),
            "bpr_adjusted_delay": delay,
            "current_load": load,
            "volume_ratio": vc,
            "congestion_multiplier": mult,
            "congestion_warning": vc > CONGESTION_WARNING_VC,
            "receives_ships": n > 0,
        })

    # ── Scoring: lowest wins. Ports that receive no ships are ranked last. ──
    max_delay = max(a["bpr_adjusted_delay"] for a in alternates) or 1
    max_cost = max(a["estimated_cost_usd"] for a in alternates) or 1
    for a in alternates:
        a["score"] = round(
            SCORE_WEIGHTS["risk"] * a["risk_score"]
            + SCORE_WEIGHTS["delay"] * a["bpr_adjusted_delay"] / max_delay
            + SCORE_WEIGHTS["cost"] * a["estimated_cost_usd"] / max_cost, 4)
    alternates.sort(key=lambda a: (not a["receives_ships"], a["score"]))
    return alternates


# ── Agent ────────────────────────────────────────────────────────────────────
ROUTE_MAX_TOKENS = 400  # BUILD_PLAN section 2.

SYSTEM_PROMPT = """You are the Route Optimization Agent in SupplyPulse.
The port has ALREADY been selected by deterministic code. Do not choose a different port.
Explain, in plain language, why the code's scoring ranks the selected port first.
Use only the numbers given to you. Do not invent numbers. Do not give a confidence percentage."""


def build_user_prompt(disrupted_port_name, severity, affected_routes, alternates):
    selected = alternates[0]
    table = [{
        "name": a["name"], "country": a["country"], "distance_nm": a["distance_nm"],
        "raw_delay_days": a["estimated_delay_days"], "bpr_delay_days": a["bpr_adjusted_delay"],
        "load_vs_capacity": a["volume_ratio"], "ships_sent": a["vessels_diverted_here"],
        "cost_per_vessel_usd": a["estimated_cost_usd"], "risk": a["risk_level"], "score": a["score"],
    } for a in alternates]
    return f"""Port disruption: {disrupted_port_name} (severity {severity.upper()})
Affected routes: {', '.join(affected_routes) or 'none'}
Selected port (chosen by code, lowest score wins; score = 0.40*risk + 0.35*delay/max + 0.25*cost/max):
{selected['name']}

All alternates scored by the code:
{json.dumps(table, indent=2)}

Write:
1. WHY THIS PORT: 2 sentences explaining the code's ranking, using the numbers above.
2. ROUTE ADJUSTMENT: 1 sentence on the lane change.
3. RISK FACTORS: 2 bullet points, based only on the figures above."""


def _print_table(alternates):
    table = Table(title="Alternate Port Analysis", box=box.ROUNDED, border_style="cyan", header_style="bold cyan")
    for col, kw in [("Port", {"min_width": 25}), ("Ships", {"justify": "right"}),
                    ("Distance (nm)", {"justify": "right"}), ("Raw delay", {"justify": "right"}),
                    ("BPR delay", {"justify": "right"}), ("Load/Cap", {"justify": "right"}),
                    ("Cost/vessel", {"justify": "right"}), ("Risk", {"justify": "center"})]:
        table.add_column(col, **kw)
    for i, a in enumerate(alternates):
        warn = "⚠" if a["congestion_warning"] else "✓"
        table.add_row(f"{'★ ' if i == 0 else '  '}{a['name']}", str(a["vessels_diverted_here"]),
                      f"{a['distance_nm']:,}", f"{a['estimated_delay_days']} d",
                      f"{warn} {a['bpr_adjusted_delay']} d",
                      f"{a['volume_ratio'] * 100:.0f}% ({a['utilization_source']})",
                      f"${a['estimated_cost_usd']:,}", a["risk_level"])
    console.print(table)
    console.print("  [dim]Score: Risk 40% + BPR delay 35% + Cost 25%, lowest wins. "
                  "BPR alpha=0.15, beta=4 (U.S. Bureau of Public Roads 1964).[/dim]")


def _parse_list(value):
    return json.loads(value) if isinstance(value, str) else list(value or [])


def route_optimization_agent(state):
    console.print(Panel("[bold cyan]ROUTE OPTIMIZATION AGENT[/bold cyan]\nAnalysing alternate ports...",
                        border_style="cyan"))
    severity = state["severity"]
    affected_routes = _parse_list(state.get("affected_routes"))
    vessels_affected = int(state["vessels_affected"])
    duration_hours = float(state["duration_hours"])

    alternates = get_alternate_ports(state["nearest_port_id"], severity, vessels_affected, duration_hours)
    _print_table(alternates)

    messages = [SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=build_user_prompt(state["nearest_port_name"], severity,
                                                       affected_routes, alternates))]
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
        "vessels_affected": vessels_affected,
        "ships_per_day": round(ships_per_day(vessels_affected, duration_hours), 2),
        "duration_hours": duration_hours,
    }
