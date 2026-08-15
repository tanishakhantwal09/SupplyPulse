import os
import json
import math
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

with open("dataset/reference/ports.json") as f:
    ports = json.load(f)
with open("dataset/reference/routes.json") as f:
    routes = json.load(f)

def haversine_nm(lat1, lon1, lat2, lon2):
    R = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return round(2 * R * math.asin(math.sqrt(a)), 1)

def get_alternate_ports(disrupted_port_id, severity):
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
            
            base_cost = distance * 45
            estimated_cost = round(base_cost * severity_cost_multiplier)
            
            risk = 'Low' if alt_port['strategic_importance'] == 'critical' else \
                   'Medium' if alt_port['strategic_importance'] == 'high' else 'High'
            
            alternates.append({
                'port_id': alt_port['port_id'],
                'name': alt_port['name'],
                'country': alt_port['country'],
                'distance_nm': distance,
                'estimated_delay_days': delay_days,
                'estimated_cost_usd': estimated_cost,
                'risk_level': risk,
                'strategic_importance': alt_port['strategic_importance'],
                'commodities': alt_port.get('commodities', [])
            })
    
    alternates.sort(key=lambda x: (
        {'Low': 0, 'Medium': 1, 'High': 2}[x['risk_level']],
        x['estimated_delay_days']
    ))
    return alternates[:3]

def route_optimization_agent(state):
    console.print(Panel(
        "[bold cyan]ROUTE OPTIMIZATION AGENT[/bold cyan]\nAnalyzing alternate shipping routes...",
        border_style="cyan"
    ))
    
    disrupted_port_id = state['nearest_port_id']
    disrupted_port_name = state['nearest_port_name']
    severity = state['severity']
    affected_routes = json.loads(state['affected_routes']) if isinstance(state['affected_routes'], str) else state['affected_routes']
    
    console.print(f"  [yellow]→[/yellow] Disrupted port: [bold]{disrupted_port_name}[/bold]")
    console.print(f"  [yellow]→[/yellow] Severity: [bold red]{severity.upper()}[/bold red]")
    console.print(f"  [yellow]→[/yellow] Affected routes: {', '.join(affected_routes)}")
    console.print(f"  [yellow]→[/yellow] Querying alternate ports from reference database...")
    
    alternates = get_alternate_ports(disrupted_port_id, severity)
    
    if alternates:
        table = Table(
            title="Alternate Port Analysis",
            box=box.ROUNDED,
            border_style="cyan",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Port", style="bold white", min_width=25)
        table.add_column("Country", min_width=12)
        table.add_column("Distance (nm)", justify="right", min_width=14)
        table.add_column("Est. Delay", justify="right", min_width=10)
        table.add_column("Est. Cost (USD)", justify="right", min_width=15)
        table.add_column("Risk", justify="center", min_width=8)
        
        for i, alt in enumerate(alternates):
            risk_color = {
                'Low': 'green', 'Medium': 'yellow', 'High': 'red'
            }.get(alt['risk_level'], 'white')
            
            marker = "★ " if i == 0 else "  "
            table.add_row(
                f"{marker}{alt['name']}",
                alt['country'],
                f"{alt['distance_nm']:,}",
                f"{alt['estimated_delay_days']} days",
                f"${alt['estimated_cost_usd']:,}",
                f"[{risk_color}]{alt['risk_level']}[/{risk_color}]"
            )
        
        console.print(table)
    
    system_prompt = """You are the Route Optimization Agent in SupplyPulse, a supply chain disruption management system.
    
Your role is to analyze port disruptions and recommend the optimal rerouting strategy.
You have access to real port data, distance calculations, and cost estimates.
Provide specific, data-driven recommendations. Be concise and structured."""

    user_prompt = f"""
Port disruption detected: {disrupted_port_name}
Severity: {severity.upper()}
Affected shipping routes: {', '.join(affected_routes)}

Analyzed alternate ports:
{json.dumps(alternates, indent=2)}

Based on this analysis:
1. RECOMMENDED PORT: Which alternate port and why (2 sentences max)
2. ROUTE ADJUSTMENT: What shipping lane adjustment is needed (1 sentence)
3. RISK FACTORS: Key risks with this rerouting (2 bullet points max)
4. CONFIDENCE: Your confidence in this recommendation (percentage)

Be specific and reference the actual port names and data provided.
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    console.print(f"\n  [yellow]→[/yellow] Querying Groq LLM for routing recommendation...")
    response = llm.invoke(messages)
    
    recommended = alternates[0] if alternates else None
    
    result = {
        'alternate_ports_analyzed': alternates,
        'recommended_port': recommended,
        'llm_reasoning': response.content,
        'agent': 'route_optimization'
    }
    
    console.print(Panel(
        f"[bold green]ROUTE RECOMMENDATION:[/bold green]\n{response.content}",
        border_style="green",
        title="Route Optimization Agent — Output"
    ))
    
    return result

if __name__ == "__main__":
    test_event = {
        'nearest_port_id': 'P001',
        'nearest_port_name': 'Port of Shanghai',
        'severity': 'critical',
        'affected_routes': '["R001", "R003", "R005"]',
        'event_location': 'Shanghai, China'
    }
    
    result = route_optimization_agent(test_event)
    console.print(f"\n[bold]Recommended alternate: {result['recommended_port']['name']}[/bold]")