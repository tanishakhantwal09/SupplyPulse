import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import math
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

load_dotenv()
console = Console()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="openai/gpt-oss-20b",
    temperature=0.1,
    max_tokens=400
)

with open("dataset/reference/ports.json") as f:
    ports = json.load(f)
with open("dataset/reference/routes.json") as f:
    routes = json.load(f)

# ── Retry with backoff ────────────────────────────────────────────────────────
def invoke_with_retry(llm, messages, max_retries=3):
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as e:
            if '429' in str(e) and attempt < max_retries - 1:
                wait = 60 * (attempt + 1)
                console.print(f"  [yellow]Rate limit hit — waiting {wait}s before retry {attempt+2}/{max_retries}...[/yellow]")
                time.sleep(wait)
            else:
                raise e

def haversine_nm(lat1, lon1, lat2, lon2):
    R = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return round(2 * R * math.asin(math.sqrt(a)), 1)

def bpr_congestion_penalty(
    base_delay: float,
    vessels_diverted: int,
    port_capacity: int,
    current_utilization: float,
    alpha: float = 1.5,
    beta: float = 4.0
):
    """
    Gap 1: Bureau of Public Roads Congestion Formula
    Adapted for maritime berth and anchorage saturation.
    Prevents the Herd Effect in unconstrained multi-agent routing.
    alpha=1.5 calibrated for maritime (road BPR uses 0.15 — maritime is 10x more severe)
    beta=4.0 standard non-linear exponent
    Reference: Wardrop J.G. (1952) — Some Theoretical Aspects of Road Traffic Research
    """
    if port_capacity <= 0:
        return base_delay, 0, 1.0, 1.0
    current_load = round(port_capacity * current_utilization)
    total_volume = current_load + vessels_diverted
    volume_ratio = total_volume / port_capacity
    congestion_mult = 1.0 + alpha * (volume_ratio ** beta)
    adjusted_delay = round(base_delay * congestion_mult, 2)
    return adjusted_delay, current_load, round(volume_ratio, 3), round(congestion_mult, 2)

def get_alternate_ports(disrupted_port_id, severity, vessels_affected=0):
    disrupted = next((p for p in ports if p['port_id'] == disrupted_port_id), None)
    if not disrupted:
        return []

    alternates = []
    for alt_id in disrupted.get('alternate_ports', []):
        alt_port = next((p for p in ports if p['port_id'] == alt_id), None)
        if alt_port:
            distance = haversine_nm(
                disrupted['lat'], disrupted['lon'],
                alt_port['lat'], alt_port['lon']
            )
            delay_days = round(distance / 400, 1)

            severity_cost_multiplier = {
                'critical': 1.8, 'high': 1.4, 'medium': 1.2, 'low': 1.0
            }.get(severity, 1.2)

            base_cost      = distance * 45
            estimated_cost = round(base_cost * severity_cost_multiplier)

            risk = (
                'Low'    if alt_port['strategic_importance'] == 'critical' else
                'Medium' if alt_port['strategic_importance'] == 'high'     else
                'High'
            )

            port_capacity    = alt_port.get('vessel_capacity', 0)
            port_utilization = alt_port.get('current_utilization', 0)
            current_load     = round(port_capacity * port_utilization)
            available_slots  = max(port_capacity - current_load, 0)

            alternates.append({
                'port_id':              alt_port['port_id'],
                'name':                 alt_port['name'],
                'country':              alt_port['country'],
                'distance_nm':          distance,
                'estimated_delay_days': delay_days,
                'estimated_cost_usd':   estimated_cost,
                'risk_level':           risk,
                'strategic_importance': alt_port['strategic_importance'],
                'commodities':          alt_port.get('commodities', []),
                'port_capacity':        port_capacity,
                'port_utilization':     port_utilization,
                'available_slots':      available_slots,
            })

    if not alternates:
        return []

    # ── Gap 1: Proportional vessel distribution — NOT all vessels to every port ──
    # Each alternate absorbs rerouted volume proportional to its available slack
    # (capacity - current load), not the full disrupted fleet broadcast to all.
    total_available_capacity = sum(a['available_slots'] for a in alternates) or 1
    for alt in alternates:
        proportion         = alt['available_slots'] / total_available_capacity
        vessels_this_port  = round(vessels_affected * proportion)

        bpr_adjusted_delay, current_load, volume_ratio, congestion_mult = bpr_congestion_penalty(
            alt['estimated_delay_days'],
            vessels_this_port,
            alt['port_capacity'],
            alt['port_utilization']
        )

        alt['bpr_adjusted_delay']    = bpr_adjusted_delay
        alt['vessels_diverted_here'] = vessels_this_port
        alt['current_load']          = current_load
        alt['volume_ratio']          = volume_ratio
        alt['congestion_multiplier'] = congestion_mult
        alt['congestion_warning']    = volume_ratio > 0.90

    # ── Weighted scoring — OUTSIDE the for loop ───────────────────────────────
    # Risk 40% + BPR-adjusted Delay 35% + Cost 25% — lowest score wins
    max_delay = max(a['bpr_adjusted_delay'] for a in alternates) or 1
    max_cost  = max(a['estimated_cost_usd']  for a in alternates) or 1

    alternates.sort(key=lambda alt: (
        0.40 * {'Low': 0, 'Medium': 1, 'High': 2}[alt['risk_level']] +
        0.35 * (alt['bpr_adjusted_delay'] / max_delay) +
        0.25 * (alt['estimated_cost_usd']  / max_cost)
    ))

    return alternates[:3]


