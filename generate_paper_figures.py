"""
SupplyPulse Research Paper Figures 5-8
Run from project root: python generate_paper_figures.py
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np
import os

os.makedirs("experiments/results/graphs", exist_ok=True)

plt.rcParams.update({'font.family': 'sans-serif', 'font.size': 11, 'axes.titlesize': 13,
    'axes.titleweight': 'bold', 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 150})

NAVY = '#0A1628'; ACCENT = '#2E86AB'; GREEN = '#2EC4B6'
GOLD = '#F4A261'; RED = '#E63946'; GRAY = '#B0C4DE'
PURPLE = '#6A4C93'


def draw_box(ax, cx, cy, w, h, text, facecolor=NAVY, textcolor='white', fontsize=11, fontweight='bold'):
    box = FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.5, edgecolor='white', facecolor=facecolor, zorder=3
    )
    ax.add_patch(box)
    ax.text(cx, cy, text, ha='center', va='center', color=textcolor,
             fontsize=fontsize, fontweight=fontweight, zorder=4, linespacing=1.4)
    return box


def draw_arrow(ax, start, end, color='#888888'):
    arrow = FancyArrowPatch(
        start, end, arrowstyle='-|>', mutation_scale=18,
        linewidth=2, color=color, zorder=2
    )
    ax.add_patch(arrow)


# ══════════════════════════════════════════════════════════════════════════
# FIGURE 5 — System Architecture Diagram
# ══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(12, 10.6))
ax.set_xlim(0, 12)
ax.set_ylim(4.7, 17.4)
ax.axis('off')
fig.suptitle('SupplyPulse System Architecture', fontsize=16, fontweight='bold', y=0.99)

# Box 1
draw_box(ax, 6, 16.5, 9.5, 1.2, "GDELT API\n(Live Events — 15min updates)", facecolor=NAVY, fontsize=12)
draw_arrow(ax, (6, 15.9), (6, 15.1))

# Box 2
draw_box(ax, 6, 14.5, 9.5, 1.2, "Gap 2: Epistemic Confidence Scoring\n(0.35 / 0.60 thresholds)", facecolor=NAVY, fontsize=12)
draw_arrow(ax, (6, 13.9), (6, 13.1))

# Box 3
draw_box(ax, 6, 12.5, 9.5, 1.2, "LangGraph Orchestrator\n(Shared State)", facecolor=NAVY, fontsize=12)
draw_arrow(ax, (6, 11.9), (6, 11.1))

# Fan-out to 4 agent boxes
agent_y = 9.3
agent_centers = [1.6, 4.7, 7.6, 10.4]
agent_widths = [2.6, 3.5, 2.6, 3.3]
agent_labels = [
    "Supervisor\nAgent",
    "Route Optimization\nAgent\n+ Gap 1 BPR\n+ PortWatch AIS",
    "Inventory\nAgent",
    "Financial Auditor\nAgent\n+ Gap 7 EU ETS\nCarbon",
]
for cx, w, label in zip(agent_centers, agent_widths, agent_labels):
    draw_arrow(ax, (6, 11.05), (cx, agent_y + 0.85))
    draw_box(ax, cx, agent_y, w, 1.7, label, facecolor=ACCENT, fontsize=10.5)

# Converge to final box
for cx in agent_centers:
    draw_arrow(ax, (cx, agent_y - 0.85), (6, 6.9))

# Box 4 — Final decision
draw_box(ax, 6, 6.0, 9.8, 1.6, "Final Unified Decision\n+ Gap 3 XAI Attribution JSON",
         facecolor=GREEN, textcolor=NAVY, fontsize=13)

plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig('experiments/results/graphs/fig5_system_architecture.png', bbox_inches='tight', dpi=150)
plt.close()
print('Figure 5 saved')

# ══════════════════════════════════════════════════════════════════════════
# FIGURE 6 — BPR Congestion Curve
# ══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(11, 7))

vc = np.linspace(0, 2.0, 500)
alpha, beta = 1.5, 4.0
multiplier = 1 + alpha * (vc ** beta)

ax.plot(vc, multiplier, color=NAVY, linewidth=2.5, zorder=3, label=r'$1 + 1.5 \times (V/C)^{4}$')
ax.fill_between(vc, 1, multiplier, alpha=0.06, color=NAVY)

points = [
    (0.65, "6 vessels (Medium)\n65% full", '#2ECC71', (-125, -55), 'right'),
    (0.75, "12 vessels (Medium)\n75% full", '#F1C40F', (-20, 55), 'center'),
    (0.98, "40 vessels (High)\n98% full", GOLD, (45, 75), 'left'),
    (1.92, "90 vessels (Critical)\n192% full", RED, (-165, -25), 'right'),
]
for x, label, color, offset, ha in points:
    y = 1 + alpha * (x ** beta)
    ax.scatter([x], [y], color=color, s=140, zorder=5, edgecolor='white', linewidth=1.5)
    y_clamped = min(y, 21.5)
    ax.annotate(
        f"{label}\nmult = {y:.2f}×",
        xy=(x, y_clamped), xytext=offset, textcoords='offset points',
        fontsize=9, fontweight='bold', color=color,
        ha=ha, va='center',
        arrowprops=dict(arrowstyle='-', color=color, lw=1)
    )

ax.axvline(x=1.0, color=RED, linestyle='--', linewidth=2, alpha=0.8, zorder=2)
ax.text(1.04, 2.2, 'Port Capacity\nLimit', color=RED, fontsize=10, fontweight='bold', rotation=0, va='bottom')

ax.set_xlim(0, 2.0)
ax.set_ylim(1, 22)
ax.set_yticks([1, 5, 10, 15, 20])
ax.set_xlabel('Volume / Capacity Ratio (V/C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Congestion Delay Multiplier', fontsize=12, fontweight='bold')
ax.set_title('Gap 1: BPR Maritime Congestion Formula\n' + r'$\alpha=1.5$, $\beta=4.0$ (Maritime-Calibrated)', fontsize=13, fontweight='bold')
ax.set_facecolor('#FAFAFA')
ax.grid(True, alpha=0.25, linestyle=':')

plt.tight_layout()
plt.savefig('experiments/results/graphs/fig6_bpr_congestion_curve.png', bbox_inches='tight', dpi=150)
plt.close()
print('Figure 6 saved')

# ══════════════════════════════════════════════════════════════════════════
# FIGURE 7 — Gap 2 Confidence Scoring Threshold Zones
# ══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 6))

bar_y, bar_h = 0.5, 0.34
zones = [
    (0.0, 0.35, RED, "REJECTED\nAgents NOT activated\n(Crime/Politics/Sports filtered)"),
    (0.35, 0.60, '#F1C40F', "MONITOR & HOLD\nLogged, not acted on"),
    (0.60, 1.0, '#2ECC71', "PROCEED\nFull 4-agent pipeline activated"),
]
for x0, x1, color, label in zones:
    ax.add_patch(Rectangle((x0, bar_y - bar_h / 2), x1 - x0, bar_h,
                            facecolor=color, edgecolor='white', linewidth=2, zorder=2))
    ax.text((x0 + x1) / 2, bar_y, label, ha='center', va='center',
             fontsize=10.5, fontweight='bold', color=NAVY, zorder=3, linespacing=1.5)

# Boundary tick labels
for x in [0.0, 0.35, 0.60, 1.0]:
    ax.plot([x, x], [bar_y - bar_h / 2 - 0.03, bar_y - bar_h / 2], color=NAVY, linewidth=1.5, zorder=4)
    ax.text(x, bar_y - bar_h / 2 - 0.06, f'{x:.2f}', ha='center', va='top', fontsize=10, fontweight='bold')

# Real-example markers
markers = [
    (0.56, 'blue', '--', "Dover anti-migrant protest\nScore: 0.56 → MONITOR", 0.92),
    (0.72, 'green', '-', "Port Felixstowe disruption\nScore: 0.72 → PROCEED", 1.18),
]
for x, color, style, label, ytext in markers:
    ax.axvline(x=x, color=color, linestyle=style, linewidth=2.2, ymin=0.15, ymax=0.85, zorder=5)
    ax.annotate(label, xy=(x, bar_y + bar_h / 2), xytext=(x, ytext),
                ha='center', va='bottom', fontsize=9.5, fontweight='bold', color=color,
                arrowprops=dict(arrowstyle='-', color=color, lw=1.2))

ax.set_xlim(-0.03, 1.03)
ax.set_ylim(0.0, 1.4)
ax.axis('off')
ax.set_title(
    'Gap 2: Epistemic Confidence Scoring\n'
    'Three-Factor Weighted Score (Source 40% + Goldstein 35% + Tone 25%)',
    fontsize=13, fontweight='bold', pad=10
)

plt.tight_layout()
plt.savefig('experiments/results/graphs/fig7_confidence_zones.png', bbox_inches='tight', dpi=150)
plt.close()
print('Figure 7 saved')

# ══════════════════════════════════════════════════════════════════════════
# FIGURE 8 — Agent Pipeline Sequential Flow
# ══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(16, 4.55))
ax.set_xlim(0, 16)
ax.set_ylim(0.45, 5.75)
ax.axis('off')

stages = [
    ("SUPERVISOR\nSituation Assessment\nAgent Delegation\n~3-5s", ACCENT),
    ("ROUTE OPTIMIZATION\nHaversine Distance\nBPR Congestion\nPortWatch AIS\n~2-4s", GREEN),
    ("INVENTORY\nCommodity Exposure\nP1-P4 Priority\nReallocation Plan\n~3-5s", GOLD),
    ("FINANCIAL AUDITOR\n6-Component Cost\nEU ETS Carbon\nPareto Frontier\n~3-6s", RED),
    ("FINAL DECISION\nUnified Output\nXAI Attribution\nAvg: 21.16s", NAVY),
]

n = len(stages)
box_w, box_h = 2.6, 3.4
centers = np.linspace(1.8, 14.2, n)
cy = 3.4

for i, (cx, (label, color)) in enumerate(zip(centers, stages)):
    textcolor = 'white'
    draw_box(ax, cx, cy, box_w, box_h, label, facecolor=color, textcolor=textcolor, fontsize=10.5)
    if i < n - 1:
        draw_arrow(ax, (cx + box_w / 2 + 0.05, cy), (centers[i + 1] - box_w / 2 - 0.05, cy), color='#555555')

ax.text(8, 0.9,
        "LangGraph Shared State passes all outputs forward — each agent reads all previous agents",
        ha='center', va='center', fontsize=11.5, fontweight='bold', color=NAVY,
        bbox=dict(boxstyle='round,pad=0.4', facecolor='#F0F0F0', edgecolor=GRAY))

ax.text(8, 5.55, 'SupplyPulse 4-Agent Sequential Pipeline',
        ha='center', va='center', fontsize=15, fontweight='bold', color='black')

plt.savefig('experiments/results/graphs/fig8_agent_pipeline.png', bbox_inches='tight', dpi=150)
plt.close()
print('Figure 8 saved')

print('\nAll 4 paper figures in: experiments/results/graphs/')
for name in ['fig5_system_architecture.png', 'fig6_bpr_congestion_curve.png',
             'fig7_confidence_zones.png', 'fig8_agent_pipeline.png']:
    path = f'experiments/results/graphs/{name}'
    size = os.path.getsize(path) / 1024
    print(f'  {name} — {size:.0f} KB')
