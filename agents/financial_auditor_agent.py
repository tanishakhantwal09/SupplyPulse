import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    model_name="openai/gpt-oss-20b",
    temperature=0.1,
    max_tokens=600
)

# ── Gap 7: EU ETS Carbon Penalty Constants ────────────────────────────────────
# Reference: IMO MEPC.328(76) & MEPC.336(76) — CII and EEXI regulations
# Reference: European Commission Directive (EU) 2023/959 — EU ETS maritime inclusion
# EU ETS reached 100% coverage of verified emissions from 1 January 2026

EU_ETS_CONFIG = {
    'specific_fuel_consumption_tonne_per_nm': 0.0191,  # tonnes HFO per nautical mile per vessel
    'co2_conversion_factor':                  3.114,   # tonnes CO2 per tonne HFO (IMO standard)
    'eua_price_eur':                          65.0,    # EU Allowance price per tonne CO2 (current)
    'eur_to_usd':                             1.08,    # EUR to USD conversion
    'cii_nm_threshold':                       500,     # nm above which CII rating is impacted
}

CII_RATING_IMPACT = {
    'critical': 'D → E (operational ban risk)',
    'high':     'C → D (improvement plan required)',
    'medium':   'B → C (minor impact)',
    'low':      'A → B (negligible)',
}


def calculate_carbon_penalty(distance_nm, vessels_affected, severity):
    """
    Gap 7: EU ETS Carbon Penalty Calculation
    Formula: Carbon Penalty = ΔDistance × SFC × CF × P_EUA × vessels
    where:
      SFC = specific fuel consumption (tonnes HFO per nm)
      CF  = CO2 conversion factor for HFO (3.114 — IMO standard)
      P_EUA = EU carbon allowance price in USD
    """
    sfc     = EU_ETS_CONFIG['specific_fuel_consumption_tonne_per_nm']
    cf      = EU_ETS_CONFIG['co2_conversion_factor']
    eua_usd = EU_ETS_CONFIG['eua_price_eur'] * EU_ETS_CONFIG['eur_to_usd']

    co2_per_vessel_tonne  = distance_nm * sfc * cf
    total_co2_tonnes      = co2_per_vessel_tonne * vessels_affected
    carbon_penalty_usd    = total_co2_tonnes * eua_usd
    cii_impact            = CII_RATING_IMPACT.get(severity, 'Unknown')

    return {
        'distance_nm':              distance_nm,
        'co2_per_vessel_tonnes':    round(co2_per_vessel_tonne, 2),
        'total_co2_tonnes':         round(total_co2_tonnes, 2),
        'eua_price_usd_per_tonne':  round(eua_usd, 2),
        'carbon_penalty_usd':       round(carbon_penalty_usd, 2),
        'cii_rating_impact':        cii_impact,
        'regulation':               'EU ETS (100% coverage from Jan 2026) + IMO CII',
    }