def route_optimization_agent(state):
    console.print(Panel(
        "[bold cyan]ROUTE OPTIMIZATION AGENT[/bold cyan]\nAnalyzing alternate shipping routes...",
        border_style="cyan"
    ))

    disrupted_port_id   = state['nearest_port_id']
    disrupted_port_name = state['nearest_port_name']
    severity            = state['severity']
    affected_routes     = (
        json.loads(state['affected_routes'])
        if isinstance(state['affected_routes'], str)
        else state['affected_routes']
    )

    vessels_affected = int(state.get('vessels_affected', 0))

    console.print(f"  [yellow]→[/yellow] Disrupted port: [bold]{disrupted_port_name}[/bold]")
    console.print(f"  [yellow]→[/yellow] Severity: [bold red]{severity.upper()}[/bold red]")
    console.print(f"  [yellow]→[/yellow] Affected routes: {', '.join(affected_routes)}")
    console.print(f"  [yellow]→[/yellow] Vessels affected: [bold]{vessels_affected}[/bold]")
    console.print(f"  [yellow]→[/yellow] Querying alternate ports from reference database...")

    alternates = get_alternate_ports(disrupted_port_id, severity, vessels_affected)

    if alternates:
        table = Table(
            title="Alternate Port Analysis",
            box=box.ROUNDED,
            border_style="cyan",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Port",           style="bold white", min_width=25)
        table.add_column("Country",        min_width=12)
        table.add_column("Distance (nm)",  justify="right", min_width=14)
        table.add_column("Est. Delay",     justify="right", min_width=10)
        table.add_column("BPR Delay",      justify="right", min_width=12)
        table.add_column("Congestion",     justify="right", min_width=12)
        table.add_column("Est. Cost (USD)", justify="right", min_width=15)
        table.add_column("Risk",           justify="center", min_width=8)

        for i, alt in enumerate(alternates):
            risk_color = {'Low': 'green', 'Medium': 'yellow', 'High': 'red'}.get(alt['risk_level'], 'white')
            marker = "★ " if i == 0 else "  "
            bpr_marker = "⚠" if alt['congestion_warning'] else "✓"
            congestion_color = "red" if alt['congestion_warning'] else "green"
            table.add_row(
                f"{marker}{alt['name']}",
                alt['country'],
                f"{alt['distance_nm']:,}",
                f"{alt['estimated_delay_days']} days",
                f"{bpr_marker} {alt['bpr_adjusted_delay']} days",
                f"[{congestion_color}]{alt['volume_ratio'] * 100:.0f}% full[/{congestion_color}]",
                f"${alt['estimated_cost_usd']:,}",
                f"[{risk_color}]{alt['risk_level']}[/{risk_color}]"
            )

        console.print(table)
        console.print(f"  [dim]Port scoring: Risk 40% + BPR Delay 35% + Cost 25% — lowest score wins[/dim]")
        console.print(f"  [dim]Gap 1 BPR: Congestion-adjusted delays prevent herd effect — Wardrop 1952[/dim]")

    system_prompt = """You are the Route Optimization Agent in SupplyPulse.
Analyze port disruptions and recommend optimal rerouting.
Be concise and data-driven. Reference actual port names and figures provided."""

    user_prompt = f"""
Port disruption: {disrupted_port_name} — Severity: {severity.upper()}
Affected routes: {', '.join(affected_routes)}
Alternate ports analyzed:
{json.dumps([{
    'name': a['name'],
    'country': a['country'],
    'distance_nm': a['distance_nm'],
    'delay_days': a['estimated_delay_days'],
    'cost_usd': a['estimated_cost_usd'],
    'risk': a['risk_level']
} for a in alternates], indent=2)}

Provide:
1. RECOMMENDED PORT: Which port and why (2 sentences max)
2. ROUTE ADJUSTMENT: What lane adjustment needed (1 sentence)
3. RISK FACTORS: 2 key risks (bullet points)
4. CONFIDENCE: Percentage confidence in recommendation
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    console.print(f"\n  [yellow]→[/yellow] Querying Groq LLM for routing recommendation...")
    response = invoke_with_retry(llm, messages)

    recommended = alternates[0] if alternates else None

    result = {
        'alternate_ports_analyzed':  alternates,
        'recommended_port':          recommended,
        'llm_reasoning':             response.content,
        'agent':                     'route_optimization',
        'bpr_congestion_applied':    True,
        'vessels_affected':          vessels_affected,
    }

    console.print(Panel(
        f"[bold green]ROUTE RECOMMENDATION:[/bold green]\n{response.content}",
        border_style="green",
        title="Route Optimization Agent — Output"
    ))

    return result


if __name__ == "__main__":
    test_event = {
        'nearest_port_id':   'P001',
        'nearest_port_name': 'Port of Shanghai',
        'severity':          'critical',
        'affected_routes':   '["R001", "R003", "R005"]',
        'event_location':    'Shanghai, China'
    }

    result = route_optimization_agent(test_event)
    console.print(f"\n[bold]Recommended alternate: {result['recommended_port']['name']}[/bold]")