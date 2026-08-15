import os
import json
import pandas as pd
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from rich.console import Console
from rich.panel import Panel

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
with open("dataset/reference/commodities.json") as f:
    commodities = json.load(f)

def get_port_info(port_name):
    for port in ports:
        if port['name'] == port_name:
            return port
    return None

def get_route_info(route_ids):
    affected = []
    for route in routes:
        if route['route_id'] in route_ids:
            affected.append(route)
    return affected

def supervisor_agent(disruption_event):
    port_info = get_port_info(disruption_event['nearest_port_name'])
    route_ids = json.loads(disruption_event['affected_routes']) if isinstance(disruption_event['affected_routes'], str) else disruption_event['affected_routes']
    route_info = get_route_info(route_ids)
    affected_commodities = json.loads(disruption_event['affected_commodities']) if isinstance(disruption_event['affected_commodities'], str) else disruption_event['affected_commodities']

    system_prompt = """You are the Supervisor Agent of SupplyPulse, an autonomous supply chain disruption management system.

Your role is to:
1. Analyze incoming disruption events
2. Assess the severity and impact
3. Coordinate a response plan
4. Delegate tasks to specialized agents

Always respond in a structured, professional manner with clear action items.
Be concise but comprehensive."""

    user_prompt = f"""
DISRUPTION EVENT DETECTED:

Event Date: {disruption_event['event_date']}
Location: {disruption_event.get('event_location', 'N/A')}
Nearest Port: {disruption_event['nearest_port_name']}
Country: {disruption_event['nearest_port_country']}
Severity: {disruption_event['severity'].upper()}
Port Type: {disruption_event['port_type']}
Strategic Importance: {disruption_event['port_strategic_importance']}

IMPACT ASSESSMENT:
- Distance to port: {disruption_event['distance_to_port_nm']} nautical miles
- Affected shipping routes: {', '.join(route_ids)}
- At-risk commodities: {', '.join(affected_commodities)}
- Estimated freight rate impact: {disruption_event['freight_impact_pct']}%
- Estimated vessels affected: {disruption_event['vessels_affected']}
- Estimated disruption duration: {disruption_event['duration_hours']} hours

NEWS SIGNAL:
- Goldstein Instability Score: {disruption_event['goldstein_scale']}
- Average News Tone: {disruption_event['avg_tone']}
- Number of News Mentions: {disruption_event['num_mentions']}
- Source: {disruption_event['source_url']}

As Supervisor Agent, provide:
1. SITUATION ASSESSMENT - What is happening and why it matters
2. IMMEDIATE ACTIONS - What must be done in the next 24 hours
3. AGENT DELEGATION - Which specialized agents to activate and why
4. REROUTING RECOMMENDATION - Preliminary alternative route suggestion
5. RISK LEVEL - Overall risk to global supply chain
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    console.print(Panel(
        "[bold blue]SUPERVISOR AGENT[/bold blue]\nReceiving disruption event and coordinating response...",
        border_style="blue"
    ))
    console.print(f"  [yellow]→[/yellow] Disrupted port: [bold]{disruption_event['nearest_port_name']}[/bold]")
    console.print(f"  [yellow]→[/yellow] Severity: [bold red]{disruption_event['severity'].upper()}[/bold red]")
    console.print(f"  [yellow]→[/yellow] Location: {disruption_event.get('event_location', 'N/A')}")
    console.print(f"  [yellow]→[/yellow] Querying Groq LLM for situation assessment...")

    response = llm.invoke(messages)

    console.print(Panel(
        f"[bold green]SITUATION ASSESSMENT:[/bold green]\n{response.content}",
        border_style="green",
        title="Supervisor Agent — Output"
    ))

    return response.content

def run_test():
    console.print("Loading validation dataset...")
    df = pd.read_csv(
        r'C:\Users\tanis\Desktop\Minor project\dataset\final\validation_set_REAL_ONLY.csv',
        low_memory=False
    )

    console.print(f"Total real validation events: {len(df):,}")
    console.print("\nSelecting test cases from real data...\n")

    critical = df[df['severity'] == 'critical'].iloc[0]
    high = df[df['severity'] == 'high'].iloc[0]
    medium = df[df['severity'] == 'medium'].iloc[0]

    test_cases = [
        ("CRITICAL SEVERITY EVENT", critical),
        ("HIGH SEVERITY EVENT", high),
        ("MEDIUM SEVERITY EVENT", medium)
    ]

    results = []

    for label, event in test_cases:
        console.print(f"\n[bold]TEST CASE: {label}[/bold]")
        response = supervisor_agent(event.to_dict())
        results.append({
            "test_case": label,
            "port": event['nearest_port_name'],
            "severity": event['severity'],
            "response": response
        })

    with open("agents/supervisor_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    console.print(f"\n[bold green]ALL TEST CASES COMPLETE[/bold green]")
    console.print(f"Results saved to: agents/supervisor_test_results.json")

if __name__ == "__main__":
    run_test()