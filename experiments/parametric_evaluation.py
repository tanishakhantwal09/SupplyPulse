import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rich.console import Console
from rich.table import Table

console = Console()

GRAPH_DIR = "experiments/results/graphs"
os.makedirs(GRAPH_DIR, exist_ok=True)

# ── Setup ─────────────────────────────────────────────────────────────────────
with open("dataset/reference/ports.json") as f:
    ports_ref = json.load(f)
known_ports = {p['name'] for p in ports_ref}

# Synthetic benchmark capacities (vessels) — deliberately larger than the
# per-berth vessel_capacity in ports.json so the sweep reaches N=500.
PORTS = [
    {"name": "Port of New York-New Jersey", "short": "New York", "capacity": 500, "base_delay": 3.1},
    {"name": "Port of Savannah",            "short": "Savannah", "capacity": 350, "base_delay": 1.9},
    {"name": "Port of Houston",             "short": "Houston",  "capacity": 400, "base_delay": 2.4},
]
for p in PORTS:
    assert p["name"] in known_ports, f"{p['name']} missing from ports.json"

ALPHA, BETA = 1.5, 4.0
N_VALUES = np.arange(20, 501, 20)
RHO_LEVELS = [0.60, 0.75, 0.90]
BOUNDARY_DAYS = 5.0
FOCUS_RHO = 0.75  # saturation level shown in Plot 1


def bpr_delay(base_delay, vessels, capacity):
    return base_delay * (1 + ALPHA * (vessels / capacity) ** BETA)


# ── Models ────────────────────────────────────────────────────────────────────
def greedy_delay(n, rho):
    """Brintrup-style: all N vessels go to the first port (New York)."""
    p = PORTS[0]
    current = rho * p["capacity"]
    return bpr_delay(p["base_delay"], current + n, p["capacity"])


def supplypulse_delay(n, rho):
    """Proportional split by available capacity; vessel-weighted mean delay."""
    available = np.array([p["capacity"] * (1 - rho) for p in PORTS])
    shares = available / available.sum()
    total = 0.0
    for p, share in zip(PORTS, shares):
        current = rho * p["capacity"]
        total += share * bpr_delay(p["base_delay"], current + share * n, p["capacity"])
    return total


# ── Sweep ─────────────────────────────────────────────────────────────────────
results = {}
for rho in RHO_LEVELS:
    g = np.array([greedy_delay(n, rho) for n in N_VALUES])
    s = np.array([supplypulse_delay(n, rho) for n in N_VALUES])
    gap = g - s
    idx = np.where(gap > BOUNDARY_DAYS)[0]
    boundary_n = int(N_VALUES[idx[0]]) if len(idx) else None
    results[rho] = {"greedy": g, "sp": s, "gap": gap, "boundary_n": boundary_n}

COST_PER_VESSEL_DAY = 50000
HOUSTON_N = 90


def cost_musd(delay_days, n):
    return delay_days * n * COST_PER_VESSEL_DAY / 1_000_000


table = Table(title="BPR Parametric Sweep — Summary", header_style="bold")
for col in ("rho", "Herd boundary (gap > 5d)", "N=90 Greedy (d)", "N=90 SP (d)",
            "Greedy @ N=500 (d)", "SP @ N=500 (d)", "Max delay diff @ N=500 (d)"):
    table.add_column(col)
summary = {}
for rho, r in results.items():
    g90, s90 = greedy_delay(HOUSTON_N, rho), supplypulse_delay(HOUSTON_N, rho)
    g500, s500 = r["greedy"][-1], r["sp"][-1]
    summary[f"{rho:.2f}"] = {
        "herd_boundary_N": r["boundary_n"],
        "N90": {"greedy_delay_days": g90, "supplypulse_delay_days": s90,
                "delay_diff_days": g90 - s90},
        "N500": {"greedy_delay_days": g500, "supplypulse_delay_days": s500,
                 "delay_diff_days": g500 - s500,
                 "reduction_pct": (1 - s500 / g500) * 100,
                 "cost_saved_musd": cost_musd(g500, 500) - cost_musd(s500, 500)},
        "max_delay_diff_days": float(r["gap"].max()),
    }
    table.add_row(f"{rho:.2f}",
                  f"N = {r['boundary_n']}" if r["boundary_n"] else "not reached",
                  f"{g90:.2f}", f"{s90:.2f}", f"{g500:.1f}", f"{s500:.1f}",
                  f"{g500 - s500:.1f}")