def calculate_pareto_options(alternates, vessels_affected, severity):
    """
    Gap 7: Pareto Frontier — Cost vs Time vs Carbon
    Generates three optimal options for three different operator priorities.
    """
    if not alternates or len(alternates) == 0:
        return []

    options = []
    for port in alternates:
        carbon = calculate_carbon_penalty(
            port.get('distance_nm', 0),
            vessels_affected,
            severity
        )
        options.append({
            'port':            port.get('name', 'N/A'),
            'country':         port.get('country', 'N/A'),
            'cost_usd':        port.get('estimated_cost_usd', 0) * vessels_affected,
            'delay_days':      port.get('estimated_delay_days', 0),
            'carbon_usd':      carbon['carbon_penalty_usd'],
            'co2_tonnes':      carbon['total_co2_tonnes'],
            'risk':            port.get('risk_level', 'N/A'),
            'total_cost_usd':  (port.get('estimated_cost_usd', 0) * vessels_affected) + carbon['carbon_penalty_usd'],
        })

    pareto = []

    # Option 1 — Minimum total cost (transport + carbon)
    min_cost = min(options, key=lambda x: x['total_cost_usd'])
    pareto.append({
        'option':        'Min Cost',
        'port':          min_cost['port'],
        'cost_usd':      min_cost['cost_usd'],
        'delay_days':    min_cost['delay_days'],
        'carbon_usd':    min_cost['carbon_usd'],
        'co2_tonnes':    min_cost['co2_tonnes'],
        'best_for':      'Cost-priority operators',
    })

    # Option 2 — Minimum carbon emissions
    min_carbon = min(options, key=lambda x: x['carbon_usd'])
    pareto.append({
        'option':        'Min Carbon',
        'port':          min_carbon['port'],
        'cost_usd':      min_carbon['cost_usd'],
        'delay_days':    min_carbon['delay_days'],
        'carbon_usd':    min_carbon['carbon_usd'],
        'co2_tonnes':    min_carbon['co2_tonnes'],
        'best_for':      'ESG / EU ETS compliance priority',
    })

    # Option 3 — Minimum transit time
    min_time = min(options, key=lambda x: x['delay_days'])
    pareto.append({
        'option':        'Min Time',
        'port':          min_time['port'],
        'cost_usd':      min_time['cost_usd'],
        'delay_days':    min_time['delay_days'],
        'carbon_usd':    min_time['carbon_usd'],
        'co2_tonnes':    min_time['co2_tonnes'],
        'best_for':      'Time-priority / perishable cargo operators',
    })

    return pareto


def calculate_financial_impact(state, route_output, inventory_output):
    severity         = state['severity']
    vessels_affected = int(state.get('vessels_affected', 50))
    freight_impact_pct = float(state.get('freight_impact_pct', 15))
    duration_hours   = int(state.get('duration_hours', 48))

    recommended_port = route_output.get('recommended_port', {}) if route_output else {}
    rerouting_cost   = recommended_port.get('estimated_cost_usd', 0) * vessels_affected
    delay_days       = recommended_port.get('estimated_delay_days', 2)
    distance_nm      = recommended_port.get('distance_nm', 0)

    daily_trade_value = {
        'critical': 850000000,
        'high':     350000000,
        'medium':   120000000,
        'low':      40000000
    }.get(severity, 120000000)

    delay_cost           = daily_trade_value * delay_days
    freight_rate_increase = (freight_impact_pct / 100) * rerouting_cost
    inventory_exposure   = inventory_output.get('total_exposure_value_usd', 0) if inventory_output else 0
    inventory_at_risk    = inventory_exposure * 0.15
    operational_cost     = vessels_affected * 25000 * (duration_hours / 24)

    # Gap 7: Add EU ETS carbon penalty as 6th component
    carbon_data          = calculate_carbon_penalty(distance_nm, vessels_affected, severity)
    carbon_penalty       = carbon_data['carbon_penalty_usd']

    total_impact = (
        rerouting_cost +
        delay_cost +
        freight_rate_increase +
        inventory_at_risk +
        operational_cost +
        carbon_penalty
    )

    return {
        'rerouting_cost':        rerouting_cost,
        'delay_cost':            delay_cost,
        'freight_rate_increase': freight_rate_increase,
        'inventory_at_risk':     inventory_at_risk,
        'operational_cost':      operational_cost,
        'carbon_penalty':        carbon_penalty,
        'total_impact':          total_impact,
        'delay_days':            delay_days,
        'freight_impact_pct':    freight_impact_pct,
        'vessels_affected':      vessels_affected,
        'duration_hours':        duration_hours,
        'distance_nm':           distance_nm,
        'carbon_details':        carbon_data,
    }


