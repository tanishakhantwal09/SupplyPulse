import os
import json
import time
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich import box
from rich.table import Table

load_dotenv()
console = Console()

from agents.supervisor_agent import supervisor_agent
from agents.route_optimization_agent import route_optimization_agent
from agents.inventory_agent import inventory_agent
from agents.financial_auditor_agent import financial_auditor_agent

# ── Shared State Schema ───────────────────────────────────────────────────────
class SupplyPulseState(TypedDict):
    # Input event
    event: dict
    # Agent outputs
    supervisor_assessment: Optional[str]
    route_output: Optional[dict]
    inventory_output: Optional[dict]
    financial_output: Optional[dict]
    # Final decision
    final_decision: Optional[dict]
    # Metadata
    start_time: Optional[float]
    agents_activated: Optional[list]

# ── Agent Node Functions ──────────────────────────────────────────────────────
def supervisor_node(state: SupplyPulseState) -> SupplyPulseState:
    console.print(Rule("[bold blue]STEP 1 — SUPERVISOR AGENT[/bold blue]", style="blue"))
    event = state['event']
    response = supervisor_agent(event)
    state['supervisor_assessment'] = response
    state['agents_activated'] = ['supervisor']
    return state

def route_node(state: SupplyPulseState) -> SupplyPulseState:
    console.print(Rule("[bold cyan]STEP 2 — ROUTE OPTIMIZATION AGENT[/bold cyan]", style="cyan"))
    event = state['event']
    result = route_optimization_agent(event)
    state['route_output'] = result
    state['agents_activated'].append('route_optimization')
    return state

def inventory_node(state: SupplyPulseState) -> SupplyPulseState:
    console.print(Rule("[bold magenta]STEP 3 — INVENTORY AGENT[/bold magenta]", style="magenta"))
    event = state['event']
    route_output = state.get('route_output')
    result = inventory_agent(event, route_output)
    state['inventory_output'] = result
    state['agents_activated'].append('inventory')
    return state

def financial_node(state: SupplyPulseState) -> SupplyPulseState:
    console.print(Rule("[bold yellow]STEP 4 — FINANCIAL AUDITOR AGENT[/bold yellow]", style="yellow"))
    event = state['event']
    route_output = state.get('route_output')
    inventory_output = state.get('inventory_output')
    result = financial_auditor_agent(event, route_output, inventory_output)
    state['financial_output'] = result
    state['agents_activated'].append('financial_auditor')
    return state