console.print(table)

plt.rcParams.update({
    "font.family": "serif", "font.size": 11, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.3,
    "figure.dpi": 100, "savefig.dpi": 300,
})

# ── Plot 1: divergence curve ──────────────────────────────────────────────────
r = results[FOCUS_RHO]
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.plot(N_VALUES, r["greedy"], color="#c0392b", lw=2.2, marker="o", ms=4,
        label="Greedy Baseline (All vessels → Port of New York)")
ax.plot(N_VALUES, r["sp"], color="#27ae60", lw=2.2, marker="s", ms=4,
        label="SupplyPulse (Proportional BPR Distribution)")
bn = r["boundary_n"]
if bn:
    ax.axvline(bn, color="purple", ls="--", lw=1.6)
    ax.text(bn + 6, ax.get_ylim()[1] * 0.55, f"Herd Effect Boundary\n(N = {bn})",
            color="purple", fontsize=10, va="center")
    mask = N_VALUES >= bn
    ax.fill_between(N_VALUES[mask], r["sp"][mask], r["greedy"][mask],
                    color="#c0392b", alpha=0.18)
ax.set_xlabel("Number of Diverted Vessels (N)")
ax.set_ylabel("BPR Adjusted Delay (Days)")
ax.set_title(f"Gap 1 BPR — Fleet Scalability and Divergence Boundary\n"
             f"(baseline saturation ρ = {FOCUS_RHO:.2f}, α = {ALPHA}, β = {BETA})")
ax.legend(loc="upper left", frameon=True)
fig.tight_layout()
fig.savefig(f"{GRAPH_DIR}/parametric_fig1_divergence_curve.png")
plt.close(fig)

# ── Plot 2: saturation heatmaps ───────────────────────────────────────────────
rho_grid = np.linspace(0.50, 0.95, 10)
G = np.array([[greedy_delay(n, rho) for n in N_VALUES] for rho in rho_grid])
S = np.array([[supplypulse_delay(n, rho) for n in N_VALUES] for rho in rho_grid])
vmax = max(G.max(), S.max())

fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
for ax, data, title in ((axes[0], G, "Greedy Baseline"), (axes[1], S, "SupplyPulse")):
    im = ax.imshow(data, origin="lower", aspect="auto", cmap="YlOrRd", vmin=0, vmax=vmax,
                   extent=[N_VALUES[0], N_VALUES[-1], rho_grid[0], rho_grid[-1]])
    ax.set_title(title)
    ax.set_xlabel("Number of Diverted Vessels (N)")
    ax.grid(False)
axes[0].set_ylabel("Baseline Port Saturation (ρ)")
fig.colorbar(im, ax=axes, label="BPR Adjusted Delay (Days)", shrink=0.9)
fig.suptitle("Port Congestion Phase Space — Greedy vs SupplyPulse")
fig.savefig(f"{GRAPH_DIR}/parametric_fig2_saturation_heatmap.png", bbox_inches="tight")
plt.close(fig)

