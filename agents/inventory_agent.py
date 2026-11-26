"""Inventory Agent: exposed stock by commodity. The LLM only explains the figures."""
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from rich import box
from rich.panel import Panel
from rich.table import Table

from agents.llm_utils import console, invoke_with_retry
from agents.reference_data import commodities, port_by_id

# ASSUMPTION: containers carried per affected vessel, by event severity. No source yet,
# and a ship's size should not depend on severity; to be calibrated (BUILD_PLAN 7.1).
CONTAINERS_PER_VESSEL = {"critical": 800, "high": 400, "medium": 200, "low": 100}
# ASSUMPTION: share of containers exposed, by commodity supply-chain sensitivity. No source yet.
SENSITIVITY_SHARE = {"critical": 0.9, "high": 0.7, "medium": 0.4, "low": 0.2}
PRIORITY_BY_SENSITIVITY = {"critical": "P1", "high": "P2", "medium": "P3", "low": "P4"}
INVENTORY_MAX_TOKENS = 700  # BUILD_PLAN section 2.


def _words(text):
    return set(re.findall(r"[a-z]+", str(text).lower().replace("_", " ")))


def match_commodities(affected_terms):
    """Whole-word matching of event commodity terms to commodities.json.

    A term matches when all its words appear as whole words. A match on the
    commodity NAME wins over a match on a subcategory. So "chemicals" matches
    "Chemicals and Pharmaceuticals", not "Oil and Petrochemicals", and
    "palm_oil" does not match "Oil and Petrochemicals".
    Returns (matched commodity records, unmatched terms).
    """
    matched_ids, unmatched = [], []
    for term in affected_terms:
        tw = _words(term)
        if not tw:
            continue
        by_name = [c for c in commodities() if tw <= _words(c["name"])]
        hits = by_name or [c for c in commodities()
                           if any(tw <= _words(s) for s in c.get("subcategories", []))]
        if not hits:
            unmatched.append(term)
        for c in hits:
            if c["commodity_id"] not in matched_ids:
                matched_ids.append(c["commodity_id"])
    matched = [c for c in commodities() if c["commodity_id"] in matched_ids]
    return matched, unmatched


def _port_name(port_id):
    port = port_by_id(port_id)
    return port["name"] if port else port_id


def calculate_exposure(commodity, severity, vessels_affected):
    containers = vessels_affected * CONTAINERS_PER_VESSEL[severity]
    share = SENSITIVITY_SHARE[commodity["supply_chain_sensitivity"]]
    exposed = round(containers * share)
    return exposed, exposed * commodity["avg_value_per_container_usd"]


SYSTEM_PROMPT = """You are the Inventory Agent in SupplyPulse.
All exposure figures were calculated by deterministic code. Explain them in plain language.
Use only the numbers and port names given. Do not invent quantities, regions or timelines."""


def inventory_agent(state, route_agent_output=None):
    console.print(Panel("[bold magenta]INVENTORY AGENT[/bold magenta]\nCalculating commodity exposure...",
                        border_style="magenta"))
    severity = state["severity"]
    vessels = int(state["vessels_affected"])
    terms = state.get("affected_commodities")
    terms = json.loads(terms) if isinstance(terms, str) else list(terms or [])
    recommended = (route_agent_output or {}).get("recommended_port", {}).get("name")

    matched, unmatched = match_commodities(terms)
    analysis, total = [], 0
    for c in matched:
        exposed, value = calculate_exposure(c, severity, vessels)
        total += value
        analysis.append({
            "commodity": c["name"],
            "sensitivity": c["supply_chain_sensitivity"],
            "exposed_containers": exposed,
            "exposure_value": value,
            "priority": PRIORITY_BY_SENSITIVITY[c["supply_chain_sensitivity"]],
            "typical_disruption_days": c.get("typical_disruption_impact_days"),  # from commodities.json
            # from commodities.json (ids), shown to the LLM as port names
            "reallocation_ports": [_port_name(pid) for pid in c.get("primary_import_ports", [])[:2]],
        })
    analysis.sort(key=lambda a: (a["priority"], -a["exposure_value"]))

    t = Table(title="Commodity Exposure", box=box.ROUNDED, border_style="magenta")
    for col in ["Commodity", "Sensitivity", "Containers", "Value (USD)", "Priority"]:
        t.add_column(col)
    for a in analysis:
        t.add_row(a["commodity"], a["sensitivity"], f"{a['exposed_containers']:,}",
                  f"${a['exposure_value']:,.0f}", a["priority"])
    console.print(t)
    if unmatched:
        console.print(f"  [yellow]No commodity record for: {', '.join(unmatched)} (not priced)[/yellow]")

    user_prompt = f"""Port disruption: {state['nearest_port_name']} (severity {severity.upper()})
Vessels affected: {vessels}. Code-selected alternate port: {recommended or 'none'}
Exposure by commodity (calculated by code):
{json.dumps([{k: a[k] for k in ('commodity', 'sensitivity', 'exposed_containers', 'exposure_value', 'priority', 'typical_disruption_days', 'reallocation_ports')} for a in analysis], indent=2)}
Total exposure: ${total:,.0f}
Terms with no commodity record (not priced): {', '.join(unmatched) or 'none'}

Write:
1. TOP PRIORITY: which commodity comes first and why, using the priority and exposure above (2 sentences).
2. REALLOCATION: which listed reallocation ports could take the top 2 commodities (1-2 sentences).
3. CAVEAT: one sentence noting that containers per vessel is an assumption."""
    explanation = invoke_with_retry([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)],
                                    INVENTORY_MAX_TOKENS, agent="inventory")
    console.print(Panel(explanation, border_style="green", title="Inventory Agent: explanation"))

    return {
        "inventory_analysis": analysis,
        "total_exposure_value_usd": total,
        "unmatched_commodities": unmatched,
        "llm_reasoning": explanation,
        "agent": "inventory",
    }