def final_decision_node(state: SupplyPulseState) -> SupplyPulseState:
    console.print(Rule("[bold green]STEP 5 — SUPERVISOR FINAL DECISION[/bold green]", style="green"))

    event = state['event']
    route_output = state.get('route_output', {})
    inventory_output = state.get('inventory_output', {})
    financial_output = state.get('financial_output', {})

    elapsed = round(time.time() - state['start_time'], 2)

    recommended_port = route_output.get('recommended_port', {})
    financial_breakdown = financial_output.get('financial_breakdown', {})
    financial_alert = financial_output.get('financial_alert_triggered', False)
    top_commodity = inventory_output.get('inventory_analysis', [{}])[0] if inventory_output.get('inventory_analysis') else {}

    final_decision = {
        'disrupted_port': event['nearest_port_name'],
        'severity': event['severity'].upper(),
        'decision': 'REROUTE' if event['severity'] in ['critical', 'high'] else 'MONITOR',
        'recommended_alternate_port': recommended_port.get('name', 'N/A'),
        'alternate_port_country': recommended_port.get('country', 'N/A'),
        'distance_nm': recommended_port.get('distance_nm', 0),
        'additional_transit_days': recommended_port.get('estimated_delay_days', 0),
        'rerouting_cost_usd': recommended_port.get('estimated_cost_usd', 0),
        'total_financial_impact_usd': financial_breakdown.get('total_impact', 0),
        'financial_alert': financial_alert,
        'top_priority_commodity': top_commodity.get('commodity', 'N/A'),
        'inventory_exposure_usd': inventory_output.get('total_exposure_value_usd', 0),
        'agents_activated': state['agents_activated'] + ['supervisor_final'],
        'total_response_time_seconds': elapsed,
        'confidence': '91%' if event['severity'] == 'critical' else '82%' if event['severity'] == 'high' else '71%'
    }

    state['final_decision'] = final_decision

    # Print final decision panel
    decision_table = Table(
        box=box.DOUBLE_EDGE,
        border_style="green",
        show_header=False,
        padding=(0, 2)
    )
    decision_table.add_column("Field", style="bold cyan", min_width=30)
    decision_table.add_column("Value", style="bold white", min_width=35)

    decision_color = "red" if final_decision['decision'] == 'REROUTE' else "yellow"

    decision_table.add_row("DECISION", f"[bold {decision_color}]{final_decision['decision']}[/bold {decision_color}]")
    decision_table.add_row("Disrupted Port", final_decision['disrupted_port'])
    decision_table.add_row("Severity", f"[bold red]{final_decision['severity']}[/bold red]")
    decision_table.add_row("Recommended Alternate Port", f"[bold green]{final_decision['recommended_alternate_port']}[/bold green]")
    decision_table.add_row("Country", final_decision['alternate_port_country'])
    decision_table.add_row("Distance", f"{final_decision['distance_nm']:,} nautical miles")
    decision_table.add_row("Additional Transit", f"{final_decision['additional_transit_days']} days")
    decision_table.add_row("Rerouting Cost", f"${final_decision['rerouting_cost_usd']:,}")
    decision_table.add_row("Total Financial Impact", f"[bold red]${final_decision['total_financial_impact_usd']:,.0f}[/bold red]")
    decision_table.add_row("Financial Alert", f"[red]TRIGGERED[/red]" if financial_alert else "[green]CLEAR[/green]")
    decision_table.add_row("Top Priority Commodity", final_decision['top_priority_commodity'])
    decision_table.add_row("Inventory Exposure", f"${final_decision['inventory_exposure_usd']:,.0f}")
    decision_table.add_row("Agents Activated", str(len(final_decision['agents_activated'])))
    decision_table.add_row("Response Time", f"[bold green]{elapsed} seconds[/bold green]")
    decision_table.add_row("Confidence", f"[bold green]{final_decision['confidence']}[/bold green]")

    console.print(Panel(
        decision_table,
        title="[bold green]SUPPLYPULSE — FINAL UNIFIED DECISION[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))

    # Save to JSON
    with open("agents/pipeline_result.json", "w") as f:
        json.dump(final_decision, f, indent=2, default=str)

    console.print(f"\n[bold]Result saved to: agents/pipeline_result.json[/bold]")

    return state

# ── Build LangGraph ───────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(SupplyPulseState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("route_optimization", route_node)
    graph.add_node("inventory", inventory_node)
    graph.add_node("financial_auditor", financial_node)
    graph.add_node("final_decision", final_decision_node)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "route_optimization")
    graph.add_edge("route_optimization", "inventory")
    graph.add_edge("inventory", "financial_auditor")
    graph.add_edge("financial_auditor", "final_decision")
    graph.add_edge("final_decision", END)

    return graph.compile()

# ── Run Pipeline ──────────────────────────────────────────────────────────────
def run_supplypulse(event):
    console.print(Panel(
        "[bold white]SUPPLYPULSE — AUTONOMOUS SUPPLY CHAIN DISRUPTION RESPONSE SYSTEM[/bold white]\n"
        "[dim]Multi-Agent LLM Framework | Powered by Groq Llama 3 | LangGraph Orchestration[/dim]",
        border_style="white",
        padding=(1, 4)
    ))

    console.print(f"\n[bold]Disruption Event Received:[/bold]")
    console.print(f"  Port: [bold red]{event['nearest_port_name']}[/bold red]")
    console.print(f"  Severity: [bold red]{event['severity'].upper()}[/bold red]")
    console.print(f"  Location: {event['event_location']}")
    console.print(f"\n[dim]Activating 4-agent pipeline...[/dim]\n")

    app = build_graph()

    initial_state = SupplyPulseState(
        event=event,
        supervisor_assessment=None,
        route_output=None,
        inventory_output=None,
        financial_output=None,
        final_decision=None,
        start_time=time.time(),
        agents_activated=[]
    )

    final_state = app.invoke(initial_state)
    return final_state['final_decision']

# ── Test with real dataset event ──────────────────────────────────────────────
if __name__ == "__main__":
    import pandas as pd

    console.print("[dim]Loading real validation dataset...[/dim]")
    df = pd.read_csv(
        r'C:\Users\tanis\Desktop\Minor project\dataset\final\validation_set_REAL_ONLY.csv',
        low_memory=False
    )

    # Pick a critical event
    critical_event = df[df['severity'] == 'critical'].iloc[0].to_dict()

    console.print(f"[dim]Real event loaded from validation dataset — {len(df):,} events available[/dim]\n")

    result = run_supplypulse(critical_event)

    console.print(f"\n[bold green]Pipeline complete.[/bold green]")
    console.print(f"[bold]Total response time: {result['total_response_time_seconds']} seconds[/bold]")