# ── Plot 3: financial cost ────────────────────────────────────────────────────
def plot_financial_cost(rho=FOCUS_RHO):
    n_fine = np.arange(20, 501, 20)
    g_cost = np.array([cost_musd(greedy_delay(n, rho), n) for n in n_fine])
    s_cost = np.array([cost_musd(supplypulse_delay(n, rho), n) for n in n_fine])

    g90, s90 = greedy_delay(HOUSTON_N, rho), supplypulse_delay(HOUSTON_N, rho)
    gc90, sc90 = cost_musd(g90, HOUSTON_N), cost_musd(s90, HOUSTON_N)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(n_fine, g_cost, color="#c0392b", lw=2.2, marker="o", ms=4, label="Greedy Baseline Cost")
    ax.plot(n_fine, s_cost, color="#27ae60", lw=2.2, marker="s", ms=4, label="SupplyPulse BPR Cost")
    ax.fill_between(n_fine, s_cost, g_cost, color="#e74c3c", alpha=0.15,
                    label="Cost Saved by BPR Routing")
    ax.scatter([HOUSTON_N], [gc90], color="#c0392b", zorder=5)
    ax.scatter([HOUSTON_N], [sc90], color="#27ae60", zorder=5)
    ax.annotate(
        f"Real Houston Case\nGreedy: ${gc90:.1f}m\nSupplyPulse: ${sc90:.1f}m\n"
        f"Saved: ${gc90 - sc90:.1f}m",
        xy=(HOUSTON_N, gc90), xytext=(HOUSTON_N + 60, g_cost.max() * 0.45),
        fontsize=10, va="center",
        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#555555"),
        arrowprops=dict(arrowstyle="->", color="#555555"))
    ax.set_xlabel("Number of Diverted Vessels (N)")
    ax.set_ylabel("Additional Delay Cost (USD Millions)")
    ax.set_title("Financial Cost of Herd Effect vs BPR Routing\n"
                 f"(ρ = {rho:.2f}, ${COST_PER_VESSEL_DAY:,} per vessel-day)")
    ax.legend(loc="upper left", frameon=True)
    fig.tight_layout()
    fig.savefig(f"{GRAPH_DIR}/parametric_fig3_financial_cost.png")
    plt.close(fig)
    return {"rho": rho, "N": n_fine.tolist(), "greedy_cost_musd": g_cost.tolist(),
            "supplypulse_cost_musd": s_cost.tolist(),
            "houston_N90": {"greedy_musd": gc90, "supplypulse_musd": sc90,
                            "saved_musd": gc90 - sc90}}


fig3 = plot_financial_cost()
saved500 = summary[f"{FOCUS_RHO:.2f}"]["N500"]["cost_saved_musd"]
console.print(f"\n[bold]Houston case (N=90, rho={FOCUS_RHO}):[/bold] "
              f"greedy ${fig3['houston_N90']['greedy_musd']:.2f}m, "
              f"SupplyPulse ${fig3['houston_N90']['supplypulse_musd']:.2f}m, "
              f"saved ${fig3['houston_N90']['saved_musd']:.2f}m")
console.print(f"[bold]Total cost saved at N=500 (rho={FOCUS_RHO}):[/bold] ${saved500:.1f}m")

# ── Save JSON ─────────────────────────────────────────────────────────────────
out = {
    "parameters": {"alpha": ALPHA, "beta": BETA, "ports": PORTS, "rho_levels": RHO_LEVELS,
                   "cost_per_vessel_day_usd": COST_PER_VESSEL_DAY,
                   "herd_boundary_threshold_days": BOUNDARY_DAYS},
    "N_values": N_VALUES.tolist(),
    "sweep": {f"{rho:.2f}": {"greedy_delay_days": r["greedy"].tolist(),
                             "supplypulse_delay_days": r["sp"].tolist(),
                             "gap_days": r["gap"].tolist(),
                             "herd_boundary_N": r["boundary_n"]}
              for rho, r in results.items()},
    "summary": summary,
    "financial_cost": fig3,
}
with open("experiments/results/parametric_evaluation.json", "w") as f:
    json.dump(out, f, indent=2)

console.print(f"\n[bold green]Saved plots to {GRAPH_DIR}/[/bold green]")

console.print("\n[bold]Plot files:[/bold]")
for name in ("parametric_fig1_divergence_curve.png", "parametric_fig2_saturation_heatmap.png",
             "parametric_fig3_financial_cost.png"):
    path = f"{GRAPH_DIR}/{name}"
    console.print(f"  {name}: {os.path.getsize(path) / 1024:.1f} KB")
console.print("  results: experiments/results/parametric_evaluation.json")
