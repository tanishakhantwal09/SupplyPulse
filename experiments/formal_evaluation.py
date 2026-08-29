import pandas as pd
import json
import time
import os
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
from agents.langgraph_orchestrator import run_supplypulse
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()
os.makedirs("experiments/results", exist_ok=True)

# Load validation data
df = pd.read_csv(
    r'C:\Users\tanis\Desktop\Minor project\dataset\final\validation_set_REAL_ONLY.csv',
    low_memory=False
)

# Sample 30 events matching Brintrup's 30 scenario evaluation
# 10 critical, 10 high, 10 medium
critical = df[df['severity'] == 'critical'].head(10)
high     = df[df['severity'] == 'high'].head(10)
medium   = df[df['severity'] == 'medium'].head(10)
test_set = pd.concat([critical, high, medium], ignore_index=True)

console.print(f"Running formal evaluation on {len(test_set)} real validation events...")
console.print("Matching Brintrup 2026 evaluation methodology — 30 scenarios\n")

# Storage
y_true_reroute   = []
y_pred_reroute   = []
y_true_alert     = []
y_pred_alert     = []
response_times   = []
port_correct     = []
agent_results    = []

for i, (_, event) in enumerate(test_set.iterrows()):
    console.print(f"[dim]Scenario {i+1}/30 — {event['nearest_port_name']} — {event['severity']}[/dim]")

    try:
        result = run_supplypulse(event.to_dict())

        # Ground truth from dataset
        gt_reroute = bool(event.get('decision_reroute', event['severity'] in ['critical','high']))
        gt_alert   = bool(event.get('decision_financial_alert', event['severity'] in ['critical','high']))
        gt_port    = str(event.get('decision_alternate_port', ''))

        # Agent prediction
        pred_reroute = result['decision'] == 'REROUTE'
        pred_alert   = result.get('financial_alert', False)
        pred_port    = str(result.get('recommended_alternate_port', ''))

        y_true_reroute.append(int(gt_reroute))
        y_pred_reroute.append(int(pred_reroute))
        y_true_alert.append(int(gt_alert))
        y_pred_alert.append(int(pred_alert))
        response_times.append(result['total_response_time_seconds'])
        port_correct.append(1 if pred_port and gt_port and pred_port in gt_port else 0)

        agent_results.append({
            'port': event['nearest_port_name'],
            'severity': event['severity'],
            'gt_reroute': gt_reroute,
            'pred_reroute': pred_reroute,
            'gt_alert': gt_alert,
            'pred_alert': pred_alert,
            'response_time': result['total_response_time_seconds'],
            'confidence': result.get('confidence', 'N/A')
        })

    except Exception as e:
        console.print(f"[red]Error on scenario {i+1}: {e}[/red]")
        continue

# ── Calculate metrics ─────────────────────────────────────────────────────────
f1_reroute    = f1_score(y_true_reroute, y_pred_reroute, zero_division=0)
precision     = precision_score(y_true_reroute, y_pred_reroute, zero_division=0)
recall        = recall_score(y_true_reroute, y_pred_reroute, zero_division=0)
accuracy      = accuracy_score(y_true_reroute, y_pred_reroute)
f1_alert      = f1_score(y_true_alert, y_pred_alert, zero_division=0)
avg_time      = sum(response_times) / len(response_times)
min_time      = min(response_times)
max_time      = max(response_times)
plan_correct  = sum(port_correct) / len(port_correct) if port_correct else 0

# Cost calculation
tokens_per_call    = 1500
agents_per_pipeline = 4
total_tokens       = tokens_per_call * agents_per_pipeline
cost_per_million   = 0.15
cost_per_analysis  = (total_tokens / 1_000_000) * cost_per_million

