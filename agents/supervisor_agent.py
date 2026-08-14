import os
import json
import pandas as pd
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

# Initialize Groq LLM
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile",
    temperature=0.1
)

# Load reference databases
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
Location: {disruption_event['event_location']}
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

    print(f"\n{'='*60}")
    print(f"SUPPLYPULSE — SUPERVISOR AGENT ACTIVATED")
    print(f"{'='*60}")
    print(f"Processing disruption at: {disruption_event['nearest_port_name']}")
    print(f"Severity: {disruption_event['severity'].upper()}")
    print(f"Querying Groq LLM (Llama 3 70B)...")
    print(f"{'='*60}\n")

    response = llm.invoke(messages)
    return response.content

def run_test():
    print("Loading validation dataset...")
    df = pd.read_csv(
        r'C:\Users\tanis\Desktop\Minor project\dataset\final\validation_set_REAL_ONLY.csv',
        low_memory=False
    )

    print(f"Total real validation events: {len(df):,}")
    print("\nSelecting test cases from real data...\n")

    # Pick one critical, one high, one medium event
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
        print(f"\n{'#'*60}")
        print(f"TEST CASE: {label}")
        print(f"{'#'*60}")

        response = supervisor_agent(event.to_dict())

        print("SUPERVISOR AGENT RESPONSE:")
        print(response)

        results.append({
            "test_case": label,
            "port": event['nearest_port_name'],
            "severity": event['severity'],
            "response": response
        })

    # Save results
    with open("agents/supervisor_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print("ALL TEST CASES COMPLETE")
    print(f"Results saved to: agents/supervisor_test_results.json")
    print(f"{'='*60}")

if __name__ == "__main__":
    run_test()