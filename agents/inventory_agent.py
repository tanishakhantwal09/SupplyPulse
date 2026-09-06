import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
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

with open("dataset/reference/commodities.json") as f:
    commodities = json.load(f)
with open("dataset/reference/ports.json") as f:
    ports = json.load(f)

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
    avg_value          = commodity.get('avg_value_per_container_usd', 50000)
    containers_per_vessel = {
        'critical': 800, 'high': 400, 'medium': 200, 'low': 100
    }.get(severity, 200)
    total_containers   = vessels_affected * containers_per_vessel
    sensitivity_multiplier = {
        'critical': 0.9, 'high': 0.7, 'medium': 0.4, 'low': 0.2
    }.get(commodity.get('supply_chain_sensitivity', 'medium'), 0.4)
    exposed_containers = round(total_containers * sensitivity_multiplier)
    exposure_value     = exposed_containers * avg_value
    return exposed_containers, exposure_value

def inventory_agent(state, route_agent_output=None):
    console.print(Panel(
        "[bold magenta]INVENTORY AGENT[/bold magenta]\nAnalyzing commodity exposure and reallocation requirements...",
        border_style="magenta"
    ))

    severity             = state['severity']
    vessels_affected     = int(state.get('vessels_affected', 50))
    affected_commodities = (
        json.loads(state['affected_commodities'])
        if isinstance(state['affected_commodities'], str)
        else state['affected_commodities']
    )
    disrupted_port   = state['nearest_port_name']
    recommended_port = None

    if route_agent_output and route_agent_output.get('recommended_port'):
        recommended_port = route_agent_output['recommended_port']['name']

    console.print(f"  [yellow]→[/yellow] Disrupted port: [bold]{disrupted_port}[/bold]")
    console.print(f"  [yellow]→[/yellow] Vessels affected: [bold]{vessels_affected}[/bold]")
    console.print(f"  [yellow]→[/yellow] At-risk commodities: {', '.join(affected_commodities)}")
    if recommended_port:
        console.print(
            f"  [yellow]→[/yellow] Rerouting to: [bold green]{recommended_port}[/bold green] "
            f"(algorithmically selected by Route Agent — Risk 40% / Delay 35% / Cost 25%)"
        )

    commodity_details = get_commodity_details(affected_commodities)

    inventory_table = Table(
        title="Commodity Exposure Analysis",
        box=box.ROUNDED,
        border_style="magenta",
        header_style="bold magenta"
    )
    inventory_table.add_column("Commodity",           style="bold white", min_width=28)
    inventory_table.add_column("Sensitivity",         justify="center",   min_width=12)
    inventory_table.add_column("Exposed Containers",  justify="right",    min_width=18)
    inventory_table.add_column("Exposure Value",      justify="right",    min_width=18)
    inventory_table.add_column("Priority",            justify="center",   min_width=10)

    inventory_analysis   = []
    total_exposure_value = 0

    for commodity in commodity_details:
        exposed_containers, exposure_value = calculate_exposure(commodity, severity, vessels_affected)
        total_exposure_value += exposure_value

        sensitivity   = commodity.get('supply_chain_sensitivity', 'medium')
        priority      = {'critical': 'P1', 'high': 'P2', 'medium': 'P3', 'low': 'P4'}.get(sensitivity, 'P3')
        p_color       = {'P1': 'red', 'P2': 'yellow', 'P3': 'cyan', 'P4': 'green'}.get(priority, 'white')
        s_color       = {'critical': 'red', 'high': 'yellow', 'medium': 'cyan', 'low': 'green'}.get(sensitivity, 'white')

        inventory_table.add_row(
            commodity['name'],
            f"[{s_color}]{sensitivity.upper()}[/{s_color}]",
            f"{exposed_containers:,}",
            f"${exposure_value:,.0f}",
            f"[{p_color}]{priority}[/{p_color}]"
        )

        inventory_analysis.append({
            'commodity':               commodity['name'],
            'sensitivity':             sensitivity,
            'exposed_containers':      exposed_containers,
            'exposure_value':          exposure_value,
            'priority':                priority,
            'typical_disruption_days': commodity.get('typical_disruption_impact_days', 14),
            'reallocation_ports':      commodity.get('primary_import_ports', [])[:2]
        })

    console.print(inventory_table)
    console.print(f"\n  [bold magenta]Total inventory exposure: [red]${total_exposure_value:,.0f}[/red][/bold magenta]")

    system_prompt = """You are the Inventory Agent in SupplyPulse.
Analyze commodity exposure during port disruptions and recommend reallocation.
Be specific, use actual numbers provided, keep responses concise."""

    user_prompt = f"""
Port disruption: {disrupted_port} — Severity: {severity.upper()}
Vessels affected: {vessels_affected}
Recommended alternate port: {recommended_port or 'To be determined'}

Commodity exposure:
{json.dumps([{
    'commodity': c['commodity'],
    'sensitivity': c['sensitivity'],
    'containers': c['exposed_containers'],
    'exposure_usd': c['exposure_value'],
    'priority': c['priority']
} for c in inventory_analysis], indent=2)}

Total at risk: ${total_exposure_value:,.0f}

Provide:
1. TOP PRIORITY ACTION: Which commodity needs immediate reallocation and why (2 sentences)
2. REALLOCATION PLAN: Quantities and destination for top 2 commodities
3. SHORTAGE RISK: Which regions face supply shortage (1-2 regions)
4. TIMELINE: Days before shortage becomes critical
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    console.print(f"\n  [yellow]→[/yellow] Querying Groq LLM for reallocation strategy...")
    response = invoke_with_retry(llm, messages)

    result = {
        'inventory_analysis':      inventory_analysis,
        'total_exposure_value_usd': total_exposure_value,
        'llm_reasoning':           response.content,
        'agent':                   'inventory'
    }

    console.print(Panel(
        f"[bold green]INVENTORY REALLOCATION STRATEGY:[/bold green]\n{response.content}",
        border_style="green",
        title="Inventory Agent — Output"
    ))

    return result


if __name__ == "__main__":
    test_event = {
        'nearest_port_id':    'P001',
        'nearest_port_name':  'Port of Shanghai',
        'severity':           'critical',
        'affected_routes':    '["R001", "R003", "R005"]',
        'affected_commodities': '["electronics", "textiles", "machinery"]',
        'vessels_affected':   350,
        'event_location':     'Shanghai, China'
    }
    test_route_output = {
        'recommended_port': {
            'name':                 'Port of Busan',
            'country':              'South Korea',
            'distance_nm':          449.3,
            'estimated_delay_days': 1.1,
            'estimated_cost_usd':   36393
        }
    }
    result = inventory_agent(test_event, test_route_output)