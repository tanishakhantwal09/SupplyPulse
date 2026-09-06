import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
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
    model_name="openai/gpt-oss-20b",
    temperature=0.1,
    max_tokens=400
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

# ── Gap 3: Retry with backoff ─────────────────────────────────────────────────
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

def supervisor_agent(disruption_event):
    port_info = get_port_info(disruption_event['nearest_port_name'])
    route_ids = json.loads(disruption_event['affected_routes']) if isinstance(disruption_event['affected_routes'], str) else disruption_event['affected_routes']
    route_info = get_route_info(route_ids)
    affected_commodities = json.loads(disruption_event['affected_commodities']) if isinstance(disruption_event['affected_commodities'], str) else disruption_event['affected_commodities']

    system_prompt = """You are the Supervisor Agent of SupplyPulse.
Coordinate EXACTLY these 4 agents only: Route Optimization Agent, Inventory Agent, Financial Auditor Agent, Supervisor Agent.
NEVER mention any other agents. Never invent agents.
Provide exactly these 5 sections:
1. SITUATION ASSESSMENT — what happened and why it matters
2. IMMEDIATE ACTIONS — top 5 operational steps
3. AGENT DELEGATION — only the 4 real agents with their specific task
4. REROUTING RECOMMENDATION — preliminary alternate port
5. RISK LEVEL — overall rating
Be concise. Maximum 3 sentences per section. Use actual figures provided."""

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

Provide the 5 required sections. Be concise — max 3 sentences each.
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

    response = invoke_with_retry(llm, messages)

    console.print(Panel(
        f"[bold green]SITUATION ASSESSMENT:[/bold green]\n{response.content}",
        border_style="green",
        title="Supervisor Agent — Output"
    ))

    return response.content


def run_test():
    console.print("Loading validation dataset...")
    df = pd.read_parquet(
        r'dataset/final/validation_set_REAL_ONLY.parquet'
    )
    console.print(f"Total real validation events: {len(df):,}")
    console.print("\nSelecting test cases from real data...\n")

    critical = df[df['severity'] == 'critical'].iloc[0]
    high     = df[df['severity'] == 'high'].iloc[0]
    medium   = df[df['severity'] == 'medium'].iloc[0]

    test_cases = [
        ("CRITICAL SEVERITY EVENT", critical),
        ("HIGH SEVERITY EVENT",     high),
        ("MEDIUM SEVERITY EVENT",   medium)
    ]

    results = []
    for label, event in test_cases:
        console.print(f"\n[bold]TEST CASE: {label}[/bold]")
        response = supervisor_agent(event.to_dict())
        results.append({
            "test_case": label,
            "port":      event['nearest_port_name'],
            "severity":  event['severity'],
            "response":  response
        })

    with open("agents/supervisor_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    console.print(f"\n[bold green]ALL TEST CASES COMPLETE[/bold green]")
    console.print(f"Results saved to: agents/supervisor_test_results.json")


if __name__ == "__main__":
    run_test()