def financial_auditor_agent(state, route_output=None, inventory_output=None):
    console.print(Panel(
        "[bold yellow]FINANCIAL AUDITOR AGENT[/bold yellow]\n"
        "Calculating total disruption cost, financial exposure, and EU ETS carbon liability...",
        border_style="yellow"
    ))

    severity      = state['severity']
    disrupted_port = state['nearest_port_name']

    console.print(f"  [yellow]→[/yellow] Disrupted port: [bold]{disrupted_port}[/bold]")
    console.print(f"  [yellow]→[/yellow] Severity: [bold red]{severity.upper()}[/bold red]")
    console.print(f"  [yellow]→[/yellow] Reading Route Agent output...")
    console.print(f"  [yellow]→[/yellow] Reading Inventory Agent output...")
    console.print(f"  [yellow]→[/yellow] Calculating total financial exposure including EU ETS carbon penalty...")

    financials = calculate_financial_impact(state, route_output, inventory_output)

    # ── 6-component financial breakdown table ─────────────────────────────────
    finance_table = Table(
        title="Financial Impact Breakdown",
        box=box.ROUNDED,
        border_style="yellow",
        header_style="bold yellow"
    )
    finance_table.add_column("Cost Component", style="bold white", min_width=32)
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
    # Gap 7 — 6th component
    carbon = financials['carbon_details']
    finance_table.add_row(
        "[bold cyan]EU ETS Carbon Penalty (Gap 7)[/bold cyan]",
        f"[bold cyan]${financials['carbon_penalty']:,.0f}[/bold cyan]",
        f"[cyan]{carbon['total_co2_tonnes']:,.1f} t CO₂ × ${carbon['eua_price_usd_per_tonne']:.2f}/t EUA[/cyan]"
    )
    finance_table.add_section()
    finance_table.add_row(
        "[bold red]TOTAL DISRUPTION IMPACT[/bold red]",
        f"[bold red]${financials['total_impact']:,.0f}[/bold red]",
        "[bold red]6-component total incl. carbon[/bold red]"
    )

    console.print(finance_table)

    # ── CII Rating Impact ─────────────────────────────────────────────────────
    console.print(f"\n  [bold cyan]EU ETS / IMO CII:[/bold cyan]")
    console.print(f"  [cyan]→[/cyan] CO₂ generated by rerouting: {carbon['total_co2_tonnes']:,.1f} tonnes")
    console.print(f"  [cyan]→[/cyan] Carbon allowance cost: ${financials['carbon_penalty']:,.0f}")
    console.print(f"  [cyan]→[/cyan] CII rating impact: {carbon['cii_rating_impact']}")
    console.print(f"  [cyan]→[/cyan] Regulation: {carbon['regulation']}")

    # ── Pareto Frontier ───────────────────────────────────────────────────────
    alternates = route_output.get('alternate_ports_analyzed', []) if route_output else []
    vessels    = int(state.get('vessels_affected', 50))
    pareto     = calculate_pareto_options(alternates, vessels, severity)

    if pareto:
        pareto_table = Table(
            title="Gap 7: Pareto Frontier — Cost vs Time vs Carbon",
            box=box.ROUNDED,
            border_style="cyan",
            header_style="bold cyan"
        )
        pareto_table.add_column("Priority Option", style="bold white", min_width=14)
        pareto_table.add_column("Port", min_width=22)
        pareto_table.add_column("Transport Cost", justify="right", min_width=16)
        pareto_table.add_column("Delay", justify="right", min_width=10)
        pareto_table.add_column("Carbon Cost", justify="right", min_width=14)
        pareto_table.add_column("CO₂ (t)", justify="right", min_width=10)
        pareto_table.add_column("Best For", min_width=28)

        for opt in pareto:
            pareto_table.add_row(
                opt['option'],
                opt['port'],
                f"${opt['cost_usd']:,.0f}",
                f"{opt['delay_days']} days",
                f"${opt['carbon_usd']:,.0f}",
                f"{opt['co2_tonnes']:,.1f}",
                opt['best_for'],
            )

        console.print(pareto_table)

    # ── Financial alert ───────────────────────────────────────────────────────
    alert_threshold = {
        'critical': 100000000,
        'high':     50000000,
        'medium':   10000000,
        'low':      1000000
    }.get(severity, 10000000)

    financial_alert = financials['total_impact'] > alert_threshold
    alert_color = "red" if financial_alert else "green"
    alert_text  = "TRIGGERED" if financial_alert else "WITHIN THRESHOLD"

    console.print(f"\n  [bold yellow]Financial Alert:[/bold yellow] [{alert_color}]{alert_text}[/{alert_color}]")
    console.print(f"  [bold yellow]Alert Threshold:[/bold yellow] ${alert_threshold:,.0f}")

    # ── LLM assessment ────────────────────────────────────────────────────────
    system_prompt = """You are the Financial Auditor Agent in SupplyPulse.
Your role is to audit financial impact including EU ETS carbon costs.
Be specific, quantitative, and concise. Reference actual figures provided."""

    user_prompt = f"""
Port disruption: {disrupted_port} — Severity: {severity.upper()}

6-component financial breakdown:
- Rerouting cost: ${financials['rerouting_cost']:,.0f}
- Trade delay cost: ${financials['delay_cost']:,.0f}
- Freight rate increase: ${financials['freight_rate_increase']:,.0f}
- Inventory exposure risk: ${financials['inventory_at_risk']:,.0f}
- Operational costs: ${financials['operational_cost']:,.0f}
- EU ETS Carbon Penalty: ${financials['carbon_penalty']:,.0f} ({carbon['total_co2_tonnes']:,.1f} tonnes CO2)
- TOTAL IMPACT: ${financials['total_impact']:,.0f}

Financial alert: {'TRIGGERED' if financial_alert else 'Within threshold'}
Alert threshold: ${alert_threshold:,.0f}
CII rating impact: {carbon['cii_rating_impact']}

Provide:
1. COST ASSESSMENT: Financial significance including carbon liability (2 sentences)
2. IMMEDIATE MITIGATION: Top 2 actions including carbon cost reduction
3. INSURANCE TRIGGER: Yes/No and why
4. COST vs REROUTING: Is rerouting justified? Include carbon savings
5. RECOMMENDATION: One clear recommendation with expected savings
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    console.print(f"\n  [yellow]→[/yellow] Querying Groq LLM for financial assessment...")
    response = llm.invoke(messages)

    result = {
        'financial_breakdown':    financials,
        'financial_alert_triggered': financial_alert,
        'alert_threshold_usd':    alert_threshold,
        'carbon_details':         carbon,
        'pareto_options':         pareto,
        'llm_reasoning':          response.content,
        'agent':                  'financial_auditor',
    }

    console.print(Panel(
        f"[bold green]FINANCIAL ASSESSMENT:[/bold green]\n{response.content}",
        border_style="green",
        title="Financial Auditor Agent — Output"
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
        'freight_impact_pct': 48.0,
        'duration_hours':     144,
        'event_location':     'Shanghai, China'
    }
    test_route_output = {
        'recommended_port': {
            'name':                 'Port of Busan',
            'distance_nm':          449.3,
            'estimated_delay_days': 1.1,
            'estimated_cost_usd':   36393,
            'risk_level':           'Low',
        },
        'alternate_ports_analyzed': [
            {
                'name': 'Port of Busan', 'country': 'South Korea',
                'distance_nm': 449.3, 'estimated_delay_days': 1.1,
                'estimated_cost_usd': 36393, 'risk_level': 'Low'
            },
            {
                'name': 'Port of Ningbo', 'country': 'China',
                'distance_nm': 110.5, 'estimated_delay_days': 0.3,
                'estimated_cost_usd': 8950, 'risk_level': 'Medium'
            },
            {
                'name': 'Port of Tokyo', 'country': 'Japan',
                'distance_nm': 1068.2, 'estimated_delay_days': 2.7,
                'estimated_cost_usd': 86523, 'risk_level': 'Low'
            },
        ]
    }
    test_inventory_output = {
        'total_exposure_value_usd': 42980000000
    }

    result = financial_auditor_agent(
        test_event,
        test_route_output,
        test_inventory_output
    )