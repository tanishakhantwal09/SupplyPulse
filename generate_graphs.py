"""
SupplyPulse Research Comparison Graphs
Run from project root: python generate_graphs.py
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import json
import os

os.makedirs("experiments/results/graphs", exist_ok=True)

plt.rcParams.update({'font.family':'sans-serif','font.size':11,'axes.titlesize':13,
    'axes.titleweight':'bold','axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})

NAVY=  '#0A1628'; ACCENT='#2E86AB'; GREEN='#2EC4B6'
GOLD=  '#F4A261'; RED=   '#E63946'; GRAY= '#B0C4DE'

try:
    with open('experiments/results/formal_evaluation.json') as f:
        d = json.load(f)
    m = d.get('metrics', {})
    f1=m.get('f1_rerouting',0.974); avg_rt=m.get('avg_response_time_seconds',21.16)
    cost=m.get('cost_per_analysis_usd',0.0009)
    print("Loaded real results from formal_evaluation.json")
except Exception as e:
    print(f"Using hardcoded results from latest run ({e})")
    f1=0.974; avg_rt=21.16; cost=0.0009

# Chart 1 — F1
fig,ax=plt.subplots(figsize=(10,6))
fig.suptitle('F1 Score: SupplyPulse vs Existing Research\nReal data vs synthetic data comparison',fontsize=13,fontweight='bold')
systems=['Brintrup 2026\n(synthetic)','Our Brintrup\nBaseline\n(real)','SupplyPulse\n(real)']
f1s=[0.977,0.857,f1]; clrs=[GRAY,GOLD,GREEN]
bars=ax.bar(systems,f1s,color=clrs,width=0.45,edgecolor='white',linewidth=2)
for bar,val in zip(bars,f1s):
    ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+0.005,f'{val:.3f}',ha='center',va='bottom',fontweight='bold',fontsize=13)
ax.fill_between([-0.5,2.5],0.962,0.991,alpha=0.08,color=GRAY)
ax.axhline(y=0.962,color=GRAY,linewidth=1,linestyle='--',alpha=0.6)
ax.axhline(y=0.991,color=GRAY,linewidth=1,linestyle='--',alpha=0.6)
ax.text(2.4,0.976,'Brintrup\nrange',fontsize=9,color='gray',ha='right',style='italic')
ax.set_ylim(0.75,1.05); ax.set_ylabel('F1 Score'); ax.set_facecolor('#FAFAFA')
plt.tight_layout()
plt.savefig('experiments/results/graphs/chart1_f1_comparison.png',bbox_inches='tight',dpi=150)
plt.close(); print('Chart 1 saved')

# Chart 2 — Response time
fig,ax=plt.subplots(figsize=(10,6))
fig.suptitle(f'Response Time Comparison (log scale)\nSupplyPulse {avg_rt:.1f}s vs Brintrup 229.8s — 10.9× faster',fontsize=13,fontweight='bold')
sys2=['Manual\nProcess\n(~3 hrs)','Brintrup 2026\n(3.83 min)','SupplyPulse\nAverage','SupplyPulse\nBest Case']
times=[10800,229.8,avg_rt,3.36]; clrs2=[RED,GOLD,GREEN,ACCENT]
bars2=ax.bar(sys2,times,color=clrs2,width=0.45,edgecolor='white',linewidth=2)
for bar,val in zip(bars2,times):
    lbl=f'{val:.0f}s\n({val/60:.1f}min)' if val>100 else f'{val:.2f}s'
    ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()*1.2,lbl,ha='center',va='bottom',fontweight='bold',fontsize=11)
ax.set_yscale('log')
ax.axhline(y=30,color='red',linewidth=2,linestyle='--',alpha=0.7)
ax.text(3.4,38,'30s target',fontsize=10,color='red',ha='right',fontweight='bold')
ax.set_ylabel('Seconds (log scale)'); ax.set_facecolor('#FAFAFA')
plt.tight_layout()
plt.savefig('experiments/results/graphs/chart2_response_time.png',bbox_inches='tight',dpi=150)
plt.close(); print('Chart 2 saved')

# Chart 3 — Carbon
fig,axes=plt.subplots(1,2,figsize=(13,5))
fig.suptitle('Gap 7: EU ETS Carbon Penalty — Cost Existing Papers Ignore\nEU ETS 100% maritime coverage from Jan 2026',fontsize=13,fontweight='bold',y=1.02)
sev=['CRITICAL\n(Houston)','HIGH\n(Colombo)','MEDIUM\n(Savannah)']
co2=[6581.5,3509.9,441.3]; cusd=[462019,246394,30979]; clrs3=[RED,GOLD,ACCENT]
b1=axes[0].bar(sev,co2,color=clrs3,width=0.5,edgecolor='white',linewidth=2)
axes[0].set_title('CO₂ Emissions (tonnes)'); axes[0].set_ylim(0,max(co2)*1.3); axes[0].set_facecolor('#FAFAFA')
for bar,val in zip(b1,co2):
    axes[0].text(bar.get_x()+bar.get_width()/2,bar.get_height()+80,f'{val:,.1f}t',ha='center',va='bottom',fontweight='bold')
b2=axes[1].bar(sev,cusd,color=clrs3,width=0.5,edgecolor='white',linewidth=2)
axes[1].set_title('EU ETS Carbon Penalty (USD)\n@ $70.20/tonne EUA'); axes[1].set_ylim(0,max(cusd)*1.3); axes[1].set_facecolor('#FAFAFA')
for bar,val in zip(b2,cusd):
    axes[1].text(bar.get_x()+bar.get_width()/2,bar.get_height()+5000,f'${val:,.0f}',ha='center',va='bottom',fontweight='bold')
plt.tight_layout()
plt.savefig('experiments/results/graphs/chart3_carbon_penalty.png',bbox_inches='tight',dpi=150)
plt.close(); print('Chart 3 saved')

# Chart 4 — Feature matrix
fig,ax=plt.subplots(figsize=(13,6))
fig.suptitle('Feature Capability Matrix\nSupplyPulse is the only system combining all 6 capabilities',fontsize=13,fontweight='bold')
feats=['Disruption\nDetection','Geographic\nRouting','Inventory\nPlan','Financial\nBreakdown','EU ETS\nCarbon','Live GDELT\nFeed']
br=[1,0,0,0,0,0]; sy=[1,0,0,0,0,0]; sp=[1,1,1,1,1,1]
x=np.arange(len(feats)); w=0.25
ax.bar(x-w,br,w,label='Brintrup 2026',color=GRAY,edgecolor='white',linewidth=1.5)
ax.bar(x,sy,w,label='Synapse 2026',color=GOLD,edgecolor='white',linewidth=1.5)
ax.bar(x+w,sp,w,label='SupplyPulse',color=GREEN,edgecolor='white',linewidth=1.5)
ax.set_xticks(x); ax.set_xticklabels(feats,fontsize=11)
ax.set_ylim(0,1.4); ax.set_yticks([0,1]); ax.set_yticklabels(['No','Yes'],fontsize=12)
ax.legend(fontsize=11,loc='upper right'); ax.set_facecolor('#FAFAFA')
for i,(b,s,p) in enumerate(zip(br,sy,sp)):
    if b==0: ax.text(i-w,0.05,'✗',ha='center',fontsize=14,color=RED,fontweight='bold')
    if s==0: ax.text(i,0.05,'✗',ha='center',fontsize=14,color=RED,fontweight='bold')
    ax.text(i+w,1.05,'✓',ha='center',fontsize=14,color=GREEN,fontweight='bold')
ax.text(0.5,-0.12,f'F1: {f1:.3f}  |  Avg response: {avg_rt:.1f}s  |  Cost: ${cost:.4f}/analysis  |  10.9× faster than Brintrup 2026',
    transform=ax.transAxes,ha='center',fontsize=10,fontweight='bold',color=NAVY)
plt.tight_layout()
plt.savefig('experiments/results/graphs/chart4_feature_matrix.png',bbox_inches='tight',dpi=150)
plt.close(); print('Chart 4 saved')

print('\nAll 4 charts in: experiments/results/graphs/')
for f in sorted(os.listdir('experiments/results/graphs/')):
    size=os.path.getsize(f'experiments/results/graphs/{f}')/1024
    print(f'  {f} — {size:.0f} KB')
