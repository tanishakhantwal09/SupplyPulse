import os
import json
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
    model_name="llama-3.3-70b-versatile",
    temperature=0.1
)

with open("dataset/reference/commodities.json") as f:
    commodities = json.load(f)

with open("dataset/reference/ports.json") as f:
    ports = json.load(f)

def get_commodity_details(affected_commodities):
    details = []
    for commodity in commodities:
        for affected in affected_commodities:
            if affected.lower() in commodity['name'].lower() or \
               any(affected.lower() in sub.lower() for sub in commodity.get('subcategories', [])):
                details.append(commodity)
                break
    return details[:4]

def calculate_exposure(commodity, severity, vessels_affected):
    avg_value = commodity.get('avg_value_per_container_usd', 50000)
    containers_per_vessel = {'critical': 800, 'high': 400, 'medium': 200, 'low': 100}.get(severity, 200)
    total_containers = vessels_affected * containers_per_vessel
    sensitivity_multiplier = {'critical': 0.9, 'high': 0.7, 'medium': 0.4, 'low': 0.2}.get(
        commodity.get('supply_chain_sensitivity', 'medium'), 0.4
    )
    exposed_containers = round(total_containers * sensitivity_multiplier)
    exposure_value = exposed_containers * avg_value
    return exposed_containers, exposure_value

def inventory_agent(state, route_agent_output=None):
    console.print(Panel(
        "[bold magenta]INVENTORY AGENT[/bold magenta]\nAnalyzing commodity exposure and reallocation requirements...",
        border_style="magenta"
    ))

    severity = state['severity']
    vessels_affected = int(state.get('vessels_affected', 50))
    affected_commodities = json.loads(state['affected_commodities']) \
        if isinstance(state['affected_commodities'], str) \
        else state['affected_commodities']
    disrupted_port = state['nearest_port_name']

    recommended_port = None
    if route_agent_output and route_agent_output.get('recommended_port'):
        recommended_port = route_agent_output['recommended_port']['name']

    console.print(f"  [yellow]→[/yellow] Disrupted port: [bold]{disrupted_port}[/bold]")
    console.print(f"  [yellow]→[/yellow] Vessels affected: [bold]{vessels_affected}[/bold]")
    console.print(f"  [yellow]→[/yellow] At-risk commodities: {', '.join(affected_commodities)}")
    if recommended_port:
        console.print(f"  [yellow]→[/yellow] Rerouting to: [bold green]{recommended_port}[/bold green] (from Route Agent)")

    commodity_details = get_commodity_details(affected_commodities)

    inventory_table = Table(
        title="Commodity Exposure Analysis",
        box=box.ROUNDED,
        border_style="magenta",
        header_style="bold magenta"
    )
    inventory_table.add_column("Commodity", style="bold white", min_width=28)
    inventory_table.add_column("Sensitivity", justify="center", min_width=12)
    inventory_table.add_column("Exposed Containers", justify="right", min_width=18)
    inventory_table.add_column("Exposure Value", justify="right", min_width=18)
    inventory_table.add_column("Priority", justify="center", min_width=10)

    inventory_analysis = []
    total_exposure_value = 0

    for commodity in commodity_details:
        exposed_containers, exposure_value = calculate_exposure(commodity, severity, vessels_affected)
        total_exposure_value += exposure_value

        sensitivity = commodity.get('supply_chain_sensitivity', 'medium')
        priority = {'critical': 'P1', 'high': 'P2', 'medium': 'P3', 'low': 'P4'}.get(sensitivity, 'P3')
        priority_color = {'P1': 'red', 'P2': 'yellow', 'P3': 'cyan', 'P4': 'green'}.get(priority, 'white')
        sensitivity_color = {'critical': 'red', 'high': 'yellow', 'medium': 'cyan', 'low': 'green'}.get(sensitivity, 'white')

        inventory_table.add_row(
            commodity['name'],
            f"[{sensitivity_color}]{sensitivity.upper()}[/{sensitivity_color}]",
            f"{exposed_containers:,}",
            f"${exposure_value:,.0f}",
            f"[{priority_color}]{priority}[/{priority_color}]"
        )

        inventory_analysis.append({
            'commodity': commodity['name'],
            'sensitivity': sensitivity,
            'exposed_containers': exposed_containers,
            'exposure_value_usd': exposure_value,
            'priority': priority,
            'typical_disruption_days': commodity.get('typical_disruption_impact_days', 14),
            'reallocation_ports': commodity.get('primary_import_ports', [])[:2]
        })

    console.print(inventory_table)
    console.print(f"\n  [bold magenta]Total inventory exposure: [red]${total_exposure_value:,.0f}[/red][/bold magenta]")

    system_prompt = """You are the Inventory Agent in SupplyPulse, a supply chain disruption management system.

Your role is to analyze commodity exposure during port disruptions and recommend inventory reallocation strategies.
You receive data from the Route Optimization Agent about recommended alternate ports.
Base your reallocation recommendations on the actual data provided.
Be specific, use the actual numbers, and keep recommendations concise."""

    user_prompt = f"""
Port disruption: {disrupted_port} — Severity: {severity.upper()}
Vessels affected: {vessels_affected}
Recommended alternate port: {recommended_port or 'To be determined'}

Commodity exposure analysis:
{json.dumps(inventory_analysis, indent=2)}

Total inventory at risk: ${total_exposure_value:,.0f}

Provide:
1. TOP PRIORITY ACTION: Which commodity needs immediate reallocation and why (2 sentences)
2. REALLOCATION PLAN: Specific quantities and destination for top 2 commodities (bullet points)
3. SHORTAGE RISK: Which regions face supply shortage if rerouting is delayed (1-2 regions)
4. TIMELINE: How many days before shortage becomes critical

Use the actual numbers from the analysis above.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    console.print(f"\n  [yellow]→[/yellow] Querying Groq LLM for reallocation strategy...")
    response = llm.invoke(messages)

    result = {
        'inventory_analysis': inventory_analysis,
        'total_exposure_value_usd': total_exposure_value,
        'llm_reasoning': response.content,
        'agent': 'inventory'
    }

    console.print(Panel(
        f"[bold green]INVENTORY REALLOCATION STRATEGY:[/bold green]\n{response.content}",
        border_style="green",
        title="Inventory Agent — Output"
    ))

    return result

if __name__ == "__main__":
    test_event = {
        'nearest_port_id': 'P001',
        'nearest_port_name': 'Port of Shanghai',
        'severity': 'critical',
        'affected_routes': '["R001", "R003", "R005"]',
        'affected_commodities': '["electronics", "textiles", "machinery"]',
        'vessels_affected': 350,
        'event_location': 'Shanghai, China'
    }

    test_route_output = {
        'recommended_port': {
            'name': 'Port of Busan',
            'country': 'South Korea',
            'distance_nm': 449.3,
            'estimated_delay_days': 1.1,
            'estimated_cost_usd': 36393
        }
    }

    result = inventory_agent(test_event, test_route_output)