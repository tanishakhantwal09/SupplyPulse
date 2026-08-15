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

def calculate_financial_impact(state, route_output, inventory_output):
    severity = state['severity']
    vessels_affected = int(state.get('vessels_affected', 50))
    freight_impact_pct = float(state.get('freight_impact_pct', 15))
    duration_hours = int(state.get('duration_hours', 48))

    recommended_port = route_output.get('recommended_port', {}) if route_output else {}
    rerouting_cost = recommended_port.get('estimated_cost_usd', 0) * vessels_affected
    delay_days = recommended_port.get('estimated_delay_days', 2)

    daily_trade_value = {
        'critical': 850000000,
        'high': 350000000,
        'medium': 120000000,
        'low': 40000000
    }.get(severity, 120000000)

    delay_cost = daily_trade_value * delay_days
    freight_rate_increase = (freight_impact_pct / 100) * rerouting_cost
    inventory_exposure = inventory_output.get('total_exposure_value_usd', 0) if inventory_output else 0
    inventory_at_risk = inventory_exposure * 0.15
    operational_cost = vessels_affected * 25000 * (duration_hours / 24)
    total_impact = rerouting_cost + delay_cost + freight_rate_increase + inventory_at_risk + operational_cost

    return {
        'rerouting_cost': rerouting_cost,
        'delay_cost': delay_cost,
        'freight_rate_increase': freight_rate_increase,
        'inventory_at_risk': inventory_at_risk,
        'operational_cost': operational_cost,
        'total_impact': total_impact,
        'delay_days': delay_days,
        'freight_impact_pct': freight_impact_pct,
        'vessels_affected': vessels_affected,
        'duration_hours': duration_hours
    }

def financial_auditor_agent(state, route_output=None, inventory_output=None):
    console.print(Panel(
        "[bold yellow]FINANCIAL AUDITOR AGENT[/bold yellow]\nCalculating total disruption cost and financial exposure...",
        border_style="yellow"
    ))

    severity = state['severity']
    disrupted_port = state['nearest_port_name']

    console.print(f"  [yellow]→[/yellow] Disrupted port: [bold]{disrupted_port}[/bold]")
    console.print(f"  [yellow]→[/yellow] Severity: [bold red]{severity.upper()}[/bold red]")
    console.print(f"  [yellow]→[/yellow] Reading Route Agent output...")
    console.print(f"  [yellow]→[/yellow] Reading Inventory Agent output...")
    console.print(f"  [yellow]→[/yellow] Calculating total financial exposure...")

    financials = calculate_financial_impact(state, route_output, inventory_output)

    finance_table = Table(
        title="Financial Impact Breakdown",
        box=box.ROUNDED,
        border_style="yellow",
        header_style="bold yellow"
    )
    finance_table.add_column("Cost Component", style="bold white", min_width=30)
    finance_table.add_column("Amount (USD)", justify="right", min_width=20)
    finance_table.add_column("Notes", min_width=30)

    finance_table.add_row(
        "Rerouting Transportation Cost",
        f"${financials['rerouting_cost']:,.0f}",
        f"{financials['vessels_affected']} vessels rerouted"
    )
    finance_table.add_row(
        "Trade Delay Cost",
        f"${financials['delay_cost']:,.0f}",
        f"{financials['delay_days']} days additional transit"
    )
    finance_table.add_row(
        "Freight Rate Increase",
        f"${financials['freight_rate_increase']:,.0f}",
        f"{financials['freight_impact_pct']}% rate surge"
    )
    finance_table.add_row(
        "Inventory Exposure Risk",
        f"${financials['inventory_at_risk']:,.0f}",
        "15% of total inventory at risk"
    )
    finance_table.add_row(
        "Operational Costs",
        f"${financials['operational_cost']:,.0f}",
        f"{financials['duration_hours']}hr disruption window"
    )
    finance_table.add_section()
    finance_table.add_row(
        "[bold red]TOTAL DISRUPTION IMPACT[/bold red]",
        f"[bold red]${financials['total_impact']:,.0f}[/bold red]",
        "[bold red]Combined financial exposure[/bold red]"
    )

    console.print(finance_table)

    alert_threshold = {
        'critical': 100000000,
        'high': 50000000,
        'medium': 10000000,
        'low': 1000000
    }.get(severity, 10000000)

    financial_alert = financials['total_impact'] > alert_threshold
    alert_color = "red" if financial_alert else "green"
    alert_text = "TRIGGERED" if financial_alert else "WITHIN THRESHOLD"
    console.print(f"\n  [bold yellow]Financial Alert:[/bold yellow] [{alert_color}]{alert_text}[/{alert_color}]")
    console.print(f"  [bold yellow]Alert Threshold:[/bold yellow] ${alert_threshold:,.0f}")

    system_prompt = """You are the Financial Auditor Agent in SupplyPulse, a supply chain disruption management system.

Your role is to audit the financial impact of supply chain disruptions and provide actionable cost mitigation recommendations.
You receive outputs from the Route Optimization Agent and Inventory Agent.
Base your analysis on the actual financial figures provided.
Be specific, quantitative, and concise."""

    user_prompt = f"""
Port disruption: {disrupted_port} — Severity: {severity.upper()}

Financial breakdown:
- Rerouting cost: ${financials['rerouting_cost']:,.0f}
- Trade delay cost: ${financials['delay_cost']:,.0f}
- Freight rate increase: ${financials['freight_rate_increase']:,.0f}
- Inventory exposure risk: ${financials['inventory_at_risk']:,.0f}
- Operational costs: ${financials['operational_cost']:,.0f}
- TOTAL IMPACT: ${financials['total_impact']:,.0f}

Financial alert: {'TRIGGERED' if financial_alert else 'Within threshold'}
Alert threshold: ${alert_threshold:,.0f}

Provide:
1. COST ASSESSMENT: Is this financially significant? Context for the total impact figure (2 sentences)
2. IMMEDIATE MITIGATION: Top 2 actions to reduce financial exposure right now
3. INSURANCE TRIGGER: Should insurance claims be initiated? Yes/No and why
4. COST vs REROUTING: Is rerouting financially justified compared to waiting out disruption?
5. RECOMMENDATION: One clear financial recommendation with expected savings

Use actual dollar figures from the analysis above.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    console.print(f"\n  [yellow]→[/yellow] Querying Groq LLM for financial assessment...")
    response = llm.invoke(messages)

    result = {
        'financial_breakdown': financials,
        'financial_alert_triggered': financial_alert,
        'alert_threshold_usd': alert_threshold,
        'llm_reasoning': response.content,
        'agent': 'financial_auditor'
    }

    console.print(Panel(
        f"[bold green]FINANCIAL ASSESSMENT:[/bold green]\n{response.content}",
        border_style="green",
        title="Financial Auditor Agent — Output"
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
        'freight_impact_pct': 48.0,
        'duration_hours': 144,
        'event_location': 'Shanghai, China'
    }

    test_route_output = {
        'recommended_port': {
            'name': 'Port of Busan',
            'distance_nm': 449.3,
            'estimated_delay_days': 1.1,
            'estimated_cost_usd': 36393
        }
    }

    test_inventory_output = {
        'total_exposure_value_usd': 42980000000
    }

    result = financial_auditor_agent(
        test_event,
        test_route_output,
        test_inventory_output
    )
    