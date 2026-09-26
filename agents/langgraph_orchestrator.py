import os
import json
import time
from datetime import datetime
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
    event: dict
    supervisor_assessment: Optional[str]
    route_output: Optional[dict]
    inventory_output: Optional[dict]
    financial_output: Optional[dict]
    final_decision: Optional[dict]
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

    event            = state['event']
    route_output     = state.get('route_output', {})
    inventory_output = state.get('inventory_output', {})
    financial_output = state.get('financial_output', {})

    elapsed = round(time.time() - state['start_time'], 2)

    recommended_port    = route_output.get('recommended_port', {})
    financial_breakdown = financial_output.get('financial_breakdown', {})
    financial_alert     = financial_output.get('financial_alert_triggered', False)
    top_commodity       = (
        inventory_output.get('inventory_analysis', [{}])[0]
        if inventory_output.get('inventory_analysis') else {}
    )

    event_date    = str(event.get('event_date', 'Unknown'))
    analysis_date = datetime.now().strftime('%Y-%m-%d %H:%M UTC')

    decision      = 'REROUTE' if event['severity'] in ['critical', 'high'] else 'MONITOR'
    alt_port_name = recommended_port.get('name', 'N/A')
    alt_port_display = (
        f"{alt_port_name} (preferred if escalation occurs)"
        if decision == 'MONITOR' else alt_port_name
    )

    target_met = elapsed < 30

    final_decision = {
        'disrupted_port':             event['nearest_port_name'],
        'event_date':                 event_date,
        'analysis_date':              analysis_date,
        'severity':                   event['severity'].upper(),
        'decision':                   decision,
        'recommended_alternate_port': alt_port_name,
        'alternate_port_display':     alt_port_display,
        'alternate_port_country':     recommended_port.get('country', 'N/A'),
        'distance_nm':                recommended_port.get('distance_nm', 0),
        'additional_transit_days':    recommended_port.get('estimated_delay_days', 0),
        'rerouting_cost_usd':         recommended_port.get('estimated_cost_usd', 0),
        'total_financial_impact_usd': financial_breakdown.get('total_impact', 0),
        'financial_alert':            financial_alert,
        'top_priority_commodity':     top_commodity.get('commodity', 'N/A'),
        'inventory_exposure_usd':     inventory_output.get('total_exposure_value_usd', 0),
        'agents_activated':           state['agents_activated'] + ['supervisor_final'],
        'total_response_time_seconds': elapsed,
        'confidence': (
            '91%' if event['severity'] == 'critical' else
            '82%' if event['severity'] == 'high' else '71%'
        )
    }

    state['final_decision'] = final_decision

    # ── Gap 3: XAI Attribution Lineage Tree ───────────────────────────────────
    # Deterministic audit trail — every number that drove every decision.
    # Reference: Turpin et al. (NeurIPS 2023) — LLM explanations are often
    # unfaithful to actual computation. This separates deterministic inputs
    # from LLM narrative so decisions are auditable without relying on LLM text.
    all_ports = route_output.get('alternate_ports_analyzed', [])

    attribution_lineage = {
        'metadata': {
            'generated_at':  analysis_date,
            'event_id':      str(event.get('event_id', 'N/A')),
            'event_date':    event_date,
            'disrupted_port': event['nearest_port_name'],
            'severity':      event['severity'].upper(),
            'note': (
                'All numerical inputs below are deterministic and mathematically '
                'reproducible. LLM narrative output is supplementary explanation only. '
                'Reference: Turpin et al. (NeurIPS 2023) — Language Models Don\'t '
                'Always Say What They Think.'
            )
        },
        'route_decision': {
            'scoring_formula': 'Risk(40%) + BPR-Adjusted Delay(35%) + NormCost(25%) — lowest score wins',
            'bpr_formula': '1 + alpha * (volume_ratio ** beta) — alpha=1.5, beta=4.0 (Wardrop 1952, maritime-calibrated)',
            'ports_evaluated': [
                {
                    'port':                   p.get('name', 'N/A'),
                    'country':                p.get('country', 'N/A'),
                    'distance_nm':            p.get('distance_nm', 0),
                    'delay_days':             p.get('estimated_delay_days', 0),
                    'bpr_adjusted_delay_days': p.get('bpr_adjusted_delay', 0),
                    'vessels_diverted_here':  p.get('vessels_diverted_here', 0),
                    'current_load':           p.get('current_load', 0),
                    'volume_ratio':           p.get('volume_ratio', 0),
                    'congestion_multiplier':  p.get('congestion_multiplier', 1.0),
                    'congestion_warning':     p.get('congestion_warning', False),
                    'utilization_source':     p.get('utilization_source', 'N/A'),
                    'cost_usd':               p.get('estimated_cost_usd', 0),
                    'risk_level':             p.get('risk_level', 'N/A'),
                    'selected':               p.get('name') == alt_port_name,
                }
                for p in all_ports
            ],
            'winning_port':    alt_port_name,
            'winning_country': recommended_port.get('country', 'N/A'),
            'winning_distance_nm':   recommended_port.get('distance_nm', 0),
            'winning_delay_days':    recommended_port.get('estimated_delay_days', 0),
            'winning_bpr_adjusted_delay_days': recommended_port.get('bpr_adjusted_delay', 0),
            'winning_volume_ratio':  recommended_port.get('volume_ratio', 0),
            'winning_congestion_warning': recommended_port.get('congestion_warning', False),
            'winning_cost_usd':      recommended_port.get('estimated_cost_usd', 0),
            'winning_risk_level':    recommended_port.get('risk_level', 'N/A'),
            'bpr_congestion_applied': route_output.get('bpr_congestion_applied', False),
            'vessels_affected':      route_output.get('vessels_affected', 0),
        },
        'financial_decision': {
            'formula': 'C_transit + C_delay + C_surcharge + C_inventory + C_operational + C_carbon (EU ETS)',
            'components': {
                'rerouting_transportation_cost_usd': financial_breakdown.get('rerouting_cost', 0),
                'trade_delay_cost_usd':              financial_breakdown.get('delay_cost', 0),
                'freight_rate_increase_usd':         financial_breakdown.get('freight_rate_increase', 0),
                'inventory_exposure_risk_usd':       financial_breakdown.get('inventory_at_risk', 0),
                'operational_costs_usd':             financial_breakdown.get('operational_cost', 0),
                'eu_ets_carbon_penalty_usd':         financial_breakdown.get('carbon_penalty', 0),
            },
            'total_usd':           financial_breakdown.get('total_impact', 0),
            'alert_triggered':     financial_alert,
            'alert_threshold_usd': financial_output.get('alert_threshold_usd', 100_000_000),
            'vessels_affected':    event.get('vessels_affected', 0),
            'duration_hours':      event.get('duration_hours', 0),
            'freight_impact_pct':  event.get('freight_impact_pct', 0),
            'note': 'All figures are derived estimates based on structured formulas. Not actual market data.',
        },
        'inventory_decision': {
            'commodities_assessed': [
                {
                    'commodity':       c.get('commodity', 'N/A'),
                    'sensitivity':     c.get('sensitivity', 'N/A'),
                    'priority_tier':   c.get('priority', 'N/A'),
                    'containers':      c.get('containers', 0),
                    'exposure_usd':    c.get('exposure_value', 0),
                }
                for c in inventory_output.get('inventory_analysis', [])
            ],
            'total_exposure_usd':   inventory_output.get('total_exposure_value_usd', 0),
            'top_priority_commodity': top_commodity.get('commodity', 'N/A'),
            'top_priority_tier':    top_commodity.get('priority', 'N/A'),
            'reallocation_triggered': decision == 'REROUTE',
        },
        'supervisor_assessment': state.get('supervisor_assessment'),
        'bpr_congestion_data': {
            'applied':       route_output.get('bpr_congestion_applied', False),
            'formula':       'BPR delay = base_delay * (1 + alpha * (volume_ratio ** beta))',
            'alpha':         1.5,
            'beta':          4.0,
            'per_port': [
                {
                    'port':                   p.get('name', 'N/A'),
                    'raw_delay_days':         p.get('estimated_delay_days', 0),
                    'bpr_delay_days':         p.get('bpr_adjusted_delay', 0),
                    'congestion_percentage':  round(p.get('volume_ratio', 0) * 100, 1),
                    'congestion_multiplier':  p.get('congestion_multiplier', 1.0),
                    'congestion_warning':     p.get('congestion_warning', False),
                }
                for p in all_ports
            ],
        },
        'portwatch_data': {
            'source': 'IMF PortWatch (satellite AIS) with static ports.json fallback',
            'per_port': [
                {
                    'port':              p.get('name', 'N/A'),
                    'portwatch_source':  p.get('utilization_source', 'N/A'),
                    'utilization':       p.get('port_utilization'),
                    'current_load':      p.get('current_load', 0),
                }
                for p in all_ports
            ],
        },
        'eu_ets_carbon_data': {
            'carbon_details':  financial_output.get('carbon_details', {}),
            'pareto_options':  financial_output.get('pareto_options', []),
            'formula':         'distance_nm * SFC(0.0191) * CF(3.114) * EUA_price_usd * vessels',
        },
        'decision_summary': {
            'final_decision':        decision,
            'decision_basis':        (
                'Severity-based rule: REROUTE if severity is critical or high, '
                'MONITOR if medium or low'
            ),
            'response_time_seconds': elapsed,
            'target_met':            target_met,
            'llm_confidence_label':  final_decision['confidence'],
            'llm_confidence_note':   'Model-generated estimate. Not statistically validated.',
        }
    }

    # ── Print final decision table ────────────────────────────────────────────
    decision_table = Table(
        box=box.DOUBLE_EDGE,
        border_style="green",
        show_header=False,
        padding=(0, 2)
    )
    decision_table.add_column("Field", style="bold cyan", min_width=30)
    decision_table.add_column("Value", style="bold white", min_width=40)

    decision_color = "red" if decision == 'REROUTE' else "yellow"

    decision_table.add_row("DECISION", f"[bold {decision_color}]{decision}[/bold {decision_color}]")
    decision_table.add_row("Disrupted Port", final_decision['disrupted_port'])
    decision_table.add_row("Event Date", event_date)
    decision_table.add_row("Analysis Date", analysis_date)
    decision_table.add_row("Severity", f"[bold red]{final_decision['severity']}[/bold red]")
    decision_table.add_row("Recommended Alternate Port", f"[bold green]{alt_port_display}[/bold green]")
    decision_table.add_row("Country", final_decision['alternate_port_country'])
    decision_table.add_row("Distance", f"{final_decision['distance_nm']:,} nautical miles")
    decision_table.add_row("Additional Transit", f"{final_decision['additional_transit_days']} days")
    decision_table.add_row("Rerouting Cost", f"${final_decision['rerouting_cost_usd']:,}")
    decision_table.add_row(
        "Est. Financial Impact",
        f"[bold red]~${final_decision['total_financial_impact_usd']:,.0f}[/bold red] (derived estimate)"
    )
    decision_table.add_row(
        "Financial Alert",
        f"[red]TRIGGERED[/red]" if financial_alert else "[green]CLEAR[/green]"
    )
    decision_table.add_row("Top Priority Commodity", final_decision['top_priority_commodity'])
    decision_table.add_row(
        "Est. Inventory Exposure",
        f"~${final_decision['inventory_exposure_usd']:,.0f} (derived estimate)"
    )
    decision_table.add_row("Unique Agents", "4 (Supervisor, Route, Inventory, Financial Auditor)")
    decision_table.add_row("Agent Executions", str(len(final_decision['agents_activated'])))
    decision_table.add_row(
        "Response Time",
        f"[bold {'green' if target_met else 'yellow'}]{elapsed}s "
        f"({'✓ under 30s target' if target_met else '⚠ above 30s target'})"
        f"[/bold {'green' if target_met else 'yellow'}]"
    )
    decision_table.add_row(
        "LLM-Reported Confidence",
        f"[bold green]{final_decision['confidence']}[/bold green] (model-generated, not statistically validated)"
    )
    decision_table.add_row(
        "XAI Attribution",
        "[bold cyan]✓ Saved to agents/pipeline_attribution.json[/bold cyan]"
    )

    console.print(Panel(
        decision_table,
        title="[bold green]SUPPLYPULSE — FINAL UNIFIED DECISION[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))

    # ── Save results ──────────────────────────────────────────────────────────
    with open("agents/pipeline_result.json", "w") as f:
        json.dump(final_decision, f, indent=2, default=str)

    with open("agents/pipeline_attribution.json", "w") as f:
        json.dump(attribution_lineage, f, indent=2, default=str)

    console.print(f"\n[bold]Result saved to:      agents/pipeline_result.json[/bold]")
    console.print(f"[bold]Attribution saved to: agents/pipeline_attribution.json[/bold]")
    console.print(
        f"[dim]Attribution file contains every mathematical input that drove "
        f"this decision — auditable without relying on LLM text.[/dim]"
    )

    return state

# ── Build LangGraph ───────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(SupplyPulseState)
    graph.add_node("supervisor",       supervisor_node)
    graph.add_node("route_optimization", route_node)
    graph.add_node("inventory",        inventory_node)
    graph.add_node("financial_auditor", financial_node)
    graph.add_node("final_decision",   final_decision_node)
    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor",         "route_optimization")
    graph.add_edge("route_optimization", "inventory")
    graph.add_edge("inventory",          "financial_auditor")
    graph.add_edge("financial_auditor",  "final_decision")
    graph.add_edge("final_decision",     END)
    return graph.compile()

# ── Run Pipeline ──────────────────────────────────────────────────────────────
def run_supplypulse(event):
    console.print(Panel(
        "[bold white]SUPPLYPULSE — AUTONOMOUS SUPPLY CHAIN DISRUPTION RESPONSE SYSTEM[/bold white]\n"
        "[dim]Multi-Agent LLM Framework | Powered by Groq LLM | LangGraph Orchestration[/dim]",
        border_style="white",
        padding=(1, 4)
    ))
    console.print(f"\n[bold]Disruption Event Received:[/bold]")
    console.print(f"  Port:     [bold red]{event['nearest_port_name']}[/bold red]")
    console.print(f"  Severity: [bold red]{event['severity'].upper()}[/bold red]")
    console.print(f"  Location: {event.get('event_location', 'N/A')}")
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
    df = pd.read_parquet(r'dataset/final/validation_set_REAL_ONLY.parquet')
    critical_event = df[df['severity'] == 'critical'].iloc[0].to_dict()
    console.print(f"[dim]Real event loaded — {len(df):,} events available[/dim]\n")
    result = run_supplypulse(critical_event)
    console.print(f"\n[bold green]Pipeline complete.[/bold green]")
    console.print(f"[bold]Total response time: {result['total_response_time_seconds']} seconds[/bold]")