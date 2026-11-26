import pandas as pd
from agents.langgraph_orchestrator import run_supplypulse
from rich.console import Console
from rich.rule import Rule

console = Console()

# Demo uses the DEVELOPMENT set. The held-out set is only for final evaluation.
print("Loading development dataset...")
df = pd.read_parquet('dataset/final/training_set.parquet')

print(f"Development events available: {len(df):,}\n")

critical = df[df['severity'] == 'critical'].iloc[2].to_dict()
high = df[df['severity'] == 'high'].iloc[2].to_dict()
medium = df[df['severity'] == 'medium'].iloc[2].to_dict()

test_cases = [
    ("CRITICAL SEVERITY — TEST CASE 1", critical),
    ("HIGH SEVERITY — TEST CASE 2", high),
    ("MEDIUM SEVERITY — TEST CASE 3", medium),
]

results = []

for label, event in test_cases:
    console.print(Rule(f"[bold white]{label}[/bold white]", style="white"))
    result = run_supplypulse(event)  # dataset event = manual scenario: the gate is shown, not enforced
    results.append(result)
    console.print("\n")

console.print(Rule("[bold green]ALL 3 TEST CASES COMPLETE[/bold green]", style="green"))
console.print(f"\n[bold]Summary:[/bold]")
for r in results:
    console.print(
        f"  {r['disrupted_port']} — {r['severity']} — "
        f"{r['decision']} → {r.get('recommended_alternate_port', 'no plan')} — "
        f"{r['total_response_time_seconds']}s"
    )