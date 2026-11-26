"""Supervisor Agent: assesses the event and states what the other agents will check.

It does not pick a port, a risk rating or any number; those come from code.
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage
from rich.panel import Panel

from agents.llm_utils import console, invoke_with_retry
from agents.reference_data import DATA_DIR, routes

SUPERVISOR_MAX_TOKENS = 700  # BUILD_PLAN section 2.

SYSTEM_PROMPT = """You are the Supervisor Agent of SupplyPulse.
You coordinate exactly four agents: Supervisor, Route Optimization, Inventory, Financial Auditor.
Never mention any other agents.
Do NOT choose an alternate port, a risk rating, a probability or any other number:
those are calculated by code later. Use only the figures given.
Write exactly these 3 sections, at most 3 sentences each:
1. SITUATION ASSESSMENT: what happened and why it matters for shipping.
2. IMMEDIATE ACTIONS: the operational steps to start now.
3. AGENT DELEGATION: what Route Optimization, Inventory and Financial Auditor will each calculate."""


def _parse_list(value):
    return json.loads(value) if isinstance(value, str) else list(value or [])


def build_user_prompt(event):
    route_ids = _parse_list(event.get("affected_routes"))
    route_names = [r["name"] for r in routes() if r["route_id"] in route_ids]
    return f"""DISRUPTION EVENT
Event date: {event.get('event_date', 'N/A')}
Location: {event.get('event_location', 'N/A')}
Nearest port: {event['nearest_port_name']} ({event.get('nearest_port_country', 'N/A')})
Severity label (rule-based): {event['severity'].upper()}
Port type: {event.get('port_type', 'N/A')}; strategic importance: {event.get('port_strategic_importance', 'N/A')}

IMPACT INPUTS (rule-based estimates from the dataset enrichment)
- Distance from event to port: {event.get('distance_to_port_nm', 'N/A')} nm
- Affected routes: {', '.join(route_names or route_ids) or 'none'}
- At-risk commodities: {', '.join(_parse_list(event.get('affected_commodities'))) or 'none'}
- Freight-rate impact estimate: {event.get('freight_impact_pct', 'N/A')}%
- Vessels affected estimate: {event.get('vessels_affected', 'N/A')}
- Duration estimate: {event.get('duration_hours', 'N/A')} hours

NEWS SIGNAL (GDELT)
- Goldstein scale: {event.get('goldstein_scale', 'N/A')}
- Average tone: {event.get('avg_tone', 'N/A')}
- Mentions: {event.get('num_mentions', 'N/A')}
- Source: {event.get('source_url', 'N/A')}"""


def supervisor_agent(event):
    console.print(Panel("[bold blue]SUPERVISOR AGENT[/bold blue]\nAssessing the event...", border_style="blue"))
    console.print(f"  Port: [bold]{event['nearest_port_name']}[/bold]   Severity: {event['severity'].upper()}")
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=build_user_prompt(event))]
    text = invoke_with_retry(messages, SUPERVISOR_MAX_TOKENS, agent="supervisor")
    console.print(Panel(text, border_style="green", title="Supervisor Agent: assessment"))
    return text


if __name__ == "__main__":
    # Uses the DEVELOPMENT set. The held-out set is only for final evaluation.
    import pandas as pd

    df = pd.read_parquet(DATA_DIR / "training_set.parquet")
    for sev in ["critical", "high", "medium"]:
        supervisor_agent(df[df["severity"] == sev].iloc[0].to_dict())