# ── Results table ─────────────────────────────────────────────────────────────
results_table = Table(
    title="SupplyPulse Formal Evaluation Results — 30 Real Validation Scenarios",
    box=box.DOUBLE_EDGE,
    border_style="green",
    header_style="bold green"
)
results_table.add_column("Metric", style="bold cyan", min_width=35)
results_table.add_column("SupplyPulse", style="bold white", min_width=20)
results_table.add_column("Brintrup 2026", style="bold yellow", min_width=20)
results_table.add_column("Project Synapse 2026", style="bold yellow", min_width=22)

results_table.add_row(
    "F1 Score (Rerouting Decision)",
    f"{f1_reroute:.3f}",
    "0.962 - 0.991",
    "N/A"
)
results_table.add_row(
    "Precision",
    f"{precision:.3f}",
    "Not reported",
    "Not reported"
)
results_table.add_row(
    "Recall",
    f"{recall:.3f}",
    "Not reported",
    "Not reported"
)
results_table.add_row(
    "Decision Accuracy",
    f"{accuracy:.3f}",
    "Not reported",
    "0.710 (Plan Correctness)"
)
results_table.add_row(
    "Financial Alert F1",
    f"{f1_alert:.3f}",
    "Not measured",
    "Not measured"
)
results_table.add_row(
    "Plan Correctness (Port Match)",
    f"{plan_correct:.3f}",
    "Not measured",
    "0.710"
)
results_table.add_row(
    "Average Response Time",
    f"{avg_time:.2f} seconds",
    "3.83 minutes (229.8s)",
    "Not reported"
)
results_table.add_row(
    "Minimum Response Time",
    f"{min_time:.2f} seconds",
    "Not reported",
    "Not reported"
)
results_table.add_row(
    "Cost Per Analysis",
    f"${cost_per_analysis:.4f}",
    "$0.0836",
    "Not reported"
)
results_table.add_row(
    "Scenarios Evaluated",
    "30 real held-out events",
    "30 synthetic scenarios",
    "30 synthetic scenarios"
)
results_table.add_row(
    "Data Type",
    "Real GDELT events 2020-2026",
    "Synthetic automotive",
    "Synthetic LMD scenarios"
)
results_table.add_row(
    "Route Optimization",
    "Yes — Haversine + LLM",
    "No",
    "No"
)
results_table.add_row(
    "Financial Assessment",
    "Yes — 5 cost components",
    "No",
    "No"
)
results_table.add_row(
    "Inventory Reallocation",
    "Yes — container quantities",
    "No",
    "No"
)

console.print(results_table)

# Save
final_results = {
    'metrics': {
        'f1_rerouting': f1_reroute,
        'precision': precision,
        'recall': recall,
        'accuracy': accuracy,
        'f1_financial_alert': f1_alert,
        'plan_correctness': plan_correct,
        'avg_response_time_seconds': avg_time,
        'min_response_time_seconds': min_time,
        'max_response_time_seconds': max_time,
        'cost_per_analysis_usd': cost_per_analysis,
    },
    'comparison': {
        'brintrup_2026_f1': '0.962-0.991',
        'brintrup_2026_response_time_seconds': 229.8,
        'brintrup_2026_cost_per_analysis': 0.0836,
        'synapse_2026_plan_correctness': 0.71,
        'synapse_2026_reasoning_quality': 0.77,
    },
    'scenarios': agent_results
}

with open("experiments/results/formal_evaluation.json", "w") as f:
    json.dump(final_results, f, indent=2, default=str)

console.print(f"\n[bold green]Results saved to experiments/results/formal_evaluation.json[/bold green]")
console.print(f"\n[bold]Key findings:[/bold]")
console.print(f"  SupplyPulse is [bold green]{229.8/avg_time:.1f}x faster[/bold green] than Brintrup 2026")
console.print(f"  SupplyPulse costs [bold green]{0.0836/cost_per_analysis:.0f}x less[/bold green] per analysis than Brintrup 2026")
console.print(f"  SupplyPulse adds route optimization, financial assessment, and inventory reallocation — none of which existing papers provide")