import pandas as pd
from agents.langgraph_orchestrator import run_supplypulse
from rich.console import Console
from rich.rule import Rule

console = Console()

print("Loading validation dataset...")
df = pd.read_csv(
    r'C:\Users\tanis\Desktop\Minor project\dataset\final\validation_set_REAL_ONLY.csv',
    low_memory=False
)

print(f"Total real validation events available: {len(df):,}\n")

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
    result = run_supplypulse(event)
    results.append(result)
    console.print("\n")

console.print(Rule("[bold green]ALL 3 TEST CASES COMPLETE[/bold green]", style="green"))
console.print(f"\n[bold]Summary:[/bold]")
for r in results:
    console.print(
        f"  {r['disrupted_port']} — {r['severity']} — "
        f"{r['decision']} → {r['recommended_alternate_port']} — "
        f"{r['total_response_time_seconds']}s"
    )